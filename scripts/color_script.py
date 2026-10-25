#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
color_script.py — 把段落色卡渲染成 color script 图（电影色彩脚本条）。

用法:
    python color_script.py color_plan.json -o docs/color_script.png
    python color_script.py color_plan.json --width 2200

输入 JSON:
{
  "title": "残光",
  "bpm": 128,
  "sections": [
    {"name": "Intro", "start": 0, "end": 12.5,
     "colors": ["#0B1020", "#1B2A4A", "#E8B04B"],
     "note": "灰蓝，唯一暖点", "hold": true},
    {"name": "サビ1", "start": 52, "end": 80,
     "colors": ["#1A1030", "#5B2A6E", "#FF6B35"], "turn": true}
  ]
}

字段:
  name    段落名（必填）
  start   开始秒（必填）
  end     结束秒（必填）
  colors  该段色板，1–7 个 hex（必填）
  note    一句话说明（可选）
  hold    是否留白/静止段（可选，画标记）
  turn    是否转折点（可选，画竖线）

输出内容（自上而下）:
  1. 时间标尺
  2. 每段的色板条（按真实时长比例）
  3. 去色测试条（同一色板转灰度 —— 检查明度结构）
  4. 明度曲线（每段平均明度，检查"有没有起伏"）
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("需要 Pillow（出图用）。装：pip install pillow\n"
             "其它依赖检查：python scripts/check_env.py")


# ---------- 颜色工具 ----------

def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"非法颜色: {h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    """相对亮度 0-100（感知加权）。"""
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0 * 100.0


def gray(rgb):
    v = int(round(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]))
    return (v, v, v)


def text_color_for(rgb):
    return (18, 18, 18) if lum(rgb) > 55 else (245, 245, 245)


# ---------- 字体 ----------

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def get_font(size, bold=False):
    if bold:
        cands = [r"C:\Windows\Fonts\msyhbd.ttc"] + FONT_CANDIDATES
    else:
        cands = FONT_CANDIDATES
    for p in cands:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------- 渲染 ----------

def fmt_t(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:04.1f}"


def render(plan, out_path, width=1800):
    sections = plan.get("sections") or []
    if not sections:
        sys.exit("JSON 里没有 sections")

    for i, s in enumerate(sections):
        for k in ("name", "start", "end", "colors"):
            if k not in s:
                sys.exit(f"第 {i+1} 段缺少字段: {k}")
        if not s["colors"]:
            sys.exit(f"第 {i+1} 段 colors 为空")

    sections = sorted(sections, key=lambda s: float(s["start"]))
    t0 = float(sections[0]["start"])
    t1 = max(float(s["end"]) for s in sections)
    total = max(t1 - t0, 0.001)

    W = int(width)
    MARGIN = 44
    HEAD_H = 96
    RULER_H = 30
    PANEL_H = 300
    CHIP_H = 86
    DESAT_H = 46
    CHART_H = 240
    FOOT_H = 56

    H = HEAD_H + RULER_H + PANEL_H + CHIP_H + DESAT_H + 24 + CHART_H + FOOT_H + MARGIN
    BG = (250, 250, 249)
    INK = (32, 32, 34)
    SUB = (130, 130, 136)
    GRID = (222, 222, 224)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    title = plan.get("title", "COLOR SCRIPT")
    bpm = plan.get("bpm")
    f_title = get_font(38, bold=True)
    f_sub = get_font(17)
    f_sec = get_font(20, bold=True)
    f_small = get_font(14)
    f_note = get_font(13)
    f_tc = get_font(15)

    # ---- header ----
    d.text((MARGIN, 26), title, font=f_title, fill=INK)
    meta = []
    if bpm:
        meta.append(f"{bpm} BPM")
    meta.append(f"总长 {fmt_t(total)}")
    meta.append(f"{len(sections)} 段")
    d.text((MARGIN, 68), "   ·   ".join(meta), font=f_sub, fill=SUB)

    # 生成色彩脚本说明
    d.text((W - MARGIN, 30), "COLOR SCRIPT", font=f_small, fill=SUB,
           anchor="ra")
    d.text((W - MARGIN, 52), "上：色板   中：去色   下：明度曲线", font=f_note,
           fill=SUB, anchor="ra")

    plot_x0 = MARGIN
    plot_w = W - MARGIN * 2

    def x_at(t):
        return plot_x0 + (float(t) - t0) / total * plot_w

    # ---- ruler ----
    ry = HEAD_H
    # 每 5 秒或自适应
    step = 5
    while plot_w / (total / step) < 46 and step < 120:
        step *= 2
    t = 0.0
    while t <= total + 0.001:
        x = x_at(t0 + t)
        d.line([(x, ry + 12), (x, ry + 20)], fill=SUB, width=1)
        d.text((x, ry - 4), fmt_t(t), font=f_small, fill=SUB, anchor="ma")
        t += step
    d.line([(plot_x0, ry + 20), (plot_x0 + plot_w, ry + 20)], fill=GRID, width=1)

    # ---- panels ----
    py = HEAD_H + RULER_H
    sec_lums = []
    for s in sections:
        x0 = x_at(s["start"])
        x1 = x_at(s["end"])
        w = max(2.0, x1 - x0)
        cols = [hex_to_rgb(c) for c in s["colors"]]

        # 垂直渐变（首色 → 末色）
        if len(cols) == 1:
            d.rectangle([x0, py, x1, py + PANEL_H], fill=cols[0])
        else:
            for yy in range(PANEL_H):
                f = yy / max(1, PANEL_H - 1)
                seg = f * (len(cols) - 1)
                i = min(int(seg), len(cols) - 2)
                k = seg - i
                c = tuple(int(cols[i][j] * (1 - k) + cols[i + 1][j] * k)
                          for j in range(3))
                d.line([(x0, py + yy), (x1, py + yy)], fill=c)

        # 分段边框
        d.rectangle([x0, py, x1, py + PANEL_H], outline=BG, width=2)

        # 段名
        if w > 34:
            top = cols[len(cols) // 2]
            tc = text_color_for(top)
            label = s["name"]
            if w < 90:
                label = label[:6]
            d.text((x0 + 10, py + 12), label, font=f_sec, fill=tc)
            dur = float(s["end"]) - float(s["start"])
            d.text((x0 + 10, py + 38), f"{dur:.1f}s", font=f_small, fill=tc)

        # hold 标记（右上角小药丸）
        if s.get("hold"):
            hw = 46
            if w > hw + 16:
                hx = x0 + w - hw - 8
                d.rectangle([hx, py + 10, hx + hw, py + 28],
                            fill=(255, 255, 255))
                d.text((hx + hw / 2, py + 19), "HOLD", font=f_note,
                       fill=(20, 20, 20), anchor="mm")
        if s.get("turn"):
            d.line([(x0, py - 8), (x0, py + PANEL_H + 8)], fill=(230, 40, 40), width=3)
            d.text((x0 + 6, py - 26), "TURN", font=f_note, fill=(230, 40, 40))

        # note
        if s.get("note") and w > 110:
            room = max(4, int((w - 18) / 13))
            d.text((x0 + 10, py + PANEL_H - 30),
                   str(s["note"])[:room],
                   font=f_note, fill=text_color_for(cols[-1]))

        # 平均明度
        sec_lums.append((x0, x1, sum(lum(c) for c in cols) / len(cols),
                         s.get("name", "")))

    # ---- chips ----
    cy = py + PANEL_H + 6
    for s in sections:
        x0 = x_at(s["start"])
        x1 = x_at(s["end"])
        cols = [hex_to_rgb(c) for c in s["colors"]]
        n = len(cols)
        cw = max(4.0, (x1 - x0 - 4) / n)
        for i, c in enumerate(cols):
            xx = x0 + i * cw
            d.rectangle([xx, cy, min(xx + cw - 1.5, x1), cy + 26], fill=c)
        # hex
        if x1 - x0 > 150:
            d.text((x0 + 2, cy + 32), "#%02X%02X%02X" % cols[0],
                   font=f_small, fill=SUB)

    # ---- desaturated test strip ----
    dy = cy + CHIP_H
    label = "去色测试（明度结构）"
    tw = d.textlength(label, font=f_note)
    d.rectangle([MARGIN - 2, dy - 20, MARGIN + tw + 2, dy - 2], fill=BG)
    d.text((MARGIN, dy - 18), label, font=f_note, fill=SUB)
    for s in sections:
        x0 = x_at(s["start"])
        x1 = x_at(s["end"])
        cols = [gray(hex_to_rgb(c)) for c in s["colors"]]
        if len(cols) == 1:
            d.rectangle([x0, dy, x1, dy + DESAT_H], fill=cols[0])
        else:
            for yy in range(DESAT_H):
                f = yy / max(1, DESAT_H - 1)
                seg = f * (len(cols) - 1)
                i = min(int(seg), len(cols) - 2)
                k = seg - i
                c = tuple(int(cols[i][j] * (1 - k) + cols[i + 1][j] * k)
                          for j in range(3))
                d.line([(x0, dy + yy), (x1, dy + yy)], fill=c)

    # ---- luminance chart ----
    chy = dy + DESAT_H + 24
    ch_top = chy
    ch_bot = chy + CHART_H
    d.text((MARGIN, chy - 22), "明度曲线（看有没有起伏）", font=f_note, fill=SUB)

    for g in (0, 25, 50, 75, 100):
        yy = ch_bot - g / 100 * CHART_H
        d.line([(plot_x0, yy), (plot_x0 + plot_w, yy)], fill=GRID, width=1)
        d.text((plot_x0 - 6, yy), str(g), font=f_small, fill=SUB, anchor="rm")

    pts = []
    for (x0, x1, L, _) in sec_lums:
        pts.append(((x0 + x1) / 2, ch_bot - L / 100 * CHART_H))

    if len(pts) >= 2:
        # 面积
        poly = [(pts[0][0], ch_bot)] + pts + [(pts[-1][0], ch_bot)]
        d.polygon(poly, fill=(226, 232, 240))
        d.line(pts, fill=(52, 84, 138), width=3, joint="curve")
    for (x, y) in pts:
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(52, 84, 138))

    # 段名标注在曲线下
    for (x0, x1, L, nm) in sec_lums:
        if x1 - x0 > 52:
            d.text(((x0 + x1) / 2, ch_bot + 8), nm[:8], font=f_small,
                   fill=SUB, anchor="ma")

    # ---- footer ----
    fy = H - FOOT_H + 6
    d.line([(MARGIN, fy - 8), (W - MARGIN, fy - 8)], fill=GRID, width=1)
    d.text((MARGIN, fy), "由 anime-mv-art-direction / color_script.py 生成  ·  "
                         "判断标准：打乱段落顺序后若分不出先后，它只是配色方案，不是色彩脚本",
           font=f_note, fill=SUB)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out, sec_lums


def main():
    ap = argparse.ArgumentParser(description="渲染 MV color script")
    ap.add_argument("plan", help="color_plan.json")
    ap.add_argument("-o", "--out", default="color_script.png")
    ap.add_argument("--width", type=int, default=1800)
    a = ap.parse_args()

    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    out, lums = render(plan, a.out, a.width)
    print(f"OK -> {out}")
    # 简单诊断
    vals = [x[2] for x in lums]
    if vals:
        spread = max(vals) - min(vals)
        print(f"明度范围 {min(vals):.0f} – {max(vals):.0f}（跨度 {spread:.0f}）")
        if spread < 25:
            print("提示: 明度跨度 < 25，段落之间会看不出变化。参考 03-color.md §3")

        flat = []
        for i in range(1, len(vals)):
            if abs(vals[i] - vals[i - 1]) < 6:
                flat.append(lums[i][3])
        if flat:
            print("提示: 这些段落与上一段明度几乎相同，切换不会显眼 —— "
                  + "、".join(flat))

        if len(vals) >= 2:
            d0 = abs(vals[-1] - vals[0])
            print(f"首尾明度差 {d0:.0f}"
                  + ("（若走循环型，这个差值就是'回来但已不同'的强度）"
                     if d0 < 30 else ""))


if __name__ == "__main__":
    main()
