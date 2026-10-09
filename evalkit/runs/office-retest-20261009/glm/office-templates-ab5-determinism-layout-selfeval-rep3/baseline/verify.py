#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立复核脚本（不写 out/，只读复核 + 一次临时目录重放）。

复核项（全部通过 exit 0，任一失败 exit 1）：
  1. run_log.json 结构完整：两遍（标注第一遍/第二遍）、每遍两产物 sha256；
  2. 日志口径：第一遍与第二遍 sha256 两两相同；
  3. 输出目录 out/会议通知/case1 恰含 文书.docx 与 fields.json；
  4. 盘上产物 sha256 与日志第二遍记录一致（日志反映真实）；
  5. records/run1_snapshot 字节快照与当前产物逐字节一致（重算，不信日志）；
  6. 第三遍重放：同 --template/--data、换临时 --outdir 再生成一次，
     两产物与 out/ 下产物逐字节一致（确定性 + 与输出目录无关）；
  7. docx 解析后视图（段落文本/对齐/缩进/字体/行距）快照 vs 当前完全一致；
  8. docx ZIP 条目时间戳全部固定 1980-01-01 00:00:00；
  9. fields.json：合法 JSON、以恰一个换行结尾、无绝对路径、无时间类键、
     模板名为 会议通知、fields 回显与输入 fixture 完全一致；
 10. docx 元数据（docProps/core.xml）不含本次运行日期（无当前时间源）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docx_inspect  # noqa: E402

OUTDIR = os.path.join(HERE, "out", "会议通知", "case1")
SNAPDIR = os.path.join(HERE, "records", "run1_snapshot")
FIXTURE = os.path.join(HERE, "fixtures", "会议通知", "case1.json")
LOG = os.path.join(HERE, "run_log.json")
ARTIFACTS = ["文书.docx", "fields.json"]

RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name,
                         (" —— " + detail) if detail else ""))
    return ok


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    # 1. run_log.json 结构
    with open(LOG, encoding="utf-8") as fh:
        log = json.load(fh)
    runs = log.get("runs", [])
    labels = [r.get("标注", "") for r in runs]
    struct_ok = (len(runs) == 2
                 and labels[0].startswith("第一遍")
                 and labels[1].startswith("第二遍")
                 and all(set(ARTIFACTS) <= set(r.get("artifacts", {})) for r in runs)
                 and all("sha256" in r["artifacts"][a] for r in runs for a in ARTIFACTS))
    check("1 run_log.json 结构（两遍+每遍两产物 sha256）", struct_ok,
          "标注: %s" % " / ".join(labels))

    # 2. 日志口径：两遍 sha256 相同
    same_log = all(runs[0]["artifacts"][a]["sha256"] == runs[1]["artifacts"][a]["sha256"]
                   for a in ARTIFACTS)
    check("2 日志记录两遍 sha256 相同", same_log)

    # 3. 输出目录恰含两产物
    listing = sorted(os.listdir(OUTDIR)) if os.path.isdir(OUTDIR) else []
    check("3 输出目录恰含两产物", listing == sorted(ARTIFACTS),
          "实际: %s" % listing)

    # 4. 盘上产物与日志第二遍 sha256 一致
    disk_ok = all(sha256_of(os.path.join(OUTDIR, a)) == runs[1]["artifacts"][a]["sha256"]
                  for a in ARTIFACTS)
    check("4 盘上产物 sha256 与日志第二遍一致", disk_ok)

    # 5. 快照与当前产物逐字节一致（重算）
    snap_ok, snap_detail = True, []
    for a in ARTIFACTS:
        with open(os.path.join(SNAPDIR, a), "rb") as fh:
            first = fh.read()
        with open(os.path.join(OUTDIR, a), "rb") as fh:
            second = fh.read()
        if first != second:
            snap_ok = False
            snap_detail.append("%s 不一致" % a)
    check("5 第一遍字节快照与第二遍产物逐字节一致（重算）", snap_ok,
         "; ".join(snap_detail))

    # 6. 第三遍重放（临时目录，不触碰 out/）
    replay_ok, replay_detail = True, []
    with tempfile.TemporaryDirectory(prefix=".verify_replay_", dir=HERE) as tmp:
        proc = subprocess.run(
            [sys.executable, "gen_doc.py", "--template", "会议通知",
             "--data", os.path.join("fixtures", "会议通知", "case1.json"),
             "--outdir", os.path.relpath(tmp, HERE)],
            cwd=HERE, capture_output=True, text=True)
        if proc.returncode != 0:
            replay_ok = False
            replay_detail.append("重放 exit=%d" % proc.returncode)
        else:
            for a in ARTIFACTS:
                with open(os.path.join(tmp, a), "rb") as fh:
                    replay = fh.read()
                with open(os.path.join(OUTDIR, a), "rb") as fh:
                    current = fh.read()
                if replay != current:
                    replay_ok = False
                    replay_detail.append("%s 与 out/ 不一致" % a)
    shutil.rmtree(os.path.join(HERE, "__pycache__"), ignore_errors=True)
    check("6 第三遍重放（临时目录）产物逐字节一致", replay_ok,
          "; ".join(replay_detail))

    # 7. docx 解析后视图一致（重算）
    fp1 = docx_inspect.paragraph_fingerprints(os.path.join(SNAPDIR, "文书.docx"))
    fp2 = docx_inspect.paragraph_fingerprints(os.path.join(OUTDIR, "文书.docx"))
    diffs = docx_inspect.fingerprint_diff(fp1, fp2)
    check("7 docx 解析后段落文本/对齐/缩进/字体/行距完全一致（重算）",
          fp1 == fp2 and len(fp1) > 0,
          "段落数 %d%s" % (len(fp1), "" if not diffs else "；差异: " + "; ".join(diffs)))

    # 8. ZIP 条目时间戳固定
    dts = {dt for _, dt in docx_inspect.zip_entry_datetimes(os.path.join(OUTDIR, "文书.docx"))}
    check("8 docx ZIP 条目时间戳固定 1980-01-01", dts == {(1980, 1, 1, 0, 0, 0)},
          "集合: %s" % sorted(dts))

    # 9. fields.json 内容口径
    with open(os.path.join(OUTDIR, "fields.json"), encoding="utf-8") as fh:
        raw = fh.read()
    fields = json.loads(raw)
    with open(FIXTURE, encoding="utf-8") as fh:
        fixture = json.load(fh)
    bad_keys = [k for k in fields if k.lower() in
                ("time", "timestamp", "generated_at", "now", "created", "modified")]
    abs_markers = [m for m in ("/home/", "/Users/", "/tmp/", "C:\\", HERE)
                   if m and m in raw]
    fields_ok = (fields.get("template") == "会议通知"
                 and fields.get("fields") == fixture
                 and raw.endswith("\n") and not raw.endswith("\n\n")
                 and not bad_keys and not abs_markers)
    check("9 fields.json 合法/静态/回显一致", fields_ok,
          "时间类键: %s；绝对路径痕迹: %s" % (bad_keys, abs_markers))

    # 10. docx 元数据无本次运行日期（核心属性不含当前时间源）
    with zipfile.ZipFile(os.path.join(OUTDIR, "文书.docx")) as zf:
        core = zf.read("docProps/core.xml").decode("utf-8")
    today_markers = [m for m in ("2026-", "2025-") if m in core]
    check("10 docProps/core.xml 不含当前时间源", not today_markers,
          "命中: %s（模板固定值 2013-12-23 除外）" % today_markers if today_markers else "")

    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n复核汇总: %d/%d 通过" % (n_pass, len(RESULTS)))
    if n_pass != len(RESULTS):
        print("失败项: %s" % "、".join(n for n, ok, _ in RESULTS if not ok))
        return 1
    print("VERIFY EXIT=0 —— 全部复核通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
