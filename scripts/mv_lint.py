#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv_lint.py — 成片逐帧缺陷检测（黑场 / 冻帧 / 闪光 / 闪烁 / 过曝 / 全屏色闪 / 抠图残留定位）

   python mv_lint.py render/mv.mp4 --bpm 128
   python mv_lint.py render/mv.mp4 -o lint.json --strict
   python mv_lint.py render/mv.mp4 --residue            # 追加抠图残留定位（需 Pillow，较慢）

与 mv_probe.py 的分工：
  mv_probe.py  采集「结构」——切点、段落、每秒亮度曲线，给分镜判断用（1 Hz）
  mv_lint.py   检测「缺陷」——逐帧全采样，输出带时间码的问题清单（全帧率）

一次 ffmpeg 遍历取全部数据：signalstats(逐帧统计) + scdet(切点) + blackdetect + freezedetect。
只写只读分析，绝不修改视频。

依赖：ffmpeg（PATH 或环境变量 FFMPEG）+ 标准库。--residue 另需 Pillow。
不需要 numpy / opencv / scipy。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")

# 有限范围 yuv 的亮度跨度（16-235）。PSE 判据里的「10% 亮度变化」按这个算。
LUMA_SPAN = 219.0
FLASH_DY = 0.10 * LUMA_SPAN      # ≈22，单帧亮度跃迁超过它才算一次 transition
FLICKER_LO, FLICKER_HI = 3.0, 20.0
CLIP_Y = 235.0                   # YMAX 到 235 即认为有像素被压死


# ----------------------------------------------------------------------------- 基础
def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-800:])
    return p.stdout.decode("utf-8", "replace")


def probe_meta(path):
    raw = run([FFPROBE, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
               "-show_entries", "format=duration",
               "-of", "json", path])
    d = json.loads(raw)
    st = d["streams"][0]
    num, den = (st.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(d["format"]["duration"])
    return {
        "width": int(st["width"]), "height": int(st["height"]),
        "fps": round(fps, 4), "duration": round(dur, 3),
        "frames": int(dur * fps + 0.5),
    }


def tc(t):
    """秒 → m:ss.ff（分镜表里常用的写法）"""
    if t is None:
        return "—"
    m = int(t // 60)
    return "%d:%05.2f" % (m, t - m * 60)


# ----------------------------------------------------------------------------- 一次遍历
FRAME_RE = re.compile(r"^frame:\s*(\d+)\s+pts:\s*\S+\s+pts_time:\s*([0-9.]+)")
KV_RE = re.compile(r"^lavfi\.([a-z]+)\.([A-Za-z]+)=(-?[0-9.]+)")


def scan_frames(path, dur=None):
    """单次 ffmpeg 遍历。stdout 收逐帧元数据，stderr 收黑场/冻帧区间。"""
    vf = ("signalstats,scdet=threshold=8,metadata=print:file=-,"
          "blackdetect=d=0.06:pix_th=0.10:pic_th=0.98,"
          "freezedetect=n=-65dB:d=0.12")
    cmd = [FFMPEG, "-nostats", "-v", "info", "-i", path, "-an",
           "-vf", vf, "-f", "null", "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-800:])
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")

    frames, cur = [], None
    for line in out.splitlines():
        m = FRAME_RE.match(line)
        if m:
            if cur:
                frames.append(cur)
            cur = {"i": int(m.group(1)), "t": float(m.group(2))}
            continue
        m = KV_RE.match(line)
        if m and cur is not None:
            cur[m.group(2)] = float(m.group(3))
    if cur:
        frames.append(cur)

    blacks = [{"start": float(a), "end": float(b), "dur": float(c)}
              for a, b, c in re.findall(
                  r"black_start:\s*([0-9.]+)\s+black_end:\s*([0-9.]+)\s+black_duration:\s*([0-9.]+)", err)]
    # freezedetect 的 start / duration / end 是三次独立输出，按出现顺序配对
    ev = re.findall(r"freeze_(start|duration|end):\s*([0-9.]+)", err)
    freezes, pend = [], {}
    for kind, val in ev:
        v = float(val)
        if kind == "start":
            pend = {"start": v}
        elif kind == "duration":
            pend["dur"] = v
        else:
            pend["end"] = v
            if "dur" not in pend:
                pend["dur"] = v - pend.get("start", v)
            freezes.append(pend)
            pend = {}
    # freezedetect 在「片子结束时仍处于冻结」的情况下只输出 freeze_start，不给 end。
    # 不补这一段，片尾的冻帧会整个丢掉。
    if pend.get("start") is not None:
        if dur:
            pend.setdefault("end", round(dur, 3))
        pend.setdefault("dur", round(pend.get("end", pend["start"]) - pend["start"], 3))
        if pend.get("dur", 0) > 0:
            freezes.append(pend)
    return frames, blacks, freezes


# ----------------------------------------------------------------------------- 检测
def detect_black(blacks, dur):
    out = []
    for b in blacks:
        s, e, d = b["start"], b["end"], b["dur"]
        if s <= 0.4:
            sev, msg = "info", "片头黑场 %.2fs（淡入起点）" % d
        elif e >= dur - 0.4:
            sev, msg = "warn", "片尾黑场 %.2fs——结尾用淡出收掉，等于没有完成" % d
        elif d >= 0.5:
            sev, msg = "error", "中段黑场 %.2fs @ %s——除非是刻意的 stop，否则是渲染断片" % (d, tc(s))
        else:
            sev, msg = "warn", "短黑场 %.2fs @ %s" % (d, tc(s))
        out.append({"id": "BLACK", "severity": sev, "t0": round(s, 3), "t1": round(e, 3),
                    "msg": msg, "hint": "刻意的画面留白请在分镜表标 hold/black；非刻意则查图层与渲染段"})
    return out


def _covered_by_black(t0, t1, blacks, ratio=0.6):
    """这一段是否基本上就是黑场。纯黑天然也是冻帧，别重复报两条。"""
    span = max(1e-6, t1 - t0)
    for b in blacks:
        ov = max(0.0, min(t1, b["end"]) - max(t0, b["start"]))
        if ov >= ratio * span:
            return True
    return False


def detect_freeze(freezes, bpm, dur, blacks=()):
    out = []
    beat = 60.0 / bpm if bpm else None
    for f in freezes:
        s = f.get("start", 0.0)
        d = f.get("dur", 0.0)
        if d < 0.12:
            continue
        if _covered_by_black(s, s + d, blacks):
            continue      # 已在黑场那条里说过，不重复
        intentional = False
        if beat:
            for k in range(1, 9):                      # 冻帧 ≈ 整数拍 → 大概率是 stop
                if abs(d - k * beat) <= max(0.08, beat * 0.12):
                    intentional = True
                    beats = k
                    break
        if intentional:
            out.append({"id": "FREEZE_BEAT", "severity": "info", "t0": round(s, 3),
                        "t1": round(s + d, 3),
                        "msg": "冻帧 %.2fs @ %s ≈ %d 拍（刻意的 stop）" % (d, tc(s), beats),
                        "hint": "保留。确认它落在段末而不是句中"})
        elif d >= 0.4:
            out.append({"id": "FREEZE_LONG", "severity": "error", "t0": round(s, 3),
                        "t1": round(s + d, 3),
                        "msg": "冻帧 %.2fs @ %s 且不落在拍上——多半是表达式/关键帧失效，不是设计" % (d, tc(s)),
                        "hint": "查该段图层是否有 framerate 依赖、表达式报错或素材丢帧"})
        else:
            out.append({"id": "FREEZE_SHORT", "severity": "warn", "t0": round(s, 3),
                        "t1": round(s + d, 3),
                        "msg": "短冻帧 %.2fs @ %s" % (d, tc(s)),
                        "hint": "若为刻意停顿可忽略；连续出现说明渲染段边界有问题"})
    return out


def cut_times(frames):
    return {f["i"] for f in frames if f.get("score", 0.0) >= 8.0 or f.get("time") is not None
            if f.get("i") is not None and (f.get("score", 0.0) >= 8.0)}


def detect_flash(frames, fps):
    """闪光 = 亮度跳上去又落回原位的**成对反转**，不是单纯的大跳。

    这一点很关键：切镜同样会让帧间亮度猛跳，靠 scene detect 排除行不通
    （scdet 会把闪光的上升沿当成切镜，反而把真闪光排掉）。可靠判据是
    「一次上升后 0.6 秒内出现幅度相近的下降」——切镜不会回弹，闪光会。
    """
    if len(frames) < 4:
        return [], []
    ys = [f.get("YAVG", 0.0) for f in frames]
    ts = [f["t"] for f in frames]
    ev = [(k, ys[k] - ys[k - 1]) for k in range(1, len(ys))
          if abs(ys[k] - ys[k - 1]) >= FLASH_DY]
    pulses, used = [], set()
    for a in range(len(ev)):
        if a in used:
            continue
        k1, d1 = ev[a]
        for b in range(a + 1, len(ev)):
            k2, d2 = ev[b]
            if ts[k2] - ts[k1] > 0.6:
                break
            if d1 * d2 < 0 and abs(d2) >= 0.55 * abs(d1):
                pulses.append({"on": round(ts[k1], 3), "off": round(ts[k2], 3),
                               "dur": round(ts[k2] - ts[k1], 3), "amp": round(d1, 1)})
                used.add(a)
                used.add(b)
                break
    out = []
    worst, worst_at = 0, 0.0
    for p in pulses:
        c = sum(1 for q in pulses if 0.0 <= q["on"] - p["on"] <= 1.0)
        if c > worst:
            worst, worst_at = c, p["on"]
    if worst > 3:
        out.append({"id": "FLASH_PSE", "severity": "error", "t0": round(worst_at, 3),
                    "msg": "%s 起 1 秒内 %d 次全屏闪光（WCAG 2.3.1 上限是每秒 3 次）"
                           % (tc(worst_at), worst),
                    "hint": "降频到每秒 ≤3，或把全屏明暗闪改成局部闪/色相闪——这两者不触发同一阈值"})
    elif worst == 3:
        out.append({"id": "FLASH_AT_LIMIT", "severity": "warn", "t0": round(worst_at, 3),
                    "msg": "%s 起 1 秒内 3 次全屏闪光，正好压在阈值上" % tc(worst_at),
                    "hint": "再加一次就越线；也确认这三次都是有意的"})
    elif pulses:
        out.append({"id": "FLASH_OK", "severity": "info", "t0": pulses[0]["on"],
                    "msg": "全片 %d 次全屏闪光，峰值 %d 次/秒（未超阈值）" % (len(pulses), worst),
                    "hint": "记录备查；若这些闪光不在拍上，属于节奏问题而非安全问题"})
    # 未被配对的单次大跳：多半是切镜。只报最强的一次，避免刷屏
    big = [(k, d) for k, d in ev if (k, d) not in
           {(ev[a][0], ev[a][1]) for a in used}]
    if big:
        k, d = max(big, key=lambda x: abs(x[1]))
        if abs(d) >= 0.30 * LUMA_SPAN:
            out.append({"id": "LUMA_JUMP", "severity": "info", "t0": round(ts[k], 3),
                        "msg": "最大一次性亮度跳变 %+.0f @ %s（无回弹，判为切镜/淡变）"
                               % (d, tc(ts[k])),
                        "hint": "切点是否落拍请用 mv_probe.py 对照 BPM 网格；这里只管是否安全"})
    return out, pulses


def detect_flicker(frames):
    """闪烁：亮度高频小幅振荡（换向 ≥4 次），典型成因是渲染段接缝或表达式抖动。"""
    if len(frames) < 8:
        return []
    ys = [f.get("YAVG", 0.0) for f in frames]
    out, run, sign = [], 0, 0
    start = None
    for k in range(1, len(ys)):
        dy = ys[k] - ys[k - 1]
        if FLICKER_LO <= abs(dy) <= FLICKER_HI:
            s = 1 if dy > 0 else -1
            if sign and s != sign:
                run += 1
                if run == 4 and start is None:
                    start = frames[k]["t"]
            else:
                run = 1
                start = None
            sign = s
        else:
            run, sign, start = 0, 0, None
    if start is not None:
        out.append({"id": "FLICKER", "severity": "warn", "t0": round(start, 3),
                    "msg": "%s 附近亮度高频振荡（±%d 级、连续换向）——画面在「抖」，不像在「动」"
                           % (tc(start), int(FLICKER_HI)),
                    "hint": "典型是并行渲染的段接缝（1/3、2/3 处）或表达式依赖随机数；把这些改成 song-time 纯函数"})
    return out


def detect_exposure(frames, fps):
    out = []
    ys = [f.get("YAVG", 0.0) for f in frames]
    ymax = [f.get("YMAX", 0.0) for f in frames]
    if not ys:
        return out
    # 连续压死白
    run, t0 = 0, None
    for k, v in enumerate(ymax):
        if v >= CLIP_Y:
            if run == 0:
                t0 = frames[k]["t"]
            run += 1
        else:
            if run >= max(3, int(fps * 0.5)):
                out.append({"id": "CLIP_WHITE", "severity": "warn", "t0": round(t0, 3),
                            "t1": round(frames[k]["t"], 3),
                            "msg": "%s 起连续 %.2fs 有像素压到 235（死白，纹理全丢）"
                                   % (tc(t0), frames[k]["t"] - t0),
                            "hint": "降 bloom / glow 或压曝光；白色角色的高光最容易先死"})
            run, t0 = 0, None
    if run >= max(3, int(fps * 0.5)):
        out.append({"id": "CLIP_WHITE", "severity": "warn", "t0": round(t0, 3),
                    "msg": "片尾有 %.2fs 死白" % (frames[-1]["t"] - t0), "hint": "同上"})
    mean = sum(ys) / len(ys)
    if mean >= 200:
        out.append({"id": "OVERALL_BRIGHT", "severity": "warn", "t0": 0,
                    "msg": "全片平均亮度 %.0f/235，整体偏亮——亮片常见问题是歌词与白色角色分不开" % mean,
                    "hint": "参考 03-color.md：高调片要靠「压暗次要区」而不是提亮主体"})
    if mean <= 25:
        out.append({"id": "OVERALL_DARK", "severity": "warn", "t0": 0,
                    "msg": "全片平均亮度 %.0f/235，整体过暗——手机屏与压缩会先吃掉暗部" % mean,
                    "hint": "暗片必须留一个 20% 面积的亮部作为视觉锚点，否则缩到手机尺寸就成一团"})
    return out


def detect_chroma(frames, fps):
    """全屏色闪：饱和红/绿/品红的整帧闪烁。亮度跃迁抓不到它，但 PSE 一样管。"""
    out = []
    red_run, t0 = 0, None
    for f in frames:
        sat, u, v = f.get("SATAVG", 0.0), f.get("UAVG", 128.0), f.get("VAVG", 128.0)
        is_red = sat >= 90 and v >= 150 and u <= 120
        if is_red:
            if red_run == 0:
                t0 = f["t"]
            red_run += 1
        else:
            if red_run >= 2:
                out.append({"id": "RED_FULLFRAME", "severity": "warn", "t0": round(t0, 3),
                            "msg": "%s 起 %.2fs 全屏饱和红" % (tc(t0), red_run / fps),
                            "hint": "饱和红满屏闪烁是光敏风险最高的形式；改成局部红或降低饱和度"})
            red_run, t0 = 0, None
    if red_run >= 2:
        out.append({"id": "RED_FULLFRAME", "severity": "warn", "t0": round(t0, 3),
                    "msg": "片尾 %.2fs 全屏饱和红" % (red_run / fps), "hint": "同上"})
    # 绿色整帧占比异常：可能是色键溢出到全屏
    greens = [f for f in frames if f.get("SATAVG", 0) >= 100 and f.get("UAVG", 128) <= 105
              and f.get("VAVG", 128) <= 108]
    if len(greens) >= max(2, int(fps * 0.3)):
        out.append({"id": "GREEN_DOMINANT", "severity": "info",
                    "t0": round(greens[0]["t"], 3),
                    "msg": "%s 起约 %.2fs 全屏高饱和绿" % (tc(greens[0]["t"]), len(greens) / fps),
                    "hint": "若是设计色可忽略；若是抠图素材没抠干净，用 --residue 定位"})
    return out


# ----------------------------------------------------------------------------- 抠图残留
def detect_residue(path, step, width=320, thin_max=3):
    """成片层面的抠图残留定位器。

    判据：高饱和色键色（绿/品红）像素，且局部「薄」（横或纵向连续厚度 ≤ thin_max）。
    厚实的绿色物体不会被判为残留，只有贴着主体的细边带会。这是定位器不是判决——
    命中帧应该用 shot_sheets.py 抽出来人眼确认。
    """
    try:
        from PIL import Image
    except Exception:
        return [{"id": "RESIDUE_SKIP", "severity": "info", "t0": 0,
                 "msg": "未安装 Pillow，跳过抠图残留定位", "hint": "pip install pillow"}]

    tmp = tempfile.mkdtemp(prefix="lint_res_")
    hits = []
    try:
        outdir = os.path.join(tmp, "f")
        os.makedirs(outdir, exist_ok=True)
        subprocess.run([FFMPEG, "-v", "error", "-i", path, "-an",
                        "-vf", "fps=1/%.3f,scale=%d:-2" % (step, width),
                        "-fps_mode", "passthrough", os.path.join(outdir, "f_%05d.png")],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        names = sorted(os.listdir(outdir))
        for n, name in enumerate(names):
            with Image.open(os.path.join(outdir, name)) as im:
                im = im.convert("RGB")
                W, H = im.size
                px = im.load()
                # 先做便宜的全局统计：没有可疑色就直接跳过这帧
                suspect = 0
                for y in range(H):
                    for x in range(W):
                        r, g, b = px[x, y]
                        if g > r + 60 and g > b + 60 and g > 120:
                            suspect += 1
                        elif r > g + 45 and b > g + 45 and min(r, b) > 90:
                            suspect += 1
                if suspect < W * H * 0.0008:      # <0.08% 不值得做逐点厚度分析
                    continue
                thin = 0
                for y in range(H):
                    for x in range(W):
                        r, g, b = px[x, y]
                        key = (g > r + 60 and g > b + 60 and g > 120) or \
                              (r > g + 45 and b > g + 45 and min(r, b) > 90)
                        if not key:
                            continue
                        # 横向连续厚度
                        hl = 0
                        xx = x - 1
                        while xx >= 0 and hl <= thin_max:
                            rr, gg, bb = px[xx, y]
                            if not ((gg > rr + 60 and gg > bb + 60 and gg > 120) or
                                    (rr > gg + 45 and bb > gg + 45 and min(rr, bb) > 90)):
                                break
                            hl += 1
                            xx -= 1
                        hr = 0
                        xx = x + 1
                        while xx < W and hr <= thin_max:
                            rr, gg, bb = px[xx, y]
                            if not ((gg > rr + 60 and gg > bb + 60 and gg > 120) or
                                    (rr > gg + 45 and bb > gg + 45 and min(rr, bb) > 90)):
                                break
                            hr += 1
                            xx += 1
                        if hl + hr + 1 <= thin_max:
                            thin += 1
                ratio = thin / float(W * H)
                if ratio >= 0.0004:
                    t = n * step
                    hits.append({"id": "RESIDUE", "severity": "warn", "t0": round(t, 3),
                                 "msg": "%s 有细薄色键色边带（占画面 %.3f%%）——疑似抠图残留" % (tc(t), ratio * 100),
                                 "hint": "用 shot_sheets.py 抽该镜确认；这类问题从源素材侧修一次比逐帧修划算"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if len(hits) > 12:
        extra = len(hits) - 12
        hits = hits[:12]
        hits.append({"id": "RESIDUE_MORE", "severity": "info", "t0": 0,
                     "msg": "另有 %d 处同类命中未列出" % extra,
                     "hint": "残留是系统性问题，从素材侧修一次比逐帧修划算"})
    return hits


# ----------------------------------------------------------------------------- 报告
SEV_ORDER = {"error": 0, "warn": 1, "info": 2}
SEV_TAG = {"error": "P0", "warn": "P1", "info": "P2"}


def summary_line(findings):
    n = {k: sum(1 for f in findings if f["severity"] == k) for k in ("error", "warn", "info")}
    if n["error"]:
        v = "有 %d 处必须先修的问题" % n["error"]
    elif n["warn"]:
        v = "%d 处需要确认是否有意" % n["warn"]
    else:
        v = "未发现技术性缺陷"
    return v, n


def main():
    ap = argparse.ArgumentParser(description="成片逐帧缺陷检测（黑场/冻帧/闪光/闪烁/过曝/抠图残留）",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default=None, help="输出 JSON 路径")
    ap.add_argument("--bpm", type=float, default=None, help="BPM；给了就能判断冻帧是不是刻意的 stop")
    ap.add_argument("--residue", action="store_true", help="追加抠图残留定位（需 Pillow，较慢）")
    ap.add_argument("--residue-step", type=float, default=1.5, help="残留抽样间隔秒（默认 1.5）")
    ap.add_argument("--strict", action="store_true", help="有 P0 时退出码 1")
    ap.add_argument("--quiet", action="store_true", help="只输出 JSON，不打人读报告")
    a = ap.parse_args()

    if not shutil.which(FFMPEG):
        sys.exit("找不到 ffmpeg。先跑 python scripts/check_env.py 看缺什么、怎么装；"
                 "或设环境变量 FFMPEG 指向可执行文件。")
    path = a.video
    if not os.path.exists(path):
        sys.exit("文件不存在: %s" % path)

    meta = probe_meta(path)
    frames, blacks, freezes = scan_frames(path, meta["duration"])
    if not frames:
        sys.exit("没取到逐帧数据，可能不是可解码的视频")

    findings = []
    findings += detect_black(blacks, meta["duration"])
    findings += detect_freeze(freezes, a.bpm, meta["duration"], blacks)
    flash, pulses = detect_flash(frames, meta["fps"])
    findings += flash
    findings += detect_flicker(frames)
    findings += detect_exposure(frames, meta["fps"])
    findings += detect_chroma(frames, meta["fps"])
    if a.residue:
        findings += detect_residue(path, a.residue_step)

    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["t0"]))
    verdict, counts = summary_line(findings)

    # 10 Hz 亮度序列，够后续做明度结构对比，又不至于把 JSON 撑爆
    step_i = max(1, int(round(meta["fps"] / 10.0)))
    series = [{"t": round(frames[i]["t"], 2), "y": round(frames[i].get("YAVG", 0.0), 1)}
              for i in range(0, len(frames), step_i)]

    result = {
        "meta": dict(meta, bpm=a.bpm, path=os.path.abspath(path)),
        "counts": {"error": counts["error"], "warn": counts["warn"], "info": counts["info"],
                   "black": len(blacks), "freeze": len(freezes),
                   "scd_hits": sum(1 for f in frames if f.get("score", 0.0) >= 10.0),
                   "flash_pulses": len(pulses)},
        "verdict": verdict,
        "findings": findings,
        "raw": {"black": blacks, "freeze": freezes},
        "luma_10hz": series,
    }

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)

    if not a.quiet:
        print("mv_lint — %s" % os.path.basename(path))
        print("  %d×%d  %.2ffps  %.2fs  %d 帧" % (meta["width"], meta["height"],
                                                  meta["fps"], meta["duration"], meta["frames"]))
        print("  闪光 %d 次 · 黑场 %d 段 · 冻帧 %d 段（切点与落拍率见 mv_probe.py）"
              % (len(pulses), len(blacks), len(freezes)))
        print()
        if not findings:
            print("  ✓ 未发现技术性缺陷")
        for f in findings:
            head = "%s %-14s %s" % (SEV_TAG[f["severity"]], f["id"], tc(f.get("t0")))
            print(head)
            print("    " + f["msg"])
            if f.get("hint"):
                print("    → " + f["hint"])
        print()
        print("结论：%s" % verdict)
        if a.out:
            print("JSON: %s" % a.out)

    if a.strict and counts["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
