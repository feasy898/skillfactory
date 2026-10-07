#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 A-07..A-10 门槛（planner 落成 2026-10-08，依 alpha 修订卡 howToJudge；D3 金标注入并签署后运行）。

用法：python3 gate_sf0006b.py <venv-python 路径>
退出码：0=全部 PASS；1=存在 FAIL。
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/pan-ding/workspace/skill工厂/skillfactory")
VPY = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / ".venv-dev" / "bin" / "python")
FIVE = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03"]
OFC = ["ofc-01", "ofc-02", "ofc-03"]
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


spec = importlib.util.spec_from_file_location("oracle_gate", ROOT / "evalkit/harness/oracle_gate.py")
og = importlib.util.module_from_spec(spec)
spec.loader.exec_module(og)


def tree(p):
    return og.hash_tree(Path(p))["tree_sha256"]


# A-07 D3 真实对拍门
accs = {}
for t in FIVE:
    r = run([VPY, ROOT / "evalkit/harness/ws4_d3_gate.py", "--task", t, "--real"], cwd=ROOT, timeout=1200)
    m = re.search(r'"accuracy"\s*:\s*([\d.]+)', (r.stdout or "") + (r.stderr or ""))
    acc = float(m.group(1)) if m else None
    accs[t] = (r.returncode == 0) and (acc is None or acc >= 0.95)
    check("A-07[%s]" % t, accs[t], "exit=%s accuracy=%s" % (r.returncode, acc))
for t in OFC:
    r = run([VPY, ROOT / "evalkit/harness/ws4_d3_gate.py", "--task", t, "--real"], cwd=ROOT, timeout=1200)
    check("A-07[%s]" % t, r.returncode == 3, "exit=%s（期望 3=WAITING_WS3 fail-closed）" % r.returncode)

# A-08 金标样本构成
bad = []
oracle_trees = {}
for t in FIVE:
    gdir = ROOT / "bench/devpool-r1/goldens" / t
    samples = sorted([d for d in gdir.iterdir() if d.is_dir()]) if gdir.is_dir() else []
    if len(samples) < 10:
        bad.append("%s:样本数%d<10" % (t, len(samples)))
        continue
    np_ = nf_ = pd_ = fn_ = 0
    if t not in oracle_trees:
        scratch = tempfile.mkdtemp(prefix="a08-oracle-")
        rg = run([VPY, "gen_oracle.py", "--out", scratch], cwd=ROOT / "evalkit/packs/ws4-dev" / t, timeout=600)
        try:
            oracle_trees[t] = tree(scratch)
        except Exception as e:
            bad.append("%s:oracle重生成失败:%s" % (t, e))
            continue
    for s in samples:
        vj = s / "verdict.json"
        if not vj.exists():
            bad.append("%s/%s:verdict缺失" % (t, s.name))
            continue
        try:
            v = json.loads(vj.read_text(encoding="utf-8"))
        except Exception as e:
            bad.append("%s/%s:verdict解析:%s" % (t, s.name, e))
            continue
        ph = v.get("product_sha256")
        if not (s / "product").is_dir() or ph != tree(s / "product"):
            bad.append("%s/%s:product_sha256不符" % (t, s.name))
        if v.get("annotator") != "owner 委托 alpha 代行" or v.get("annotator_kind") != "delegated-signing-model":
            bad.append("%s/%s:annotator口径" % (t, s.name))
        if v.get("expected_pass") is True:
            np_ += 1
            if tree(s / "product") != oracle_trees[t]:
                pd_ += 1
        elif v.get("expected_pass") is False:
            nf_ += 1
            if not str(v.get("source", "")).startswith("corruption:"):
                fn_ += 1
    if np_ < 4 or nf_ < 4:
        bad.append("%s:正/负=%d/%d 各须≥4" % (t, np_, nf_))
    if pd_ < 2:
        bad.append("%s:过且异于oracle的%d<2" % (t, pd_))
    if fn_ < 2:
        bad.append("%s:挂且非corruption的%d<2" % (t, fn_))
check("A-08", not bad, ";".join(bad[:6]) or "5 题样本构成全部达标")

# A-09 标注不可静默翻改（轻量：verdict.json 历史唯一，或入 RELABEL.md）
bad = []
relab = ROOT / "bench/devpool-r1/goldens/RELABEL.md"
relab_txt = relab.read_text(encoding="utf-8", errors="replace") if relab.exists() else ""
for t in FIVE:
    gdir = ROOT / "bench/devpool-r1/goldens" / t
    for vj in sorted(gdir.glob("*/verdict.json")):
        rel = vj.relative_to(ROOT)
        lg = git("log", "--format=%H", "--", str(rel))
        n = len([x for x in lg.stdout.split() if x.strip()])
        if n > 1 and str(rel) not in relab_txt:
            bad.append("%s:改写%d次且未登记RELABEL" % (rel, n))
check("A-09", not bad, ";".join(bad[:4]) or "verdict 历史唯一")

# A-10 READY 翻绿（先重跑派生，再断言；含 A-05 二次保全）
ps = ROOT / "bench/devpool-r1/pool-state.json"
before = json.loads(ps.read_text(encoding="utf-8"))
r = run([VPY, ROOT / "evalkit/harness/ws4_pool_state.py"], cwd=ROOT, timeout=600)
after = json.loads(ps.read_text(encoding="utf-8"))
preserved = (json.dumps(before, sort_keys=True, ensure_ascii=False)
             == json.dumps(after, sort_keys=True, ensure_ascii=False))
bad = []
if not preserved:
    bad.append("重跑前后状态漂移")
ready_true = 0
for t in after["tasks"]:
    d1s = (t["d1_record"]["signoff"] or {}).get("签署人")
    d3s = t["d3_record"]["signoff"] or {}
    d3_ok = all(d3s.get(k) for k in ("签署人", "日期", "被签对象sha256"))
    expect = bool(d1s) and accs.get(t["id"], False) and d3_ok and t["line"] in ("mm", "hot")
    if bool(t.get("ready")) != expect:
        bad.append("%s:ready=%s 期望%s" % (t["id"], t.get("ready"), expect))
    if expect:
        ready_true += 1
    if t["line"] in ("mm", "hot"):
        if t["d3_record"].get("annotator_kind") != "delegated-signing-model":
            bad.append("%s:annotator_kind" % t["id"])
        if d3s.get("签署人") != "owner 委托 alpha 代行":
            bad.append("%s:d3签署人" % t["id"])
        gt = ROOT / "bench/devpool-r1/goldens" / t["id"]
        if d3s.get("被签对象sha256") and tree(gt) != d3s.get("被签对象sha256"):
            bad.append("%s:d3签署对象≠金标树哈希" % t["id"])
    elif t.get("ready"):
        bad.append("%s:ofc 不应 ready" % t["id"])
if after["counts"]["ready"] != ready_true or ready_true < 5:
    bad.append("counts.ready=%s 实际满足=%d（须相等且≥5）" % (after["counts"]["ready"], ready_true))
check("A-10", r.returncode == 0 and not bad,
      ";".join(bad[:5]) or "ready 派生正确 counts.ready=%d" % ready_true)

print("== SF-0006 A-07..A-10 门槛: %d/%d PASS" % (sum(1 for x in results if x), len(results)))
sys.exit(0 if all(results) else 1)
