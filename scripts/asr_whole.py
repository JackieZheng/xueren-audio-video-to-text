# -*- coding: utf-8 -*-
"""
asr_whole.py —— 长音视频转写「整段优先，超100分钟才拆分，出错冷却重试」

策略（按用户要求）:
  1. B通道优先，免登录/免 key。
  2. 时长 <= 100 分钟：整段一次提交（不拆分，最快且最少触发风控）。
  3. 时长 > 100 分钟：ffmpeg 拆成 60 分钟段，并行提交 B通道。
  4. 任一段遇 412/429/超时：休息 5 分钟(cooldown) 后整组重试，最多 3 轮。
  5. 分段并行结果按全局时间戳(offset) 合并为一份完整文稿。

时间戳说明:
  B通道返回的 utterances 时间单位是【毫秒】。

用法:
  python asr_whole.py "F:\\...\\音频.mp3"
  python asr_whole.py "音频.mp3" --parallel 4   # 超过100分钟时并行段数
  python asr_whole.py "音频.mp3" --cooldown 300  # 出错冷却秒数(默认300=5分钟)

产出(在音频所在目录):
  <原名>.txt                 最终成品(纯文字，不带时间戳，与音频同名)
  asr_out_<原名>/part_XX.mp3    仅>100分钟时生成的 60 分钟分段（中间产物，转写成功后自动删除，需要时自动重建）
  asr_out_<原名>/part_XX.json   每段结果缓存（中间产物，同上；--keep 可保留用于断点续传）
"""
import os, sys, time, json, argparse, subprocess, logging
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
logging.getLogger().setLevel(logging.WARNING)

from asrlib import BChannelASR
from asrlib.ASRData import ASRData, ASRDataSeg

# 默认 ffmpeg/ffprobe 依赖 PATH 或环境变量；未设置时由 _find_ffmpeg() 按 环境变量 → PATH → skill/bin/ 依次解析。
DEFAULT_FFMPEG = None
DEFAULT_FFPROBE = None


def _shutil_which(name):
    """受管 Python 下 shutil.which 偶尔失效，回退 PATH 手工查找。"""
    import shutil
    found = shutil.which(name)
    if found:
        return found
    try:
        import os as _os, platform
        path_dirs = _os.environ.get("PATH", "").split(_os.pathsep)
        if platform.system() == "Windows":
            exts = (_os.environ.get("PATHEXT", ".exe;.cmd;.bat").split(";"))
            for d in path_dirs:
                for e in exts:
                    p = _os.path.join(d, name + e)
                    if _os.path.isfile(p):
                        return p
        else:
            for d in path_dirs:
                p = _os.path.join(d, name)
                if _os.path.isfile(p) and _os.access(p, _os.X_OK):
                    return p
    except Exception:
        pass
    return None


def _find_ffmpeg():
    """按优先级解析 ffmpeg / ffprobe：
    1) 环境变量 FFMPEG / FFPROBE（显式指定）
    2) PATH 查找
    3) 当前目录 skills/xueren-audio-video-to-text/bin/ffmpeg*.exe
    都找不到 -> 返回 None（由 main 引导下载）。"""
    import os, glob
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_ff = os.environ.get("FFMPEG")
    base_fp = os.environ.get("FFPROBE")
    if not base_ff:
        candidates = [_shutil_which("ffmpeg")]
        candidates += sorted(glob.glob(os.path.join(here, "bin", "ffmpeg*.exe")))
        base_ff = next((c for c in candidates if c and os.path.isfile(c)), None)
    if not base_fp:
        p_candidates = [_shutil_which("ffprobe")]
        p_candidates += sorted(glob.glob(os.path.join(here, "bin", "ffprobe*.exe")))
        base_fp = next((c for c in p_candidates if c and os.path.isfile(c)), None)
    if base_ff and not base_fp:
        # 找不到独立 ffprobe，退化为用 ffmpeg 自身做探测
        base_fp = base_ff
    return base_ff, base_fp


_ff, _fp = _find_ffmpeg()
FFMPEG = _ff
FFPROBE = _fp

WHOLE_LIMIT_MIN = 100   # 整段提交上限(分钟)，超过则拆分
PART_MIN        = 60    # 拆分后每段时长(分钟)
POLL_INTERVAL   = 3     # 轮询间隔(秒)


# ---------- 基础工具 ----------
def probe_duration(path):
    out = subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        stderr=subprocess.STDOUT, timeout=30)
    return float(out.decode().strip())


def ms_to_clock(ms):
    """毫秒 -> MM:SS / HH:MM:SS 时钟串。"""
    total_s = int(ms) // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def ensure_audio(src):
    """若输入是视频（mp4/mkv/mov/avi 等），用 ffmpeg 提取音频为 mp3，返回音频路径。
    若已是音频格式（mp3/wav/m4a/flac）则直接返回原路径。"""
    ext = os.path.splitext(src)[1].lower()
    supported = {".mp3", ".wav", ".m4a", ".flac"}
    if ext in supported:
        return src
    # 视频 → 提取音频
    base = os.path.splitext(src)[0]
    out_mp3 = base + ".mp3"
    print(f"[视频转音频] {os.path.basename(src)} -> {os.path.basename(out_mp3)}", flush=True)
    cmd = [FFMPEG, "-y", "-i", src, "-vn", "-c:a", "libmp3lame",
           "-b:a", "128k", "-ar", "16000", "-ac", "1", out_mp3]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if not os.path.exists(out_mp3) or os.path.getsize(out_mp3) == 0:
        raise RuntimeError(f"视频转音频失败: {src}")
    print(f"  音频已生成: {out_mp3} ({os.path.getsize(out_mp3)//1024}KB)", flush=True)
    return out_mp3


def transcribe_whole_bchannel(path, max_wait):
    """整段提交 B通道，返回 (ASRData, 原始时间基于0)。带 412/429 冷却重试(max_wait内)。"""
    asr = BChannelASR(path)
    asr.upload()
    tid = asr.create_task()
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            d = asr.result(tid)
            if d.get("state") == 4:
                res = json.loads(d["result"])
                utts = res.get("utterances", [])
                segs = [ASRDataSeg(u["transcript"],
                                    int(u.get("start_time", 0)),
                                    int(u.get("end_time", 0))) for u in utts]
                data = ASRData(segs)
                return data
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            msg = str(e)
            if "412" in msg or "429" in msg:
                print(f"    [!] 风控/限流(第{attempt}次)，冷却至下次...")
                time.sleep(POLL_INTERVAL * 3)
                continue
            raise
    raise TimeoutError(f"B通道任务 {tid} 在 {max_wait}s 内未完成")


# ---------- 整段路径 ----------
def run_whole(src, args, orig_src=None):
    dur = probe_duration(src)
    max_wait = max(300, int(dur * 1.5) + 120)
    print(f"[整段提交] {os.path.basename(src)} 时长 {dur/60:.1f} 分钟，"
          f"轮询上限 {max_wait}s")
    data = transcribe_whole_bchannel(src, max_wait)
    base_src = orig_src or src
    out = write_full_txt(base_src, [(0.0, data)], args)
    return out, len(data.segments)


# ---------- 拆分并行路径 ----------
def split_parts(src, outdir, part_min):
    os.makedirs(outdir, exist_ok=True)
    parts = []
    for f in os.listdir(outdir):
        if f.startswith("part_") and f.endswith(".mp3"):
            os.remove(os.path.join(outdir, f))
    total = probe_duration(src)
    seg_s = part_min * 60
    n = int(total // seg_s) + (1 if total % seg_s > 1 else 0)
    for i in range(n):
        p = os.path.join(outdir, f"part_{i:02d}.mp3")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            parts.append((i, p))
            continue
        cmd = [FFMPEG, "-y", "-i", src,
               "-ss", str(i * seg_s), "-t", str(seg_s),
               "-c:a", "libmp3lame", "-b:a", "128k",
               "-ar", "16000", "-ac", "1", p]
        subprocess.run(cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        parts.append((i, p))
    parts.sort()
    return parts


def transcribe_part(path, max_wait):
    """单个 60 分钟段提交 B通道，返回 ASRData(时间相对该段0点)。"""
    asr = BChannelASR(path)
    asr.upload()
    tid = asr.create_task()
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            d = asr.result(tid)
            if d.get("state") == 4:
                res = json.loads(d["result"])
                utts = res.get("utterances", [])
                segs = [ASRDataSeg(u["transcript"],
                                    int(u.get("start_time", 0)),
                                    int(u.get("end_time", 0))) for u in utts]
                return ASRData(segs)
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            msg = str(e)
            if "412" in msg or "429" in msg:
                print(f"    [!] {os.path.basename(path)} 风控(第{attempt}次)...")
                time.sleep(POLL_INTERVAL * 3)
                continue
            raise
    raise TimeoutError(f"段 {os.path.basename(path)} {max_wait}s 未完成")


def run_parts(src, args, orig_src=None):
    base = os.path.splitext(src)[0]
    outdir = os.path.join(os.path.dirname(src), "asr_out_" + os.path.basename(base))
    part_min = args.part_min
    parts = split_parts(src, outdir, part_min)
    seg_s = part_min * 60
    # 每个 60 分钟段转写上限：段时长的 1.5 倍 + 120s
    part_max_wait = max(600, int(seg_s * 1.5) + 120)
    total_dur = probe_duration(src)
    print(f"[拆分并行] 共 {len(parts)} 段(每段 {part_min} 分钟)，并行度 {args.parallel}")

    failed_round = 0
    while True:
        # 找出未成功的段(已有 part_XX.json 缓存则跳过)
        todo = []
        for i, p in parts:
            jf = p[:-4] + ".json"
            if os.path.exists(jf) and os.path.getsize(jf) > 0:
                continue
            todo.append((i, p))
        if not todo:
            break
        print(f"  -> 本轮待转写 {len(todo)} 段(并行 {args.parallel})")

        def work(item):
            i, p = item
            try:
                data = transcribe_part(p, part_max_wait)
                jf = p[:-4] + ".json"
                with open(jf, "w", encoding="utf-8") as f:
                    json.dump([{"text": s.text, "start": s.start_time,
                                "end": s.end_time} for s in data.segments],
                              f, ensure_ascii=False)
                print(f"    [ok] {os.path.basename(p)} {len(data.segments)} 句")
                return True
            except Exception as e:
                print(f"    [fail] {os.path.basename(p)}: {type(e).__name__} {str(e)[:60]}")
                return False

        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            list(ex.map(work, todo))

        # 检查是否全部成功
        still = []
        for i, p in parts:
            jf = p[:-4] + ".json"
            if not (os.path.exists(jf) and os.path.getsize(jf) > 0):
                still.append(p)
        if not still:
            break
        failed_round += 1
        if failed_round >= 3:
            print(f"[!] 仍有 {len(still)} 段失败，已达最大重试轮数(3)")
            break
        print(f"[冷却] 失败 {len(still)} 段，休息 {args.cooldown}s 后重试"
              f"(第 {failed_round}/3 轮)...")
        time.sleep(args.cooldown)

    # 合并所有段
    blocks = []
    all_ok = True
    for i, p in parts:
        jf = p[:-4] + ".json"
        offset_ms = i * seg_s * 1000
        if os.path.exists(jf) and os.path.getsize(jf) > 0:
            with open(jf, encoding="utf-8") as f:
                raw = json.load(f)
            segs = [ASRDataSeg(x["text"], x["start"], x["end"]) for x in raw]
            blocks.append((offset_ms, ASRData(segs)))
        else:
            blocks.append((offset_ms, None))
            all_ok = False
    base_src = orig_src or src
    out = write_full_txt(base_src, blocks, args, total_dur=total_dur, part_min=part_min,
                         all_ok=all_ok)
    # 用后自动删除中间产物目录（part_XX.mp3 + part_XX.json 整目录），需要时再自动重建。
    # 断点续传场景可传 --keep 保留。
    if all_ok and not getattr(args, "keep", False):
        cleanup_asr_out(outdir)
    return out, all_ok


# ---------- 合并输出 ----------
def merge_blocks(blocks, part_min=None):
    """把所有 blocks 的 segments 合并成一个带全局时间戳的 ASRData 列表。
    返回 [(ASRData, offset_ms), ...] 原样返回，offset_ms 用于全局修正。"""
    return blocks


def write_full_txt(src, blocks, args, total_dur=None, part_min=None, all_ok=True):
    fmt = getattr(args, "fmt", "txt")
    base = os.path.splitext(src)[0]
    ext = {"txt": ".txt", "srt": ".srt", "ass": ".ass"}[fmt]
    out = base + ext
    mode = "整段" if len(blocks) == 1 and total_dur is None else f"分段并行(每段{part_min}分钟)"
    status_str = "完整" if all_ok else "部分段缺失"

    if fmt == "txt":
        # 纯文字交付：不带任何头部说明（文件名/生成/模式/状态/分隔线），只留转写内容。
        # 仅在整组有缺失段时，在缺失处保留一行定位标注。
        with open(out, "w", encoding="utf-8") as f:
            for offset_ms, data in blocks:
                if data is None:
                    f.write(f"(本段 {ms_to_clock(offset_ms)} 起 转写缺失)\n")
                    continue
                for seg in data.segments:
                    f.write(f"{seg.text}\n")
    elif fmt == "srt":
        # 收集所有 segments（全局时间戳），生成标准 SRT
        srt_path = out
        with open(srt_path, "w", encoding="utf-8") as f:
            n = 0
            for offset_ms, data in blocks:
                if data is None:
                    continue
                for seg in data.segments:
                    global_start = offset_ms + seg.start_time
                    global_end   = offset_ms + seg.end_time
                    n += 1
                    f.write(f"{n}\n{seg._ms_to_srt_time(global_start)} --> {seg._ms_to_srt_time(global_end)}\n{seg.text}\n\n")
    elif fmt == "ass":
        # 生成标准 ASS（全局时间戳）
        ass_path = out
        style_str = (
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding\n"
            "Style: Default,微软雅黑,54,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,"
            "0,0,1,2,0,2,10,10,10,1\n"
        )
        ass_content = (
            "[Script Info]\n"
            f"; {os.path.basename(src)}（B通道转写）\n"
            f"; 生成: {time.strftime('%Y-%m-%d %H:%M')}  模式: {mode}  状态: {status_str}\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1920\n"
            "PlayResY: 1080\n\n"
            f"{style_str}\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        for offset_ms, data in blocks:
            if data is None:
                continue
            for seg in data.segments:
                global_start = offset_ms + seg.start_time
                global_end   = offset_ms + seg.end_time
                s_ts = seg._ms_to_ass_ts(global_start)
                e_ts = seg._ms_to_ass_ts(global_end)
                ass_content += f"Dialogue: 0,{s_ts},{e_ts},Default,,0,0,0,,{seg.text}\n"
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    return out


# ---------- 中间产物目录 asr_out_* 清理 ----------
def cleanup_asr_out(outdir):
    """删除 asr_out_* 中间产物目录（part_XX.mp3 + part_XX.json 整目录）。
    转写成功后调用，保持成品目录干净；需要时由 split_parts 重新自动创建。"""
    import shutil
    if not outdir or not os.path.isdir(outdir):
        return
    shutil.rmtree(outdir, ignore_errors=True)
    print(f"[清理] 已删除中间目录: {os.path.basename(outdir)}", flush=True)


# ---------- main ----------
def _ensure_ffmpeg():
    """缺 ffmpeg 时的兜底：先尝试自动下载当前平台的 ffmpeg 到 skill/bin/，
    下载失败则打印明确的下载指引（当前目录放置 ffmpeg.exe 即可）。"""
    global FFMPEG, FFPROBE
    if FFMPEG and os.path.isfile(FFMPEG):
        return
    import sys as _s, platform
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bindir = os.path.join(here, "bin")
    os.makedirs(bindir, exist_ok=True)
    bit = 64 if _s.maxsize > 2 ** 32 else 32
    platform_key = {"win32": "win64", "darwin": "macos", "linux": "linux64"}.get(_s.platform, "win64")
    url = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
           f"ffmpeg-master-latest-{platform_key}-{bit}.zip"
           if platform_key == "win64"
           else "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
    dest_zip = os.path.join(bindir, "ffmpeg.zip")
    try:
        import urllib.request, zipfile
        print(f"[依赖] 未找到 ffmpeg，尝试自动下载到 {bindir} ...")
        urllib.request.urlretrieve(url, dest_zip)
        with zipfile.ZipFile(dest_zip) as z:
            z.extractall(bindir)
        os.remove(dest_zip)
        ff = None
        for root, _, files in os.walk(bindir):
            for fn in files:
                if fn.lower().startswith("ffmpeg") and fn.lower().endswith(".exe"):
                    ff = os.path.join(root, fn)
                    break
            if ff:
                break
        if ff:
            FFMPEG = ff
            FFPROBE = os.path.join(os.path.dirname(ff), "ffprobe.exe")
            print(f"[依赖] ffmpeg 已下载到 {FFMPEG}")
            return
    except Exception as e:
        print(f"[依赖] 自动下载失败: {e}")
    print("\n[依赖缺失] 本机缺少 ffmpeg，请手动下载并放到 skill 目录的 bin/ 下：")
    print("  - Windows: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
    print(f"            解压后把 ffmpeg.exe / ffprobe.exe 放到 {bindir}\\")
    print("  - 或设置环境变量 FFMPEG / FFPROBE 指向你的 ffmpeg 路径")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--parallel", type=int, default=3, help="拆分时并行段数，默认3")
    ap.add_argument("--part-min", type=int, default=PART_MIN,
                   help="拆分每段分钟数，默认60")
    ap.add_argument("--cooldown", type=int, default=300,
                   help="出错冷却秒数，默认300(5分钟)")
    ap.add_argument("--format", "--fmt", dest="fmt", default="txt",
                   choices=["txt", "srt", "ass"],
                   help="输出格式：txt(纯文字文稿，默认不带时间戳)/srt(标准SRT字幕)/ass(标准ASS字幕)，默认txt")
    ap.add_argument("--keep", action="store_true",
                   help="转写成功后保留 asr_out_* 中间目录（默认用后自动删除，便于断点续传可显式 --keep）")
    args = ap.parse_args()

    _ensure_ffmpeg()
    src = args.audio
    assert os.path.exists(src), f"文件不存在: {src}"
    # 视频格式先提取音频
    audio = ensure_audio(src)
    dur_min = probe_duration(audio) / 60
    print(f"=== B通道转写: {os.path.basename(audio)}  时长 {dur_min:.1f} 分钟 ===")

    t0 = time.time()
    if dur_min <= WHOLE_LIMIT_MIN:
        out, n = run_whole(audio, args, orig_src=src)
        print(f"\n完成: {out}  ({n} 句, 耗时 {time.time()-t0:.0f}s)")
        # 若源文件是视频，清理中间生成的 mp3
        if audio != src and os.path.exists(audio):
            os.remove(audio)
            print(f"[清理] 已删除中间音频: {os.path.basename(audio)}")
    else:
        out, all_ok = run_parts(audio, args, orig_src=src)
        status = "完整" if all_ok else "部分缺失"
        print(f"\n完成({status}): {out}  (耗时 {time.time()-t0:.0f}s)")
        if all_ok and not args.keep:
            print(f"[提示] asr_out_* 中间目录已自动删除（如需保留断点续传可加 --keep）")
        elif all_ok and args.keep:
            print(f"[提示] 已保留 asr_out_* 中间目录（--keep）")


if __name__ == "__main__":
    main()
