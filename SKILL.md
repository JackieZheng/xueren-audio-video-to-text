---
id: xueren-audio-video-to-text
name: 雪人老师·音视频转文字
title: 雪人老师·音视频转文字
description: 长音频/视频转文字（B通道，免登录/免 key）。基于 AsrTools 开源库转写 mp3/wav/m4a/flac 等音频；视频（mp4 等）自动用 ffmpeg 提取音频转码 mp3 后提交。默认输出与原文件同名的纯文字 txt（不带时间戳、无头部说明）。音频 ≤100 分钟整段提交，>100 分钟自动拆 60 分钟段并行，出错冷却 5 分钟重试。适用于课程录音、讲座、播客、会议录音、教学视频等。
slug: xueren-audio-video-to-text
displayName: 雪人老师·音视频转文字
summary: 长音频/视频转文字（B通道，免登录/免 key）。
description_en: Convert long audio/video to text via AsrTools (no login/key needed).
version: 2.6.13
author: 雪人
license: GPL-3.0
allowed-tools: ""
display_name: xueren-audio-video-to-text
display_name_zh: 雪人老师·音视频转文字
trigger: ["音频转文字", "视频转文字", "转写音频", "转写视频", "语音转文字", "transcribe audio", "transcribe video", "把这段录音转成文字", "听写"]
examples: "用户提供一段 30 分钟课程录音 mp3（或一段 mp4 视频）路径说「把这段录音转成文字」，即用 B通道整段提交转写（视频先自动提音频），输出与原文件同名的纯文字 .txt（不带时间戳、无头部说明）；若 2 小时讲座则自动拆 3 段并行。"
agent_created: true
platforms: [WorkBuddy]
github: https://github.com/JackieZheng/xueren-audio-video-to-text
skillhub: https://skillhub.cn/skills/indiv-xueren/xueren-audio-video-to-text
release: https://github.com/JackieZheng/xueren-audio-video-to-text/releases
metadata:
  author: 雪人
  category: 效率工具
description_zh: 长音频/视频转文字（B通道，免登录/免 key）。基于 AsrTools 开源库转写 mp3/wav/m4a/flac 等音频；视频（mp4 等）自动用 ffmpeg 提取音频转码 mp3 后提交。默认输出与原文件同名的纯文字 txt（不带时间戳、无头部说明）。音频 ≤100 分钟整段提交，>100 分钟自动拆 60 分钟段并行，出错冷却 5 分钟重试。适用于课程录音、讲座、播客、会议录音、教学视频等。

---

# 雪人老师·音视频转文字

## 概述

长音频/视频（课程/讲座/播客/会议/教学视频）转文字，默认输出**纯文字完整文稿**（同名 txt，不带时间戳）。

**核心通道：B通道（免登录、免 key）**，基于 AsrTools 开源库转写。音频单次提交上限约 100 分钟，超过自动拆分并行转写。**视频（mp4 等 B通道不支持的格式）由脚本自动用 ffmpeg 提取音频并转码 mp3 后再提交**，用户无需手动转换。偶发风控 412，内置冷却 5 分钟自动重试。

默认 txt 为纯文字（每句一行，无 `[mm:ss]` 时间戳）。如需字幕可加 `--format srt` / `ass`。

## 安装到 AI 工具（以 WorkBuddy 为例）

本 skill 可装入任何支持 SKILL 规范的 AI 工具，两种方式：

1. **给项目地址**：直接把仓库地址 `https://github.com/JackieZheng/xueren-audio-video-to-text` 与一句需求发给 AI，由其自行克隆、装依赖、装入 skill 目录。
2. **下载 release 包**：到 Releases 下载最新 `.zip` 解压后，把该目录交给 AI 让其安装。

装好后**使用为对话形式**：发文件路径 + 一句「把这段录音转成文字」即可，AI 调用本 skill 在同目录产出同名 txt（纯文字、无时间戳、无头部说明）。详见 README「在 AI 工具里安装与使用」章节。

## 配置与参数

本 skill 目录**不打包第三方依赖**（保持轻量、可移植），运行时按「能用到本机就优先用本机，缺失时下载到当前目录」解析；脚本参数默认值见「执行流程 → 调用入口」参数表。依赖解析顺序与默认参数如下：

| 依赖 | 本机默认位置 | 解析顺序 | 缺失时 |
|------|-------------|---------|--------|
| **Python** | 受管 Python 3（已含 `requests`） | 直接用本机 Python | 安装 Python 3 并 `pip install requests` |
| **requests** | 随 Python 环境 | `import requests` | `pip install requests` |
| **ffmpeg/ffprobe** | 系统 `PATH` 或 `skill/bin/` | ①环境变量 `FFMPEG`/`FFPROBE` → ② `PATH` → ③ `skill/bin/` | 自动下载 ffmpeg 到 `skill/bin/`；下载失败则提示手动下载放 `skill/bin/` |

> 脚本 `asr_whole.py` 启动时自动执行 `_ensure_ffmpeg()`：本机任一位置有 ffmpeg 就直接用；都没有则下载/指引到 skill 目录的 `bin/`。`requests` 在本机已就绪，缺它才需安装。

## 你的工作方式

1. **确认文件存在** — `ls -lh <media_path>`（音频或视频）
2. **执行转写** — 调 `scripts/asr_whole.py`，**后台运行**（转写耗时约等于音频时长；视频会先自动提音频）。视频无需用户手动转音频，直接给 mp4 路径即可。**脚本已内置实时进度上报**（自动接入 `xueren-workbuddy-live-progress`）：启动后进度卡片出现在 `http://127.0.0.1:8791/`，**本轮结束前必须 `present_files` 打开该地址**让用户看实时进度（整段任务 `0/1 → 1/1`，拆段任务按"段"逐段推进并写日志）。面板 skill 缺失/不可用时**静默降级**，绝不影响转写本体。
3. **交付结果** — 用 `present_files` 展示与原文件同名的 `<原名>.txt`（纯文字）
4. **收尾源文件删除清单（2026-09-30 用户约定，强制）** — 转写完成、`present_files` 之后，**在回复末尾给出一份"本轮源文件清单"表格**，每行一个源文件，带序号 1/2/3…、完整路径、文件大小；表格下方给出**明确的删除回复指引**。**判定口径（严格，唯一权威）**：回复**序号**（`1` / `2,3` / `1-3`）→ 删除对应源文件；回复 **`0`** → 删除**全部**；回复**其它任何字符、或不回复** → **一律忽略，不进行任何删除操作**（`全删` / `保留` / `好` / `谢谢` 等均属"其它字符"，**不删**）。**只认 `0` 和合法序号**，绝不把模糊当默认同意。收到合法指令后走系统回收站（不硬删）。

   **清单格式样板**：
   ```
   | # | 源文件 | 大小 |
   |---|---|---|
   | 1 | F:\Desktop\Download\周老师\院校9月30日.wav | 178 MB |
   | 2 | F:\Desktop\Download\大三大四家长必看....mp4 | 92 MB |

   回复 `1` 删第 1 个 / `2,3` 删第 2、3 个 / `0` 删除全部 / 其它回复一律不删。
   ```

   **删除实现（走回收站，不硬删）** — **直接用 `scripts/recycle.py`**：

   ```bash
   python scripts/recycle.py "<path1>" ["<path2>" ...] [--dry-run] [--json]
   ```

   脚本做三件事：① `SHFileOperationW`（FO_DELETE + FOF_ALLOWUNDO）把文件送进**系统回收站**；② **逐个校验**结果——原路径消失 + 回收站出现**大小完全一致**的新 `$R*` 数据文件；③ 打印 `[OK]/[ERR]` 与退出码（0 全成功 / 1 有失败）。

   > ⚠️ **别信 API 的返回码/异常，要看结果**：本机实测 `SHFileOperationW` 与 PowerShell 的 `DeleteFile(..., SendToRecycleBin)` 对中文路径都**报错但实际删成功**（rc=2 / 「无法找到指定文件」）。判定只看：原路径 `os.path.exists` 为假 **且** 回收站出现同大小 `$R*` 条目（`$R*` 是数据、`$I*` 是元数据；**按大小匹配，别信文件名**）。
   > ⚠️ **回收站可能在"别的盘"**：本机 `~\Users\JackieZheng`），所以 C 盘路径下的文件其实落在 D 盘、条目也在 `D:\$Recycle.Bin`。`recycle.py` 已按「realpath 盘符 → 字面盘符 → 其余固定盘」全部搜一遍，**不要自己按路径字符串推盘符**。
   > **逐个删、逐个校验**；**不删产物**（txt 不在清单里）；**只列本轮消耗的源文件**，不翻旧账；产物不完整/任务中途不提示删除，避免误删。
   > **静默即不删**：用户没回复、或回复的不是 `0` 与合法序号，**一个文件都不动**，也不要追问催促——下次任务收尾时重新给清单即可。

## 执行流程

### 调用入口

```bash
python scripts/asr_whole.py "<media_path>" [--parallel 3] [--cooldown 300] [--part-min 60] [--no-progress]
```

> 脚本位于本 skill 目录下的 `scripts/asr_whole.py`，由本机任意可用的 Python 3 直接运行（无需绝对路径）。

**参数说明**
| 参数 | 默认 | 说明 |
|------|------|------|
| `media` | 必填 | 音频或视频文件绝对路径。音频：mp3/wav/m4a/flac；视频：mp4 等（自动提音频） |
| `--parallel` | 3 | 拆分时并行段数（仅 >100 分钟生效） |
| `--cooldown` | 300 | 出错冷却秒数（默认 5 分钟） |
| `--part-min` | 60 | 拆分每段分钟数（默认 60） |
| `--format` | txt | 输出格式：`txt`（纯文字文稿，不带时间戳）/ `srt`（标准 SRT 字幕）/ `ass`（标准 ASS 字幕） |
| `--keep` | 关 | 转写成功后**保留** `asr_out_*` 中间目录（默认会自动删除，便于断点续传/重跑） |
| `--no-progress` | 关 | **不接入**实时进度面板（默认自动接入 `xueren-workbuddy-live-progress`，缺失时静默降级） |

### 实时进度面板（默认开启）

转写启动即自动在 `~/.workbuddy/live-progress/jobs.json` 登记一张进度卡片，面板 `http://127.0.0.1:8791/` 实时显示：

| 阶段 | 卡片内容 |
|------|---------|
| 启动（**先于提音频**） | `转写 <文件名>` · 视频显示「提取音频中…」+ 日志「视频文件 → ffmpeg 提取音频」；音频显示「准备中…」；同时写一条「预估总耗时 ~Ns（准备 a + 转写 b，经验基线）」 |
| 提音频后 | 更新文案：「`X 分钟 · 整段提交`」或「`X 分钟 · 拆 N 段并行`」；并用**实测准备耗时**刷新预估总耗时 |
| 整段转写中 | 日志「整段提交 B 通道，排队转写中…」；**卡片走「时间基线」模式**：显示 `已运行 / 预估耗时 / 时间进度 / 预计完成`（超出预估显「已超 Xs」），曲线按真实时间折算 |
| 拆段转写中 | 每完成一轮刷新 `已完成 k/N 段` 并写日志；**拿到真实段计数后自动切回实测速率/ETA**（首段完成前用预估顶着）；风控/冷却/失败重试同样写入日志 |
| 结束 | `status=done/failed` + 「完成 N 句 · 耗时 Xs」/「部分缺失 · 耗时 Xs」 |

> 视频提音频（ffmpeg 提取 60 分钟以上可能要 1~2 分钟）也计入面板可见范围——卡片在 `ensure_audio()` **之前**就建立，避免"任务已在跑、面板却空白"。

- **整段任务为何用「预估」而不是实测速率**：整段提交是"原子"的——中途拿不到任何可数进度（`done` 全程为 0，只在结束时跳 1），面板的采样口径（≥2 点 + 跨 ≥20s + `done` 有增长）**天然算不出速率**。故脚本登记时 `total=None` + `planned_sec=预估`，让面板至少能给出「预计完成」钟点；**这一项是经验预估，不是真实进度**。
- **预估基线**（常量在 `asr_whole.py` 顶部，均取自本机实测）：整段转写 ≈ `0.6 秒/音频分钟`（上限 30~120s）；视频提音频 ≈ `0.15 秒/源文件 MB`（上限 20~300s）；拆分切分 ≈ `0.25 秒/音频分钟`（上限 90s）。这些**只用于面板对表**，不参与任何结算或产物逻辑。
- **实现**：`_open_progress()` 惰性 `from progress import Progress`（路径 `~/.workbuddy/skills/xueren-workbuddy-live-progress/scripts`）；导入失败或写盘失败一律 `except` 吞掉，**不抛错、不拖慢转写**。
- **并发安全**：拆段路径的进度在**主线程**按已完成 `part_XX.json` 数量汇总上报（`progress.inc()` 是读-改-写，多线程并发会丢更新）。
- **不重复卡片**：`xueren-workbuddy-live-progress/scripts/hook_bg.py` 的跳过清单已含 `asr_whole.py`，故不会另生成一张 hook 后台卡。
- **历史记录可删**：面板上未运行的任务卡片右上角有 `✕`（二次确认）；全清用折叠区「清空已结束」。

### 脚本策略（自动判断，无需手动选）

| 音频时长 | 策略 | 原因 |
|---------|------|------|
| ≤ 100 分钟 | **整段一次提交** | 不拆分，最少触发风控 |
| > 100 分钟 | **拆 60 分钟段并行提交** | B通道单次上限 100 分钟 |

出错（412 风控/429 限流/超时）→ 全部失败段冷却 `--cooldown` 秒后整组重试，**最多 3 轮**。每段结果落 `part_XX.json` 缓存，重跑时断点续传不重复。

### 产出（音频所在目录）

| 文件 | 说明 |
|------|------|
| `<原名>.txt` | 最终成品（与音频同名，纯文字、**不带时间戳、无头部说明**；`--format srt/ass` 时对应 `<原名>.srt`/`<原名>.ass`） |
| `asr_out_<原名>/part_XX.mp3` | 仅 >100 分钟时生成的 60 分钟分段（**中间产物，转写成功后自动删除**） |
| `asr_out_<原名>/part_XX.json` | 每段转写结果缓存（中间产物；成功后自动删除，`--keep` 可保留用于断点续传） |

> `asr_out_*` 目录**需要时自动创建**（拆分时 `split_parts` 调用 `os.makedirs(exist_ok=True)`），**用后自动删除**（转写成功后 `run_parts` 调用 `cleanup_asr_out`）。若失败想保留做断点续传，加 `--keep`。

## 资源目录

### asrlib/（核心库，AsrTools 开源包）
- `ASRData.py` — ASRData / ASRDataSeg 数据结构（时间戳单位=**毫秒**）
- `BaseASR.py` — 基类
- `BChannelASR.py` — B通道（upload → create_task → 轮询 result，免登录）
- `JChannelASR.py` — J通道（备选，单次上限约 60s，偶有 429 限流）
- `KChannelASR.py` — K通道（服务端已禁用，勿用）
- `WhisperASR.py` — 本地 Whisper（需 API key，本 skill 不使用）

### scripts/
- `asr_whole.py` — 唯一入口脚本（整段/拆分并行/冷却重试）
- `recycle.py` — 收尾删源文件用：`SHFileOperationW` 送进系统回收站 + **逐个校验**（原路径消失 + 回收站出现同大小 `$R*` 数据文件），支持 `--dry-run` / `--json`；跨盘自动搜（见上「回收站可能在别的盘」）

## 注意事项

- **B通道 412 风控**：IP 级持续封禁，5 分钟冷却通常足够，极端情况可能需 20~30 分钟。脚本 3 轮重试后仍失败时，告知用户稍后手动重跑。
- **时间戳单位是毫秒**：`ASRDataSeg.start_time/end_time` 为毫秒值，`ms_to_clock()` 负责换算。
- **免登录**：B通道上传/建任务/查结果全流程免第三方 cookie，无需任何凭据。
- **偶发失败属正常**：用户反馈"偶尔会失败"即 B通道风控特性，冷却后重跑即可。
- **繁简转换**：本 skill 不自动转简体，如需简体可后续对 txt 跑 opencc。
