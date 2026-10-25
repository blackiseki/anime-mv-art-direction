# anime-mv-art-direction

二次元动画 MV / PV 的**视觉企划与美术指导** skill —— 让影像在动手之前就已经成立。

<div align="center">

<b>简体中文</b> ｜
<a href="https://github.com/blackiseki/anime-mv-art-direction/blob/main/README_en.md">English</a> ｜
<a href="https://github.com/blackiseki/anime-mv-art-direction/blob/main/README_ja.md">日本語</a>

</div>

面向静止画 MAD、AMV、Vocaloid / ボカロ PV、V 家手书、文字 PV（リリックビデオ）、剧情向剪辑、原创曲 MV、歌ってみた 封面影像。

它是一个 skill（技能包）—— 一份写给 AI agent 读的方法论文档，外加几个可直接跑的检测脚本。不是软件，不是渲染器，也不是插件。

不绑定任何特定的 agent 或编辑器：凡能读取 `SKILL.md` 的工具都能用；脚本是普通 Python / ffmpeg 命令行，脱离 agent 也能手动执行。

## 它解决什么

专业制作流程（AE 工程、WebGL 引擎、Blender、SD 出图）解决「**怎么渲染出来**」。这个 skill 解决三件它们在结构上无法解决的事：

1. **取舍** —— 可选风格是无限的，成片只有一个。选择发生在动手之前。
2. **一致性** —— 一个决定要能约束后面 60 个决定，否则每镜都「好看」但整片散架。
3. **完成度** —— 创作者卡住通常不是技术不够，是不知道下一步该定什么。

判据只有一条：**规则必须能否决某个具体做法**，否则它只是形容词。

- ❌ 整体偏冷色
- ✅ 环境永远冷调，只有皮肤和光源保留暖色；出现第二种暖色即视为失误

## 核心模型：三次翻译

MV 美术失败几乎都能归到一个原因 —— **情绪没有被翻译成结构**。整个流程就是三次翻译，每一步都必须落到纸面：

```
情绪 / 歌词   →  论点（一句话的视觉机制）
   ↓ 02-concept
论点          →  五条系统规则（色彩·母题·场景·镜头·文字）
   ↓ 03-systems
系统规则      →  时间表（每段每秒的画面与色彩）
   ↓ 04-score
```

## 两种模式

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

## 工作流（P0 → P5）

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

## 安装

把整个目录放到你所用的 agent 的 skill 目录下（各家命名不同，通常是 `~/.<tool>/skills/` 或项目内的 `.<tool>/skills/`）：

```bash
# 用户级（所有项目可用）
~/.<tool>/skills/anime-mv-art-direction/

# 或项目级（只在这个项目可用）
<project>/.<tool>/skills/anime-mv-art-direction/
```

不知道放哪儿的话，看该工具文档里 "skills" 一节；只要目录名是 `anime-mv-art-direction`、根下有 `SKILL.md`，就能被识别。

技能加载只看 `SKILL.md`，其余目录都是按需读取的参考资料与脚本。没有 agent 也能用：直接读 `references/` 并按 `scripts/` 里的命令行跑。

## 依赖

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

## 脚本

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

## 目录结构

```
SKILL.md                 主控：定位、工作流、阶段闸门
README.md                中文说明（本文件）
README_en.md             English
README_ja.md             日本語
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

## 一个设计原则

`assets/decision-matrix.md` 是**设计成打印出来手写**的——27 行，每行选一个主项并写下代价。写字比点头有效，这是这份东西最容易失效的地方。

同理，`check_env.py` 不报「缺失」就完事，而是输出「现在可用的部分」：缺 ffmpeg 时它会明确告诉你，企划、矛盾检测、决策矩阵、反模式评审、分镜表校验**仍然全部可用**。

## 授权提醒

- **字体与音源需自行确认商用授权**，在企划阶段就记进 `VISUAL_BIBLE.md` 的「素材与授权」栏
- 二创请遵守原曲与原作的使用条款；原创角色不要做成既有角色的相似物

## 许可证

代码与文档采用 [MIT License](LICENSE)。这是对**本 skill 本身**的授权，不涉及你用它所创作的 MV、以及 MV 里引用的音乐、字体、图像素材。
