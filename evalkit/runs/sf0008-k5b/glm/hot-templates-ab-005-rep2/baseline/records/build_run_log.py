#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从实际捕获的 records/ 与 out/ 现场派生 run_log.json（不手填可推导字段）。"""
import hashlib
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = "/home/pan-ding/workspace/skill工厂/skillfactory/dist/hot-templates-skill/scripts/gen.py"

CALLS = [
    {
        "call_id": 1,
        "purpose": "验收①确定性复跑 第1次（相同输入）",
        "command": "python3 %s --platform dy --topic '确定性复跑主题' --points '[\"要点甲\", \"要点乙\", \"要点丙\"]' --outdir out/run1" % GEN,
        "input": {"platform": "dy", "topic": "确定性复跑主题",
                  "points": ["要点甲", "要点乙", "要点丙"],
                  "points_form": "inline JSON string",
                  "outdir": "out/run1"},
        "exit_code": 0,
        "record_prefix": "run1",
        "outdir": "out/run1",
        "expectation": "exit 0；stdout 一行 OK 摘要；outdir 下骨架.md 与 structure.json 两文件非空",
        "note": "",
    },
    {
        "call_id": 2,
        "purpose": "验收①确定性复跑 第2次（相同输入，不同输出目录）",
        "command": "python3 %s --platform dy --topic '确定性复跑主题' --points '[\"要点甲\", \"要点乙\", \"要点丙\"]' --outdir out/run2" % GEN,
        "input": {"platform": "dy", "topic": "确定性复跑主题",
                  "points": ["要点甲", "要点乙", "要点丙"],
                  "points_form": "inline JSON string",
                  "outdir": "out/run2"},
        "exit_code": 0,
        "record_prefix": "run2",
        "outdir": "out/run2",
        "expectation": "exit 0；stdout 一行 OK 摘要；outdir 下骨架.md 与 structure.json 两文件非空",
        "note": "",
    },
    {
        "call_id": 3,
        "purpose": "验收②非法 platform（bilibili）",
        "command": "python3 %s --platform bilibili --topic '确定性复跑主题' --points '[\"要点甲\", \"要点乙\", \"要点丙\"]' --outdir out/invalid-platform" % GEN,
        "input": {"platform": "bilibili", "topic": "确定性复跑主题",
                  "points": ["要点甲", "要点乙", "要点丙"],
                  "points_form": "inline JSON string",
                  "outdir": "out/invalid-platform"},
        "exit_code": 2,
        "record_prefix": "run3",
        "outdir": "out/invalid-platform",
        "expectation": "exit 2；stderr 为 argparse 英文 invalid choice 报错（SKILL.md 判为预期）；输出目录不被创建",
        "note": "stderr 来自 argparse（英文报错），符合 SKILL.md 失败判据中『非法 platform 时为 argparse 英文报错，属预期』",
    },
    {
        "call_id": 4,
        "purpose": "验收②空 topic（纯空白串 '   '）",
        "command": "python3 %s --platform dy --topic '   ' --points '[\"要点甲\", \"要点乙\", \"要点丙\"]' --outdir out/empty-topic" % GEN,
        "input": {"platform": "dy", "topic": "   ",
                  "points": ["要点甲", "要点乙", "要点丙"],
                  "points_form": "inline JSON string",
                  "outdir": "out/empty-topic"},
        "exit_code": 2,
        "record_prefix": "run4",
        "outdir": "out/empty-topic",
        "expectation": "exit 2；stderr 含 [gen.py] 错误：--topic 不能为空；输出目录不被创建",
        "note": "",
    },
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


calls_out = []
for c in CALLS:
    prefix = c["record_prefix"]
    outdir_abs = os.path.join(BASE, c["outdir"])
    outdir_created = os.path.isdir(outdir_abs)
    files = []
    if outdir_created:
        for name in sorted(os.listdir(outdir_abs)):
            p = os.path.join(outdir_abs, name)
            files.append({"path": os.path.join(c["outdir"], name),
                          "bytes": os.path.getsize(p),
                          "sha256": sha256(p)})
    stdout = read_text(os.path.join(BASE, "records", prefix + ".stdout"))
    stderr = read_text(os.path.join(BASE, "records", prefix + ".stderr"))
    stdout_summary = stdout.strip() if stdout.strip() else "(empty)"
    stderr_lines = [ln for ln in stderr.splitlines()]
    stderr_summary = stderr_lines[-1].strip() if stderr_lines else "(empty)"

    c["input"]["outdir_abs"] = outdir_abs
    verdict = "PASS"
    if c["call_id"] in (1, 2):
        ok = (c["exit_code"] == 0 and stdout_summary.startswith("OK ")
              and len(files) == 2 and all(f["bytes"] > 0 for f in files))
        verdict = "PASS" if ok else "FAIL"
    else:
        ok = (c["exit_code"] == 2 and not outdir_created and stderr_summary != "(empty)")
        verdict = "PASS" if ok else "FAIL"

    calls_out.append({
        "call_id": c["call_id"],
        "purpose": c["purpose"],
        "command": c["command"],
        "input": c["input"],
        "exit_code": c["exit_code"],
        "stdout_summary": stdout_summary,
        "stderr_summary": stderr_summary,
        "stderr_raw_lines": stderr_lines,
        "outdir_created": outdir_created,
        "files": files,
        "expectation": c["expectation"],
        "verdict": verdict,
        "note": c["note"],
    })

# 确定性比对（cmp 子进程实跑 + sha256）
det = {"method": "cmp 逐字节比对 + sha256", "files": {}, "verdict": "PASS"}
for name in ("骨架.md", "structure.json"):
    a = os.path.join(BASE, "out/run1", name)
    b = os.path.join(BASE, "out/run2", name)
    proc = subprocess.run(["cmp", a, b], capture_output=True, text=True)
    det["files"][name] = {
        "file_a": "out/run1/" + name,
        "file_b": "out/run2/" + name,
        "cmp_exit_code": proc.returncode,
        "identical": proc.returncode == 0,
        "cmp_output": proc.stdout.strip() if proc.stdout.strip() else "(no output, files identical)",
        "sha256_file_a": sha256(a),
        "sha256_file_b": sha256(b),
        "sha256_equal": sha256(a) == sha256(b),
    }
    if not (proc.returncode == 0 and sha256(a) == sha256(b)):
        det["verdict"] = "FAIL"
det["conclusion"] = ("两次生成产物逐字节一致：骨架.md 与 structure.json 的 cmp 退出码均为 0，"
                     "sha256 两两相等。") if det["verdict"] == "PASS" else "存在不一致，见 files 明细。"

all_pass = all(c["verdict"] == "PASS" for c in calls_out) and det["verdict"] == "PASS"
log = {
    "task": "hot-templates 工程性验收：① 同输入确定性复跑逐字节比对；② 非法 platform 与空 topic 的失败路径",
    "skill": "hot-templates@1.0.0",
    "generator": GEN,
    "python": subprocess.run([sys.executable, "--version"], capture_output=True,
                             text=True).stdout.strip(),
    "working_directory": BASE,
    "generation_call_count": len(calls_out),
    "calls": calls_out,
    "determinism_check": det,
    "overall_conclusion": ("4/4 调用全部符合预期：同输入两次生成产物逐字节一致（cmp=0、sha256 相等）；"
                           "非法 platform=bilibili 与空白 topic 均以 exit 2 失败、stderr 报错符合预期形态、"
                           "未创建任何输出目录。原始 stdout/stderr 捕获留存于 records/ 目录。"
                           ) if all_pass else "存在 FAIL 项，见各 call 的 verdict 与 determinism_check。",
}

out_path = os.path.join(BASE, "run_log.json")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("written:", out_path, "all_pass=", all_pass)
