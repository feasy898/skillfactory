#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0009 门槛（planner 依 alpha 测试卡 howToJudge 落成，2026-10-08；开发方不得修改本脚本）。

用法：python3 gate_sf0009.py <venv-python 路径>
前置：planning/test-cards-20261008/base_commit.txt 存在本卡开工时的 HEAD 哈希。
退出码：0=全部 PASS；1=存在 FAIL。
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/pan-ding/workspace/skill工厂/skillfactory")
VPY = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / ".venv-dev" / "bin" / "python")
results = []
TREE_IDS = {
    "dist/meeting-minutes-skill/reference": "0c4c1c91dc1e1ce0a5f15af39896f49d3db317d7",
    "dist/office-templates-skill/reference": "99ead1a5887201f8faec07aee6918fc3752e89e2",
    "dist/hot-templates-skill/reference": "7debb3aabdaa0d891fa309159e76880c772f369f",
}
FIVE = ["zctl-mcp", "acceptor-agent", "hotwords", "deploy-pack", "speaker-mapping"]


def run(args, cwd=None, timeout=600):
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
    check("R-00", False, "base_commit.txt 缺失：开发方未记录本卡开工 HEAD")
    print("== SF-0009 门槛: 0/1 PASS")
    sys.exit(1)

# R-01 REGISTRY 只追加不改历史
d = git("diff", base + "..HEAD", "--", "REGISTRY.md")
removed = [l for l in d.stdout.splitlines() if l.startswith("-") and not l.startswith("---")]
added = [l for l in d.stdout.splitlines() if l.startswith("+") and not l.startswith("+++")]
blob = "\n".join(added)
check("R-01", (not removed) and len(added) >= 1,
      "删行=%d 增行=%d" % (len(removed), len(added)))

# R-02 ③登记内容在位
ok2 = ("reference/" in blob) and ("禁止直接对外分发" in blob) \
    and ("owner-delegated-signing-20261008" in blob)
check("R-02", ok2, "reference/=红 禁止直接对外分发=红 签署文件路径=红" if ok2 else "新增行缺关键词")

# R-03 reference/ 原样不动
ok3 = True
detail3 = []
for k, v in TREE_IDS.items():
    r = git("rev-parse", "HEAD:" + k)
    got = r.stdout.strip()
    if r.returncode != 0 or got != v:
        ok3 = False
        detail3.append("%s=%s(期望 %s)" % (k, got[:12] or "缺失", v[:12]))
st = git("status", "--porcelain", "--",
         "dist/meeting-minutes-skill/reference",
         "dist/office-templates-skill/reference",
         "dist/hot-templates-skill/reference")
if st.stdout.strip():
    ok3 = False
    detail3.append("工作区有改动: " + st.stdout[:120])
check("R-03", ok3, "; ".join(detail3) or "三个 tree id 相符且工作区干净")

# R-04 豁免注记覆盖五件 + 形态描述更正
ok4 = all(n in blob for n in FIVE) and ("形态豁免" in blob)
zl = "\n".join(l for l in added if ("zctl-mcp" in l or "acceptor-agent" in l))
if ok4:
    if ("未体检" not in zl) or ("C 级" in zl) or ("C（" in zl):
        ok4 = False
check("R-04", ok4, "五件名称/形态豁免/未体检口径" + ("" if ok4 else " 不满足"))

# R-05 豁免不升级状态
dd = git("diff", "--name-status", base + "..HEAD", "--", "dist/")
top_added = [l for l in dd.stdout.splitlines()
             if l[:1] in ("A", "D") and "/" not in l.split("\t")[-1]]
no_claim = not any(("可分发" in l) and any(n in l for n in FIVE) for l in added)
hc = git("diff", "--stat", base + "..HEAD", "--", "v3/tools/healthcheck")
check("R-05", (not top_added) and no_claim and hc.stdout.strip() == "",
      "dist 顶层增删=%d 可分发措辞=%s healthcheck diff=%s" % (len(top_added), no_claim, hc.stdout.strip() == ""))

# R-06 豁免对象确定性门（临时副本 0/1/2）
for asset in ["zctl-mcp", "acceptor-agent"]:
    tmp = Path(tempfile.mkdtemp(prefix="r06-")) / asset
    shutil.copytree(ROOT / "v5/assets" / asset, tmp,
                    ignore=shutil.ignore_patterns("__pycache__"))
    r0 = run([VPY, str(tmp / "eval/runner.py")], cwd=tmp, timeout=300)
    empty = tempfile.mkdtemp()
    r1_ = run([VPY, str(tmp / "eval/runner.py"), empty, "oracle"], cwd=tmp, timeout=300)
    r2_ = run([VPY, str(tmp / "eval/runner.py"), "x"], cwd=tmp, timeout=300)
    check("R-06[%s]" % asset, r0.returncode == 0 and r1_.returncode == 1 and r2_.returncode == 2,
          "green=%s red=%s usage=%s" % (r0.returncode, r1_.returncode, r2_.returncode))

print("== SF-0009 门槛: %d/%d PASS" % (sum(1 for x in results if x), len(results)))
sys.exit(0 if all(results) else 1)
