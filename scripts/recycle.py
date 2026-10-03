#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把文件移入 Windows 回收站，并**逐个校验**是否真的进去了。

为什么不直接用 PowerShell / shutil：
- `shutil`/`os.remove` 是**硬删**，不进回收站（破坏"可还原"承诺）。
- PowerShell 的 `[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(...SendToRecycleBin)`
  在本机对**中文路径会报假错**（"无法找到指定文件"）而实际删除成功 —— 无法据返回码判定。
- 本脚本走 Shell 原生 `SHFileOperationW`（FO_DELETE + FOF_ALLOWUNDO），
  并且**不信返回码、只看结果**：原路径消失 + 回收站出现同大小 `$R*` 数据文件。

用法：
    python recycle.py <file> [<file> ...] [--json] [--dry-run]

退出码：0 = 全部成功；1 = 有文件失败/校验不过；2 = 参数错误。
"""
import argparse
import ctypes
import glob
import json
import os
import sys
import time
from ctypes import wintypes

FO_DELETE = 3
FOF_ALLOWUNDO = 0x40        # 走回收站
FOF_NOCONFIRMATION = 0x10
FOF_SILENT = 0x4
FOF_NOERRORUI = 0x400


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def _send_to_recycle_bin(path):
    """调 Shell API 删除（进回收站）。返回 (rc, aborted)。"""
    op = _SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0\0"   # 必须以双 null 结尾
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    op.fAnyOperationsAborted = False
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return rc, bool(op.fAnyOperationsAborted)


def _candidate_drives(path):
    """要搜哪些盘的回收站。

    不能只看路径字符串的盘符：本机 `C:\\Users\\JackieZheng` 是 **D: 的 junction**
    （`os.path.realpath` → `D:\\Users\\JackieZheng`），文件实际落在 D 盘，
    回收站条目也就在 `D:\\$Recycle.Bin`。故按「realpath 盘符 → 字面盘符 → 其余固定盘」
    的顺序全部搜一遍（多搜几个目录的开销可忽略）。
    """
    drives = []
    for p in (os.path.realpath(path), os.path.abspath(path)):
        d = os.path.splitdrive(p)[0].upper()
        if d and d not in drives:
            drives.append(d)
    for c in "CDEFGHIJ":
        if c + ":" not in drives:
            drives.append(c + ":")
    return drives


def _recycle_candidates(path, since_ts=None):
    """列出回收站里的 `$R*`（数据）文件，可只保留最近改动的。返回带所在盘信息。"""
    out = []
    for drive in _candidate_drives(path):
        root = os.path.join(drive + os.sep, "$Recycle.Bin")
        if not os.path.isdir(root):
            continue
        for p in glob.glob(os.path.join(root, "*", "$R*")):
            if not os.path.isfile(p):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if since_ts and st.st_mtime < since_ts - 5:
                continue
            out.append({"path": p, "drive": drive, "size": st.st_size,
                        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))})
    return out


def recycle(files, dry_run=False):
    results = []
    for f in files:
        rec = {"file": f, "ok": False}
        if not os.path.isfile(f):
            rec["error"] = "文件不存在"
            results.append(rec)
            continue
        size = os.path.getsize(f)
        rec["size"] = size
        if dry_run:
            rec.update(ok=True, dry_run=True, note="预演，未删除")
            results.append(rec)
            continue

        before = {c["path"] for c in _recycle_candidates(f)}
        t0 = time.time()
        rc, aborted = _send_to_recycle_bin(f)
        time.sleep(0.2)

        gone = not os.path.exists(f)
        # 校验：回收站里出现"大小一致 + 刚新增"的 $R* 数据文件
        fresh = [c for c in _recycle_candidates(f, since_ts=t0) if c["path"] not in before]
        match = [c for c in fresh if c["size"] == size] or \
                [c for c in _recycle_candidates(f) if c["size"] == size]

        rec["rc"] = rc
        rec["aborted"] = aborted
        rec["recycle_bin"] = match[0]["path"] if match else None
        rec["drive"] = match[0]["drive"] if match else \
            os.path.splitdrive(os.path.realpath(f))[0].upper()
        rec["ok"] = bool(gone and match)
        if not rec["ok"]:
            if not gone:
                rec["error"] = "原路径仍存在（未删除）"
            else:
                rec["error"] = "原路径已消失，但回收站未找到同大小条目（可能是硬删）"
        results.append(rec)
    return results


def main():
    ap = argparse.ArgumentParser(description="移入 Windows 回收站 + 逐个校验（不看返回码，只看结果）")
    ap.add_argument("files", nargs="+", help="要删除的文件路径")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--dry-run", action="store_true", help="只预演，不删除")
    args = ap.parse_args()

    if not sys.platform.startswith("win"):
        print("[!] 本脚本依赖 Windows Shell API（SHFileOperationW），当前平台不支持", file=sys.stderr)
        return 2

    results = recycle(args.files, dry_run=args.dry_run)

    if args.json:
        print(json.dumps({"results": results,
                          "ok": all(r["ok"] for r in results)}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "OK " if r["ok"] else "ERR"
            extra = f" → 回收站 {os.path.basename(r['recycle_bin'])}" if r.get("recycle_bin") else ""
            err = f"  ({r['error']})" if r.get("error") else ""
            print(f"[{mark}] {r['file']}{extra}{err}")
            if "rc" in r and not r["ok"]:
                print(f"      rc={r['rc']} aborted={r['aborted']}")
        print(f"\n合计 {len(results)} 个，成功 {sum(1 for r in results if r['ok'])} 个")

    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
