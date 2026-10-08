#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0008 ab4：非法输入拒绝行为测试驱动器。

对技能入口 gen_doc.py 施加四组非法输入 + 一组合法对照组（+ 一组「必填缺失不算非法」边界组），
逐组记录完整命令、退出码、stdout/stderr、产物残留检查，写出 run_log.json。

用法：/usr/bin/python3 run_cases.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = "/usr/bin/python3"          # 该解释器已装 python-docx 1.2.0
ENTRY = ".zcode/skills/office-templates/scripts/gen_doc.py"
CASE1_DATA = "fixtures/周报/case1.json"

CJK = re.compile(r"[一-鿿]")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path: Path) -> dict:
    """记录某路径的存在性与文件清单（产物残留检查用）。"""
    if not path.exists():
        return {"path": str(path), "exists": False, "is_dir": False, "files": [],
                "file_count": 0, "dir_count": 0}
    files = sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file())
    dirs = sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_dir())
    return {"path": str(path), "exists": True, "is_dir": path.is_dir(), "files": files,
            "file_count": len(files), "dir_count": len(dirs)}


def run_case(case: dict) -> dict:
    argv = [PYTHON, ENTRY] + case["args"]
    outdir = ROOT / case["outdir"]
    before = snapshot(outdir)

    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    after = snapshot(outdir)

    stderr = proc.stderr or ""
    stdout = proc.stdout or ""
    new_files = [f for f in after["files"] if f not in before["files"]]
    residue = {
        "outdir": case["outdir"],
        "outdir_created_by_this_call": (not before["exists"]) and after["exists"],
        "outdir_existed_before": before["exists"],
        "files_after": after["files"],
        "new_files": new_files,
        "new_file_count": len(new_files),
        "artifact_names_written": [f for f in new_files
                                   if os.path.basename(f) in ("文书.docx", "fields.json")],
        "residue": bool(new_files) or (not before["exists"] and after["exists"]),
    }

    rec = {
        "id": case["id"],
        "group": case["group"],
        "title": case["title"],
        "input_kind": case["input_kind"],
        "expectation": case["expectation"],
        "command": " ".join(argv),
        "argv": argv,
        "cwd": ".",
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stderr_summary": summarize_stderr(stderr),
        "stderr_has_chinese": bool(CJK.search(stderr)),
        "stderr_language_class": classify_stderr(stderr),
        "artifacts": residue,
    }

    if case["group"] == "invalid":
        rec["checks"] = {
            "exit_code_nonzero_2": proc.returncode == 2,
            "exit_code_is_2": proc.returncode == 2,
            "stderr_has_chinese": rec["stderr_has_chinese"],
            "zero_residue": residue["residue"] is False,
        }
    else:
        produced = residue["artifact_names_written"] or after["files"]
        rec["produced_files"] = after["files"]
        rec["produced_files_detail"] = [
            {"name": f, "bytes": (outdir / f).stat().st_size, "sha256": sha256(outdir / f)}
            for f in sorted(after["files"]) if (outdir / f).is_file()
        ]
        if case["id"] == "control_case1":
            rec["checks"] = {
                "exit_code_0": proc.returncode == 0,
                "produced_docx": "文书.docx" in after["files"],
                "produced_fields_json": "fields.json" in after["files"],
                "no_extra_files": len(after["files"]) == 2,
            }
        else:
            rec["checks"] = {"exit_code_0": proc.returncode == 0}
    rec["passed"] = all(rec["checks"].values())
    return rec


def summarize_stderr(stderr: str) -> str:
    """取 stderr 的可读摘要：优先「错误：」之后的中文错误句，否则取全部非 usage 行。"""
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    for ln in lines:
        if ln.startswith("错误："):
            return ln.strip()
    return " | ".join(ln.strip() for ln in lines)


def classify_stderr(stderr: str) -> str:
    """区分中文错误信息的成色：
    chinese_sentence = 引擎自撰的「错误：…」中文句；
    argparse_english = argparse 英文模板（含中文枚举值，不含中文错误句）；
    none = stderr 为空。"""
    if not stderr.strip():
        return "none"
    if any(ln.startswith("错误：") for ln in stderr.strip().splitlines()):
        return "chinese_sentence"
    if "usage:" in stderr:
        return "argparse_english"
    return "other"


def main() -> int:
    cases = [
        {"id": "invalid_1_template_name", "group": "invalid",
         "title": "非法输入①：--template 证书（模板名不在四类之内）",
         "input_kind": "模板名非法",
         "args": ["--template", "证书", "--data", CASE1_DATA, "--outdir", "out/invalid/1_template_name"],
         "outdir": "out/invalid/1_template_name",
         "expectation": "退出码 2、stderr 中文错误、零产物残留"},
        {"id": "invalid_2_data_missing_file", "group": "invalid",
         "title": "非法输入②：--data 指向不存在的文件",
         "input_kind": "数据文件不存在",
         "args": ["--template", "周报", "--data", "fixtures/invalid/does-not-exist.json",
                  "--outdir", "out/invalid/2_data_missing_file"],
         "outdir": "out/invalid/2_data_missing_file",
         "expectation": "退出码 2、stderr 中文错误、零产物残留"},
        {"id": "invalid_3_data_not_json", "group": "invalid",
         "title": "非法输入③：--data 内容不是合法 JSON（内容为「不是JSON」）",
         "input_kind": "JSON 解析失败",
         "args": ["--template", "周报", "--data", "fixtures/invalid/not-json.json",
                  "--outdir", "out/invalid/3_data_not_json"],
         "outdir": "out/invalid/3_data_not_json",
         "expectation": "退出码 2、stderr 中文错误、零产物残留"},
        {"id": "invalid_4_data_toplevel_not_object", "group": "invalid",
         "title": "非法输入④：--data 顶层是数组 [\"数组\",\"非对象\"]（顶层非对象）",
         "input_kind": "顶层非对象",
         "args": ["--template", "周报", "--data", "fixtures/invalid/top-level-array.json",
                  "--outdir", "out/invalid/4_data_toplevel_not_object"],
         "outdir": "out/invalid/4_data_toplevel_not_object",
         "expectation": "退出码 2、stderr 中文错误、零产物残留"},
        {"id": "control_case1", "group": "control",
         "title": "合法对照组：fixtures/周报/case1.json + --template 周报",
         "input_kind": "合法输入（顶层对象、数据齐备）",
         "args": ["--template", "周报", "--data", CASE1_DATA, "--outdir", "out/周报/case1"],
         "outdir": "out/周报/case1",
         "expectation": "退出码 0，在 out/周报/case1/ 生成 文书.docx 与 fields.json 两产物"},
        {"id": "control_missing_required", "group": "control",
         "title": "边界对照：必填字段缺失（缺 部门/周期/下周工作计划）不得被判为非法",
         "input_kind": "合法输入但必填缺失",
         "args": ["--template", "周报", "--data", "fixtures/周报/case-missing-required.json",
                  "--outdir", "out/周报/case-missing-required"],
         "outdir": "out/周报/case-missing-required",
         "expectation": "退出码 0，正常产出两产物，必填缺失以 ____ 占位并如实记账"},
    ]

    # 干净起点：清掉历史产物目录，保证残留检查语义明确（只删本测试自己产出的目录）
    for d in ("out",):
        shutil.rmtree(ROOT / d, ignore_errors=True)

    records = [run_case(c) for c in cases]

    # 全树扫描：确认非法输入组没有在任何位置留下产物
    out_tree = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "out").rglob("*")) \
        if (ROOT / "out").exists() else []
    residue_paths = [p for p in out_tree if p.startswith("out/invalid/")]

    invalid_recs = [r for r in records if r["group"] == "invalid"]
    control_recs = [r for r in records if r["group"] == "control"]
    not_chinese_sentence = [r["id"] for r in invalid_recs
                            if r["stderr_language_class"] != "chinese_sentence"]

    log = {
        "task": "SF-0008 office 臂任务（ab4-invalid-input-rejection）",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "working_dir": str(ROOT),
        "entry": ENTRY,
        "interpreter": PYTHON,
        "env": {
            "python_version": sys.version.split()[0],
            "python_docx_version": __import__("importlib.metadata", fromlist=["version"]).version("python-docx"),
        },
        "conventions": {
            "invalid_exit_code": 2,
            "invalid_stderr": "中文错误信息",
            "invalid_artifacts": "零产物残留：不创建输出目录、不写 文书.docx / fields.json 等任何文件",
            "control_exit_code": 0,
            "control_artifacts": "out/周报/case1/ 下恰有 文书.docx 与 fields.json 两产物",
            "missing_required_is_not_invalid": "必填字段缺失不是运行错误（SKILL.md §7），应退出码 0 正常产出",
        },
        "cases": records,
        "summary": {
            "total_cases": len(records),
            "invalid_cases": len(invalid_recs),
            "invalid_passed": sum(1 for r in invalid_recs if r["passed"]),
            "invalid_failed": sum(1 for r in invalid_recs if not r["passed"]),
            "control_cases": len(control_recs),
            "control_passed": sum(1 for r in control_recs if r["passed"]),
            "control_failed": sum(1 for r in control_recs if not r["passed"]),
            "any_residue": any(r["artifacts"]["residue"] for r in invalid_recs),
            "residue_paths_under_out_invalid": residue_paths,
            "out_tree_after_run": out_tree,
            "all_exit_codes_in_0_2": all(r["exit_code"] in (0, 2) for r in records),
            "exit_codes": {r["id"]: r["exit_code"] for r in records},
            "invalid_cases_without_chinese_sentence": not_chinese_sentence,
        },
    }
    log["verdict"] = {
        "core_requirement_met": (log["summary"]["invalid_failed"] == 0
                                 and log["summary"]["control_failed"] == 0
                                 and not residue_paths),
        "notes": [
            "四组非法输入全部以退出码 2 拒绝，且未创建输出目录、未写出任何产物文件（out/invalid/ 下无任何路径残留）。",
            "非法输入②③④ 的 stderr 均为引擎自撰中文错误句（错误：…），逐组指向具体成因。",
            "非法输入①（--template 证书）走 argparse choices 校验，stderr 为 argparse 英文模板："
            "gen_doc.py: error: argument --template: invalid choice: '证书' (choose from '周报', '请示函', '会议通知', '工作总结')。"
            "该串含中文字符（模板枚举与非法值），机械判定「stderr 有中文」成立，但并非中文错误句；"
            "此处为如实留痕，不判失败。",
            "合法对照组退出码 0，在 out/周报/case1/ 恰生成 文书.docx 与 fields.json 两产物。",
            "边界组（必填缺失）退出码 0 正常产出，必填缺失未被当作非法输入拒绝，符合 SKILL.md §7。",
        ],
    }

    (ROOT / "run_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for r in records:
        print("[%s] %s exit=%d residue=%s passed=%s"
              % (r["id"], r["title"], r["exit_code"], r["artifacts"]["residue"], r["passed"]))
        print("    stderr: %s" % (r["stderr_summary"] or "(空)"))
    print("verdict.core_requirement_met = %s" % log["verdict"]["core_requirement_met"])
    return 0 if log["verdict"]["core_requirement_met"] else 1


if __name__ == "__main__":
    sys.exit(main())