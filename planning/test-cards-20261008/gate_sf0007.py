#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0007 门槛（planner 依 alpha 测试卡 howToJudge 落成，2026-10-08；开发方不得修改本脚本）。

用法：python3 gate_sf0007.py <venv-python 路径>
前置：planning/test-cards-20261008/base_commit.txt 存在本卡开工时的 HEAD 哈希。
退出码：0=全部 PASS；1=存在 FAIL。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/pan-ding/workspace/skill工厂/skillfactory")
VPY = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / ".venv-dev" / "bin" / "python")
results = []


def run(args, cwd=None, timeout=900):
    try:
        return subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None,
                              capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        class R:
            returncode = -1
            stdout = ""
            stderr = "spawn-error: %s" % e
        return R()


def check(cid, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + " " + cid + "  " + str(detail)[:400])


def git(*args):
    return run(["git", "-C", ROOT, *args])


base_file = ROOT / "planning/test-cards-20261008/base_commit.txt"
base = base_file.read_text(encoding="utf-8").strip() if base_file.exists() else ""
if not base:
    check("K5A-00", False, "base_commit.txt 缺失")
    print("== SF-0007 门槛: 0/1 PASS")
    sys.exit(1)

# K5A-01 变体 *.md 中 reference/ 引用不再悬空（整改后通常应零引用；如保留引用则必须真实存在）
pat = re.compile(r"reference/[\w./\-\u4e00-\u9fff]*")
dang = []
total = 0
build = ROOT / "dist/build"
if not build.is_dir():
    check("K5A-01", False, "dist/build 不存在")
else:
    for md in build.rglob("*.md"):
        rel = md.relative_to(build).parts
        if len(rel) < 3:
            continue
        pkgroot = build / rel[0] / rel[1]
        txt = md.read_text(encoding="utf-8", errors="replace")
        for m in pat.findall(txt):
            total += 1
            if not (pkgroot / m).exists():
                dang.append("%s:%s" % (md.relative_to(ROOT), m))
    check("K5A-01", not dang, "引用 %d 处，悬空 %d %s" % (total, len(dang), dang[:4]))

# K5A-02 WS2 全部门不回退
r = run([VPY, "tests/run_checks.py"], cwd=ROOT / "dist", timeout=900)
out = (r.stdout or "") + (r.stderr or "")
check("K5A-02", r.returncode == 0 and ("28" in out) and ("FAIL 0" in out or "PASS 28" in out),
      "exit=%s %s" % (r.returncode, out[-200:]))

# K5A-03 canonical 三包零改动
d3 = git("diff", "--stat", base + "..HEAD", "--",
         "dist/meeting-minutes-skill", "dist/office-templates-skill", "dist/hot-templates-skill")
check("K5A-03", d3.stdout.strip() == "", "canonical diff 为空" if d3.stdout.strip() == "" else d3.stdout[:200])

# K5A-04 披露口径写进 9 份变体 EVALUATION.md
bad = []
for variant in ["standard", "claude-code", "learner"]:
    for pkg, extra in [("meeting-minutes", []), ("office-templates", ["single_round_signal"]),
                       ("hot-templates", ["release-candidate"])]:
        ev = build / variant / pkg / "EVALUATION.md"
        if not ev.exists():
            bad.append("%s/%s:missing" % (variant, pkg))
            continue
        txt = ev.read_text(encoding="utf-8", errors="replace")
        need = ["synthetic-passed", "real-verified", "效率门"] + extra
        for kw in need:
            if kw not in txt:
                bad.append("%s/%s:%s" % (variant, pkg, kw))
check("K5A-04", not bad, ";".join(bad) or "9 份 EVALUATION.md 披露口径齐")

# K5A-05 变体中不得出现参照物或 oracle 目录
leaks = [str(p.relative_to(ROOT)) for p in build.rglob("*")
         if p.is_dir() and p.name in ("reference", "oracle")]
check("K5A-05", not leaks, ";".join(leaks[:4]) or "dist/build 无 reference/oracle 目录")

# K5A-06 build-summary.json 引用闭合（二选一）
bs = ROOT / "dist/build/build-summary.json"
tk = (ROOT / "dist/dist-compliance-tickets.md").read_text(encoding="utf-8", errors="replace")
ok6 = False
d6 = ""
if bs.exists():
    try:
        data = json.loads(bs.read_text(encoding="utf-8"))
        ok6 = isinstance(data, dict) and len(data) >= 1
        d6 = "build-summary.json 存在且可解析"
    except Exception as e:
        d6 = "build-summary.json 解析失败: %s" % e
else:
    if "build-summary.json" not in tk:
        ok6 = True
        d6 = "文件不存在且 tickets 已不再引用"
    else:
        d6 = "文件不存在且 tickets 仍引用（tickets.md 第 26 行附近）"
check("K5A-06", ok6, d6)

# K5A-07 未经新签署不得出现发布批准文件
check("K5A-07", not (ROOT / "evidence/publish-approval.md").exists(),
      "publish-approval.md 不存在" if not (ROOT / "evidence/publish-approval.md").exists()
      else "发现 publish-approval.md——违反②裁决")

print("== SF-0007 门槛: %d/%d PASS" % (sum(1 for x in results if x), len(results)))
sys.exit(0 if all(results) else 1)
