#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shotlist_check.py — 分镜表结构化检查。

用法:
    python shotlist_check.py docs/SHOTLIST.csv --bpm 128 --fps 24
    python shotlist_check.py docs/SHOTLIST.csv --bpm 128 --fps 24 --strict

检查项:
  [错误] 时间断点/重叠、必填字段为空、时长与起止不符
  [警告] 切点不落拍、特效堆叠(>2)、景别过度集中、hold 不足、
         素材复用过低、歌词来不及读、转场超预算、段落缺失

退出码: 0 全过 / 1 有错误 / 2 有警告(仅 --strict 时)
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED = ["no", "start", "end", "dur", "section", "lyric", "shot", "angle",
            "subject", "move", "trans", "beat", "asset"]

SHOT_TYPES = ["ELS", "FS", "MLS", "MS", "MCU", "CU", "ECU"]

# 段落推荐的每镜时长区间（秒），来源 references/04-shot.md §6.3
SECTION_DUR = {
    "intro": (2.0, 8.0),
    "a": (1.5, 4.0), "aメロ": (1.5, 4.0), "a-melo": (1.5, 4.0), "verse": (1.5, 4.0),
    "b": (0.8, 3.0), "bメロ": (0.8, 3.0), "b-melo": (0.8, 3.0), "pre": (0.8, 3.0),
    "サビ": (0.4, 2.0), "chorus": (0.4, 2.0), "副歌": (0.4, 2.0),
    "間奏": (1.5, 8.0), "间奏": (1.5, 8.0), "inter": (1.5, 8.0),
    "cメロ": (2.0, 8.0), "c-melo": (2.0, 8.0), "bridge": (2.0, 8.0),
    "outro": (2.0, 8.0),
}

TEXT_TRANS = 8   # 特殊转场预算（不含 cut / none）


def parse_time(s):
    s = str(s).strip()
    if not s:
        raise ValueError("空时间")
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60 + float(sec)
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3600 + int(m) * 60 + float(sec)
    return float(s)


def sec_key(name):
    n = str(name).strip().lower()
    for k in SECTION_DUR:
        if n.startswith(k):
            return k
    return None


def count_lyric_chars(s):
    """估算歌词字数：CJK 每字算 1，拉丁按词算 1。"""
    s = str(s).strip()
    if s in ("-", "", "nan", "None"):
        return 0
    cjk = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", s))
    latin = len(re.findall(r"[A-Za-z]+", s))
    return cjk + latin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    p = Path(a.csv)
    if not p.exists():
        sys.exit(f"找不到文件: {p}")

    with p.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        sys.exit("CSV 为空")

    errs, warns, infos = [], [], []

    # ---- 字段 ----
    header = list(rows[0].keys())
    missing_cols = [c for c in REQUIRED if c not in header]
    if missing_cols:
        errs.append(f"缺少列: {', '.join(missing_cols)}")

    shots = []
    for i, r in enumerate(rows, start=1):
        try:
            st = parse_time(r.get("start"))
            en = parse_time(r.get("end"))
        except Exception as e:
            errs.append(f"第 {i} 行时间无法解析: {e}")
            continue
        dur = en - st
        shots.append({**r, "_i": i, "_st": st, "_en": en, "_dur": dur})

        for c in REQUIRED:
            v = str(r.get(c, "")).strip()
            if v in ("", "nan", "None") and not (c == "lyric" and v == ""):
                warns.append(f"#{r.get('no', i)} 字段 {c} 为空")
        if dur <= 0:
            errs.append(f"#{r.get('no', i)} 时长 <= 0（{st} -> {en}）")

    shots.sort(key=lambda x: x["_st"])

    # ---- 连续性与重叠 ----
    frame = 1.0 / a.fps
    gaps, overlaps = [], []
    for i in range(1, len(shots)):
        prev, cur = shots[i - 1], shots[i]
        delta = cur["_st"] - prev["_en"]
        if abs(delta) <= frame * 0.6:
            continue
        if delta > 0:
            gaps.append((prev, cur, delta))
        else:
            overlaps.append((prev, cur, -delta))

    for prev, cur, d in gaps:
        (errs if d > 0.1 else warns).append(
            f"时间断点 {d:.3f}s：#{prev.get('no')}({prev['_en']:.2f}) → "
            f"#{cur.get('no')}({cur['_st']:.2f})")
    for prev, cur, d in overlaps:
        errs.append(f"时间重叠 {d:.3f}s：#{prev.get('no')} 与 #{cur.get('no')}")

    total = shots[-1]["_en"] - shots[0]["_st"] if shots else 0

    # ---- 卡点 ----
    beat_ok = 0
    if a.bpm:
        beat = 60.0 / a.bpm
        off = []
        for s in shots:
            rel = (s["_st"] - shots[0]["_st"]) / beat
            dist = abs(rel - round(rel)) * beat
            if dist <= frame * 1.5:
                beat_ok += 1
            else:
                off.append((s, dist))
        ratio = beat_ok / len(shots) * 100
        infos.append(f"切点落拍率 {ratio:.0f}%（{beat_ok}/{len(shots)}）")
        if ratio < 70:
            warns.append(
                f"落拍率偏低（{ratio:.0f}%）。用真实音轨拍点，或切点提前 1–2 帧")
        worst = sorted(off, key=lambda x: -x[1])[:5]
        for s, d in worst:
            if d > beat * 0.5:
                infos.append(
                    f"  #{s.get('no')} 偏离拍点 {d*1000:.0f}ms（{d/beat:.2f} 拍）")

    # ---- 时长 vs 段落建议 ----
    sec_durs = defaultdict(list)
    for s in shots:
        sec_durs[str(s.get("section", "")).strip()].append(s["_dur"])
        k = sec_key(s.get("section", ""))
        if k:
            lo, hi = SECTION_DUR[k]
            if s["_dur"] < lo * 0.55 or s["_dur"] > hi * 1.9:
                warns.append(
                    f"#{s.get('no')} 时长 {s['_dur']:.2f}s 偏离「{s.get('section')}」"
                    f"参考区间 {lo}–{hi}s")

    avg = sum(s["_dur"] for s in shots) / len(shots)

    # ---- 景别分布 ----
    dist = Counter(str(s.get("shot", "")).strip().upper() for s in shots)
    tot = sum(dist.values())
    infos.append("景别分布 " + " / ".join(
        f"{k or '?'} {v/tot*100:.0f}%" for k, v in dist.most_common()))
    ms = dist.get("MS", 0) + dist.get("MCU", 0)
    if ms / tot > 0.55:
        warns.append(f"中景类占 {ms/tot*100:.0f}%，画面会平（建议 <50%）")
    if dist.get("ECU", 0) + dist.get("CU", 0) == 0:
        warns.append("没有任何特写/大特写，情绪没有落点")
    if dist.get("ELS", 0) + dist.get("FS", 0) == 0:
        warns.append("没有远景/全景，缺少空间与呼吸")

    # ---- 特效堆叠 ----
    fx_over = []
    fx_count = 0
    for s in shots:
        fx = str(s.get("fx", "")).strip()
        if fx in ("", "-", "nan"):
            continue
        n = len([x for x in re.split(r"[+,/、，]", fx) if x.strip()])
        fx_count += n
        if n > 2:
            fx_over.append((s, n))
    for s, n in fx_over:
        warns.append(f"#{s.get('no')} 有 {n} 个特效（上限 2）")
    infos.append(f"特效总计 {fx_count} 个，平均 {fx_count/len(shots):.2f}/镜")
    if fx_count / len(shots) > 1.5:
        warns.append("特效密度过高，会遮蔽结构（参考 07-review.md #3）")

    # ---- hold ----
    holds = [s for s in shots if str(s.get("hold", "")).strip().upper().startswith("Y")]
    long_shots = [s for s in shots if s["_dur"] >= 2.5]
    infos.append(f"HOLD 标记 {len(holds)} 个；≥2.5s 长镜 {len(long_shots)} 个")
    if len(holds) < 3 and len(long_shots) < 3:
        warns.append("hold 不足 3 个且长镜不足 3 个，全片会没有呼吸")

    # ---- 素材复用 ----
    assets = Counter(str(s.get("asset", "")).strip() for s in shots)
    reuse = sum(v for k, v in assets.items() if "复用" in k or "reuse" in k.lower())
    ratio = reuse / tot * 100 if tot else 0
    infos.append(f"复用比例 {ratio:.0f}%（{dict(assets.most_common(5))}）")
    if ratio < 40:
        warns.append(f"复用比例 {ratio:.0f}% 偏低，工期风险（建议 ≥40%）")

    # ---- 转场预算 ----
    trans = Counter(str(s.get("trans", "")).strip().lower() for s in shots)
    special = sum(v for k, v in trans.items()
                  if k not in ("cut", "none", "", "-", "nan"))
    infos.append(f"特殊转场 {special} 个（预算 ≤{TEXT_TRANS}）")
    if special > TEXT_TRANS:
        warns.append(f"特殊转场 {special} 个，超过预算 {TEXT_TRANS}，会稀释重音")

    # ---- 歌词可读性 ----
    too_fast = []
    for s in shots:
        n = count_lyric_chars(s.get("lyric", ""))
        if n == 0:
            continue
        need = n / 4.0          # 每秒约 4 字（中日混排保守值）
        if s["_dur"] < need:
            too_fast.append((s, n, need))
    for s, n, need in too_fast:
        warns.append(
            f"#{s.get('no')} 歌词 {n} 字只有 {s['_dur']:.2f}s（需 ≥{need:.1f}s）")
    if len(too_fast) > len([s for s in shots if count_lyric_chars(s.get('lyric', ''))]) * 0.25:
        warns.append("超过 1/4 的歌词镜头读不完（参考 05-type.md §7）")

    # ---- 段落完整性 ----
    secs = [str(s.get("section", "")).strip() for s in shots]
    have = set(secs)
    for must in ("Intro", "Outro"):
        if not any(must.lower() in x.lower() for x in have):
            warns.append(f"没有 {must} 段")

    # ---- 输出 ----
    line = "─" * 62
    print(line)
    print(f"分镜检查  {p.name}")
    print(f"{len(shots)} 镜 / 总长 {total:.2f}s / 平均 {avg:.2f}s/镜"
          + (f" / {a.bpm} BPM" if a.bpm else ""))
    print(line)
    for i in infos:
        print(f"  · {i}")

    if errs:
        print(f"\n错误 {len(errs)}")
        for e in errs:
            print(f"  ✗ {e}")
    if warns:
        print(f"\n警告 {len(warns)}")
        for w in warns:
            print(f"  ! {w}")
    if not errs and not warns:
        print("\n全部通过。")

    print(line)
    if errs:
        return 1
    if warns and a.strict:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
