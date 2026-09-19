# 雪人老师·音视频转文字（xueren-audio-video-to-text）

> 长音频/视频转文字 skill，基于 **B通道**（免登录、免 key）自动转写。
> 默认输出与原文件**同名的纯文字 txt**（不带时间戳、无头部说明），视频自动提取音频。

## 特性

- **免登录、免 key**：全流程无需任何第三方凭据
- **音频**：支持 mp3 / wav / m4a / flac，单次上限约 100 分钟，超过自动拆 60 分钟段并行
- **视频**：支持 mp4 等视频格式，自动用 ffmpeg 提取音频转码 mp3 后提交，无需手动转换
- **输出**：默认纯文字 txt（无时间戳、无头部说明），可选 `--format srt` / `ass` 生成字幕
- **错误处理**：偶发风控 412 / 限流 429，内置冷却 5 分钟自动重试，最多 3 轮
- **轻量可移植**：不打包第三方依赖，运行时按「本机优先、缺失下载到 skill/bin/」解析

## 安装

1. 克隆仓库（或下载 zip 解压）：

   ```bash
   git clone <repo-url> xueren-audio-video-to-text
   cd xueren-audio-video-to-text
   ```

2. 准备 Python 3（建议 3.9+），并安装唯一依赖：

   ```bash
   pip install requests
   ```

3. 安装 ffmpeg / ffprobe（Windows 推荐 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)，macOS 用 `brew install ffmpeg`，Linux 用包管理器）。脚本会按「环境变量 → 本机默认 → PATH → `skill/bin/`」解析；若自动解析不到，可设环境变量：

   ```bash
   export FFMPEG=/path/to/ffmpeg
   export FFPROBE=/path/to/ffprobe
   ```

   或将 ffmpeg 直接放到 `skill/bin/` 下。

## 在 AI 工具里安装与使用（以 WorkBuddy 为例）

本 skill 遵循通用的 SKILL 规范（`SKILL.md` + `meta.json` + 脚本），可装入任何支持 skill 的 AI 工具（WorkBuddy、Claude Code、Cursor 等）。**安装有两种方式**，装好后**使用就是普通的对话形式**——把文件路径丢给 AI，说一句「把这段录音转成文字」即可。

### 方式一：直接给项目地址，让 AI 自行下载安装

在对话框里把仓库地址和一句话需求一起发给 AI，让它自己克隆、装依赖、装 skill、执行转写：

```
帮我安装这个 skill 并把这段录音转成文字：
项目地址：https://github.com/JackieZheng/xueren-audio-video-to-text
录音路径：C:/Users/<你>/Downloads/lecture.mp3
```

支持 skill 的 AI 工具（如 WorkBuddy）会自动完成：克隆仓库 → 装入 skill 目录 → 准备 Python + `requests` + ffmpeg → 调用 `scripts/asr_whole.py` 转写 → 交付同名 txt。

### 方式二：下载 release 包，再交给 AI 安装

1. 到 [Releases](https://github.com/JackieZheng/xueren-audio-video-to-text/releases) 下载最新 `.zip`（如 `xueren-audio-video-to-text-v2.6.0.zip`），解压；
2. 把解压出的文件夹交给 AI，说一句「安装这个 skill 并转写这段录音」：

   ```
   安装这个目录下的 skill：C:/Users/<你>/Downloads/xueren-audio-video-to-text
   然后转写：C:/Users/<你>/Downloads/lecture.mp3
   ```

两种方式装好后，**使用都一样简单**——后续对话里直接发文件路径 + 一句转写需求即可，例如：

```
把 C:/Users/<你>/Downloads/meeting.mp4 转成文字
```

AI 会调用该 skill，在文件同目录产出 `meeting.txt`（纯文字、无时间戳、无头部说明），视频会自动先提取音频。

> 提示：首次使用请确保本机有 Python 3（含 `requests`）与 ffmpeg/ffprobe，否则 AI 会先引导补齐。

## 使用方法

直接转写（音频或视频均可，输出与原文件**同名的纯文字 txt**，不带时间戳、无头部说明）：

```bash
# 基本用法
python scripts/asr_whole.py "path/to/lecture.mp3"
python scripts/asr_whole.py "path/to/video.mp4"     # 视频自动提音频

# 长音频（>100 分钟）自动拆 60 分钟段并行
python scripts/asr_whole.py "path/to/long.mp3" --parallel 3 --part-min 60

# 指定输出格式（默认 txt，可选 srt / ass）
python scripts/asr_whole.py "path/to/lecture.mp3" --format srt

# 出错冷却更久（默认 300 秒 = 5 分钟）
python scripts/asr_whole.py "path/to/lecture.mp3" --cooldown 600
```

完成后在媒体文件同目录得到：

- `<原名>.txt`（默认）或 `<原名>.srt` / `<原名>.ass`
- `asr_out_<原名>/part_XX.mp3` 与 `asr_out_<原名>/part_XX.json`（仅长音频拆分时生成；属中间产物，转写成功后可直接删除）

## 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `media` | 必填 | 音频或视频文件绝对路径。音频：mp3/wav/m4a/flac；视频：mp4 等（自动提音频） |
| `--parallel` | 3 | 拆分时并行段数（仅 >100 分钟生效） |
| `--cooldown` | 300 | 出错冷却秒数（默认 5 分钟） |
| `--part-min` | 60 | 拆分每段分钟数（默认 60） |
| `--format` | txt | 输出格式：`txt`（纯文字）/ `srt` / `ass` |
| `--keep` | 关 | 转写成功后**保留** `asr_out_*` 中间目录（默认会自动删除，便于断点续传/重跑） |

## 产出

| 文件 | 说明 |
|------|------|
| `<原名>.txt` | 最终成品（与音频同名，纯文字、不带时间戳、无头部说明） |
| `asr_out_<原名>/part_XX.mp3` | 仅 >100 分钟时生成的 60 分钟分段（**中间产物，转写成功后自动删除**） |
| `asr_out_<原名>/part_XX.json` | 每段转写结果缓存（中间产物；成功后自动删除，`--keep` 可保留用于断点续传） |

> `asr_out_*` 目录**需要时自动创建**（拆分时自动 `mkdir`），**用后自动删除**（转写成功后整目录清理）。若失败想保留做断点续传，加 `--keep`。

## 资源依赖

本 skill **不打包第三方依赖**，运行时按「本机优先、缺失下载到 `skill/bin/`」解析。请在 `asr_whole.py` 的 `FFMPEG_SEARCH` 列表中填入你本机的 Python 与 ffmpeg 路径。

| 依赖 | 说明 | 缺失时 |
|------|------|--------|
| **Python 3** | 需已安装 `requests` | `pip install requests` |
| **ffmpeg / ffprobe** | 用于视频提取音频、拆分长音频 | 自动下载到 `skill/bin/`；失败则手动下载放置 |

> 脚本 `_ensure_ffmpeg()` 的解析顺序：①环境变量 `FFMPEG`/`FFPROBE` → ②本机默认路径 → ③ `PATH` → ④ `skill/bin/`。请按你机器实际情况修改脚本内的路径常量。

## 项目结构

```
xueren-audio-video-to-text/
├── SKILL.md              # skill 定义（frontmatter + 说明）
├── meta.json             # skill 元数据
├── .gitignore
├── asrlib/               # 核心 ASR 库
│   ├── ASRData.py        # ASRData / ASRDataSeg 数据结构（毫秒）
│   ├── BaseASR.py        # 基类
│   ├── BChannelASR.py    # B通道（upload → create_task → 轮询，免登录）
│   ├── JChannelASR.py    # J通道（备选，单次上限约 60s）
│   ├── KChannelASR.py    # K通道（服务端已禁用）
│   ├── WhisperASR.py     # 本地 Whisper（需 API key，本 skill 不使用）
│   └── __init__.py
└── scripts/
    └── asr_whole.py      # 唯一入口脚本（整段/拆分并行/冷却重试）
```

## 注意事项

- **B通道 412 风控**：IP 级持续封禁，5 分钟冷却通常足够，极端情况需 20~30 分钟。脚本 3 轮重试后仍失败时，告知用户稍后手动重跑。
- **时间戳单位是毫秒**：`ASRDataSeg.start_time/end_time` 为毫秒值，`ms_to_clock()` 负责换算。
- **免登录**：B通道上传/建任务/查结果全流程免第三方 cookie，无需任何凭据。
- **偶发失败属正常**：即 B通道风控特性，冷却后重跑即可。
- **繁简转换**：本 skill 不自动转简体，如需简体可后续对 txt 跑 opencc。

## 版本

- **v2.6.0**（2026-09-19）：`asr_out_*` 中间目录用后自动删、需要时自动建；新增 `--keep` 开关保留断点续传
- **v2.5.0**（2026-09-18）：视频自动提音频；默认纯文字同名 txt（无时间戳、无头部）；依赖本机优先
- **v2.4.0**：视频格式自动提取音频转码 mp3 后提交
- **v2.3.0**：默认 txt 去时间戳、同名交付、去头部说明
- **v2.2.0**：支持 srt/ass 字幕格式

## License

本项目基于开源项目 **[AsrTools](https://github.com/WEIFENG2333/AsrTools)**（核心转写库 `asrlib/` 即来源于它，AsrTools 采用 **GPL-3.0** 协议）；本仓库在 AsrTools 基础上封装了脚本化、ffmpeg 自动提音频、长音频拆分并行等易用层。

**协议说明**：本项目整体采用 **GPL-3.0**（GNU 通用公共许可证 v3）开源协议，与上游 AsrTools 保持一致。GPL 为强 copyleft 协议：可自由使用、修改、传播，但衍生/再分发版本必须以 GPL-3.0 同样条款继续发布，且须附带完整许可证与版权声明。

完整协议见 [./LICENSE](./LICENSE) · [GPL-3.0 全文](https://www.gnu.org/licenses/gpl-3.0.html)
