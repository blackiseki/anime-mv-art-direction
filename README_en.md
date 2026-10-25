# anime-mv-art-direction

**Visual planning and art direction for anime MV / PV** — the film should already hold together before you touch the timeline.

<div align="center">

<a href="https://github.com/blackiseki/anime-mv-art-direction/blob/main/README.md">简体中文</a> ｜
<b>English</b> ｜
<a href="https://github.com/blackiseki/anime-mv-art-direction/blob/main/README_ja.md">日本語</a>

</div>

Built for still-image MAD, AMV, Vocaloid / ボカロ PV, hand-drawn PV (手书), lyric video (文字PV), narrative edits, original-song MVs, and 歌ってみた cover art.

This is a skill package: a methodology document written to be read by an AI agent, plus a handful of detection scripts you can also run by hand. It is **not** a renderer, **not** a plugin, and **not** tied to any particular agent or editor. Anything that can read `SKILL.md` can use it, and the scripts are plain Python / ffmpeg command lines — no agent required.

## What it solves

Your production pipeline (After Effects, WebGL engines, Blender, Stable Diffusion) answers one question: *how do I render this*. This skill answers the three questions that pipelines structurally cannot:

1. **Selection.** Styles are infinite; the finished film is one. That choice happens before you open After Effects.
2. **Consistency.** One decision has to constrain the next sixty — otherwise every shot looks fine and the whole thing collapses.
3. **Finishing.** Creators stall not because their technique is weak, but because they don't know what to decide next.

There is exactly one criterion for a usable rule:

> **A rule must be able to veto a specific move. Otherwise it is just an adjective.**

- ❌ "Overall cool colour palette."
- ✅ "Environment is always cool; only skin and practical light stay warm. A second warm source counts as a defect."

## Core model: three translations

Almost every MV art failure traces to one cause — **emotion was never translated into structure.** The whole process is three translations, each one landing on paper:

```
emotion / lyrics   →  thesis (a one-sentence visual mechanism)
      ↓ 02-concept
thesis             →  five system rules (colour · motif · scene · shot · type)
      ↓ 03-systems
system rules       →  timeline (what happens, and in what colour, every second)
      ↓ 04-score
```

## Two modes

| Mode | Input | Output |
|---|---|---|
| **Plan (forward)** | nothing shot yet — just a song and lyrics | `VISUAL_BIBLE.md` + `color_script.png` + `SHOTLIST.csv` |
| **Audit (reverse)** | a finished cut or an `.aep` project | timestamped notes: keep / fix / cut |

The three deliverables are the foundation of the whole film:

| Deliverable | The question it answers | File |
|---|---|---|
| Visual bible | What **is** this film? (thesis + five system rules) | `docs/VISUAL_BIBLE.md` |
| Colour script | How does colour **move over time**? | `docs/color_script.png` |
| Shot list | What **happens** in each second? | `docs/SHOTLIST.csv` |

## Workflow (P0 → P5)

Planning runs P0 → P4; diagnosis jumps straight to P5. Every gate stops for your confirmation — it will not dump a 40-page plan on you in one shot.

| Stage | What gets decided | Reference |
|---|---|---|
| **P0 Intake** | What are we actually making? Format, length, beat grid, references, constraints. | `01-intake.md` |
| **P1 Thesis** | One sentence: the visual mechanism the whole film runs on. | `02-concept.md` |
| **P2 Five systems** | Colour / motif / scene / shot / type — forced single choice, 2–3 options each, **with the cost of each**. | `03-color.md`, `03-motif.md`, `04-shot.md`, `05-type.md` |
| **P3 Timeline** | Colour script + shot list; beat-to-frame conversion. | `04-shot.md`, `06-craft.md` |
| **P4 Self-check** | Anti-pattern checklist, ROI-ranked. | `07-review.md` |
| **P5 Audit** | Hard defects → cut points vs. beat grid → 22 anti-patterns. | `08-audit.md`, `09-ae-read.md` |

Audit order is fixed: hard-defect detection first (black frames / freezes / flashes / flicker / clipping / full-frame colour flash), then reverse-engineer real cut points against the beat grid, then a timestamped report against 22 anti-patterns.

## Install

Drop the whole directory into your agent's skills directory. Naming differs between tools — usually `~/.<tool>/skills/` or `.<tool>/skills/` inside a project:

```bash
# User-level (available in every project)
~/.<tool>/skills/anime-mv-art-direction/

# Or project-level
<project>/.<tool>/skills/anime-mv-art-direction/
```

If you're not sure where that is, look for the "skills" section in your tool's docs. As long as the directory is named `anime-mv-art-direction` and contains `SKILL.md` at its root, it will be picked up.

Only `SKILL.md` is loaded up front; everything else is reference material and scripts, read on demand. **No agent at all?** Read `references/` and run the scripts in `scripts/` directly.

## Requirements

**Run the self-check first. Do not assume anything is installed:**

```bash
python scripts/check_env.py
```

| Dependency | Needed? | Notes |
|---|---|---|
| Python 3.9+ | Required | Planning and shot-list validation work on the standard library alone |
| `ffmpeg` / `ffprobe` | Required for video scripts | Frame extraction, scene detection, per-frame stats, contact sheets |
| `Pillow` | Optional | Only `color_script.py` (draws the lightness curve) and `--residue` (per-pixel) truly need it; `shot_sheets.py` falls back to an ffmpeg engine |
| A CJK font | Recommended | Without one, CJK text in generated images renders as tofu boxes (labels are mostly ASCII and unaffected) |
| After Effects | Optional | Only `ae_dump.jsx` |

**Explicitly not required:** numpy, opencv, scipy, librosa, matplotlib. All detection and statistics use native ffmpeg filters plus the standard library — one less dependency means one less class of "it won't install".

**Missing ffmpeg is not fatal.** Planning, contradiction detection, the decision matrix, anti-pattern review, and shot-list validation are all pure text / stdlib. What you lose is data-verified checking, not judgement.

## Scripts

| Script | What it does | Needs |
|---|---|---|
| `check_env.py` | Environment self-check: versions, ffmpeg filters, Pillow, fonts, AE — and tells you what still works | — |
| `color_script.py` | JSON colour plan → colour script image (swatches + desaturation strip + lightness curve + span diagnosis) | Pillow |
| `shotlist_check.py` | Shot-list validation: overlapping edges, shot-size clustering, effect stacking, hold counts, transition budget, lyric readability | — |
| `mv_probe.py` | Reverse-engineer real cut points, brightness curve, audio envelope, beat alignment | ffmpeg |
| `mv_lint.py` | Per-frame defect detection: black frames / freezes / flashes / flicker / clipping / full-frame colour flash; `--residue` adds matte-residue localisation | ffmpeg (+ Pillow) |
| `shot_sheets.py` | Contact sheets from the first / middle / last frame of each shot; dual engine (Pillow / ffmpeg) | ffmpeg |
| `ae_dump.jsx` | Run inside AE; exports layers / keyframes / interpolation / effects / type settings as JSON | AE |

Typical usage:

```bash
# Plan: colour plan → colour script image
python scripts/color_script.py assets/color_plan.example.json -o color_script.png

# Plan: validate the shot list
python scripts/shotlist_check.py SHOTLIST.csv --bpm 128 --fps 24

# Audit: hard defects in a finished cut
python scripts/mv_lint.py mv.mp4 --bpm 128 -o lint.json

# Audit: reverse-engineer cut points and check the beat grid
python scripts/mv_probe.py mv.mp4 -o probe.json --shots-csv cuts.csv

# Audit: contact sheets per shot
python scripts/shot_sheets.py mv.mp4 --probe probe.json -o review/
```

## Layout

```
SKILL.md                 Main controller: positioning, workflow, stage gates
README.md                Chinese
README_en.md             English
README_ja.md             日本語
references/
  00-setup.md            Dependency matrix, installation, troubleshooting
  00-method.md           Method: the three translations, criteria, contradiction detection
  01-intake.md           Intake: what to ask first
  02-concept.md          Thesis + a library of 10 visual-mechanism patterns
  03-color.md            Colour: lightness structure, hue strategy, desaturation test
  03-motif.md            Motif, scene, material
  04-shot.md             Shot list: beat mapping, field spec, shot grammar
  05-type.md             Type voices, layout
  06-craft.md            Technique, transition budget, compression loss
  07-review.md           20+ anti-patterns, checklist, ROI ranking
  08-audit.md            Audit: 22 anti-patterns → observable evidence
  09-ae-read.md          Reading an After Effects project
assets/
  VISUAL_BIBLE.template.md   Visual bible template
  shotlist.template.csv      Shot-list template (11-shot sample, validates out of the box)
  decision-matrix.md         27-row decision matrix (designed to be printed and filled in by hand)
  color_plan.example.json    Sample colour-plan input
  color_script.example.png   Sample output
scripts/                 See the table above
```

## One design principle

`assets/decision-matrix.md` is **designed to be printed and filled in by hand** — 27 rows, one primary choice per row, plus the cost you accept. Writing it down works; nodding does not. This is the part most likely to quietly fail.

The same idea shapes `check_env.py`: it doesn't just list what's missing, it reports **what is available right now**. With no ffmpeg it tells you explicitly that planning, contradiction detection, the decision matrix, anti-pattern review and shot-list validation **all still work** — you only lose data-verified checking.

## Rights and licensing notes

- **Fonts and audio need commercial licensing checked by you.** Record it in the "assets and licences" section of `VISUAL_BIBLE.md` at the planning stage, not at upload time.
- Follow the terms of the original song and source work for derivative pieces; do not make original characters resemble existing ones.

## License

Code and documentation are under the [MIT License](LICENSE). That covers **this skill only** — not the MVs you make with it, and not the music, fonts or images you put into them.
