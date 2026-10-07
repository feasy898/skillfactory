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
import re
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


# A-01 拆仓残留路径清零（evalkit 全量 Python 文件；冷读复核发现 run_all.py:23 亦拼接，
# 只查 5 文件会假绿，2026-10-08 收紧为全量扫描）
bad = []
for p in sorted((ROOT / "evalkit").rglob("*.py")):
    if "__pycache__" in p.parts:
        continue
    if "afp-clone" in p.read_text(encoding="utf-8", errors="replace"):
        bad.append(str(p.relative_to(ROOT)))
check("A-01", not bad, ";".join(bad[:6]) or "evalkit/**/*.py afp-clone 零命中")

# A-01 补充（alpha 修订同步，2026-10-08）：evalkit 外白名单、存量不改写、存量不被调用
WHITELIST = {
    "planning/reports/sf0004-probes/build_ledger.py",
    "planning/reports/sf0004-probes/close_guards.py",
    "planning/reports/sf0004-probes/gen_deliverables.py",
    "planning/reports/sf0004-probes/snap_open.py",
    "v5/assets/speaker-mapping/out/fix_student.py",
}
rg = run(["git", "-C", ROOT, "grep", "--untracked", "-l", "afp-clone", "--",
          "*.py", "*.sh", "*.ps1", "*.js", "*.mjs", "*.ts", ":!evalkit"])
outside = {l.strip() for l in (rg.stdout or "").splitlines() if l.strip()}
extra = {f for f in outside - WHITELIST
         if not f.startswith("planning/test-cards-20261008/gate_")}
ok_out = rg.returncode in (0, 1) and not extra
dn = run(["git", "-C", ROOT, "diff", "--quiet", "c5b4ca0", "--",
          "planning/reports/sf0004-probes", "v5/assets/speaker-mapping/out"])
call = run(["grep", "-rIlE", "sf0004-probes|speaker-mapping/out", str(ROOT / "evalkit"),
            "--include=*.py"])
check("A-01b", ok_out and dn.returncode == 0 and call.returncode == 1,
      "白名单外新增=%s 存量改写=%s 被调用命中=%s" % (
          sorted(extra)[:3] or "无", dn.returncode, call.returncode))

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
base_file = ROOT / "planning/test-cards-20261008/base_commit.txt"
base = base_file.read_text(encoding="utf-8").strip() if base_file.exists() else "HEAD"
head_cl = git("show", base + ":evalkit/CHANGELOG.md")
before = head_cl.stdout.count("ws4_judge.py") if head_cl.returncode == 0 else 0
now = (ROOT / "evalkit/CHANGELOG.md").read_text(encoding="utf-8").count("ws4_judge.py")
r3 = run([VPY, ROOT / "evalkit/harness/verify_sf0003.py"], cwd=ROOT, timeout=1800)
kf = (ROOT / "evalkit/harness/keyfiles.sha256")
n_gen = len(re.findall(r"packs/ws4-dev/[^/]+/gen_oracle\.py", kf.read_text(encoding="utf-8"))) if kf.exists() else 0
n_rc = len(re.findall(r"packs/ws4-dev/[^/]+/runner_contract\.json", kf.read_text(encoding="utf-8"))) if kf.exists() else 0
m = re.search(r"全绿（(\d+) 门", r3.stdout or "")
ok4 = (r1.returncode == 0 and now >= before + 1 and r3.returncode == 0
       and m is not None and int(m.group(1)) >= 34
       and n_gen == 8 and n_rc == 8)
check("A-04", ok4,
      "freeze=%s changelog %d->%d sf0003=%s(全绿%s门) keyfiles gen=%d/8 rc=%d/8"
      % (r1.returncode, before, now, r3.returncode,
         m.group(1) if m else "?", n_gen, n_rc))

# A-05 签署与就绪保全（alpha 修订同步）：d1/d3 signoff 与 ready/counts.ready 前后一致
ps = ROOT / "bench/devpool-r1/pool-state.json"
snap = json.loads(ps.read_text(encoding="utf-8"))


def state_of(d):
    return {
        "d1": [t["d1_record"]["signoff"] for t in d["tasks"]],
        "d3": [t["d3_record"]["signoff"] for t in d["tasks"]],
        "ready": [t.get("ready") for t in d["tasks"]],
        "counts_ready": d["counts"]["ready"],
    }


before_state = state_of(snap)
r = run([VPY, ROOT / "evalkit/harness/ws4_pool_state.py"], cwd=ROOT, timeout=600)
after = json.loads(ps.read_text(encoding="utf-8"))
after_state = state_of(after)
same = before_state == after_state
signed = all((t["d1_record"]["signoff"] or {}).get("签署人") for t in after["tasks"])
check("A-05", r.returncode == 0 and same and signed,
      "exit=%s d1/d3/ready 保持=%s 已签=%s %s" % (r.returncode, same, signed, ((r.stderr or "") + (r.stdout or ""))[-160:]))

# A-06 签署对象与现物一致（alpha 修订同步）：唯一对拍基准 = 签署落盘提交 c5b4ca0 的
# pool-state 快照（不得读工作树 pool-state.json——ws4_pool_state.py:137-148 重跑会按现盘重算，自证假绿）
rsnap = run(["git", "-C", ROOT, "show", "c5b4ca0:bench/devpool-r1/pool-state.json"])
try:
    snap0 = json.loads(rsnap.stdout)
    bad = []
    if len(snap0["tasks"]) != len(after["tasks"]):
        bad.append("题数不一致")
    for t0, tw in zip(snap0["tasks"], after["tasks"]):
        pack = ROOT / t0["pack"]
        sha0 = t0["pack_files_sha256"]
        h = hashlib.sha256((pack / "brief.md").read_bytes()).hexdigest()
        so = (tw["d1_record"]["signoff"] or {}).get("被签对象sha256")
        if not (h == so == sha0.get("brief.md")):
            bad.append(t0["id"] + ":brief")
        for rel, s in sha0.items():
            if rel == "brief.md":
                continue
            if rel.startswith("fixtures/"):
                f = pack / rel
                if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != s:
                    bad.append("%s:%s" % (t0["id"], rel))
            # rubric/task.json 已含于上面 fixtures 同式的逐一比对：
            if rel in ("rubric.md", "task.json"):
                f = pack / rel
                if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != s:
                    bad.append("%s:%s" % (t0["id"], rel))
        disk_fx = {str(p.relative_to(pack)) for p in (pack / "fixtures").rglob("*") if p.is_file()}
        snap_fx = {k for k in sha0 if k.startswith("fixtures/")}
        if disk_fx != snap_fx:
            bad.append("%s:fixtures集合增删" % t0["id"])
    check("A-06", rsnap.returncode == 0 and not bad,
          ";".join(bad[:6]) or "32 个题面文件与 c5b4ca0 快照逐一相等，fixtures 集合无增删")
except Exception as e:
    check("A-06", False, "快照读取/解析失败: %s" % e)

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
