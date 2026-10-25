#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shot_sheets.py — 按**镜头**取样拼图（不是按时间等间隔）。

为什么按镜头而不是等间隔：
  等间隔（每 1.5s 一帧）适合"整体过一遍"，但会漏掉短镜头、也看不出单镜内部的运动。
  本脚本按**真实切点**每镜取首/中/尾，适合"逐镜检查它为什么不好看"。
  需要先有镜头表：用 mv_probe.py --shots-csv 生成，或手写。

依赖: ffmpeg 与 ffprobe 必须在 PATH。
      拼图有两个引擎，Pillow 不是必需的：
        --engine pillow  需要 Pillow（pip install pillow）
        --engine ffmpeg  只需要 ffmpeg 的 drawtext/hstack/vstack
        --engine auto    默认，有 Pillow 用 Pillow，没有就自动走 ffmpeg
      先跑 check_env.py 确认缺什么。

用法:
    # 直接用探头结果（推荐）
    python shot_sheets.py mv.mp4 --probe probe.json -o review/

    # 或手给切点
    python shot_sheets.py mv.mp4 --cuts "2.0,4.5,7.0" --duration 10 -o review/

    # 每镜只看中点（更快）
    python shot_sheets.py mv.mp4 --probe probe.json --phases mid -o review/

    # 只看某一段（找问题镜头时用）
    python shot_sheets.py mv.mp4 --probe probe.json --range 30:75 -o review/

输出: <out>/sheet_00.png, sheet_01.png ... 每格标注 镜号 / 时间码 / 时长 / 相位
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except ImportError:  # Pillow 只是可选的绘图引擎，缺失时走 ffmpeg 引擎
    Image = ImageDraw = ImageFont = None
    HAVE_PIL = False

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
PHASES = {"head": 0.12, "mid": 0.5, "tail": 0.88}

# 版式常量：两个引擎共用同一套数值，保证输出外观一致
L_PAD, L_LABEL, L_GAP, L_TITLE = 8, 44, 6, 26
C_BG, C_LINE = 0xF7F7F6, 0xDCDCDE
C_MAIN, C_SUB, C_HEAD = 0x19191B, 0x78787E, 0x1E1E20
C_FAIL = 0x3C3C3E

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc", r"C:\Windows\Fonts\meiryo.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def find_font_file(bold=False):
    """返回可用的字体文件路径（给 ffmpeg 的 drawtext 用）。
    找不到时返回 None —— 标签内容基本是 ASCII（#001 / 0:01.24 / mid），
    drawtext 的默认字体也够用；只有标题里的中文文件名会显示成方块。"""
    cands = ([r"C:\Windows\Fonts\msyhbd.ttc"] if bold else []) + FONT_CANDIDATES
    for p in cands:
        if Path(p).exists():
            return p
    return None


def get_font(size, bold=False):
    if not HAVE_PIL:
        return None
    cands = ([r"C:\Windows\Fonts\msyhbd.ttc"] if bold else []) + FONT_CANDIDATES
    for p in cands:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def tc(t, dec=2):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:05.2f}" if dec == 2 else f"{int(m)}:{int(s):02d}"


def video_size(path):
    out = subprocess.check_output(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)]).decode()
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def grab(path, t, out_png, width):
    """抽单帧。-ss 在 -i 之前：快速定位并重编码，精度足够做缩略图。"""
    cmd = [FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(path),
           "-frames:v", "1", "-vf", f"scale={width}:-2", "-y", str(out_png)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Path(out_png).exists() and Path(out_png).stat().st_size > 0


def load_shots(a):
    if a.probe:
        d = json.loads(Path(a.probe).read_text(encoding="utf-8"))
        shots = [{"no": s["no"], "start": s["start"], "end": s["end"], "dur": s["dur"]}
                 for s in d.get("shots", [])]
        if not shots:
            sys.exit("probe.json 里没有 shots")
        return shots
    if a.cuts:
        pts = [float(x) for x in a.cuts.replace(" ", "").split(",") if x]
        dur = a.duration
        if dur is None:
            dur = float(subprocess.check_output(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(a.video)]).decode().strip())
        b = [0.0] + [p for p in pts if 0 < p < dur] + [dur]
        return [{"no": i + 1, "start": b[i], "end": b[i + 1],
                 "dur": round(b[i + 1] - b[i], 3)} for i in range(len(b) - 1)]
    sys.exit("需要 --probe 或 --cuts")


def ff_quote(p):
    """filter 表达式里的路径：反斜杠改正斜杠、冒号转义、整体单引号包裹。"""
    s = str(p).replace("\\", "/").replace(":", "\\:")
    return "'" + s + "'"


def render_pillow(done, cols, per, tw, th, vname, out_dir):
    """引擎 A：Pillow。逐格 paste + 画文字，坐标由代码算。"""
    f_body, f_title = get_font(13), get_font(15, bold=True)
    cell_w = tw + L_PAD * 2
    cell_h = th + L_LABEL + L_PAD
    sheets = 0
    for start in range(0, len(done), per):
        chunk = done[start:start + per]
        rows = (len(chunk) + cols - 1) // cols
        W = cols * cell_w + L_GAP
        H = rows * cell_h + L_GAP + L_TITLE
        img = Image.new("RGB", (W, H), (247, 247, 246))
        d = ImageDraw.Draw(img)
        d.text((L_PAD, 6), f"{vname}   [{start+1}-{start+len(chunk)}]",
               font=f_title, fill=(30, 30, 32))

        for k, (p, s, ph, t) in enumerate(chunk):
            cx = L_GAP + (k % cols) * cell_w
            cy = L_TITLE + (k // cols) * cell_h
            if p:
                try:
                    img.paste(Image.open(p).convert("RGB"), (cx + L_PAD, cy + L_PAD))
                except Exception:
                    p = None
            if not p:
                d.rectangle([cx + L_PAD, cy + L_PAD, cx + L_PAD + tw, cy + L_PAD + th],
                            fill=(60, 60, 62))
                d.text((cx + L_PAD + 8, cy + L_PAD + 8), "抽帧失败", font=f_body,
                       fill=(230, 230, 230))

            ly = cy + L_PAD + th + 4
            d.text((cx + L_PAD, ly), f"#{s['no']:03d}  {tc(t)}", font=f_title, fill=(25, 25, 27))
            d.text((cx + L_PAD, ly + 17), f"{ph}  {s['dur']:.2f}s", font=f_body,
                   fill=(120, 120, 126))
            d.rectangle([cx, cy, cx + cell_w - L_GAP, cy + cell_h - L_GAP],
                        outline=(220, 220, 222), width=1)

        sp = out_dir / f"sheet_{sheets:02d}.png"
        img.save(sp)
        print(f"  -> {sp}")
        sheets += 1
    return sheets


def render_ffmpeg(done, cols, per, tw, th, vname, out_dir, tmp):
    """引擎 B：ffmpeg 滤镜。每格 pad+drawbox+两行 drawtext，再 hstack/vstack。

    文字走 textfile 而不是 text=，避开 drawtext 的冒号与百分号转义地狱
    （时间码 '#001  0:01.24' 本身就带冒号，放 text= 里必须写成 0\\:01.24）。
    标签内容基本都是 ASCII，所以没有中文字体时也不会变成方块。
    """
    cell_w = tw + L_PAD * 2
    cell_h = th + L_LABEL + L_PAD
    font = find_font_file()
    font_b = find_font_file(bold=True)
    fopt = ("fontfile=" + ff_quote(font) + ":") if font else ""
    fopt_b = ("fontfile=" + ff_quote(font_b) + ":") if font_b else ""
    full_w = cols * cell_w
    sheets = 0

    for start in range(0, len(done), per):
        chunk = done[start:start + per]
        rows = (len(chunk) + cols - 1) // cols
        H = rows * cell_h + L_GAP + L_TITLE

        ins, chains = [], []
        for k, (p, s, ph, t) in enumerate(chunk):
            if p:
                ins += ["-i", str(p)]
            else:  # 抽帧失败的位置用纯色顶替，保持输入序号与 [k:v] 一一对应
                ins += ["-f", "lavfi", "-i", f"color=c=0x{C_FAIL:06X}:s={tw}x{th}"]
            la = tmp / f"t{start+k:04d}a.txt"
            lb = tmp / f"t{start+k:04d}b.txt"
            la.write_text(f"#{s['no']:03d}  {tc(t)}", encoding="utf-8")
            lb.write_text(f"{ph}  {s['dur']:.2f}s", encoding="utf-8")
            chains.append(
                f"[{k}:v]scale={tw}:{th},"
                f"pad={cell_w}:{cell_h}:{L_PAD}:{L_PAD}:0x{C_BG:06X},"
                f"drawbox=x=0:y=0:w={cell_w-L_GAP}:h={cell_h-L_GAP}:"
                f"color=0x{C_LINE:06X}:t=1,"
                f"drawtext={fopt_b}textfile={ff_quote(la)}:"
                f"x={L_PAD}:y={L_PAD+th+4}:fontsize=15:fontcolor=0x{C_MAIN:06X},"
                f"drawtext={fopt}textfile={ff_quote(lb)}:"
                f"x={L_PAD}:y={L_PAD+th+21}:fontsize=13:fontcolor=0x{C_SUB:06X}[t{k}]")

        rl = []
        for r in range(rows):
            idx = [k for k in range(r * cols, min((r + 1) * cols, len(chunk)))]
            fill = f",pad={full_w}:{cell_h}:0:0:0x{C_BG:06X}" if len(idx) < cols else ""
            if len(idx) == 1:
                chains.append(f"[t{idx[0]}]pad={full_w}:{cell_h}:0:0:0x{C_BG:06X}[r{r}]")
            else:
                src = "".join(f"[t{k}]" for k in idx)
                chains.append(f"{src}hstack=inputs={len(idx)}{fill}[r{r}]")
            rl.append(f"[r{r}]")

        stack = (f"{rl[0]}pad={full_w+L_GAP}:{H}:{L_GAP}:{L_TITLE}:0x{C_BG:06X}[tg]"
                 if rows == 1 else
                 f"{''.join(rl)}vstack=inputs={rows},"
                 f"pad={full_w+L_GAP}:{H}:{L_GAP}:{L_TITLE}:0x{C_BG:06X}[tg]")
        chains.append(stack)

        tf = tmp / f"t{start:04d}title.txt"
        tf.write_text(f"{vname}   [{start+1}-{start+len(chunk)}]", encoding="utf-8")
        chains.append(f"[tg]drawtext={fopt_b}textfile={ff_quote(tf)}:x={L_GAP}:y=6:"
                      f"fontsize=15:fontcolor=0x{C_HEAD:06X}[out]")

        script = tmp / f"filter{start:04d}.txt"
        script.write_text(";\n".join(chains), encoding="utf-8")
        sp = out_dir / f"sheet_{sheets:02d}.png"
        cmd = [FFMPEG, "-y", "-v", "error"] + ins + [
            "-filter_complex_script", str(script), "-map", "[out]",
            "-frames:v", "1", str(sp)]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            sys.exit("ffmpeg 拼图失败（可加 --engine pillow 试试）：\n"
                     + r.stderr.decode("utf-8", "replace")[:800])
        print(f"  -> {sp}")
        sheets += 1
    return sheets


def main():
    ap = argparse.ArgumentParser(description="按镜头取样拼图")
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="review")
    ap.add_argument("--probe", default=None, help="mv_probe.py 产出的 probe.json")
    ap.add_argument("--cuts", default=None, help="逗号分隔的切点秒数")
    ap.add_argument("--duration", type=float, default=None, help="配合 --cuts 使用")
    ap.add_argument("--phases", default="head,mid,tail",
                    help="取哪些相位：head,mid,tail 任意组合（默认全取）")
    ap.add_argument("--range", default=None, help="只处理时间段，如 30:75")
    ap.add_argument("--thumb-w", type=int, default=320)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--per-sheet", type=int, default=16)
    ap.add_argument("--engine", choices=["auto", "pillow", "ffmpeg"], default="auto",
                    help="拼图引擎：auto=有 Pillow 就用，没有自动转 ffmpeg（默认）")
    a = ap.parse_args()

    engine = a.engine
    if engine == "auto":
        engine = "pillow" if HAVE_PIL else "ffmpeg"
    if engine == "pillow" and not HAVE_PIL:
        sys.exit("指定了 --engine pillow，但没有 Pillow。\n"
                 "  装：pip install pillow\n"
                 "  或者不装，改用 --engine ffmpeg（只要 ffmpeg 就能出图）")

    if not shutil.which(FFMPEG):
        sys.exit("找不到 ffmpeg。先跑 python scripts/check_env.py 看缺什么、怎么装；"
                 "或设环境变量 FFMPEG 指向可执行文件。")

    v = Path(a.video)
    if not v.exists():
        sys.exit(f"文件不存在: {v}")

    shots = load_shots(a)
    phases = [p.strip() for p in a.phases.split(",") if p.strip() in PHASES]
    if not phases:
        sys.exit("--phases 无效，可选 head,mid,tail")

    if a.range:
        lo, hi = (float(x) for x in a.range.split(":"))
        shots = [s for s in shots if s["start"] < hi and s["end"] > lo]
        if not shots:
            sys.exit("该时间段内没有镜头")

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    vw, vh = video_size(v)
    tw = a.thumb_w
    th = int(round(tw * vh / vw / 2) * 2)

    # 建立任务表
    jobs = []
    for s in shots:
        for ph in phases:
            t = s["start"] + (s["end"] - s["start"]) * PHASES[ph]
            jobs.append((s, ph, round(min(t, s["end"] - 0.01), 3)))

    total = len(jobs)
    print(f"{len(shots)} 镜 × {len(phases)} 相位 = {total} 帧，缩略图 {tw}x{th}")

    tmp = Path(tempfile.mkdtemp(prefix="shots_"))
    frames = []
    try:
        for i, (s, ph, t) in enumerate(jobs):
            p = tmp / f"f{i:04d}.png"
            ok = grab(v, t, p, tw)
            frames.append((p if ok else None, s, ph, t))
            if (i + 1) % 20 == 0 or i == total - 1:
                print(f"  抽帧 {i+1}/{total}")

        per = max(1, min(a.per_sheet, a.cols * a.cols))
        if engine == "ffmpeg":
            print("  引擎: ffmpeg 滤镜")
            sheets = render_ffmpeg(frames, a.cols, per, tw, th, v.name, out_dir, tmp)
        else:
            print("  引擎: Pillow")
            sheets = render_pillow(frames, a.cols, per, tw, th, v.name, out_dir)

        print(f"\n共 {sheets} 张。把图逐张看一遍，对照 references/07-review.md 的 22 条反模式。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
