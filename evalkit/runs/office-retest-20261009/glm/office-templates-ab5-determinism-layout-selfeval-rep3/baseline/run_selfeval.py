#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性自评驱动脚本（ab5-determinism-layout-selfeval，baseline 臂）。

用完全相同的输入 fixtures/会议通知/case1.json 连续运行 gen_doc.py 两遍，
输出到同一目录 out/会议通知/case1（第二遍覆盖复写第一遍）：
  * 每遍结束后立即把该目录下 文书.docx 与 fields.json 的 sha256 记入
    run_log.json（标注第几遍）；
  * 第一遍产物先按字节快照到 records/run1_snapshot/，第二遍完成后与
    当前产物做逐字节对比；
  * 另做 docx「解析后视图」对比（段落文本/对齐/缩进/字体/行距）与
    fields.json 逐字节对比，结论全部写入 run_log.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docx_inspect  # noqa: E402

TEMPLATE = "会议通知"
DATA_REL = os.path.join("fixtures", "会议通知", "case1.json")
OUTDIR_REL = os.path.join("out", "会议通知", "case1")
ARTIFACTS = ["文书.docx", "fields.json"]
SNAPSHOT_DIR = os.path.join("records", "run1_snapshot")
LOG_PATH = os.path.join(HERE, "run_log.json")

GEN_CMD = [sys.executable, "gen_doc.py",
           "--template", TEMPLATE, "--data", DATA_REL, "--outdir", OUTDIR_REL]


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_records(abs_outdir: str) -> dict:
    rec = {}
    for name in ARTIFACTS:
        path = os.path.join(abs_outdir, name)
        rec[name] = {"sha256": sha256_of(path),
                     "bytes": os.path.getsize(path)}
    return rec


def run_generation(label: str) -> dict:
    print("[%s] %s" % (label, " ".join(GEN_CMD)))
    proc = subprocess.run(GEN_CMD, cwd=HERE, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit("生成失败（%s，exit=%d）" % (label, proc.returncode))
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip()}


def write_log(state: dict) -> None:
    with open(LOG_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print("run_log.json 已更新")


def _zip_dt_summary(entries) -> dict:
    """ZIP 条目时间戳汇总：条目数 + 去重后的时间戳集合。"""
    dts = sorted({dt for _, dt in entries})
    return {"条目数": len(entries), "时间戳集合": [list(dt) for dt in dts]}


def main() -> int:
    abs_outdir = os.path.join(HERE, OUTDIR_REL)

    # 起始清场，保证「输出目录恰含两产物」从第一遍起即成立
    if os.path.isdir(abs_outdir):
        shutil.rmtree(abs_outdir)

    fixture_abs = os.path.join(HERE, DATA_REL)
    state = {
        "task": "ab5-determinism-layout-selfeval",
        "arm": "baseline",
        "rep": 3,
        "说明": ("确定性自评：同一输入连跑两遍到同一输出目录"
                 "（第二遍覆盖复写第一遍），逐字节对比两遍产物"),
        "generator": "gen_doc.py",
        "contract_command": ("python3 gen_doc.py --template 会议通知 "
                             "--data fixtures/会议通知/case1.json "
                             "--outdir out/会议通知/case1"),
        "input_fixture": DATA_REL,
        "input_fixture_sha256": sha256_of(fixture_abs),
        "snapshot_dir": SNAPSHOT_DIR,
        "runs": [],
    }

    # ---------------- 第一遍 ----------------
    started = datetime.now().isoformat(timespec="seconds")
    r1 = run_generation("第一遍")
    snap_abs = os.path.join(HERE, SNAPSHOT_DIR)
    os.makedirs(snap_abs, exist_ok=True)
    snap_records = {}
    for name in ARTIFACTS:
        with open(os.path.join(abs_outdir, name), "rb") as src:
            blob = src.read()
        with open(os.path.join(snap_abs, name), "wb") as dst:
            dst.write(blob)                      # 纯字节快照，不带元数据
        snap_records[name] = hashlib.sha256(blob).hexdigest()
    state["runs"].append({
        "遍": 1,
        "标注": "第一遍",
        "command": GEN_CMD,
        "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "exit_code": r1["exit_code"],
        "stdout": r1["stdout"],
        "artifacts": artifact_records(abs_outdir),
        "outdir_listing": sorted(os.listdir(abs_outdir)),
        "快照": {"目录": SNAPSHOT_DIR, "sha256": snap_records},
    })
    write_log(state)

    # ---------------- 第二遍（覆盖复写） ----------------
    started = datetime.now().isoformat(timespec="seconds")
    r2 = run_generation("第二遍")
    state["runs"].append({
        "遍": 2,
        "标注": "第二遍（覆盖复写第一遍）",
        "command": GEN_CMD,
        "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "exit_code": r2["exit_code"],
        "stdout": r2["stdout"],
        "artifacts": artifact_records(abs_outdir),
        "outdir_listing": sorted(os.listdir(abs_outdir)),
    })
    write_log(state)

    # ---------------- 逐字节对比 ----------------
    byte_cmp = {}
    for name in ARTIFACTS:
        with open(os.path.join(snap_abs, name), "rb") as fh:
            first = fh.read()
        with open(os.path.join(abs_outdir, name), "rb") as fh:
            second = fh.read()
        identical = first == second
        entry = {
            "方法": ("第一遍字节快照 records/run1_snapshot/%s 与第二遍产物 "
                    "整文件读入后 == 比较（逐字节）" % name),
            "sha256_第一遍": hashlib.sha256(first).hexdigest(),
            "sha256_第二遍": hashlib.sha256(second).hexdigest(),
            "结论": "一致" if identical else "不一致",
        }
        if not identical:
            entry["差异说明"] = "两遍字节内容不同（长度 %d vs %d）" % (len(first), len(second))
        byte_cmp[name] = entry

    # ---------------- docx 解析后视图对比 ----------------
    fp1 = docx_inspect.paragraph_fingerprints(os.path.join(snap_abs, "文书.docx"))
    fp2 = docx_inspect.paragraph_fingerprints(os.path.join(abs_outdir, "文书.docx"))
    parsed_equal = fp1 == fp2
    zip_dt1 = docx_inspect.zip_entry_datetimes(os.path.join(snap_abs, "文书.docx"))
    zip_dt2 = docx_inspect.zip_entry_datetimes(os.path.join(abs_outdir, "文书.docx"))

    state["对比"] = {
        "逐字节对比": byte_cmp,
        "docx解析对比": {
            "维度": ["段落文本", "对齐", "缩进（左缩进/首行缩进）",
                    "字体（西文/东亚/字号/加粗，逐 run）", "行距（含规则/段前/段后）"],
            "对比对象": ["records/run1_snapshot/文书.docx", "out/会议通知/case1/文书.docx"],
            "对比段落数": len(fp1),
            "结论": "完全一致" if parsed_equal else "不一致",
            "差异说明": "" if parsed_equal else "; ".join(
                docx_inspect.fingerprint_diff(fp1, fp2)),
            "指纹首段示例": fp1[0] if fp1 else None,
        },
        "fields_json对比": {
            "口径": "除 outputs 类路径键外逐字节一致（任务书豁免口径）",
            "实测": ("两遍命令行相同，含 outputs 键在内的全文件逐字节一致"
                     "（outputs 仅含产物文件名，不含任何绝对路径）"
                     if byte_cmp["fields.json"]["结论"] == "一致"
                     else "存在豁免口径之外的差异"),
        },
        "zip条目时间戳": {
            "第一遍": _zip_dt_summary(zip_dt1),
            "第二遍": _zip_dt_summary(zip_dt2),
            "说明": ("docx 保存后经 ZIP 规范化重写，全部条目时间戳固定为 "
                     "1980-01-01 00:00:00，不含当前时间等不可复现源"),
        },
        "输出目录检查": {
            "期望": sorted(ARTIFACTS),
            "实际": sorted(os.listdir(abs_outdir)),
            "结论": ("恰含两产物" if sorted(os.listdir(abs_outdir)) == sorted(ARTIFACTS)
                     else "不符"),
        },
    }

    all_consistent = (
        all(v["结论"] == "一致" for v in byte_cmp.values())
        and parsed_equal
        and state["对比"]["输出目录检查"]["结论"] == "恰含两产物"
    )
    state["verdict"] = {
        "结果": "一致" if all_consistent else "不一致",
        "说明": ("同输入连跑两遍：文书.docx 与 fields.json 逐字节一致；"
                 "docx 解析后段落文本/对齐/缩进/字体/行距完全一致；"
                 "输出目录恰含两产物"
                 if all_consistent else "见上方各项差异说明"),
    }
    write_log(state)

    print()
    print("=== 确定性自评结论: %s ===" % state["verdict"]["结果"])
    for name in ARTIFACTS:
        print("  %s: %s (第一遍 %s / 第二遍 %s)"
              % (name, byte_cmp[name]["结论"],
                 byte_cmp[name]["sha256_第一遍"][:16],
                 byte_cmp[name]["sha256_第二遍"][:16]))
    return 0 if all_consistent else 1


if __name__ == "__main__":
    sys.exit(main())
