---
id: xueren-audio-video-to-text
name: 雪人老师·音视频转文字
title: 雪人老师·音视频转文字
description: 长音频/视频转文字（B通道，免登录/免 key）。基于 AsrTools 开源库转写 mp3/wav/m4a/flac 等音频；视频（mp4 等）自动用 ffmpeg 提取音频转码 mp3 后提交。默认输出与原文件同名的纯文字 txt（不带时间戳、无头部说明）。音频 ≤100 分钟整段提交，>100 分钟自动拆 60 分钟段并行，出错冷却 5 分钟重试。适用于课程录音、讲座、播客、会议录音、教学视频等。
description_zh: 雪人老师·音视频转文字
description_en: xueren-audio-video-to-text
version: 2.6.1
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
release: https://github.com/JackieZheng/xueren-audio-video-to-text/releases
metadata:
  author: 雪人
  category: 效率工具
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

## 资源依赖

本 skill 目录**不打包第三方依赖**（保持轻量、可移植），运行时按「能用到本机就优先用本机，缺失时下载到当前目录」解析：

| 依赖 | 本机默认位置 | 解析顺序 | 缺失时 |
|------|-------------|---------|--------|
| **Python** | 受管 Python 3（已含 `requests`） | 直接用本机 Python | 安装 Python 3 并 `pip install requests` |
| **requests** | 随 Python 环境 | `import requests` | `pip install requests` |
| **ffmpeg/ffprobe** | 系统 `PATH` 或 `skill/bin/` | ①环境变量 `FFMPEG`/`FFPROBE` → ② `PATH` → ③ `skill/bin/` | 自动下载 ffmpeg 到 `skill/bin/`；下载失败则提示手动下载放 `skill/bin/` |

> 脚本 `asr_whole.py` 启动时自动执行 `_ensure_ffmpeg()`：本机任一位置有 ffmpeg 就直接用；都没有则下载/指引到 skill 目录的 `bin/`。`requests` 在本机已就绪，缺它才需安装。

## 你的工作方式

1. **确认文件存在** — `ls -lh <media_path>`（音频或视频）
2. **执行转写** — 调 `scripts/asr_whole.py`，**后台运行**（转写耗时约等于音频时长；视频会先自动提音频）。视频无需用户手动转音频，直接给 mp4 路径即可。
3. **交付结果** — 用 `present_files` 展示与原文件同名的 `<原名>.txt`（纯文字）

## 执行流程

### 调用入口

```bash
python scripts/asr_whole.py "<media_path>" [--parallel 3] [--cooldown 300] [--part-min 60]
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

## 注意事项

- **B通道 412 风控**：IP 级持续封禁，5 分钟冷却通常足够，极端情况可能需 20~30 分钟。脚本 3 轮重试后仍失败时，告知用户稍后手动重跑。
- **时间戳单位是毫秒**：`ASRDataSeg.start_time/end_time` 为毫秒值，`ms_to_clock()` 负责换算。
- **免登录**：B通道上传/建任务/查结果全流程免第三方 cookie，无需任何凭据。
- **偶发失败属正常**：用户反馈"偶尔会失败"即 B通道风控特性，冷却后重跑即可。
- **繁简转换**：本 skill 不自动转简体，如需简体可后续对 txt 跑 opencc。
