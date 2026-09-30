# xueren-audio-video-to-text · 开发日志

> 版本演进 / changelog / 踩坑记录。SKILL.md 只写业务内容，日志在此文件。

## v2.6.4（2026-09-30）

**变更**：转写过程接入实时进度面板（用户 2026-09-30 21:50 询问「转换过程中能否调用[实时进度]skill显示实时进度」）。

- **`scripts/asr_whole.py`**：
  - 新增惰性接入层 `_open_progress()` / `_p_set()` / `_p_log()` / `_p_end()` / `count_parts()`，自动 `from progress import Progress`（路径 `~/.workbuddy/skills/xueren-live-progress/scripts`）。**导入失败/写盘失败一律静默降级**，不影响转写本体。
  - `main()`：新增 `--no-progress` 开关；按 `整段=1 段 / 拆段=ceil(dur/part_min) 段` 建卡片，`try/except` 包裹主体，成功 `ok()` / 异常 `fail()`。
  - `run_whole()`：提交前 `set(0)` + log，完成后 `set(1)`。
  - `run_parts()`：拆分后 set 基数；**在主线程**按已完成 `part_XX.json` 数量 `set(k)`（避开 `progress.inc()` 的读-改-写竞态）；冷却/失败/达最大轮数均写日志。
- **`xueren-live-progress/scripts/hook_bg.py`**：跳过清单新增 `asr_whole.py`，避免面板出现"hook 后台卡 + 脚本进度卡"两张重复卡片。
- **实测（2026-09-30 21:55，20 秒测试音频）**：卡片 `转写 test_asr_progress.wav` 正确经历 `running 0/1` → `done 1/1`，日志 5 条完整（启动 → 提交 → 完成），hook 提示语为「该命令自带进度上报，跳过自动登记」。

## v2.6.3（2026-09-30）

**变更**：新增「收尾源文件删除清单」硬约定（用户 2026-09-30 21:37 指定）。

- **变更点**：`你的工作方式` 追加第 4 步 —— 转写完成后在回复末尾给出"本轮源文件清单"表格（序号 / 完整路径 / 大小），附明确的回复指引（`1` / `2` / `1,2` / `全删` / `保留`）。
- **删除实现**：走 Windows 回收站 API（`[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(..., SendToRecycleBin)`），**不硬删**。
- **范围收敛**：只列本轮任务实际消耗的源文件（不翻历史），产物（txt 等）不入清单。
- **触发时机**：产物完整落盘时才提示，任务中途/产物不完整不提示，避免误删。
- **背景**：音视频转文字场景源文件动辄 100MB+，用户希望转完即清；用户先指定"任务完成后提示一下是否删除源文件"（21:36），本轮细化为"最好给个列表，每个源文件后边加上删除，让用户点击删除"（21:37）。

## v2.6.2（此前）

**变更**：（未在本文件记录，见 GitHub Release v2.6.2 说明）

## 更早版本

见 GitHub：https://github.com/JackieZheng/xueren-audio-video-to-text/releases
