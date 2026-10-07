#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 A 层门槛（planner 依 alpha 测试卡 howToJudge 落成，2026-10-08；开发方不得修改本脚本）。

用法：python3 gate_sf0006a.py <venv-python 路径>
退出码：0=全部机检条款 PASS；1=存在 FAIL。
A-13/A-14 本轮不机检（由开发方按卡面命令执行并在汇报中给出退出码，B 层实测复验），打印 SKIP 不计入退出码。
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/pan-ding/workspace/skill工厂/skillfactory")
VPY = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / ".venv-dev" / "bin" / "python")
IDS = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03", "ofc-01", "ofc-02", "ofc-03"]
results = []


def run(args, cwd=None, timeout=900):
    try:
        return subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None,
                              capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # spawn 失败按红处理
        class R:
            returncode = -1
            stdout = ""
            stderr = "spawn-error: %s" % e
        return R()


def check(cid, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + " " + cid + "  " + str(detail)[:500])


def skip(cid, detail=""):
    print("SKIP " + cid + "  " + str(detail)[:300])


def git(*args):
    return run(["git", "-C", ROOT, *args])


# A-01 拆仓残留路径清零
bad = []
for rel in ["evalkit/harness/ws4_judge.py", "evalkit/harness/ws4_gen.py",
            "evalkit/harness/ws4_d3_gate.py", "evalkit/harness/ws4_pool_state.py"]:
    p = ROOT / rel
    if not p.exists():
        bad.append(rel + ":missing")
    elif "afp-clone" in p.read_text(encoding="utf-8", errors="replace"):
        bad.append(rel)
check("A-01", not bad, ";".join(bad) or "afp-clone 零命中")

# A-02 8 题生成器红绿自检（真实仓布局）
fails = []
for t in IDS:
    r = run([VPY, "gen_oracle.py", "--selftest"], cwd=ROOT / "evalkit/packs/ws4-dev" / t, timeout=600)
    if r.returncode != 0 or "SELFTEST PASS" not in (r.stdout or ""):
        fails.append("%s:exit=%s:%s" % (t, r.returncode, ((r.stderr or "") + (r.stdout or ""))[-140:]))
check("A-02", not fails, ";".join(fails) or "8/8 SELFTEST PASS")

# A-03 runner_contract.json 重生成为本仓真实路径
bad = []
for t in IDS:
    rc = ROOT / ("evalkit/packs/ws4-dev/%s/runner_contract.json" % t)
    try:
        txt = rc.read_text(encoding="utf-8")
        c = json.loads(txt)
        rr, rp = c.get("ref_root_verbatim"), c.get("runner_path")
        ok = bool(rr) and os.path.isdir(rr) and bool(rp) and os.path.isfile(rp) \
            and c.get("selfcheck_exit") == 0 and c.get("redpath_exit") == 1 \
            and "D:\\" not in txt
        if not ok:
            bad.append("%s:rr=%r,rp=%r,sc=%r,red=%r" % (t, rr, rp, c.get("selfcheck_exit"), c.get("redpath_exit")))
    except Exception as e:
        bad.append("%s:%s" % (t, e))
check("A-03", not bad, ";".join(bad) or "8 份 contract 指向本仓且红绿记录齐")

# A-04 钉版协议：freeze verify + CHANGELOG 登记 + verify_sf0003 不回退
r1 = run([VPY, ROOT / "evalkit/harness/freeze_device.py", "verify", "--evalkit", ROOT / "evalkit"],
         cwd=ROOT, timeout=600)
head_cl = git("show", "HEAD:evalkit/CHANGELOG.md")
before = head_cl.stdout.count("ws4_judge.py") if head_cl.returncode == 0 else 0
now = (ROOT / "evalkit/CHANGELOG.md").read_text(encoding="utf-8").count("ws4_judge.py")
r3 = run([VPY, ROOT / "evalkit/harness/verify_sf0003.py"], cwd=ROOT, timeout=1800)
ok4 = r1.returncode == 0 and now >= before + 1 and r3.returncode == 0 and "34" in (r3.stdout or "")
check("A-04", ok4,
      "freeze=%s changelog %d->%d sf0003=%s %s" % (r1.returncode, before, now, r3.returncode,
                                                   ((r3.stderr or "") + (r3.stdout or ""))[-160:]))

# A-05 签署保全：重跑 ws4_pool_state.py 不得冲掉 signoff
ps = ROOT / "bench/devpool-r1/pool-state.json"
snap = json.loads(ps.read_text(encoding="utf-8"))
r = run([VPY, ROOT / "evalkit/harness/ws4_pool_state.py"], cwd=ROOT, timeout=600)
after = json.loads(ps.read_text(encoding="utf-8"))
same = all(after["tasks"][i]["d1_record"]["signoff"] == snap["tasks"][i]["d1_record"]["signoff"]
           for i in range(len(snap["tasks"])))
signed = all((t["d1_record"]["signoff"] or {}).get("签署人") for t in after["tasks"])
check("A-05", r.returncode == 0 and same and signed,
      "exit=%s 保持=%s 已签=%s %s" % (r.returncode, same, signed, ((r.stderr or "") + (r.stdout or ""))[-160:]))

# A-06 签署对象与现物一致（brief 哈希 = signoff；题面四类文件 = pool-state 清单）
bad = []
for t in after["tasks"]:
    pack = ROOT / t["pack"]
    so = (t["d1_record"]["signoff"] or {})
    h = hashlib.sha256((pack / "brief.md").read_bytes()).hexdigest()
    if h != so.get("被签对象sha256"):
        bad.append(t["id"] + ":brief-mismatch")
    for rel, sha in t["pack_files_sha256"].items():
        f = pack / rel
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != sha:
            bad.append("%s:%s" % (t["id"], rel))
check("A-06", not bad, ";".join(bad) or "8 题签署哈希与现物一致")

# A-11 负控与分类器阳性对照
scratch = tempfile.mkdtemp(prefix="sf0006a-nc-")
r1 = run([VPY, ROOT / "evalkit/nc/run_nc.py", "--out", scratch], cwd=ROOT, timeout=2400)
r2 = run([VPY, ROOT / "evalkit/evaluators/classify.py", "--selftest"], cwd=ROOT, timeout=600)
check("A-11", r1.returncode == 0 and r2.returncode == 0,
      "nc=%s classify=%s %s" % (r1.returncode, r2.returncode,
                                ((r1.stderr or "") + (r1.stdout or ""))[-200:]))

# A-12 结构断言：开发方按卡面命令构建的 mm-01 双臂样例树（evalkit/runs/sf0006-a-gate/）无参照物泄漏
armroot = ROOT / "evalkit/runs/sf0006-a-gate"
if not armroot.is_dir():
    check("A-12", False, "未找到 arm 树 evalkit/runs/sf0006-a-gate/（开发方未按卡面命令建臂）")
else:
    leaks = [str(d.relative_to(ROOT)) for d in armroot.rglob("*")
             if d.is_dir() and d.name in ("reference", "oracle")]
    nfiles = sum(1 for x in armroot.rglob("*") if x.is_file())
    check("A-12", not leaks, "泄漏=%d 文件数=%d %s" % (len(leaks), nfiles, leaks[:3]))

skip("A-13", "由开发方按卡面命令执行并汇报退出码；B 层冒烟将实测复验 nonce 矩阵")
skip("A-14", "由开发方按卡面命令执行并汇报退出码；B-04 将用 oracle_gate verify 实测复验")

print("== SF-0006 A 层门槛: %d/%d PASS" % (sum(1 for x in results if x), len(results)))
sys.exit(0 if all(results) else 1)
