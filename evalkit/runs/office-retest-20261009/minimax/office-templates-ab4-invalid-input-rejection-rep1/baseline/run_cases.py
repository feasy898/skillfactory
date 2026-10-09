#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4 非法输入拒绝行为测试驱动。

依次施加四组非法输入 + 一组合法对照，逐组记录到 run_log.json：
完整命令、退出码、stderr 摘要、产物残留检查。
"""

import json
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(BASE, "gen_doc.py")
OUT = os.path.join(BASE, "out")
TMP = os.path.join(BASE, "tmp_inputs")

EXIT_CODE_CONVENTION = 2


def snapshot_out():
    """记录 out/ 目录当前的完整文件清单（产物残留检查的基线）。"""
    if not os.path.isdir(OUT):
        return []
    found = []
    for root, _dirs, files in os.walk(OUT):
        for name in files:
            found.append(os.path.relpath(os.path.join(root, name), BASE))
    return sorted(found)


def run_case(group, desc, argv, expect_valid, cwd=BASE):
    """跑一组，记录退出码/stderr/残留。"""
    before = snapshot_out()
    proc = subprocess.run(
        [sys.executable] + argv,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    after = snapshot_out()

    created = sorted(set(after) - set(before))
    stderr_text = (proc.stderr or "").strip()
    stdout_text = (proc.stdout or "").strip()
    stderr_summary_lines = [ln for ln in stderr_text.splitlines() if ln.strip()]
    has_chinese = any(
        any("一" <= ch <= "鿿" for ch in ln) for ln in stderr_summary_lines
    )

    rec = {
        "group": group,
        "description": desc,
        "input_class": "合法" if expect_valid else "非法",
        "command": "python3 gen_doc.py " + " ".join(argv[1:]),
        "exit_code": proc.returncode,
        "stderr": stderr_text,
        "stderr_summary": stderr_summary_lines,
        "stderr_has_chinese": has_chinese,
        "stdout": stdout_text,
        "artifacts_before": before,
        "artifacts_after": after,
        "newly_created_files": created,
        "residue_free": created == [],
    }

    if expect_valid:
        case_dir = os.path.join(OUT, "周报", "case1")
        rec["expected_output_dir"] = "out/周报/case1"
        rec["expected_output_dir_exists"] = os.path.isdir(case_dir)
        rec["expected_artifacts"] = ["文书.docx", "fields.json"]
        rec["expected_artifacts_present"] = sorted(
            f for f in os.listdir(case_dir) if os.path.isfile(os.path.join(case_dir, f))
        ) if os.path.isdir(case_dir) else []
        rec["exit_code_matches_convention"] = proc.returncode == 0
    else:
        rec["expected_output_dir"] = None
        rec["exit_code_matches_convention"] = proc.returncode == EXIT_CODE_CONVENTION
        rec["rejected_with_convention_code"] = proc.returncode == EXIT_CODE_CONVENTION
        rec["rejected_with_chinese_stderr"] = has_chinese and proc.returncode != 0
        rec["created_out_dir"] = os.path.isdir(OUT) and not before and bool(created)
        rec["no_partial_artifact"] = created == []

    # 每组非法输入跑完后清场，保证下一组从零残留状态开始
    if not expect_valid:
        for rel in created:
            p = os.path.join(BASE, rel)
            if os.path.isfile(p):
                os.remove(p)
        if os.path.isdir(OUT) and not os.listdir(OUT):
            os.rmdir(OUT)

    return rec


def main():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    bad_json = os.path.join(TMP, "notjson.json")
    with open(bad_json, "w", encoding="utf-8") as fh:
        fh.write("这不是JSON，只是一段普通中文文本。\n")

    array_json = os.path.join(TMP, "array.json")
    with open(array_json, "w", encoding="utf-8") as fh:
        fh.write('["数组", "非对象"]')

    cases = [
        ("illegal-1-invalid-template", "--template 证书（模板名非法）",
         ["gen_doc.py", "--template", "证书", "--data", "fixtures/周报/case1.json"], False),
        ("illegal-2-data-file-missing", "--data 指向不存在的文件",
         ["gen_doc.py", "--template", "周报", "--data", "fixtures/周报/不存在.json"], False),
        ("illegal-3-json-parse-failure", "--data 指向内容为「不是JSON」的文件",
         ["gen_doc.py", "--template", "周报", "--data", bad_json], False),
        ("illegal-4-toplevel-not-object", "--data 指向内容为 [\"数组\",\"非对象\"] 的文件",
         ["gen_doc.py", "--template", "周报", "--data", array_json], False),
        ("legal-control", "合法对照组：fixtures/周报/case1.json",
         ["gen_doc.py", "--template", "周报", "--data", "fixtures/周报/case1.json"], True),
    ]

    records = [run_case(g, d, a, v) for g, d, a, v in cases]

    shutil.rmtree(TMP, ignore_errors=True)

    illegal = [r for r in records if r["input_class"] == "非法"]
    legal = [r for r in records if r["input_class"] == "合法"]
    log = {
        "task": "ab4-invalid-input-rejection",
        "arm": "baseline",
        "entry_point": "gen_doc.py",
        "python": sys.version.split()[0],
        "convention": {
            "invalid_exit_code": EXIT_CODE_CONVENTION,
            "invalid_stderr_language": "中文",
            "invalid_residue_policy": "零产物残留：不创建输出目录、不写半成品",
            "missing_required_field_policy": "必填缺失不算非法输入，占位符补齐并正常生成",
        },
        "cases": records,
        "summary": {
            "illegal_total": len(illegal),
            "illegal_rejected_with_exit_2": sum(
                1 for r in illegal if r["exit_code"] == EXIT_CODE_CONVENTION),
            "illegal_with_chinese_stderr": sum(
                1 for r in illegal if r["stderr_has_chinese"]),
            "illegal_with_zero_residue": sum(1 for r in illegal if r["residue_free"]),
            "legal_exit_0": sum(1 for r in legal if r["exit_code"] == 0),
            "legal_artifacts_ok": sum(
                1 for r in legal
                if r["expected_artifacts_present"] == ["fields.json", "文书.docx"]),
            "all_passed": (
                all(r["exit_code"] == EXIT_CODE_CONVENTION and r["stderr_has_chinese"]
                    and r["residue_free"] for r in illegal)
                and all(r["exit_code"] == 0
                        and r["expected_artifacts_present"] == ["fields.json", "文书.docx"]
                        for r in legal)
            ),
        },
    }

    with open(os.path.join(BASE, "run_log.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=2)

    print(json.dumps(log["summary"], ensure_ascii=False, indent=2))
    return 0 if log["summary"]["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
