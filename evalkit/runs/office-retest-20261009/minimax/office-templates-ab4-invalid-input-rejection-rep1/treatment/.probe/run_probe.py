#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4 非法输入拒绝行为探测：五组调用（4 非法 + 1 合法对照），逐组记录
完整命令 / 退出码 / stdout / stderr / 产物残留（输出目录是否被创建、是否写出任何文件）。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / ".probe"
ENTRY = ROOT / ".zcode/skills/office-templates/scripts/gen_doc.py"

# 非法组统一使用一个「应当永不出现」的输出目录，若被创建即视为残留。
RESIDUE_DIRS = {
    "case1_bad_template": PROBE / "out/case1_bad_template",
    "case2_missing_data": PROBE / "out/case2_missing_data",
    "case3_not_json": PROBE / "out/case3_not_json",
    "case4_top_level_array": PROBE / "out/case4_top_level_array",
}
# 合法对照组产物目录（任务书指定布局）：out/周报/case1
CONTROL_OUTDIR = ROOT / "out/周报/case1"
# 附加探针：必填缺失不算非法
MISSING_OUTDIR = PROBE / "out/case6_missing_required"

CASES = [
    ("case1_bad_template", "① --template 证书（模板名非法）", ["--template", "证书"],
     "fixtures/周报/case1.json", RESIDUE_DIRS["case1_bad_template"], False),
    ("case2_missing_data", "② --data 指向不存在的文件", ["--template", "周报"],
     "fixtures/周报/不存在的数据.json", RESIDUE_DIRS["case2_missing_data"], False),
    ("case3_not_json", "③ --data 指向内容为「不是JSON」的文件", ["--template", "周报"],
     ".probe/not_json.json", RESIDUE_DIRS["case3_not_json"], False),
    ("case4_top_level_array", "④ --data 指向内容为 [\"数组\",\"非对象\"] 的文件（顶层非对象）",
     ["--template", "周报"], ".probe/top_level_array.json",
     RESIDUE_DIRS["case4_top_level_array"], False),
    ("case5_control_legal", "⑤ 合法对照组：fixtures/周报/case1.json",
     ["--template", "周报"], "fixtures/周报/case1.json", CONTROL_OUTDIR, True),
    ("case6_missing_required", "⑥ 附加探针：必填缺失输入（不算非法，应 exit 0 并正常产出）",
     ["--template", "周报"], ".probe/missing_required.json", MISSING_OUTDIR, True),
]


def snapshot_dir(p: Path) -> dict:
    """目录快照：是否存在、递归文件清单（含 sha256 与字节数）。"""
    if not p.exists():
        return {"exists": False, "is_dir": False, "entries": []}
    entries = []
    for f in sorted(p.rglob("*")):
        if f.is_file():
            b = f.read_bytes()
            entries.append({
                "path": str(f.relative_to(p)),
                "bytes": len(b),
                "sha256": hashlib.sha256(b).hexdigest(),
            })
        else:
            entries.append({"path": str(f.relative_to(p)) + "/", "type": "dir"})
    return {"exists": True, "is_dir": p.is_dir(), "entries": entries}


def summarize(text: str, limit: int = 400) -> str:
    t = text.strip()
    if len(t) > limit:
        t = t[:limit] + " …（已截断）"
    return t


def main() -> int:
    # 干净起点：清掉上一轮遗留的输出目录
    for d in list(RESIDUE_DIRS.values()) + [CONTROL_OUTDIR, MISSING_OUTDIR]:
        if d.exists():
            shutil.rmtree(d)

    env = dict(os.environ)
    env["PYTHONPATH"] = "/home/pan-ding/.local/lib/python3.12/site-packages"

    results = []
    for cid, title, tpl_args, data, outdir, expect_ok in CASES:
        before = snapshot_dir(outdir)
        cmd = [sys.executable, str(ENTRY)] + tpl_args + ["--data", data,
                                                         "--outdir", str(outdir)]
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        after = snapshot_dir(outdir)
        file_names = [e.get("path", "") for e in after["entries"] if "path" in e]
        wrote = sorted(n for n in file_names if not n.endswith("/"))
        created = not before["exists"] and after["exists"]
        residue = {
            "outdir": str(outdir.relative_to(ROOT)) if outdir.is_relative_to(ROOT) else str(outdir),
            "outdir_existed_before": before["exists"],
            "outdir_created_by_this_call": created,
            "outdir_exists_after": after["exists"],
            "files_after": wrote,
            "file_count_after": len(wrote),
            "has_docx": "文书.docx" in wrote,
            "has_fields_json": "fields.json" in wrote,
            "zero_residue": (not after["exists"]) or (len(wrote) == 0),
        }
        results.append({
            "id": cid,
            "title": title,
            "expect": "exit 0 + 两产物" if expect_ok else "exit 2 + 零产物残留",
            "command": " ".join(
                ["python3"] + [str(ENTRY.relative_to(ROOT)) if c == str(ENTRY) else c
                               for c in cmd[1:]]),
            "command_full": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout": summarize(proc.stdout),
            "stderr": summarize(proc.stderr),
            "stderr_lines": [ln for ln in proc.stderr.strip().splitlines() if ln.strip()],
            "residue_check": residue,
        })

    out = {"cases": results}
    (PROBE / "probe_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())