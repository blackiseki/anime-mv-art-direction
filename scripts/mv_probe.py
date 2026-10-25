#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mv_probe.py — 逆向探针：把一支**已完成的** MV 拆成可判断的数据。

方向说明：
  本脚本走的是**逆向**——从成片反推真实切点，再回头核对它到底有没有踩在拍上。
  所以这里**不做**段落识别、不做 downbeat 检测、不做 impact 检测。
  若你手上已经有拍点数据（beats / downbeats 的 JSON），用 `--audio-json` 直接读入，
  比从音轨粗估准确得多；没有的话给 `--bpm` 用等距网格近似。

产出:
  meta       时长/帧率/分辨率/码率/音轨
  cuts       真实切点（ffmpeg 场景检测）
  shots      由此推出的镜头表（可导出 CSV，供 07-review 用）
  luma       每秒平均亮度（明度结构）
  audio_env  RMS 包络（只看强弱与停顿，不做节拍分析）
  align      切点 vs 拍点 / 强拍的对齐核对

用法:
    # 只要有成片
    python mv_probe.py mv.mp4 -o probe.json --shots-csv cuts.csv

    # 已有拍点 JSON（推荐，最准）
    python mv_probe.py mv.mp4 -o probe.json --audio-json analysis/audio.json

    # 已知 BPM，用网格近似
    python mv_probe.py mv.mp4 -o probe.json --bpm 128

依赖: ffmpeg 与 ffprobe 必须在 PATH（或设环境变量 FFMPEG / FFPROBE）。
      先跑 check_env.py 确认。不需要 numpy / opencv / librosa。
"""

import argparse
import array
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def die(msg):
    sys.exit(f"[mv_probe] {msg}")


def have(tool):
    return shutil.which(tool) is not None


def run(cmd, binary=False):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout if binary else p.stdout.decode("utf-8", "ignore")
    err = p.stderr.decode("utf-8", "ignore")
    return p.returncode, out, err


# ---------- 元数据 ----------

def probe_meta(path):
    rc, out, err = run([FFPROBE, "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", str(path)])
    if rc != 0:
        die(f"ffprobe 失败: {err.strip()[:300]}")
    d = json.loads(out)
    fmt = d.get("format", {})
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        die("没有视频流")

    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    duration = float(fmt.get("duration") or v.get("duration") or 0)

    meta = {
        "duration": round(duration, 3),
        "fps": round(fps, 3),
        "width": v.get("width"),
        "height": v.get("height"),
        "aspect": ("vertical" if (v.get("height") or 0) > (v.get("width") or 0) else "horizontal"),
        "video_codec": v.get("codec_name"),
        "pix_fmt": v.get("pix_fmt"),
        "bitrate_kbps": round(int(fmt.get("bit_rate") or 0) / 1000, 1),
        "audio": None,
    }
    if a:
        meta["audio"] = {"codec": a.get("codec_name"),
                         "sample_rate": a.get("sample_rate"),
                         "channels": a.get("channels")}
    return meta


# ---------- 切点（逆向核心） ----------

def detect_cuts(path, threshold):
    """ffmpeg select=gt(scene,th) + showinfo，从 stderr 解析 pts_time。"""
    vf = f"select='gt(scene\\,{threshold})',showinfo"
    rc, out, err = run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
                        "-filter:v", vf, "-an", "-f", "null", "-"])
    cuts = []
    for m in re.finditer(r"pts_time:([0-9]+\.?[0-9]*)", err + out):
        t = float(m.group(1))
        if not cuts or t - cuts[-1] > 0.08:
            cuts.append(round(t, 3))
    return cuts


def build_shots(cuts, duration):
    b = [0.0] + [c for c in cuts if 0.05 < c < duration - 0.05] + [duration]
    shots = []
    for i in range(len(b) - 1):
        s, e = b[i], b[i + 1]
        if e - s < 0.03:
            continue
        shots.append({"no": len(shots) + 1,
                      "start": round(s, 3), "end": round(e, 3),
                      "dur": round(e - s, 3)})
    return shots


# ---------- 明度 ----------

def luma_curve(path):
    """fps=1 + scale=1:1 + gray → 每秒 1 字节，就是该秒平均亮度。"""
    rc, out, err = run([FFMPEG, "-v", "error", "-i", str(path), "-an",
                        "-vf", "fps=1,scale=1:1", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], binary=True)
    if rc != 0 or not out:
        return []
    return [{"t": float(i), "y": int(b)} for i, b in enumerate(out)]


# ---------- 音频包络（只服务于停顿与强弱，不做节拍分析） ----------

def audio_rms(path, win_ms=100, ar=2000):
    rc, out, err = run([FFMPEG, "-v", "error", "-i", str(path), "-vn",
                        "-ac", "1", "-ar", str(ar), "-f", "s16le", "-"],
                       binary=True)
    if rc != 0 or not out:
        return []
    samples = array.array("h")
    samples.frombytes(out[: len(out) - (len(out) % 2)])
    win = int(ar * win_ms / 1000)
    env, i, n = [], 0, len(samples)
    while i + win <= n:
        seg = samples[i:i + win]
        s = 0
        for x in seg:
            s += x * x
        env.append({"t": round(i / ar, 2), "r": round(math.sqrt(s / win) / 32768.0, 4)})
        i += win
    return env


# ---------- 对齐核对 ----------

def nearest_dist(t, arr):
    best = None
    for b in arr:
        d = abs(b - t)
        if best is None or d < best:
            best = d
    return best if best is not None else 1e9


def align_cuts(cuts, beats, downbeats, fps, source):
    if not cuts or not beats:
        return None
    tol = 1.5 / (fps or 24)
    ok, offs = 0, []
    for c in cuts:
        d = nearest_dist(c, beats)
        if d <= tol:
            ok += 1
        else:
            offs.append({"t": c, "off_ms": round(d * 1000)})
    res = {"source": source, "aligned": ok, "total": len(cuts),
           "ratio": round(ok / len(cuts), 3), "tol_ms": round(tol * 1000),
           "worst": sorted(offs, key=lambda x: -x["off_ms"])[:10]}
    if downbeats:
        dok = sum(1 for c in cuts if nearest_dist(c, downbeats) <= tol)
        res["downbeat_ratio"] = round(dok / len(cuts), 3)
        res["downbeat_hits"] = dok
    return res


def grid_from_bpm(bpm, duration):
    beat = 60.0 / bpm
    beats = [round(i * beat, 3) for i in range(int(duration / beat) + 2)]
    down = [round(i * 4 * beat, 3) for i in range(int(duration / (4 * beat)) + 2)]
    return beats, down


def estimate_bpm(env):
    """兜底估计。能量几乎平（纯音/环境音）时返回 None，避免给出假数字。"""
    if len(env) < 20:
        return None
    vals = [e["r"] for e in env]
    mean = sum(vals) / len(vals)
    if mean <= 1e-6 or (max(vals) - min(vals)) < 0.15 * mean:
        return None
    onset = [0.0] + [max(0.0, vals[i] - vals[i - 1]) for i in range(1, len(vals))]
    mx = max(onset) or 1.0
    onset = [x / mx for x in onset]
    peaks = [env[i]["t"] for i in range(1, len(onset) - 1)
             if onset[i] > 0.25 and onset[i] >= onset[i - 1] and onset[i] >= onset[i + 1]]
    if len(peaks) < 6:
        return None
    gaps = sorted(g for g in (peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1))
                  if 0.2 < g < 2.0)
    if not gaps:
        return None
    bpm = 60.0 / gaps[len(gaps) // 2]
    while bpm < 70:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    return round(bpm, 1)


# ---------- 摘要 ----------

def summarize(meta, shots, luma, env):
    out = {}
    durs = [s["dur"] for s in shots]
    if durs:
        out["shot_count"] = len(shots)
        out["avg_dur"] = round(sum(durs) / len(durs), 2)
        out["min_dur"] = round(min(durs), 2)
        out["max_dur"] = round(max(durs), 2)
        out["cuts_per_min"] = round(len(shots) / (meta["duration"] / 60), 1) if meta["duration"] else None
        out["under_0_4s"] = sum(1 for d in durs if d < 0.4)
        out["over_4s"] = sum(1 for d in durs if d > 4.0)
    if luma:
        ys = [p["y"] for p in luma]
        out["luma_min"], out["luma_max"] = min(ys), max(ys)
        out["luma_spread"] = max(ys) - min(ys)
        out["luma_mean"] = round(sum(ys) / len(ys), 1)
        out["dark_ratio"] = round(sum(1 for y in ys if y < 40) / len(ys), 2)
        out["bright_ratio"] = round(sum(1 for y in ys if y > 200) / len(ys), 2)
    if env:
        rs = [e["r"] for e in env]
        out["rms_mean"] = round(sum(rs) / len(rs), 4)
        thr = out["rms_mean"] * 0.15
        stops, run = [], 0
        for e in env:
            if e["r"] < thr:
                run += 1
            else:
                if run >= 10:
                    stops.append({"t": round(e["t"] - run * 0.1, 2), "len": round(run * 0.1, 1)})
                run = 0
        if run >= 10:
            stops.append({"t": round(env[-1]["t"] - run * 0.1, 2), "len": round(run * 0.1, 1)})
        out["stops"] = stops
    return out


def write_shots_csv(shots, path):
    def tc(t):
        m, sec = divmod(t, 60)
        return f"{int(m)}:{sec:05.2f}"
    lines = ["no,start,end,dur"]
    lines += [f"{s['no']},{tc(s['start'])},{tc(s['end'])},{s['dur']:.2f}" for s in shots]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main():
    ap = argparse.ArgumentParser(description="成片逆向探针")
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="probe.json")
    ap.add_argument("--threshold", type=float, default=0.3,
                    help="场景检测阈值 0-1（默认 0.3；漏检降到 0.2，误检升到 0.4）")
    ap.add_argument("--bpm", type=float, default=None, help="已知 BPM（网格近似）")
    ap.add_argument("--audio-json", default=None,
                    help="已有的拍点 JSON（读 beats / downbeats，比从音轨粗估准得多）")
    ap.add_argument("--shots-csv", default=None)
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()

    if not have(FFMPEG) or not have(FFPROBE):
        die("找不到 ffmpeg / ffprobe。先跑 python scripts/check_env.py 看缺什么、怎么装；"
            "或设环境变量 FFMPEG / FFPROBE 指向可执行文件。")
    v = Path(a.video)
    if not v.exists():
        die(f"文件不存在: {v}")

    print(f"[1/5] 元数据  {v.name}")
    meta = probe_meta(v)
    print(f"      {meta['width']}x{meta['height']} {meta['aspect']}  "
          f"{meta['fps']}fps  {meta['duration']}s  {meta['bitrate_kbps']}kbps")

    print("[2/5] 场景检测（几十秒到几分钟）")
    cuts = detect_cuts(v, a.threshold)
    shots = build_shots(cuts, meta["duration"])
    print(f"      切点 {len(cuts)} → 镜头 {len(shots)}")

    print("[3/5] 明度曲线")
    luma = luma_curve(v)
    print(f"      采样 {len(luma)} 点" if luma else "      跳过")

    env = []
    if meta["audio"] and not a.no_audio:
        print("[4/5] 音频包络（只看强弱/停顿）")
        env = audio_rms(v)
        print(f"      {len(env)} 窗口" if env else "      跳过")
    else:
        print("[4/5] 无音轨")

    print("[5/5] 对齐核对")
    beats, downbeats, source = [], [], None
    if a.audio_json:
        aj = Path(a.audio_json)
        if not aj.exists():
            die(f"--audio-json 不存在: {aj}")
        d = json.loads(aj.read_text(encoding="utf-8"))
        beats = d.get("beats") or []
        downbeats = d.get("downbeats") or []
        source = f"audio.json({aj.name})"
        print(f"      beats {len(beats)} / downbeats {len(downbeats)}")
    elif a.bpm:
        beats, downbeats = grid_from_bpm(a.bpm, meta["duration"])
        source = f"bpm grid {a.bpm}"
    elif env:
        b = estimate_bpm(env)
        if b:
            beats, downbeats = grid_from_bpm(b, meta["duration"])
            source = f"bpm estimate ~{b}（粗糙，仅供量级判断）"
            print(f"      估计 BPM≈{b}")
        else:
            print("      音频无明显节奏，跳过")

    align = align_cuts(cuts, beats, downbeats, meta["fps"], source) if source else None

    result = {
        "file": str(v),
        "meta": meta,
        "cuts": cuts,
        "shots": shots,
        "luma": luma,
        "audio_env": env,
        "align": align,
        "summary": summarize(meta, shots, luma, env),
        "params": {"threshold": a.threshold, "audio_json": a.audio_json,
                   "bpm": a.bpm},
    }
    Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"      -> {a.out}")
    if a.shots_csv:
        write_shots_csv(shots, a.shots_csv)
        print(f"      -> {a.shots_csv}")

    print("\n" + "-" * 56)
    for k, val in result["summary"].items():
        if k == "stops":
            if val:
                print("  停顿: " + "、".join(f"{s['t']}s×{s['len']}s" for s in val))
        else:
            print(f"  {k}: {val}")
    if align:
        print(f"  落拍率: {align['ratio']*100:.0f}% ({align['aligned']}/{align['total']}) "
              f"[{align['source']}]")
        if "downbeat_ratio" in align:
            print(f"  强拍命中: {align['downbeat_ratio']*100:.0f}%")
    print("-" * 56)


if __name__ == "__main__":
    main()
