# 09 — 读 AE 工程：拿到视频永远给不了的那一层

Contents: 1 为什么必须读工程 · 2 安全规程（先读）· 3 运行方法 · 4 输出结构 · 5 字段→诊断对照 · 6 哪些能改哪些不能 · 7 读不到什么

---

## 1 为什么必须读工程

从成片视频里永远看不出这些：

| 视频看不出 | 工程里一目了然 | 为什么重要 |
|---|---|---|
| 这一层有几个关键帧 | `transform[].keys` | 180 个位置关键帧 = 手搓过密，运动一定抖 |
| 运动是线性还是缓动 | `linear_ratio` | 全线性 = 机械感，这是"廉价"最隐蔽的来源 |
| 加了 5 个效果还是关了 4 个 | `effects[].enabled` | 视频看着素，工程里可能堆了 8 个 |
| 用的是哪个字体 | `text.font` | 字体超 3 家族 = 全片风格散 |
| 图层怎么命名的 | `layers[].name` | `Solid 47` 满屏 = 没有结构，改不动 |
| 谁是父级 | `layers[].parent` | 抖动是父子链造成的还是刻意的 |
| 段落标记打在哪 | `markers` | 和音乐段落是否对齐 |

**一句话**：视频告诉你"看起来怎样"，工程告诉你"为什么会这样"。

---

## 2 安全规程（先读，再看脚本）

⚠️ **先确认 AE 的自动保存是开着的（首选项 → 自动保存）。很多人是关的，脚本崩了或 AE 崩了就是直接丢工作。**

按顺序做，一条都别跳：

1. **先备份** `.aep`（复制一份带时间戳的重命名），不管脚本多"只读"。
2. **AE 必须是单实例**。`AfterFX.exe -r` 会尝试接入已有实例；如果你已经开着工程，先手动保存并关闭，再跑脚本。
3. **不要在有未保存修改时跑**。脚本末尾会 `app.quit()`，未保存的内容会被丢弃——除非你设 `AE_DUMP_QUIT=0`。
4. **大工程加 `AE_DUMP_TRANSFORM_ONLY=1`**。长合成很容易吃满内存，32GB 也不够用（典型表现：`RenderTaskManager Shutdown took 2 seconds` + 崩溃码 `0::42`）。
5. **不要在脚本里顺手改工程**。本脚本是只读的；如果你自己扩展，把"读"和"写"分成两个脚本。

---

## 3 运行方法

把 `<AE>` 换成你的 AfterFX.exe 实际路径（Windows 默认在 `C:\Program Files\Adobe\Adobe After Effects <版本>\Support Files\AfterFX.exe`），把 `<SKILL>` 换成本 skill 目录。

### Windows（cmd）
```bat
set AE_DUMP_OUT=G:\proj\ae_dump.json
set AE_DUMP_TRANSFORM_ONLY=0
"C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.exe" -r "<SKILL>\scripts\ae_dump.jsx"
```

### 从 Bash（Git Bash / WSL）
```bash
export AE_DUMP_OUT="G:/proj/ae_dump.json"
"/c/Program Files/Adobe/Adobe After Effects 2026/Support Files/AfterFX.exe" -r "<SKILL>/scripts/ae_dump.jsx"
```

注意 `-r` 的运行方式：AE 会启动、执行脚本、然后按脚本里的 `app.quit()` 退出。**它会打开一个窗口**，不是无头运行。跑之前把别的工程关掉。

### 在 AE 界面里跑（最稳）
`File > Scripts > Run Script File…` → 选 `ae_dump.jsx`。
输出默认落到**工程文件同目录**的 `ae_dump.json`。这种方式不触发 `app.quit()`（除非你设了 `AE_DUMP_QUIT=1`）。

### 环境变量
| 变量 | 默认 | 作用 |
|---|---|---|
| `AE_DUMP_OUT` | 工程目录 / `ae_dump.json` | 输出路径 |
| `AE_DUMP_TRANSFORM_ONLY` | `0` | `1` = 跳过效果参数，只导变换（大工程快很多） |
| `AE_DUMP_MAX_KEYS` | `24` | 每属性最多记多少关键帧，超出只记统计 |
| `AE_DUMP_QUIT` | `1` | `0` = 导完不退出 AE（在界面里跑时建议设 0） |

---

## 4 输出结构

```jsonc
{
  "ae_version": "26.0",
  "project": "G:\\proj\\mv.aep",
  "comp_count": 2,
  "comps": [{
    "name": "MAIN",
    "width": 1920, "height": 1080,
    "duration": 196.0, "frameRate": 24,
    "numLayers": 42,
    "bg": [0, 0, 0],
    "markers": [{ "t": 56.0, "comment": "サビ1" }],
    "layers": [{
      "index": 3, "name": "char_main", "type": "av",
      "enabled": true, "locked": false,
      "inPoint": 0, "outPoint": 196, "startTime": 0,
      "parent": 2, "threeD": false,
      "source": "char_A_pose01.png",
      "transform": [{
        "name": "Position", "animated": true,
        "keys": 46, "avg_gap_s": 0.42, "linear_keys": 46, "linear_ratio": 1,
        "sample": [{ "t": 0, "v": [960, 540], "it": 6612, "ot": 6612 }]
      }],
      "effects": [{ "name": "Lumetri Color", "enabled": true, "params": [] }],
      "text": null
    }]
  }]
}
```

插值类型编码：`6612` 线性 · `6613` 贝塞尔 · `6614` 定格。

---

## 5 字段 → 诊断对照

拿到 JSON 后，按这张表逐条扫。**每条都要指出具体图层名**，否则用户不知道改哪里。

| 字段 | 异常阈值 | 结论 | 改法 |
|---|---|---|---|
| `linear_ratio` | > 0.8 | 运动几乎全线性 → 机械、廉价 | 关键帧全选 → F9 缓动；或给位置加 2 帧缓入 |
| `avg_gap_s` | < 0.15 | 关键帧过密（手搓） | 删中间帧，用 2 个关键帧 + 缓动代替 10 个 |
| `keys` | 单属性 > 60 | 同上 | 同上 |
| `effects[].length` | 单层 > 3 | 效果堆叠 | 砍到 2 个以内，其余合并到调色 |
| `enabled: false` 的图层 | 占比 > 20% | 工程里有大量废层 | 清理，避免渲染时误开 |
| `name` 匹配 `Solid \d+|图层 \d+` | > 30% | 没有命名结构 | 至少给"人物/背景/文字/特效"前缀 |
| `text.font` 去重 | > 3 种 | 字体家族超预算 | 收敛到 3 个，明确各自职责 |
| `fontSize` | 竖屏且 < 50px | 手机上看不清 | ×1.5 |
| `parent` | 链长 > 4 | 父子链过深 | 运动难控，易抖动 |
| `markers` | 为空 | 没有段落标记 | 按音乐打上 サビ/Cメロ 标记，方便对齐 |
| `inPoint/outPoint` | 图层超出 comp 时长 | 冗余计算 | 裁掉 |

**诊断话术示例**：
> `char_main` 的位置属性有 46 个关键帧，平均间隔 0.42 秒，且 **46 个全是线性插值**。这就是"人动起来像被拖着走"的原因——不是画的问题。删到 6 个关键帧（每个乐句一个），全选 F9，再给首尾各 3 帧缓入。

---

## 6 哪些能改，哪些不要自动改

| 操作 | 安全度 | 说明 |
|---|---|---|
| 批量把线性关键帧改贝塞尔 | ✅ 安全 | 视觉立刻变好，可撤销 |
| 批量提前切点 1–2 帧 | ✅ 安全 | 但 AE 里"切点"是图层 inPoint，位移要连带关键帧 |
| 改色板 / 改调色效果参数 | ✅ 较安全 | 改完必须出图确认 |
| 改文字内容 / 字号 / 字体 | ⚠️ 需确认 | 字体缺失会变默认字体，务必先确认字体已装 |
| 删图层 | ⚠️ 需确认 | 可能有表达式引用它 |
| 改表达式 | ❌ 不要自动改 | 你不知道原作者意图 |
| 重排图层顺序 | ❌ 不要自动改 | 会改变遮挡关系，等于改构图 |
| 新建合成 / 重渲染 | ❌ 不归本 skill | 交给渲染流程 |

**铁律**（沿用你的工作习惯）：**改完先出图给用户确认，再考虑渲染。** 不要擅自渲染。

每次修改只做一类，做完让用户看一眼，再下一类。批量改三类，出问题时无法定位是哪一类导致的。

---

## 7 读不到什么

诚实边界：

- **表达式的结果**。只导出静态值，表达式驱动的运动读不到。有表达式的属性在 `sample` 里可能是常量。
- **插件内部**。第三方效果（Trapcode / BorisFX）的参数结构因插件而异，`params` 可能是空的。
- **素材文件的实际内容**。只有文件名。
- **渲染设置 / 输出模块**。不导出。
- **时间重映射的曲线**。只记关键帧，不记曲线形状。
- **颜色管理设置**。不导出，色彩空间要单独问用户。

需要这些时，明确告诉用户"这一项我读不到"，不要假装知道。
