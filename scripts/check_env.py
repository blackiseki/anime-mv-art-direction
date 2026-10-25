#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_env.py — 环境自检。**在任何分析之前先跑这个**，不要假定机器上有 ffmpeg。

    python scripts/check_env.py

逐项检查本 skill 的脚本所依赖的外部程序，缺什么就打印对应平台的安装方法。
退出码：0 全部就绪；1 缺少必需项（此时只有纯文本部分能用，脚本跑不了）。

为什么要单独做这一步：ffmpeg 不是 Python 自带的东西，很多机器上根本没有；
Pillow 也不是。没有它俩，出图与视频分析全部失效，而报错往往是一句看不懂的
traceback。这里把它变成一句人话。
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata

# 视频相关脚本需要这些 ffmpeg 内置滤镜，缺一个对应检测就失效
NEED_FILTERS = ["blackdetect", "freezedetect", "signalstats", "scdet", "metadata"]
# 出图脚本需要一个能显示中文的字体，否则中文全是方块
CJK_FONTS = [
    (r"C:\Windows\Fonts\msyh.ttc", "微软雅黑"),
    (r"C:\Windows\Fonts\msyhbd.ttc", "微软雅黑 Bold"),
    (r"C:\Windows\Fonts\simhei.ttf", "黑体"),
    (r"C:\Windows\Fonts\YuGothM.ttc", "游ゴシック"),
    (r"C:\Windows\Fonts\meiryo.ttc", "Meiryo"),
    ("/System/Library/Fonts/PingFang.ttc", "苹方"),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", "Hiragino Sans GB"),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "文泉驿正黑"),
]

OK, NG, WARN = "OK", "缺失", "注意"


def _dw(s):
    """显示宽度：中文/全角算 2 列，否则 %-Ns 补空格会错位。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width):
    s = str(s)
    return s + " " * max(0, width - _dw(s))


def _cut(s, width):
    """按显示宽度截断，超出加省略号。"""
    s = str(s)
    if _dw(s) <= width:
        return s
    out, w = "", 0
    for c in s:
        cw = 2 if unicodedata.east_asian_width(c) in "WF" else 1
        if w + cw > width - 1:
            break
        out += c
        w += cw
    return out + "…"


def row(label, value, status):
    print("  %s %s %s" % (_pad(label, 14), _pad(_cut(value, 34), 34), status))


def row2(label, status):
    print("  %s %s" % (_pad(label, 40), status))


def _run(cmd):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def check_python():
    v = sys.version_info
    good = (v.major, v.minor) >= (3, 9)
    return ("%d.%d.%d" % (v.major, v.minor, v.micro)), (OK if good else NG), good


def check_tool(name, args=("-version",)):
    path = shutil.which(name)
    if not path:
        return None, None, NG, False
    out = _run([path] + list(args))
    m = re.search(r"version\s+(\S+)", out, re.I)
    ver = m.group(1).rstrip(",") if m else "未知版本"
    return path, ver, OK, True


def check_filters(ffmpeg_path):
    if not ffmpeg_path:
        return [], list(NEED_FILTERS), False
    out = _run([ffmpeg_path, "-hide_banner", "-filters"])
    have = []
    for name in NEED_FILTERS:
        if re.search(r"^\s*\S{3}\s+%s\s" % re.escape(name), out, re.M):
            have.append(name)
    missing = [n for n in NEED_FILTERS if n not in have]
    return have, missing, not missing


def check_pillow():
    try:
        import PIL
        return PIL.__version__, OK, True
    except Exception:
        return None, NG, False


def check_font():
    for p, label in CJK_FONTS:
        if os.path.exists(p):
            return label, OK, True
    return None, WARN, False


def check_ae():
    """AE 只对 ae_dump.jsx 有用，且只在 Windows 上存在。可选。"""
    if platform.system() != "Windows":
        return None, "不适用", None
    cands = [
        r"G:\AE\Adobe After Effects 2026\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2025\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2024\Support Files\AfterFX.exe",
    ]
    for p in cands:
        if os.path.exists(p):
            return p, OK, True
    return None, "未找到", None


def install_hint(system, need_ff=True, need_pil=True):
    """只列出真正缺的那几项——把没缺的也列出来会让人以为环境坏得更严重。"""
    lines = []
    if need_ff:
        if system == "Windows":
            lines += [
                "  ffmpeg : winget install Gyan.FFmpeg      （装完重开终端）",
                "          或 scoop install ffmpeg",
                "           手动：https://www.gyan.dev/ffmpeg/builds/ 解压后把 bin 目录加进 PATH",
            ]
        elif system == "Darwin":
            lines.append("  ffmpeg : brew install ffmpeg")
        else:
            lines += [
                "  ffmpeg : sudo apt install ffmpeg   （Debian/Ubuntu）",
                "           sudo dnf install ffmpeg   （Fedora）",
                "           sudo pacman -S ffmpeg     （Arch）",
            ]
    if need_pil:
        cmd = ("python -m pip install pillow" if system == "Windows"
               else "python3 -m pip install pillow")
        lines.append("  Pillow : " + cmd)
    return "\n".join(lines)


def main():
    system = platform.system()
    print("anime-mv-art-direction — 环境自检")
    print("  平台 %s / %s" % (system, platform.machine()))
    print()

    py_ver, py_st, py_ok = check_python()
    row("Python", py_ver + "（需 3.9+）", py_st)

    ff_path, ff_ver, ff_st, ff_ok = check_tool("ffmpeg")
    row("ffmpeg", ff_ver if ff_ok else "未安装", ff_st)

    fp_path, fp_ver, fp_st, fp_ok = check_tool("ffprobe")
    row("ffprobe", fp_ver if fp_ok else "未安装", fp_st)

    have, missing, filt_ok = check_filters(ff_path)
    if ff_ok:
        row("ffmpeg 滤镜", "全部可用" if filt_ok else "缺 " + ",".join(missing),
            OK if filt_ok else NG)
    else:
        row("ffmpeg 滤镜", "无法检查", NG)

    pil_ver, pil_st, pil_ok = check_pillow()
    row("Pillow", pil_ver or "未安装", pil_st)

    font_label, font_st, font_ok = check_font()
    row("中文字体", font_label or "未找到", font_st)

    ae_path, ae_st, ae_ok = check_ae()
    if ae_st != "不适用":
        row("After Effects", ae_st if not ae_ok else ae_path, ae_st)

    print()

    # 分档结论：哪些脚本现在能用
    text_ok = py_ok
    video_ok = ff_ok and fp_ok and filt_ok
    image_ok = pil_ok

    print("  现在可用的部分：")
    row2("纯文本（企划/决策矩阵/反模式评审）", "可用" if text_ok else "不可用")
    row2("shotlist_check.py（只读 CSV）", "可用" if text_ok else "不可用")
    row2("mv_lint / mv_probe", "可用" if video_ok else "缺 ffmpeg")
    if not video_ok:
        row2("shot_sheets.py（接触表）", "缺 ffmpeg")
    else:
        row2("shot_sheets.py（接触表）",
             "Pillow 引擎" if image_ok else "ffmpeg 引擎（未装 Pillow，自动降级）")
    row2("color_script 出图", "可用" if (image_ok and font_ok)
         else ("缺 Pillow" if not image_ok else "缺中文字体"))
    row2("mv_lint --residue（残留定位）", "可用" if (video_ok and image_ok) else "缺 Pillow 或 ffmpeg")
    row2("ae_dump.jsx（读 .aep，可选）", "可用" if ae_ok else "需要 AE")
    print()

    bad = []
    if not py_ok:
        bad.append("Python 版本过低（需 3.9+）")
    if not ff_ok or not fp_ok:
        bad.append("缺 ffmpeg / ffprobe")
    if ff_ok and not filt_ok:
        bad.append("ffmpeg 版本过旧，缺滤镜：" + ",".join(missing))
    if not pil_ok:
        bad.append("缺 Pillow（只影响 color_script 出图与 --residue；"
                   "shot_sheets 会自动改用 ffmpeg 引擎）")
    if not font_ok:
        bad.append("缺中文字体（只影响出图，不影响分析）")

    if bad:
        print("  需要处理：")
        for b in bad:
            print("    - " + b)
        print()
        need_ff = (not ff_ok) or (not fp_ok) or (ff_ok and not filt_ok)
        print("  安装方法（%s）：" % system)
        print(install_hint(system, need_ff=need_ff, need_pil=not pil_ok))
        print()
        print("  装好后重开终端，再跑一次本脚本确认。")
        # 缺字体、缺 Pillow 都只是部分能力受限，不算致命
        fatal = bool([b for b in bad if "字体" not in b and "Pillow" not in b])
        sys.exit(1 if fatal else 0)

    print("  结论：所需环境齐全，所有脚本可用。")


if __name__ == "__main__":
    main()
