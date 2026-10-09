#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4-invalid-input-rejection 用例执行器（baseline 臂）。

逐组施加输入、以子进程方式调用 gen.py，记录完整命令 / 退出码 / stderr 摘要，
并用「执行前后文件系统快照比对」检查该次调用是否留下任何产物残留，
最终落盘 run_log.json。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ARM_DIR = Path(__file__).resolve().parent
PY = sys.executable
GEN = str(ARM_DIR / "gen.py")

EXIT_OK = 0
EXIT_INVALID_INPUT = 2

# 这些是执行前就存在的输入/脚本，不算「本次调用产生的产物」。
PRE_EXISTING_PREFIXES = ("fixtures", "invalid_inputs", "extra_inputs")
PRE_EXISTING_FILES = {
    "brief.md",
    "README.md",
    "gen.py",
    "run_cases.py",
    "run_log.json",
}

CASES = [
    {
        "id": "invalid-template",
        "group": "①",
        "label": "模板名非法：--template 证书",
        "kind": "invalid",
        "argv": ["--template", "证书", "--data", "fixtures/周报/case1.json"],
        "rationale": "「证书」不在模板登记表内，属非法模板名。",
    },
    {
        "id": "missing-data-file",
        "group": "②",
        "label": "数据文件不存在：--data invalid_inputs/does-not-exist.json",
        "kind": "invalid",
        "argv": [
            "--template",
            "周报",
            "--data",
            "invalid_inputs/does-not-exist.json",
        ],
        "rationale": "--data 指向不存在的路径。",
    },
    {
        "id": "not-json",
        "group": "③",
        "label": "JSON 解析失败：--data invalid_inputs/not-json.txt（内容「不是JSON」）",
        "kind": "invalid",
        "argv": ["--template", "周报", "--data", "invalid_inputs/not-json.txt"],
        "rationale": "文件存在且可读，但内容不是合法 JSON。",
    },
    {
        "id": "top-level-not-object",
        "group": "④",
        "label": '顶层非对象：--data invalid_inputs/top-level-array.json（内容 ["数组","非对象"]）',
        "kind": "invalid",
        "argv": [
            "--template",
            "周报",
            "--data",
            "invalid_inputs/top-level-array.json",
        ],
        "rationale": "JSON 合法但顶层是数组，不是对象。",
    },
    {
        "id": "valid-control",
        "group": "对照",
        "label": "合法对照组：--template 周报 --data fixtures/周报/case1.json",
        "kind": "valid",
        "argv": ["--template", "周报", "--data", "fixtures/周报/case1.json"],
        "rationale": "唯一合法输入，应成功出两份产物。",
    },
    {
        "id": "missing-required-not-rejected",
        "group": "补测",
        "label": "必填缺失不算非法：--data extra_inputs/missing-required.json（输出到 .scratch/）",
        "kind": "boundary",
        "argv": [
            "--template",
            "周报",
            "--data",
            "extra_inputs/missing-required.json",
            "--outdir",
            ".scratch/missing-required",
        ],
        "rationale": "缺 周期/下周工作计划/问题与需协调事项 三个字段；"
        "任务书明确要求不得把缺失当错误拒绝，应退出码 0 且字段占位。"
        "为不污染约定的 out/ 产物布局，该组输出改写到 .scratch/ 并在记录后清理。",
    },
]

CJK_RE = re.compile(r"[一-鿿　-〿＀-￯]")


def snapshot():
    """递归列出臂目录下所有「非输入」路径，用于前后比对。"""
    found = set()
    for root, dirs, files in os.walk(ARM_DIR):
        rel_root = Path(root).relative_to(ARM_DIR)
        parts = rel_root.parts
        if parts and parts[0] in PRE_EXISTING_PREFIXES:
            continue
        # .scratch/ 不排除：补测组的产物需要能被快照差集看见。
        for name in list(dirs) + files:
            rel = rel_root / name
            if rel.parts and rel.parts[0] in PRE_EXISTING_PREFIXES:
                continue
            if len(rel.parts) == 1 and rel.name in PRE_EXISTING_FILES:
                continue
            found.add(str(rel))
    return found


def run_case(case):
    argv = [PY, GEN] + case["argv"]
    before = snapshot()
    proc = subprocess.run(
        argv, cwd=str(ARM_DIR), capture_output=True, text=True, timeout=120
    )
    after = snapshot()
    created = sorted(after - before)

    stderr = proc.stderr.strip()
    stdout = proc.stdout.strip()
    record = {
        "id": case["id"],
        "group": case["group"],
        "label": case["label"],
        "kind": case["kind"],
        "rationale": case["rationale"],
        "command": " ".join(argv),
        "command_argv": argv,
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr_excerpt": stderr if len(stderr) <= 600 else stderr[:600] + " ……（已截断）",
        "stderr_has_chinese": bool(CJK_RE.search(stderr)),
        "artifact_residue": {
            "checked_scope": "臂目录下全部非输入文件/目录（执行前后快照比对）",
            "created_paths": created,
            "created_count": len(created),
            "no_residue": created == [],
        },
    }
    return record, created


def check_invalid(rec):
    checks = {
        "exit_code_is_2": rec["exit_code"] == EXIT_INVALID_INPUT,
        "stderr_has_chinese_message": rec["stderr_has_chinese"],
        "zero_artifact_residue": rec["artifact_residue"]["no_residue"],
    }
    checks["verdict"] = "pass" if all(checks.values()) else "fail"
    return checks


def check_valid(rec, arm_dir):
    case_dir = arm_dir / "out" / "周报" / "case1"
    docx = case_dir / "文书.docx"
    fields = case_dir / "fields.json"
    checks = {
        "exit_code_is_0": rec["exit_code"] == EXIT_OK,
        "docx_exists": docx.is_file(),
        "fields_json_exists": fields.is_file(),
        "docx_is_valid_zip": bool(docx.is_file() and zipfile.is_zipfile(str(docx))),
    }
    docx_size = docx.stat().st_size if docx.is_file() else 0
    checks["docx_size_bytes"] = docx_size
    checks["docx_nonempty"] = docx_size > 0
    fields_doc = None
    if fields.is_file():
        try:
            fields_doc = json.loads(fields.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            checks["fields_json_parses"] = False
            checks["fields_json_error"] = str(exc)
        else:
            checks["fields_json_parses"] = True
            checks["fields_json_missing_empty"] = fields_doc.get("missing_fields") == []
    expected_created = [
        "out",
        "out/周报",
        "out/周报/case1",
        "out/周报/case1/fields.json",
        "out/周报/case1/文书.docx",
    ]
    checks["artifacts_created_as_expected"] = (
        sorted(rec["artifact_residue"]["created_paths"]) == sorted(expected_created)
    )
    verdict_inputs = [
        checks["exit_code_is_0"],
        checks["docx_exists"],
        checks["fields_json_exists"],
        checks["docx_is_valid_zip"],
        checks["docx_nonempty"],
        checks.get("fields_json_parses", False),
        checks["artifacts_created_as_expected"],
    ]
    checks["verdict"] = "pass" if all(verdict_inputs) else "fail"
    return checks, fields_doc


def check_boundary(rec):
    created = rec["artifact_residue"]["created_paths"]
    checks = {
        "exit_code_is_0": rec["exit_code"] == EXIT_OK,
        "not_rejected_as_invalid": rec["exit_code"] != EXIT_INVALID_INPUT,
        "docx_exists": str(Path(".scratch/missing-required/周报/missing-required/文书.docx"))
        in created,
        "fields_json_exists": str(
            Path(".scratch/missing-required/周报/missing-required/fields.json")
        )
        in created,
    }
    fields_file = ARM_DIR / ".scratch/missing-required/周报/missing-required/fields.json"
    if fields_file.is_file():
        doc = json.loads(fields_file.read_text(encoding="utf-8"))
        checks["missing_fields_detected"] = doc.get("missing_fields") == [
            "周期",
            "下周工作计划",
            "问题与需协调事项",
        ]
        checks["missing_fields_placeholder_filled"] = all(
            item["value"] == "（未填写）"
            for item in doc.get("fields", [])
            if item["key"] in doc.get("missing_fields", [])
        )
    verdict_inputs = [v for k, v in checks.items() if isinstance(v, bool)]
    checks["verdict"] = "pass" if all(verdict_inputs) else "fail"
    return checks


def main():
    records = []
    for case in CASES:
        rec, _ = run_case(case)
        if case["kind"] == "invalid":
            rec["checks"] = check_invalid(rec)
        elif case["kind"] == "valid":
            checks, fields_doc = check_valid(rec, ARM_DIR)
            rec["checks"] = checks
            if fields_doc:
                rec["fields_json_preview"] = {
                    "template": fields_doc.get("template"),
                    "missing_fields": fields_doc.get("missing_fields"),
                    "fields": [
                        {"key": f["key"], "present": f["present"], "value": f["value"]}
                        for f in fields_doc.get("fields", [])
                    ],
                }
        else:
            rec["checks"] = check_boundary(rec)
        records.append(rec)
        print(
            "[%s] exit=%s verdict=%s residue=%s"
            % (
                case["id"],
                rec["exit_code"],
                rec["checks"]["verdict"],
                rec["artifact_residue"]["created_paths"],
            )
        )

    scratch = ARM_DIR / ".scratch"
    scratch_existed = scratch.exists()
    if scratch_existed:
        shutil.rmtree(scratch)

    invalid_recs = [r for r in records if r["kind"] == "invalid"]
    valid_recs = [r for r in records if r["kind"] == "valid"]
    boundary_recs = [r for r in records if r["kind"] == "boundary"]

    summary = {
        "invalid_groups_total": len(invalid_recs),
        "invalid_groups_rejected_with_code_2": sum(
            1 for r in invalid_recs if r["exit_code"] == EXIT_INVALID_INPUT
        ),
        "invalid_groups_with_chinese_stderr": sum(
            1 for r in invalid_recs if r["stderr_has_chinese"]
        ),
        "invalid_groups_with_zero_residue": sum(
            1 for r in invalid_recs if r["artifact_residue"]["no_residue"]
        ),
        "valid_control_exit_0": all(r["exit_code"] == EXIT_OK for r in valid_recs),
        "valid_control_artifacts_ok": all(
            r["checks"]["verdict"] == "pass" for r in valid_recs
        ),
        "missing_required_not_rejected": all(
            r["checks"]["verdict"] == "pass" for r in boundary_recs
        ),
        "scratch_cleaned": not scratch.exists(),
        "all_cases_pass": all(r["checks"]["verdict"] == "pass" for r in records),
    }

    run_log = {
        "task": "office-templates-ab4-invalid-input-rejection",
        "arm": "baseline",
        "entrypoint": "gen.py",
        "interpreter": PY,
        "invocation_contract": {
            "usage": "gen.py --template <模板名> --data <JSON 文件> [--outdir <输出根目录>]",
            "invalid_input_exit_code": EXIT_INVALID_INPUT,
            "valid_exit_code": EXIT_OK,
            "artifacts": "out/<模板名>/<数据文件名>/文书.docx 与 out/<模板名>/<数据文件名>/fields.json",
            "missing_field_policy": "缺失字段按「（未填写）」占位，不拒绝、不计入非法输入",
        },
        "artifact_residue_method": "每次调用前后对臂目录做递归快照差集；"
        "fixtures/、invalid_inputs/、extra_inputs/ 与脚本自身视为执行前既有，不计入残留。",
        "cases": records,
        "summary": summary,
    }
    (ARM_DIR / "run_log.json").write_text(
        json.dumps(run_log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nsummary:", json.dumps(summary, ensure_ascii=False))
    return 0 if summary["all_cases_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())