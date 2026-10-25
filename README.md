# anime-mv-art-direction

一份关于「让影像在动手之前就已经成立」的美术指导方法 —— 适用于静止画 MAD、AMV、Vocaloid PV、手书、文字 PV、剧情向剪辑。<br>
An art-direction method for anime music videos — make the film hold together before you touch the timeline.<br>
アニメ MV / PV のための映像設計・アートディレクション — 手を動かす前に、映像が成立している状態をつくる。

> 点开对应语言阅读，其余收起 · Open the language you need, the rest stay collapsed · 使いたい言語だけ開いてください

<details open>
<summary><b>中文</b></summary>

二次元动画 MV / PV 的**视觉企划与美术指导** skill —— 让影像在动手之前就已经成立。

面向静止画 MAD、AMV、Vocaloid / ボカロ PV、V 家手书、文字 PV（リリックビデオ）、剧情向剪辑、原创曲 MV、歌ってみた 封面影像。

它是一个 skill（技能包）—— 一份写给 AI agent 读的方法论文档，外加几个可直接跑的检测脚本。不是软件，不是渲染器，也不是插件。

不绑定任何特定的 agent 或编辑器：凡能读取 `SKILL.md` 的工具都能用；脚本是普通 Python / ffmpeg 命令行，脱离 agent 也能手动执行。

### 它解决什么

专业制作流程（AE 工程、WebGL 引擎、Blender、SD 出图）解决「**怎么渲染出来**」。这个 skill 解决三件它们在结构上无法解决的事：

1. **取舍** —— 可选风格是无限的，成片只有一个。选择发生在动手之前。
2. **一致性** —— 一个决定要能约束后面 60 个决定，否则每镜都「好看」但整片散架。
3. **完成度** —— 创作者卡住通常不是技术不够，是不知道下一步该定什么。

判据只有一条：**规则必须能否决某个具体做法**，否则它只是形容词。

- ❌ 整体偏冷色
- ✅ 环境永远冷调，只有皮肤和光源保留暖色；出现第二种暖色即视为失误

### 核心模型：三次翻译

MV 美术失败几乎都能归到一个原因 —— **情绪没有被翻译成结构**。整个流程就是三次翻译，每一步都必须落到纸面：

```
情绪 / 歌词   →  论点（一句话的视觉机制）
   ↓ 02-concept
论点          →  五条系统规则（色彩·母题·场景·镜头·文字）
   ↓ 03-systems
系统规则      →  时间表（每段每秒的画面与色彩）
   ↓ 04-score
```

### 两种模式

| 模式 | 输入 | 产出 |
|---|---|---|
| **企划（正向）** | 还没动手，只有歌和歌词 | `VISUAL_BIBLE.md` + `color_script.png` + `SHOTLIST.csv` |
| **诊断（逆向）** | 已有成片或 `.aep` 工程 | 带时间码的「保留 / 修 / 砍」建议 |

三件交付物是整个影像的地基：

| 产出 | 回答的问题 | 文件 |
|---|---|---|
| 视觉圣经 | 这支片子**是**什么？（论点 + 五条系统规则） | `docs/VISUAL_BIBLE.md` |
| 色彩脚本 | 色彩**随时间**怎么走？ | `docs/color_script.png` |
| 分镜表 | 每一秒**发生**什么？ | `docs/SHOTLIST.csv` |

### 工作流（P0 → P5）

企划走 P0 → P4，诊断直接跳到 P5。每个阶段都停下来等你确认，不会一次抛一份 40 页企划过来。

| 阶段 | 决定什么 | 参考文件 |
|---|---|---|
| **P0 建档** | 到底在做什么？形式、时长、卡点网格、参考、约束。 | `01-intake.md` |
| **P1 论点** | 一句话：整片运行的视觉机制。 | `02-concept.md` |
| **P2 五条系统** | 色彩 / 母题 / 场景 / 镜头 / 文字 —— 强制单选，每项给 2–3 个选项**并写明代价**。 | `03-color.md`、`03-motif.md`、`04-shot.md`、`05-type.md` |
| **P3 时间表** | 色彩脚本 + 分镜表；卡点到帧的换算。 | `04-shot.md`、`06-craft.md` |
| **P4 自检** | 反模式清单，按 ROI 排序。 | `07-review.md` |
| **P5 逆向诊断** | 硬缺陷 → 切点核对踩拍 → 22 条反模式。 | `08-audit.md`、`09-ae-read.md` |

诊断顺序固定：先跑硬缺陷检测（黑场 / 冻帧 / 闪光 / 闪烁 / 过曝 / 全屏色闪），再从成片逆推真实切点核对拍点，最后按 22 条反模式出带时间码的报告。

### 安装

把整个目录放到你所用的 agent 的 skill 目录下（各家命名不同，通常是 `~/.<tool>/skills/` 或项目内的 `.<tool>/skills/`）：

```bash
# 用户级（所有项目可用）
~/.<tool>/skills/anime-mv-art-direction/

# 或项目级（只在这个项目可用）
<project>/.<tool>/skills/anime-mv-art-direction/
```

不知道放哪儿的话，看该工具文档里 "skills" 一节；只要目录名是 `anime-mv-art-direction`、根下有 `SKILL.md`，就能被识别。

技能加载只看 `SKILL.md`，其余目录都是按需读取的参考资料与脚本。没有 agent 也能用：直接读 `references/` 并按 `scripts/` 里的命令行跑。

### 依赖

**先跑自检，不要假设机器上有这些东西：**

```bash
python scripts/check_env.py
```

| 依赖 | 是否必需 | 说明 |
|---|---|---|
| Python 3.9+ | 必需 | 仅标准库也能做企划与分镜校验 |
| `ffmpeg` / `ffprobe` | 视频类脚本必需 | 抽帧、场景检测、逐帧统计、拼图 |
| `Pillow` | 可选 | 只有 `color_script.py`（画明度曲线）和 `--residue`（逐像素）真正需要；`shot_sheets.py` 没有它会自动改用 ffmpeg 引擎 |
| 中文字体 | 建议 | 缺失时图里的中文变方块（标签内容多为 ASCII，不受影响） |
| After Effects | 可选 | 只有 `ae_dump.jsx` 需要 |

**明确不需要**：numpy、opencv、scipy、librosa、matplotlib。全部检测与统计都用 ffmpeg 原生滤镜 + 标准库实现——少一层依赖就少一类「装不上」。

**没有 ffmpeg 也能用大半功能**：企划、矛盾检测、决策矩阵、反模式评审、分镜表校验全部是纯文本 / stdlib。失去的只是「用数据验证」，不是判断力。

### 脚本

| 脚本 | 作用 | 依赖 |
|---|---|---|
| `check_env.py` | 环境自检：版本、ffmpeg 滤镜、Pillow、字体、AE——并告诉你现在哪些能用 | 无 |
| `color_script.py` | JSON 色卡 → 色彩脚本图（色板 + 去色测试条 + 明度曲线 + 跨度诊断） | Pillow |
| `shotlist_check.py` | 分镜表校验：断点重叠、景别集中、特效堆叠、hold 数、转场预算、歌词可读性 | 无 |
| `mv_probe.py` | 从成片逆推真实切点、亮度曲线、音频包络、踩点核对 | ffmpeg |
| `mv_lint.py` | 逐帧缺陷检测：黑场 / 冻帧 / 闪光 / 闪烁 / 过曝 / 全屏色闪，`--residue` 加抠图残留定位 | ffmpeg（+ Pillow） |
| `shot_sheets.py` | 按镜头取首 / 中 / 尾做接触表，双引擎（Pillow / ffmpeg） | ffmpeg |
| `ae_dump.jsx` | 在 AE 内运行，导出图层 / 关键帧 / 插值 / 效果为 JSON | AE |

典型用法：

```bash
# 企划：色卡 → 色彩脚本图
python scripts/color_script.py assets/color_plan.example.json -o color_script.png

# 企划：分镜表自检
python scripts/shotlist_check.py SHOTLIST.csv --bpm 128 --fps 24

# 诊断：成片硬缺陷
python scripts/mv_lint.py mv.mp4 --bpm 128 -o lint.json

# 诊断：逆推切点 + 核对踩拍
python scripts/mv_probe.py mv.mp4 -o probe.json --shots-csv cuts.csv

# 诊断：按镜头取样拼图
python scripts/shot_sheets.py mv.mp4 --probe probe.json -o review/
```

### 目录结构

```
SKILL.md                 主控：定位、工作流、阶段闸门
README.md                本文件（中文 / English / 日本語）
references/
  00-setup.md            依赖矩阵、安装、常见故障
  00-method.md           方法论：三次翻译、判据、矛盾检测
  01-intake.md           建档：先问什么
  02-concept.md          论点 + 10 型视觉机制模式库
  03-color.md            色彩：明度结构、色相策略、去色测试
  03-motif.md            母题、场景、材质
  04-shot.md             分镜：卡点换算、字段规范、镜头语法
  05-type.md             字体声部、排版
  06-craft.md            技法、转场预算、压缩损失
  07-review.md           20+ 条反模式、自检清单、ROI 排序
  08-audit.md            成片诊断：22 条反模式 → 可观测证据
  09-ae-read.md          AE 工程读取
assets/
  VISUAL_BIBLE.template.md   视觉圣经模板
  shotlist.template.csv      分镜表模板（11 镜样例，可直接跑校验）
  decision-matrix.md         27 行决策矩阵（设计成打印出来手写）
  color_plan.example.json    色彩脚本输入样例
  color_script.example.png   输出效果参考
scripts/                 见上表
```

### 一个设计原则

`assets/decision-matrix.md` 是**设计成打印出来手写**的——27 行，每行选一个主项并写下代价。写字比点头有效，这是这份东西最容易失效的地方。

同理，`check_env.py` 不报「缺失」就完事，而是输出「现在可用的部分」：缺 ffmpeg 时它会明确告诉你，企划、矛盾检测、决策矩阵、反模式评审、分镜表校验**仍然全部可用**。

### 授权提醒

- **字体与音源需自行确认商用授权**，在企划阶段就记进 `VISUAL_BIBLE.md` 的「素材与授权」栏
- 二创请遵守原曲与原作的使用条款；原创角色不要做成既有角色的相似物

### 许可证

代码与文档采用 [MIT License](LICENSE)。这是对**本 skill 本身**的授权，不涉及你用它所创作的 MV、以及 MV 里引用的音乐、字体、图像素材。

</details>

<details>
<summary><b>English</b></summary>

**Visual planning and art direction for anime MV / PV** — the film should already hold together before you touch the timeline.

Built for still-image MAD, AMV, Vocaloid / ボカロ PV, hand-drawn PV (手书), lyric video (文字PV), narrative edits, original-song MVs, and 歌ってみた cover art.

This is a skill package: a methodology document written to be read by an AI agent, plus a handful of detection scripts you can also run by hand. It is **not** a renderer, **not** a plugin, and **not** tied to any particular agent or editor. Anything that can read `SKILL.md` can use it, and the scripts are plain Python / ffmpeg command lines — no agent required.

### What it solves

Your production pipeline (After Effects, WebGL engines, Blender, Stable Diffusion) answers one question: *how do I render this*. This skill answers the three questions that pipelines structurally cannot:

1. **Selection.** Styles are infinite; the finished film is one. That choice happens before you open After Effects.
2. **Consistency.** One decision has to constrain the next sixty — otherwise every shot looks fine and the whole thing collapses.
3. **Finishing.** Creators stall not because their technique is weak, but because they don't know what to decide next.

There is exactly one criterion for a usable rule:

> **A rule must be able to veto a specific move. Otherwise it is just an adjective.**

- ❌ "Overall cool colour palette."
- ✅ "Environment is always cool; only skin and practical light stay warm. A second warm source counts as a defect."

### Core model: three translations

Almost every MV art failure traces to one cause — **emotion was never translated into structure.** The whole process is three translations, each one landing on paper:

```
emotion / lyrics   →  thesis (a one-sentence visual mechanism)
      ↓ 02-concept
thesis             →  five system rules (colour · motif · scene · shot · type)
      ↓ 03-systems
system rules       →  timeline (what happens, and in what colour, every second)
      ↓ 04-score
```

### Two modes

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

### Workflow (P0 → P5)

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

### Install

Drop the whole directory into your agent's skills directory. Naming differs between tools — usually `~/.<tool>/skills/` or `.<tool>/skills/` inside a project:

```bash
# User-level (available in every project)
~/.<tool>/skills/anime-mv-art-direction/

# Or project-level
<project>/.<tool>/skills/anime-mv-art-direction/
```

If you're not sure where that is, look for the "skills" section in your tool's docs. As long as the directory is named `anime-mv-art-direction` and contains `SKILL.md` at its root, it will be picked up.

Only `SKILL.md` is loaded up front; everything else is reference material and scripts, read on demand. **No agent at all?** Read `references/` and run the scripts in `scripts/` directly.

### Requirements

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

### Scripts

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

### Layout

```
SKILL.md                 Main controller: positioning, workflow, stage gates
README.md                This file (中文 / English / 日本語)
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

### One design principle

`assets/decision-matrix.md` is **designed to be printed and filled in by hand** — 27 rows, one primary choice per row, plus the cost you accept. Writing it down works; nodding does not. This is the part most likely to quietly fail.

The same idea shapes `check_env.py`: it doesn't just list what's missing, it reports **what is available right now**. With no ffmpeg it tells you explicitly that planning, contradiction detection, the decision matrix, anti-pattern review and shot-list validation **all still work** — you only lose data-verified checking.

### Rights and licensing notes

- **Fonts and audio need commercial licensing checked by you.** Record it in the "assets and licences" section of `VISUAL_BIBLE.md` at the planning stage, not at upload time.
- Follow the terms of the original song and source work for derivative pieces; do not make original characters resemble existing ones.

### License

Code and documentation are under the [MIT License](LICENSE). That covers **this skill only** — not the MVs you make with it, and not the music, fonts or images you put into them.

</details>

<details>
<summary><b>日本語</b></summary>

アニメ MV / PV の**映像設計・アートディレクション**のための skill —— 手を動かす前に、映像がすでに成立している状態をつくる。

静止画MAD、AMV、ボカロPV、手描きPV（手书）、文字PV（リリックビデオ）、物語系の編集、オリジナル曲MV、歌ってみたのカバー映像向け。

これは skill（スキルパッケージ）です。AI エージェントが読む方法論ドキュメントと、手動でも実行できる検出スクリプト群で構成されています。ソフトでもレンダラーでもプラグインでもありません。

特定のエージェントやエディタに依存しません。`SKILL.md` を読めるツールなら何でも使えます。スクリプトはただの Python / ffmpeg コマンドラインなので、エージェントなしでも動きます。

### 何を解決するのか

制作ツール（After Effects、WebGL エンジン、Blender、Stable Diffusion）は「**どう描くか**」に答えます。この skill は、それらが構造的に答えられない三つに答えます。

1. **取捨選択** —— 表現は無限、完成尺は一本。選択は AE を開く前に終わっている。
2. **一貫性** —— 一つの決定が次の六十を縛れなければ、各カットは綺麗でも作品全体が崩れる。
3. **完成** —— 行き詰まりの原因は技術不足ではなく、次に何を決めるか分からないこと。

ルールは一つだけ。

> **ルールは具体的な手を否決できなければ、それは形容詞にすぎない。**

- ❌ 全体に寒色寄り
- ✅ 環境は常に寒色。肌と光源だけ暖色を残す。二つ目の暖色光源が出たら破綻とみなす

### 中核モデル：三回の翻訳

MV の美術が失敗する原因はほぼ一つ —— **感情が構造に翻訳されていない**。プロセス全体が三回の翻訳で、毎回紙に落とします。

```
感情 / 歌詞    →  テーゼ（一行の視覚メカニズム）
      ↓ 02-concept
テーゼ        →  五つのシステムルール（色彩・モチーフ・場面・カメラ・文字）
      ↓ 03-systems
ルール        →  タイムライン（毎秒の画面と色彩）
      ↓ 04-score
```

### 二つのモード

| モード | 入力 | 出力 |
|---|---|---|
| **企画（順方向）** | まだ何も作っていない。曲と歌詞だけ | `VISUAL_BIBLE.md` + `color_script.png` + `SHOTLIST.csv` |
| **診断（逆方向）** | 完成尺または `.aep` プロジェクト | タイムコード付きの「残す / 直す / 切る」 |

三つの成果物が映像全体の土台になります。

| 成果物 | 答える問い | ファイル |
|---|---|---|
| ビジュアルバイブル | この映像は**何か**（テーゼ＋五つのルール） | `docs/VISUAL_BIBLE.md` |
| カラースクリプト | 色彩が**時間の中で**どう動くか | `docs/color_script.png` |
| 絵コンテ表 | 毎秒**何が起きる**か | `docs/SHOTLIST.csv` |

### ワークフロー（P0 → P5）

企画は P0 → P4、診断は P5 へ直行。各段階で必ず止まり、確認を待ちます。40 ページの企画書を一度に投げることはありません。

| 段階 | 決めること | 参照 |
|---|---|---|
| **P0 採譜・整理** | 何を作るのか。形式、尺、拍のグリッド、参考、制約。 | `01-intake.md` |
| **P1 テーゼ** | 一行で：作品全体を動かす視覚メカニズム。 | `02-concept.md` |
| **P2 五つのシステム** | 色彩 / モチーフ / 場面 / カメラ / 文字 —— 単一選択を強制。各項目 2–3 案と**それぞれのコスト**を明記。 | `03-color.md`、`03-motif.md`、`04-shot.md`、`05-type.md` |
| **P3 タイムライン** | カラースクリプト＋絵コンテ表。拍からフレームへの換算。 | `04-shot.md`、`06-craft.md` |
| **P4 セルフチェック** | アンチパターン一覧、ROI 順。 | `07-review.md` |
| **P5 逆方向診断** | ハード欠陥 → カット点と拍の照合 → 22 のアンチパターン。 | `08-audit.md`、`09-ae-read.md` |

診断の順序は固定です。まずハード欠陥（黒フレーム / フリーズ / フラッシュ / 明滅 / 白飛び / 全画面色フラッシュ）、次に完成尺から実際のカット点を逆算して拍と照合、最後に 22 のアンチパターンでタイムコード付きの指摘を出します。

### インストール

ディレクトリごと、お使いのエージェントの skills ディレクトリに置きます（名称はツールごとに違い、通常は `~/.<tool>/skills/` か、プロジェクト内の `.<tool>/skills/`）。

```bash
# ユーザーレベル（全プロジェクトで有効）
~/.<tool>/skills/anime-mv-art-direction/

# またはプロジェクトレベル
<project>/.<tool>/skills/anime-mv-art-direction/
```

場所が分からない場合は、そのツールのドキュメントの "skills" の節を見てください。ディレクトリ名が `anime-mv-art-direction` で、直下に `SKILL.md` があれば認識されます。

読み込まれるのは `SKILL.md` だけです。他は必要に応じて読む参考資料とスクリプトです。**エージェントなしでも使えます** —— `references/` を読み、`scripts/` のコマンドを直接実行してください。

### 必要環境

**まずセルフチェックを実行してください。入っている前提で進めないこと：**

```bash
python scripts/check_env.py
```

| 依存 | 必須か | 備考 |
|---|---|---|
| Python 3.9+ | 必須 | 標準ライブラリだけでも企画と絵コンテ検証は可能 |
| `ffmpeg` / `ffprobe` | 動画系スクリプトで必須 | フレーム抽出、シーン検出、フレーム統計、コンタクトシート |
| `Pillow` | 任意 | 実際に必要なのは `color_script.py`（明度カーブ）と `--residue`（ピクセル単位）のみ。`shot_sheets.py` は無ければ ffmpeg エンジンに自動で切り替わる |
| CJK フォント | 推奨 | 無いと生成画像の日本語・中国語が豆腐になる（ラベルはほぼ ASCII なので影響なし） |
| After Effects | 任意 | `ae_dump.jsx` のみ |

**明示的に不要**：numpy、opencv、scipy、librosa、matplotlib。検出と統計はすべて ffmpeg ネイティブフィルタ＋標準ライブラリで実装しています。依存が一つ減れば「入らない」というトラブルも一つ減ります。

**ffmpeg が無くても大半は使えます**：企画、矛盾検出、意思決定マトリクス、アンチパターン評価、絵コンテ検証はすべてテキスト / 標準ライブラリのみ。失うのは「データでの検証」だけで、判断力ではありません。

### スクリプト

| スクリプト | 役割 | 依存 |
|---|---|---|
| `check_env.py` | 環境チェック：バージョン、ffmpeg フィルタ、Pillow、フォント、AE —— そして現在使える範囲を表示 | なし |
| `color_script.py` | JSON 色設計 → カラースクリプト画像（スウォッチ＋脱色テスト＋明度カーブ＋レンジの診断） | Pillow |
| `shotlist_check.py` | 絵コンテ検証：端点の重複、画角の偏り、エフェクトの重ね掛け、hold 数、トランジション予算、歌詞の可読性 | なし |
| `mv_probe.py` | 完成尺から実際のカット点、輝度カーブ、音声エンベロープ、拍合わせを逆算 | ffmpeg |
| `mv_lint.py` | フレーム単位の欠陥検出：黒フレーム / フリーズ / フラッシュ / 明滅 / 白飛び / 全画面色フラッシュ。`--residue` でマット残りの位置も特定 | ffmpeg（+ Pillow） |
| `shot_sheets.py` | カットごとに最初 / 中間 / 最後のフレームでコンタクトシート。デュアルエンジン（Pillow / ffmpeg） | ffmpeg |
| `ae_dump.jsx` | AE 内で実行。レイヤー / キーフレーム / 補間 / エフェクトを JSON に書き出す | AE |

典型的な使い方：

```bash
# 企画：色設計 → カラースクリプト画像
python scripts/color_script.py assets/color_plan.example.json -o color_script.png

# 企画：絵コンテ表の検証
python scripts/shotlist_check.py SHOTLIST.csv --bpm 128 --fps 24

# 診断：完成尺のハード欠陥
python scripts/mv_lint.py mv.mp4 --bpm 128 -o lint.json

# 診断：カット点の逆算と拍の照合
python scripts/mv_probe.py mv.mp4 -o probe.json --shots-csv cuts.csv

# 診断：カットごとのコンタクトシート
python scripts/shot_sheets.py mv.mp4 --probe probe.json -o review/
```

### 構成

```
SKILL.md                 メイン制御：位置づけ、ワークフロー、段階ゲート
README.md                本ファイル（中文 / English / 日本語）
references/
  00-setup.md            依存マトリクス、インストール、トラブルシューティング
  00-method.md           方法論：三回の翻訳、判断基準、矛盾検出
  01-intake.md           ヒアリング：最初に何を聞くか
  02-concept.md          テーゼ＋10 種の視覚メカニズム・パターン集
  03-color.md            色彩：明度構造、色相戦略、脱色テスト
  03-motif.md            モチーフ、場面、質感
  04-shot.md             絵コンテ：拍の換算、フィールド仕様、カメラ文法
  05-type.md             文字の声部、レイアウト
  06-craft.md            技法、トランジション予算、圧縮損失
  07-review.md           20 以上のアンチパターン、チェックリスト、ROI 順
  08-audit.md            完成尺診断：22 のアンチパターン → 観測可能な証拠
  09-ae-read.md          AE プロジェクトの読み取り
assets/
  VISUAL_BIBLE.template.md   ビジュアルバイブル雛形
  shotlist.template.csv      絵コンテ表雛形（11 カットの例、そのまま検証可能）
  decision-matrix.md         27 行の意思決定マトリクス（印刷して手書きする前提）
  color_plan.example.json    色設計の入力例
  color_script.example.png   出力例
scripts/                 上の表を参照
```

### 設計上の一つの原則

`assets/decision-matrix.md` は**印刷して手で書き込む前提**で作っています —— 27 行、各行で主案を一つ選び、受け入れるコストを書く。書くことは頷くより効きます。ここが一番静かに壊れる部分です。

`check_env.py` も同じ発想です。「足りないもの」を並べるだけでなく、**いま使える範囲**を出力します。ffmpeg が無い場合でも、企画、矛盾検出、意思決定マトリクス、アンチパターン評価、絵コンテ検証は**すべて使える**と明示します。失うのはデータ検証だけです。

### 権利・ライセンスの注意

- **フォントと音源の商用利用可否はご自身で確認してください。** アップロード時ではなく、企画段階で `VISUAL_BIBLE.md` の「素材とライセンス」欄に記録します。
- 二次創作は原曲・原作の利用条件に従ってください。オリジナルキャラクターを既存キャラクターに似せないこと。

### ライセンス

コードとドキュメントは [MIT License](LICENSE) です。これは**この skill 自体**に対する許諾であり、あなたが本 skill で制作した MV、および MV 内で使用した音楽・フォント・画像素材には及びません。

</details>
