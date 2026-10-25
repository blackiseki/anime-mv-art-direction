# 00 — 运行环境与依赖（先读这一份）

Contents: 1 不要假定环境就绪 · 2 依赖矩阵 · 3 自检 · 4 安装 · 5 中文字体 · 6 常见故障 · 7 没有 ffmpeg 时还能做什么

---

## 1 不要假定环境就绪

本 skill 的**判断方法**是纯文本的——色彩纪律、分镜结构、反模式、矛盾检测、决策矩阵，这些不需要任何软件，在纸上也能用。

但**带脚本的那部分**（出色彩脚本图、检测成片缺陷、逆推切点、按镜头取样）全部依赖外部程序。这些程序**不是 Python 自带的**，很多机器上根本没有：

- `ffmpeg` / `ffprobe` 是**独立软件**，不随系统或 Python 安装
- `Pillow` 是第三方库，需要单独 `pip install`
- 出图还要一个**能显示中文的字体**，否则中文会渲染成方块

所以**在跑任何脚本之前先自检**：

```bash
python scripts/check_env.py
```

它逐项报告缺什么、当前哪些脚本能用、以及对应平台的安装命令。缺失时退出码为 1。

**不要跳过这步直接跑 mv_lint.py。** 没装 ffmpeg 时它只会抛一句 `FileNotFoundError: [WinError 2]`，看不出是缺什么。

---

## 2 依赖矩阵

按脚本查，不要装多余的：

| 脚本 | Python | ffmpeg/ffprobe | Pillow | 中文字体 | 说明 |
|---|---|---|---|---|---|
| `check_env.py` | ✅ | — | — | — | 纯 stdlib，本身不需要任何依赖 |
| `shotlist_check.py` | ✅ | — | — | — | 纯 stdlib，只读 CSV |
| `color_script.py` | ✅ | — | **必需** | 建议 | 出 `color_script.png` |
| `mv_probe.py` | ✅ | **必需** | — | — | 切点 / 亮度 / 包络 / 对齐 |
| `mv_lint.py` | ✅ | **必需** | 仅 `--residue` | — | 不带 `--residue` 时只要 ffmpeg |
| `shot_sheets.py` | ✅ | **必需** | 可选 | 建议 | 按镜头取样拼图。默认有 Pillow 就用，没有自动改用 ffmpeg 滤镜，两者版式一致 |
| `ae_dump.jsx` | — | — | — | — | 在 **After Effects 内部**运行，需要 AE 本身 |

**Python 版本**：3.9 以上（用了 `from __future__ import annotations` 与新式类型标注）。

**明确不需要**：numpy、opencv、scipy、librosa、matplotlib。全部检测与统计都用 ffmpeg 原生滤镜 + 标准库实现，这是刻意设计的——少一层依赖就少一类"装不上"。

---

## 3 自检的判据

`check_env.py` 检查的具体内容，知道它在查什么才知道结果怎么读：

| 项 | 判据 | 缺失的后果 |
|---|---|---|
| Python | 主次版本 ≥ 3.9 | 脚本语法错误，全不可用 |
| ffmpeg / ffprobe | `shutil.which()` 能找到，且 `-version` 有输出 | 视频类脚本全不可用 |
| ffmpeg 滤镜 | `blackdetect` `freezedetect` `signalstats` `scdet` `metadata` 五个都在 | 老版本 ffmpeg 可能缺；对应检测会失效而不是报错，**这个最危险** |
| Pillow | 能 `import PIL` | `color_script.py` 出图不可用；`--residue` 不可用。**`shot_sheets.py` 不受影响**——它会自动改用 ffmpeg 滤镜引擎 |
| 中文字体 | msyh / simhei / YuGoth / 苹方 / Noto CJK 任一存在 | 图能出，但中文变方块 |
| After Effects | 常见安装路径存在 | 只影响 `ae_dump.jsx`，可选 |

「滤镜缺失」单独列出来是因为它**不会报错**——ffmpeg 会照常跑完，只是某个检测静默失效。宁可先查一遍。

---

## 4 安装

### Windows

```powershell
winget install Gyan.FFmpeg
# 或
scoop install ffmpeg
```

装完**重开终端**（PATH 只在启动时读取）。手动安装的话从 https://www.gyan.dev/ffmpeg/builds/ 下 `release-essentials`，解压后把里面的 `bin` 目录加进系统 PATH。

```bash
python -m pip install pillow
```

验证：

```bash
ffmpeg -version
python -c "import PIL; print(PIL.__version__)"
```

### macOS

```bash
brew install ffmpeg
python3 -m pip install pillow
```

### Linux

```bash
sudo apt install ffmpeg        # Debian / Ubuntu
sudo dnf install ffmpeg        # Fedora
sudo pacman -S ffmpeg          # Arch
python3 -m pip install pillow
```

Linux 上还常缺中文字体：

```bash
sudo apt install fonts-noto-cjk        # 或 fonts-wqy-zenhei
```

---

## 5 中文字体

`color_script.py` 与 `shot_sheets.py` 里的文字（段落名、时间码、镜号）需要 CJK 字体。找不到时 `color_script.py` 会**静默退回 Pillow 的默认位图字体**——图还是出得来，但中文全是方块，而且你不会收到任何警告。

`shot_sheets.py` 的 ffmpeg 引擎好一些：它的标签内容本身是 ASCII（`#001` / `0:01.24` / `mid`），没有 CJK 字体也能正常显示，只有顶部标题里的中文文件名会退化。

字体候选路径写在脚本的 `FONT_CANDIDATES` 里。用的是系统自带字体（Windows 微软雅黑、macOS 苹方、Linux Noto CJK），**不需要额外下载字体文件**。

如果自检显示「中文字体 未找到」，装一个 Noto CJK 即可；或者改用英文段落名，让图用默认字体也能读。

---

## 6 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| `python: command not found` | 有些系统只有 `python3` | 用 `python3 scripts/xxx.py` |
| `ffmpeg: command not found` 但刚装过 | 没重开终端，PATH 还是旧的 | 关掉终端重开，再跑 `check_env.py` |
| `FileNotFoundError: [WinError 2]` | 缺 ffmpeg，且脚本没做前置检查 | 跑 `check_env.py` 看缺哪项 |
| 图出来了但中文是方块 | 缺 CJK 字体 | 见 §5 |
| `mv_lint.py` 报「没取到逐帧数据」 | 文件不是可解码视频，或路径有中文/空格问题 | 用 `ffprobe 文件名` 先确认能读 |
| 检测全部为 0 而视频明显有问题 | ffmpeg 版本过旧，缺滤镜（静默失效） | `check_env.py` 会报「ffmpeg 滤镜 缺 xxx」 |
| `--residue` 直接跳过 | 没装 Pillow | `pip install pillow` |

---

## 7 没有 ffmpeg 时还能做什么

这部分很重要：**这个 skill 的大半价值不依赖 ffmpeg。**

不需要任何软件就能完成的：

- P0 建档、P1 定论点、P2 五条系统规则（色彩 / 母题 / 分镜 / 字体 / 工艺）
- 全部矛盾检测（创作者说的和实际选的冲突）
- 诊断三问（最贵的一秒在哪、删掉哪段就不成立、首尾帧什么关系）
- `assets/decision-matrix.md` 的 27 行取舍
- `assets/VISUAL_BIBLE.template.md` 的填写
- 22 条反模式的人工对照（`07-review.md`），以及「保留 / 修 / 砍」三栏
- `shotlist_check.py` 的分镜表校验（纯 stdlib）

只有这几件事需要 ffmpeg：**从成片反推切点、逐帧缺陷检测、按镜头抽帧**。也就是说，缺 ffmpeg 时你失去的是「用数据验证」，不是「判断力」。

此时最有效的替代做法：**自己数**。把成片拖进剪辑软件，用它的标记功能数一分钟内的切点数；把进度条拖到副歌看亮度有没有真的起来。慢，但比装不上软件就停工要好。
