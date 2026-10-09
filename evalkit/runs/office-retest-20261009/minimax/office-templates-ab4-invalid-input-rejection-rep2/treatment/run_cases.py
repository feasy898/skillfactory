#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4-invalid-input-rejection 测试装置。

对引擎入口 gen_doc.py 施加四组非法输入 + 一组合法对照组，逐组记录
完整命令、退出码、stderr 摘要、产物残留检查（该次调用是否创建了输出
目录 / 写出了 文书.docx 或 fields.json 等任何文件）。

只读地驱动引擎、自己不做判定替身：所有判定均取自子进程的真实
stdout/stderr/退出码与文件系统实测。
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / ".zcode" / "skills" / "office-templates"
ENTRY = SKILL / "scripts" / "gen_doc.py"
DATA = ROOT / "fixtures" / "周报" / "case1.json"

PY = os.environ.get("OFFICE_PYTHON") or sys.executable


def snapshot(root: Path) -> set:
    """递归列出 root 下所有路径（相对字符串），用于残留比对。"""
    out = set()
    if not root.exists():
        return out
    for p in root.rglob("*"):
        out.add(str(p.relative_to(root)))
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def run_group(group: str, note: str, argv: list, outdir: Path, expect: str) -> dict:
    """执行一次调用并记录全部观测量。outdir 必须事前不存在。"""
    pre_existed = outdir.exists()
    before = snapshot(ROOT)

    proc = subprocess.run([PY, str(ENTRY)] + argv,
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")

    after = snapshot(ROOT)
    new_paths = sorted(after - before)
    outdir_created = outdir.exists()
    artifacts = sorted(str(p.relative_to(ROOT)) for p in outdir.rglob("*")) if outdir_created else []

    cmd_str = " ".join([PY, str(ENTRY.relative_to(ROOT))] + argv)
    return {
        "group": group,
        "note": note,
        "expected": expect,
        "command": cmd_str,
        "argv": argv,
        "outdir": str(outdir.relative_to(ROOT)),
        "outdir_existed_before": pre_existed,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "residue": {
            "outdir_created_by_this_call": outdir_created,
            "files_under_outdir": artifacts,
            "any_file_created_in_workdir": new_paths,
        },
    }


def main() -> int:
    # 记录环境
    env = {
        "python": PY,
        "python_version": subprocess.run([PY, "-V"], capture_output=True, text=True).stdout.strip(),
        "entry": str(ENTRY.relative_to(ROOT)),
        "entry_sha256": sha256(ENTRY),
        "python_docx": subprocess.run(
            [PY, "-c", "import docx;print(getattr(docx,'__version__','unknown'))"],
            capture_output=True, text=True).stdout.strip(),
    }

    # ---- 合法对照组 ----
    ok_out = ROOT / "out" / "周报" / "case1"
    if ok_out.exists():
        shutil.rmtree(ok_out)
    g5 = run_group(
        "G5-合法对照", "fixtures/周报/case1.json（全部字段齐备）",
        ["--template", "周报", "--data", "fixtures/周报/case1.json",
         "--outdir", "out/周报/case1"],
        ok_out, expect="exit=0 且 out/周报/case1 下恰有 文书.docx + fields.json")
    g5["artifacts"] = []
    if ok_out.exists():
        for name in ("文书.docx", "fields.json"):
            p = ok_out / name
            if p.is_file():
                g5["artifacts"].append({
                    "file": str(p.relative_to(ROOT)),
                    "bytes": p.stat().st_size,
                    "sha256": sha256(p),
                })
        extra = [str(p.relative_to(ROOT)) for p in sorted(ok_out.rglob("*"))
                 if p.name not in ("文书.docx", "fields.json")]
        g5["unexpected_files_under_outdir"] = extra
        fields = json.loads((ok_out / "fields.json").read_text(encoding="utf-8"))
        g5["fields_summary"] = fields.get("summary")
        g5["fields_title"] = fields.get("title")

    # ---- 四组非法输入 ----
    groups = []
    groups.append(run_group(
        "G1-非法模板名", "--template 证书（不在四类模板名之内）",
        ["--template", "证书", "--data", "fixtures/周报/case1.json",
         "--outdir", "out/invalid/g1_证书"],
        ROOT / "out" / "invalid" / "g1_证书", expect="exit=2，stderr 中文报错，零产物残留"))

    groups.append(run_group(
        "G2-数据文件不存在", "--data 指向不存在的文件",
        ["--template", "周报", "--data", "fixtures/周报/不存在的数据.json",
         "--outdir", "out/invalid/g2_missing"],
        ROOT / "out" / "invalid" / "g2_missing", expect="exit=2，stderr 中文报错，零产物残留"))

    groups.append(run_group(
        "G3-JSON解析失败", "--data 指向内容为「不是JSON」的文件",
        ["--template", "周报", "--data", "invalid_inputs/not_json.json",
         "--outdir", "out/invalid/g3_not_json"],
        ROOT / "out" / "invalid" / "g3_not_json", expect="exit=2，stderr 中文报错，零产物残留"))

    groups.append(run_group(
        "G4-顶层非对象", '--data 指向内容为 ["数组","非对象"] 的文件',
        ["--template", "周报", "--data", "invalid_inputs/top_level_array.json",
         "--outdir", "out/invalid/g4_array"],
        ROOT / "out" / "invalid" / "g4_array", expect="exit=2，stderr 中文报错，零产物残留"))

    # ---- G6：必填缺失不算非法（应 exit 0 而非被拒）----
    miss_dir = ROOT / "invalid_inputs" / "missing_required.json"
    miss_dir.write_text(json.dumps({
        "部门": "研发部",
        "填报人": "王小明",
        "周期": "2026-09-21 至 2026-09-27",
        "本周工作内容": ["完成打分器 v0.9 与评测台联调"],
        # 故意缺：下周工作计划（必填列表）
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    g6 = run_group(
        "G6-必填缺失", "缺必填「下周工作计划」，按 F7/C3 不得判为非法",
        ["--template", "周报", "--data", "invalid_inputs/missing_required.json",
         "--outdir", "probe/g6_missing_required"],
        ROOT / "probe" / "g6_missing_required",
        expect="exit=0 且正常产出（必填缺失记 missing_required 而非错误）")
    if (ROOT / "probe" / "g6_missing_required").exists():
        g6["fields_summary"] = json.loads(
            (ROOT / "probe" / "g6_missing_required" / "fields.json")
            .read_text(encoding="utf-8")).get("summary")

    log = {"env": env,
           "groups": [g1 := groups[0], groups[1], groups[2], groups[3], g5, g6]}
    log["groups"] = [groups[0], groups[1], groups[2], groups[3], g5, g6]
    (ROOT / "run_log_raw.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for g in log["groups"]:
        print("%-16s exit=%-3s outdir_created=%-5s files=%s"
              % (g["group"], g["exit_code"],
                 g["residue"]["outdir_created_by_this_call"],
                 g["residue"]["files_under_outdir"]))
        if g["stderr"]:
            print("   stderr: " + g["stderr"].splitlines()[0][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())