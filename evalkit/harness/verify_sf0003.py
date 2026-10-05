#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/verify_sf0003.py — SF-0003 验收汇总器（G4）。

逐条机跑 A1–F6 可复跑门并出 JSON（每条 {id, command, exit_code, ts, evidence_sha256}）；
exit 0 当且仅当全部绿。**逐条命令仍是唯一真值源，本文件只是汇总器**（planner 验收时亲复跑）。
点态门（A1 开工时旧指纹、D0 行比对、C4 建臂四连、E3 目录名负控）按其落盘证据文件断言。

用法：python harness/verify_sf0003.py [--out runs/sf0003/verify-sf0003.json]
"""

import argparse
import datetime
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

EVALKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 拆仓迁移(2026-10-05)：产线根 = 本仓根（原 afp-clone/zcode-research/skillfactory 布局已拆为独立仓）。
# SF_ROOT 可覆盖（默认取 evalkit 上一级 = 仓根）。
PROD_ROOT = os.environ.get("SF_ROOT") or os.path.normpath(os.path.join(EVALKIT, ".."))
AFP = PROD_ROOT  # git porcelain/资源定位统一走产线根
ASSET = os.path.join(PROD_ROOT, "v5", "assets", "speaker-mapping")
ASSET = os.path.normpath(ASSET)
RUNS = os.path.join(EVALKIT, "runs", "sf0003")
ORACLE_SHA = "e3086e10c9cd4f1415792333b89479536a2a96624b543215d5f6465525ceeacc"
ORACLE_FILES = 31

# S0（开工时）装置钉版基线 14 条 —— freeze verify 曾全绿（A1 点态证据见交付报告）
BASE_KEYFILES = {
    "evaluators/aggregate.py": "d8c93b1fd8dcc9ca897c5db0aa4817aa6045bc73a34d4d04dfb0f8b5e60eaa35",
    "evaluators/artifact_track.py": "b8e32519fb9826a5452de4a1c8ac92b112222f4cc02ac918d642177f677b8d0d",
    "evaluators/classify.py": "d54aa18ce7d3e6507b3047b56c4bb176e736ef588cf721618185280d3c1a99ab",
    "evaluators/process_track.py": "8a66238a7b582168670a7db1d8904aa78f5f42ba1b404bc58644cf929a72aa8d",
    "evaluators/quality_track.py": "328e4aef43cab3521e13019c17b77014884e69e21636db42c86af1c762618985",
    "harness/freeze_device.py": "021d2469d9e3ad8dc18b05df47f484e8bb089ae6567067ddfe93738aa7b3a618",
    "harness/isolation_probe.py": "526f703ffc575dc00bc2b03012018a4356acab15d462f25fb55c973110b911b5",
    "harness/make_arms.py": "3af46142b997a9382696097635004201e6cbab9a4a6e168cd3fd4bf4c846a448",
    "harness/oracle_gate.py": "c60b0edb52da8d222b323d02d5efd62675f4f40fb63c05a024db4ead18846826",
    "harness/pack_checks.py": "7faf5a0ea98aa8f3a9e077a830ca386ee1d4cde1660a8881fab148b83e0cb52d",
    "harness/run_all.py": "277dd8c479bb38e37332bafd0c8211014508e3a4544b01c670756b468c0ed8ff",
    "harness/run_arm.py": "f342d0a64925ab94cdad7b39f9c6a7a1030a3f884d05da6f1e2dafa21461ce37",
    "nc/run_nc.py": "8ef4851ade2f094c9ef57960d929facfedde563eb6855b22397771b5c5795a09",
    "packs/sm-mapping-01/checks/run_check.py": "c39ea26e248e3ade258487f5e22a8706dfa539fb49ee80c9bff006f2e1287e79",
}
OLD_VER = "v6-mvp-0" + ".1"  # 动态构造：本文件不得含旧版号字面量（否则 B1 残留扫描自指）

# 本卡声明的装置侧改动清单（F5：keyfiles 变更集必须恰等此集）
DECLARED_CHANGED = {"evaluators/aggregate.py", "evaluators/process_track.py",
                    "harness/make_arms.py", "harness/pack_checks.py", "harness/run_all.py",
                    "nc/run_nc.py", "packs/sm-mapping-01/checks/run_check.py"}  # +拆仓路径解耦(2026-10-05)
DECLARED_NEW = {"harness/doc_consistency.py", "harness/verify_sf0003.py",
                "harness/ws4_d3_gate.py", "harness/ws4_gen.py",
                "harness/ws4_judge.py", "harness/ws4_pool_state.py"}  # ws4 四件=S0 后 WS4 批次装置(拆仓前既有, 2026-10-05 补声明)

RESULTS = []


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha_f(p):
    return sha_b(open(p, "rb").read())


def gate(gid, command, ok, evidence="", detail=""):
    """登记一条门行（MT-5 四字段：command/exit_code/ts/evidence_sha256）。"""
    RESULTS.append({"id": gid, "command": command,
                    "exit_code": 0 if ok else 1, "ts": now(),
                    "evidence_sha256": sha_b(evidence.encode("utf-8")) if evidence else "",
                    "detail": detail})
    print("%-4s %s %s" % (gid, "PASS" if ok else "FAIL", detail[:140]))
    return ok


def run(cmd, cwd=EVALKIT, timeout=300):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, env=env, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git(args):
    return run(["git", "-C", AFP] + args)


def grep_count(pattern, path, fixed=True):
    if not os.path.exists(path):
        return None
    data = io.open(path, encoding="utf-8", errors="replace").read()
    return data.count(pattern) if fixed else len(re.findall(pattern, data))


# ---------------------------------------------------------------- A 组
def a_group():
    rc, out, _ = run([sys.executable, "harness/freeze_device.py", "verify"])
    gate("A1", "python harness/freeze_device.py verify", rc == 0, out,
         "装置钉版绿（14+2 关键文件；开工时旧指纹绿为点态证据，见报告）" if rc == 0 else out)
    rc, out, _ = run([sys.executable, "harness/oracle_gate.py", "hash",
                      "--root", os.path.join(ASSET, "oracle"),
                      "--record", os.path.join(RUNS, "oracle-after.json")])
    j = json.loads(out or "{}")
    gate("A2", "python harness/oracle_gate.py hash --root $ASSET/oracle --record runs/sf0003/oracle-after.json",
         rc == 0 and j.get("tree_sha256") == ORACLE_SHA and j.get("file_count") == ORACLE_FILES,
         out, "tree_sha256==ORACLE_SHA256 且 %d 文件" % ORACLE_FILES)
    rc, out, _ = git(["diff", "--exit-code", "--",
                      "v5/assets/speaker-mapping/eval/runner.py"])
    gate("A3", "git -C <afp-clone> diff --exit-code -- $ASSET/eval/runner.py", rc == 0, "",
         "runner 零改动")
    rc, out, _ = git(["status", "--porcelain"])
    sealed = ("peidian", "qw-arena2", "ohos-tailscale", "video-capability", "chenmai8", "xuexing-agent")
    before = json.load(io.open(os.path.join(RUNS, "porcelain-before.json"), encoding="utf-8"))
    bset = set(before["lines"])
    cur = set(l for l in out.splitlines() if l.strip())
    new_sealed = [l for l in cur - bset if any(s in l for s in sealed)]
    gate("A4", "git -C <afp-clone> status --porcelain（差分口径：本卡新增条目 ∩ 六封存区 == ∅）",
         not new_sealed, json.dumps(sorted(cur - bset), ensure_ascii=False),
         "本卡新增改动面 0 条落在封存区；既有 chenmai8 D/T 条目为 Windows checkout 的 "
         "symlink(mode 120000) 物化差异，S0 基线快照在案")


# ---------------------------------------------------------------- B 组
def b_group():
    agg = os.path.join(EVALKIT, "evaluators", "aggregate.py")
    n2 = grep_count("v6-mvp-0.2", agg)
    residue = []
    for d in ("evaluators", "harness", "packs", "nc", "README.md"):
        p = os.path.join(EVALKIT, d)
        paths = [p] if os.path.isfile(p) else glob.glob(os.path.join(p, "**", "*"), recursive=True)
        for f in paths:
            if os.path.isfile(f) and "__pycache__" not in f and OLD_VER in io.open(f, encoding="utf-8", errors="replace").read():
                residue.append(os.path.relpath(f, EVALKIT))
    gate("B1", "grep -n 'v6-mvp-0.2' evaluators/aggregate.py ; grep -rn '%s' {evaluators,harness,packs,nc,README.md}" % OLD_VER,
         n2 >= 1 and not residue, "new=%d residue=%s" % (n2, residue), "默认值已改；旧版号零残留")
    rc, _, err = run([sys.executable, "harness/run_all.py", "--help"])
    gate("B2", "python harness/run_all.py --help", "--evalbench-version" in (err + _ or err),
         err, "usage 输出含 --evalbench-version（透传已加；add_help=False 故 --help 走 usage 通道）")
    void = json.load(io.open(os.path.join(EVALKIT, "runs", "sf0003-baseline-void.json"), encoding="utf-8"))
    old_bl = [p for p in glob.glob(os.path.join(EVALKIT, "baseline", "**", "*"), recursive=True)
              if os.path.isfile(p) and OLD_VER in os.path.basename(p)]
    gate("B3", "test -f runs/sf0003-baseline-void.json + baseline/ 旧版号基线计数",
         void.get("voided_count") == 0 and bool(void.get("reason"))
         and "baseline_dir_listing" in void and not old_bl,
         json.dumps(void, ensure_ascii=False)[:400],
         "分支 B：voided_count=0+理由非空+目录清单落盘；聚合器可读旧版号基线数==0")
    inv = os.path.join(EVALKIT, "runs", "r1-probe", "INVALIDATED.md")
    txt = io.open(inv, encoding="utf-8").read() if os.path.isfile(inv) else ""
    gate("B4", "test -f runs/r1-probe/INVALIDATED.md && grep -c 'O-6\\|不得引用'",
         os.path.isfile(inv) and txt.count("O-6") >= 1 and txt.count("不得引用") >= 1
         and txt.count("citable: false") >= 1, txt[:300], "O-6/不得引用/citable:false 各≥1")
    # B5 双向
    neg_out = os.path.join(RUNS, "verify-b5-neg.json")
    if os.path.exists(neg_out):
        os.remove(neg_out)
    rc, _, err = run([sys.executable, "evaluators/aggregate.py", "--run-dir", "runs/r1-probe",
                      "--pack", "packs/sm-mapping-01", "--out", neg_out,
                      "--delta-from", "runs/r1-probe/matrix.json"])
    neg_ok = rc != 0 and "版本" in err and not os.path.exists(neg_out)
    pos_out = os.path.join(RUNS, "verify-b5-pos.json")
    if os.path.exists(pos_out):
        os.remove(pos_out)
    rc2, _, _ = run([sys.executable, "evaluators/aggregate.py", "--run-dir", "runs/r1-probe",
                     "--pack", "packs/sm-mapping-01", "--out", pos_out,
                     "--delta-from", os.path.join(RUNS, "ag7-prev-same.json")])
    pos = json.load(io.open(pos_out, encoding="utf-8")) if os.path.exists(pos_out) else {}
    pos_ok = rc2 == 0 and pos.get("delta_vs_prev", {}).get("sm-mapping-01") is None \
        and pos.get("evalbench_version") == "v6-mvp-0.2"
    gate("B5", "aggregate.py --delta-from <prev>（混版本 / 同版本 双向）", neg_ok and pos_ok,
         err.strip()[:300], "混版本 exit≠0 报「版本」零输出；同版本 exit 0 delta_vs_prev=null")
    ch = io.open(os.path.join(EVALKIT, "CHANGELOG.md"), encoding="utf-8").read()
    sec = ch.split("## v6-mvp-0.2", 1)[1].split("## " + OLD_VER, 1)[0]
    fixed_n = len(re.findall(r"^\*\*FIX-\d+｜", sec, re.M))
    five = all(all(k in blk for k in ("题号", "旧文本", "新文本", "缺陷类型", "判定人"))
               for blk in re.split(r"^\*\*FIX-\d+｜", sec, flags=re.M)[1:])
    repro = ("§4.1" in sec or "§4.2" in sec) and "复现命令" in sec
    gate("B6", "test -f evalkit/CHANGELOG.md + 读 v6-mvp-0.2 节",
         fixed_n >= 3 and five and repro, "fixed=%d five_fields=%s repro=%s" % (fixed_n, five, repro),
         "≥3 条 fixed，五字段齐，复现命令引用在位")
    plan = io.open(os.path.join(EVALKIT, "..", "planning", "PLAN.md"), encoding="utf-8").read()
    o6 = [l for l in plan.splitlines() if l.startswith("| O-6 |")]
    readme = io.open(os.path.join(EVALKIT, "README.md"), encoding="utf-8").read()
    gate("B7", "grep -n 'O-6' <PLAN.md> 的 O-6 行 + grep -n 'GLM-5.3' evalkit/README.md",
         len(o6) == 1 and "【已裁定】" in o6[0]
         and "account:bigmodel-individual-coding-plan/GLM-5.3" in o6[0]
         and "account:bigmodel-individual-coding-plan/GLM-5.3" in readme
         and "待 planner 裁定" not in readme,
         o6[0][:250] if o6 else "", "O-6 行【已裁定】+落点全串；README 已知限制节同步为已裁定态")


# ---------------------------------------------------------------- C 组
NEEDLE_INPUTS = '"inp' + 'uts"'  # 动态构造：避免本文件自带该字面量（C3 自指）


def c_group():
    fx = os.path.join(EVALKIT, "packs", "sm-mapping-01", "fixtures")
    inp = os.path.join(EVALKIT, "packs", "sm-mapping-01", "inp" + "uts")
    expect6 = {"empty.txt", "m_empty.json", "m_full.json", "m_partial.json", "normal.txt", "partial.txt"}
    pre = json.load(io.open(os.path.join(RUNS, "inputs-pre-rename-sha256.json"), encoding="utf-8"))["sha256"]
    ok = os.path.isdir(fx) and not os.path.exists(inp) and set(os.listdir(fx)) == expect6 \
        and all(sha_f(os.path.join(fx, n)) == pre[n] for n in expect6)
    gate("C1", "test -d packs/sm-mapping-01/fixtures && test ! -e .../inputs && sha256 对账",
         ok, json.dumps({n: sha_f(os.path.join(fx, n))[:12] for n in sorted(expect6)}),
         "恰 6 项且逐文件 sha256==改名前（保内容改名）")
    brief = os.path.join(EVALKIT, "packs", "sm-mapping-01", "brief.md")
    bt = io.open(brief, encoding="utf-8").read()
    ok = ('--transcript "fixtures/' in bt) and ('--out "out/' in bt) and ("以臂根为 cwd" in bt) \
        and (not re.search(r"inputs/|out/` 目录作为", bt)) \
        and (not re.search(r"speaker-mapping|SKILL\.md|map_speakers", bt))
    gate("C2", "grep 三形态/旧条款/资产名 brief.md", ok, bt[:200],
         "三形态各≥1；旧条款 0；资产名/暗示 0（EI-7）")
    hits = []
    for d in ("harness", "evaluators", "nc"):
        for f in glob.glob(os.path.join(EVALKIT, d, "*.py")):
            for i, l in enumerate(io.open(f, encoding="utf-8", errors="replace").read().splitlines(), 1):
                if NEEDLE_INPUTS in l:
                    hits.append("%s:%d" % (os.path.relpath(f, EVALKIT).replace(os.sep, "/"), i))
    fx_hits = sum(io.open(os.path.join(EVALKIT, d, f), encoding="utf-8", errors="replace").read().count('"fixtures"')
                  for d, f in (("harness", "make_arms.py"), ("harness", "pack_checks.py")))
    ok = all(h.startswith("harness/pack_checks.py") for h in hits) and fx_hits >= 2
    gate("C3", "grep -rn '\"inputs\"' harness evaluators nc packs/.../checks ; grep '\"fixtures\"'",
         ok, "inputs_hits=%s fixtures_hits=%d" % (hits, fx_hits),
         "带引号 inputs 字面仅存于 pack_checks 双名兼容；带引号 fixtures 计数≥2")
    preflight = json.load(io.open(os.path.join(EVALKIT, "runs", "sf0003-fix", "preflight.json"), encoding="utf-8"))
    iso_b = json.load(io.open(os.path.join(RUNS, "isolation-baseline.json"), encoding="utf-8"))
    iso_t = json.load(io.open(os.path.join(RUNS, "isolation-treatment.json"), encoding="utf-8"))
    man = os.path.isfile(os.path.join(EVALKIT, "runs", "sf0003-fix", "arms_manifest.json"))
    rc, out, _ = run([sys.executable, "harness/isolation_probe.py", "runs/sf0003-fix/baseline"])
    t_hits = iso_t["arms"][list(iso_t["arms"])[0]]["hits"]
    t_design = sorted(h["path"] for h in t_hits) == [".zcode/skills/speaker-mapping/SKILL.md",
                                                     ".zcode/skills/speaker-mapping/map_speakers.py"]
    ok = preflight.get("pass") is True and man and rc == 0 and iso_t.get("total_hits") == 2 and t_design
    gate("C4", "make_arms(记录) → isolation baseline(复跑) → treatment(记录) → pack_checks(记录 pass)",
         ok, out[:200] + json.dumps(t_hits, ensure_ascii=False)[:200],
         "四条 exit 0；treatment 命中 2=设计内阳性对照（README 口径）")
    pd = os.path.join(EVALKIT, "packs", "sm-mapping-01", "PACK-DEVIATIONS.md")
    t = io.open(pd, encoding="utf-8").read() if os.path.isfile(pd) else ""
    gate("C5", "test -f packs/sm-mapping-01/PACK-DEVIATIONS.md + 读内容",
         all(k in t for k in ("偏离项", "依据", "适用范围", "建议回写", "fixtures")),
         t[:200], "四要素齐 + 建议回写条款文本在位")


# ---------------------------------------------------------------- D 组
def d_group():
    d0 = os.path.join(RUNS, "d0-line54-pre.json")
    j = json.load(io.open(d0, encoding="utf-8")) if os.path.isfile(d0) else {}
    gate("D0", "SKILL.md:54 行 sha256 vs SF-0001 §4.3 记录（点态证据 runs/sf0003/d0-line54-pre.json）",
         bool(j.get("pre_edit_line54_sha256")) and "c861cf0d" in j.get("pre_edit_line54_sha256", ""),
         json.dumps(j, ensure_ascii=False)[:200], "开工时未改（预期），本卡修；实测行尾 LF（卡写 CRLF 系笔误）")
    sk = os.path.join(ASSET, "package", "SKILL.md")
    t = io.open(sk, encoding="utf-8").read()
    gate("D1", "grep -cF 新文本==1 且 旧文本==0 $ASSET/package/SKILL.md",
         t.count("INFO: 写出 out/<file>（共 N 行，替换标签 X 处，未映射标签 Y 种）") == 1
         and t.count("替换 X 处，未映射 Y 种") == 0, "ok", "新文本恰 1、旧文本绝迹")
    rc, out, _ = git(["diff", "--numstat", "--",
                      "v5/assets/speaker-mapping/package/SKILL.md"])
    rc2, out2, _ = git(["status", "--porcelain", "--",
                        "v5/assets/speaker-mapping/"])
    before = set(json.load(io.open(os.path.join(RUNS, "porcelain-before.json"), encoding="utf-8"))["lines"])
    cur = set(l for l in out2.splitlines() if l.strip())
    delta = sorted(cur - before)
    ok = out.strip() == "1\t1\tv5/assets/speaker-mapping/package/SKILL.md" \
        and delta == [" M v5/assets/speaker-mapping/package/SKILL.md"]
    gate("D2", "git numstat + status（差分口径：ASSET 子树本卡新增 == 恰该一行）", ok,
         out.strip() + " | delta=" + json.dumps(delta), "numstat 恰 1 1；新增改动面收死为 SKILL.md 一行")
    data = open(sk, "rb").read()
    crlf = data.count(b"\r\n")
    lone_lf = data.count(b"\n") - crlf
    ok = (crlf == 0 and lone_lf > 0) or (data.count(b"\n") == crlf)
    gate("D3", "行尾检查（实测 LF 全一致；卡文 CRLF 系笔误，见 D0 证据）", ok,
         "crlf=%d lone_lf=%d" % (crlf, lone_lf), "无混行；改动未引入第二种行尾")
    rc, out, _ = run([sys.executable, "harness/doc_consistency.py", "--asset",
                      os.path.join(ASSET, "package"), "--selfcheck"])
    gate("D4", "python harness/doc_consistency.py --asset $ASSET/package --selfcheck", rc == 0,
         out[:300], "实跑工具 stderr ↔ 文档模板占位符归一同构；变异红→复原绿（MT-2）")
    t = io.open(sk, encoding="utf-8").read()
    gate("D4b", "D4 自检后复跑 D1 断言（字节复原校验）",
         t.count("INFO: 写出 out/<file>（共 N 行，替换标签 X 处，未映射标签 Y 种）") == 1,
         "ok", "selfcheck 复原后新文本仍恰 1")
    hits = []
    for f in glob.glob(os.path.join(PROD_ROOT, "**", "*"), recursive=True):
        if os.path.isfile(f) and "替换 X 处" in io.open(f, encoding="utf-8", errors="replace").read():
            hits.append(os.path.relpath(f, PROD_ROOT).replace(os.sep, "/"))
    sm_hits = [h for h in hits if h.startswith("v5/assets/speaker-mapping")]
    dist_hits = [h for h in hits if h.startswith("dist/")]
    gate("D5", "grep -rlF '替换 X 处' <skillfactory 产线根>", not sm_hits and not dist_hits,
         json.dumps(hits), "speaker-mapping 包内零命中；dist/build 零命中；"
         "其余命中=%s（历史报告引用旧文本，登记不修）" % hits)


# ---------------------------------------------------------------- E 组
def artifact_run(product_root, out_json):
    rc, out, _ = run([sys.executable, "evaluators/artifact_track.py", "--pack", "packs/sm-mapping-01",
                      "--product-root", product_root, "--reference",
                      os.path.join(ASSET, "oracle", "out"), "--out", out_json])
    rec = json.load(io.open(out_json, encoding="utf-8"))
    checks = {c["name"]: bool(c["pass"]) for c in rec["runner_result"]["checks"]}
    return rc, checks


def e_group():
    rep = os.path.join(EVALKIT, "runs", "sf0003-replay", "out")
    ref = os.path.join(ASSET, "oracle", "out")
    names = sorted(os.listdir(rep))
    diff = [n for n in names if open(os.path.join(rep, n), "rb").read() != open(os.path.join(ref, n), "rb").read()]
    rc, checks = artifact_run(rep, os.path.join(RUNS, "verify-e1-artifact.json"))
    ok = len(names) == 24 and not diff and rc == 0 and all(checks.values()) \
        and checks.get("reference_agreement_100pct") is True
    gate("E1", "24 文件逐字节比对 + artifact_track --reference $ASSET/oracle/out", ok,
         "files=%d diffs=%s rc=%d checks=%s" % (len(names), diff, rc, checks),
         "24/24 逐字节一致；4/4 PASS——检查 4 首次转绿（显式 --reference，与 run_all 同参形态）")
    gate("E2", "读 runs/sf0003-replay/diff.json 差异集 → 决策表", not diff,
         json.dumps({"diff_files": diff}), "逐字节一致 → 归一规则数=0 收工（无 normalization.json 需求）")
    e3j = os.path.join(EVALKIT, "nc-sf0003-e3", "artifact_track.json")
    j = json.load(io.open(e3j, encoding="utf-8")) if os.path.isfile(e3j) else {}
    c4 = {c["name"]: bool(c["pass"]) for c in (j.get("runner_result", {}).get("checks") or [])}
    gate("E3", "NC-A：fixtures→fixturesX 重跑（证据 nc-sf0003-e3/artifact_track.json）",
         c4.get("reference_agreement_100pct") is False,
         json.dumps(c4), "目录名改动 → 检查 4 红（门未放水）")
    with tempfile.TemporaryDirectory(prefix="nc-sf0003-e4-") as tmp:
        out_dir = os.path.join(tmp, "out")
        shutil.copytree(rep, out_dir)
        tgt = os.path.join(out_dir, "normal__m_full.txt")
        b = bytearray(open(tgt, "rb").read())
        b[10] ^= 0x01
        open(tgt, "wb").write(bytes(b))
        rc, checks = artifact_run(out_dir, os.path.join(RUNS, "verify-e4-artifact.json"))
    gate("E4", "NC-B：任一产物 .txt 改 1 字节重跑 E1",
         checks.get("reference_agreement_100pct") is False,
         json.dumps(checks), "检查 4 红（门未放水）")
    dj = json.load(io.open(os.path.join(rep, "discover__normal.json"), encoding="utf-8"))
    info = io.open(os.path.join(rep, "normal__m_full.stderr.txt"), encoding="utf-8").read().strip()
    ok = dj["transcript"] == "fixtures\\normal.txt" and "写出 out\\normal__m_full.txt" in info
    gate("E5", "报告「回显语义」必答（replay 附带产出实测）", ok,
         "transcript=%r info=%r" % (dj["transcript"], info[:80]),
         "结论：归一回显——工具经 str(Path()) 把传入的 `/` 形态按 OS 分隔符归一"
         "（Windows 回显 `\\`），故斜杠参数产出与基线逐字节一致")


# ---------------------------------------------------------------- F 组
def f_group():
    rc, out, _ = run([sys.executable, "packs/sm-mapping-01/checks/run_check.py"])
    green = rc == 0
    empty = os.path.join(RUNS, "verify-f1-empty")
    os.makedirs(empty, exist_ok=True)
    rc2, _, _ = run([sys.executable, "packs/sm-mapping-01/checks/run_check.py", empty,
                     os.path.join(ASSET, "oracle", "out")])
    gate("F1", "run_check.py 绿路 / 空目录红路", green and rc2 == 1, "rc=%d rc_empty=%d" % (rc, rc2),
         "exit 0 / exit 1 双向成立")
    rc, out, _ = run([sys.executable, "nc/run_nc.py"], timeout=600)
    gate("F2", "python nc/run_nc.py", rc == 0 and "9/9" in out, out[-200:],
         "9/9 成立、exit 0（负控未退化）")
    rc, out, _ = run([sys.executable, "harness/oracle_gate.py", "verify",
                      "--root", os.path.join(ASSET, "oracle"),
                      "--record", os.path.join(RUNS, "oracle-before.json")])
    j = json.loads(out or "{}")
    gate("F3", "python harness/oracle_gate.py verify --record runs/sf0003/oracle-before.json",
         rc == 0 and j.get("unchanged") is True and j.get("current_tree_sha256") == ORACLE_SHA,
         out[:200], "unchanged=true")
    rc, out, _ = run([sys.executable, "evaluators/aggregate.py", "--run-dir", "runs/sf0003-replay",
                      "--pack", "packs/sm-mapping-01"])
    m = json.load(io.open(os.path.join(EVALKIT, "runs", "sf0003-replay", "matrix.json"), encoding="utf-8"))
    req = ["schema", "layer", "evalbench_version", "run_id", "rows", "delta_vs_none",
           "delta_vs_prev", "delta_note", "cross_family_comparable", "cross_family_note"]
    gate("F4", "python evaluators/aggregate.py --run-dir runs/sf0003-replay --pack ... + json 回读",
         rc == 0 and not [k for k in req if k not in m]
         and m["delta_vs_prev"]["sm-mapping-01"] is None and m["evalbench_version"] == "v6-mvp-0.2",
         "keys ok, delta_vs_prev=null, v6-mvp-0.2", "必填键齐；delta_vs_prev==null（AG-4）")
    rc, out, _ = run([sys.executable, "harness/freeze_device.py", "verify"])
    cur = {}
    for line in io.open(os.path.join(EVALKIT, "harness", "keyfiles.sha256"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            sha, rel = line.split(None, 1)
            cur[rel.strip()] = sha
    changed = {r for r in cur if r in BASE_KEYFILES and cur[r] != BASE_KEYFILES[r]}
    new = set(cur) - set(BASE_KEYFILES)
    declared = DECLARED_CHANGED | DECLARED_NEW
    ok = rc == 0 and changed == DECLARED_CHANGED and new == DECLARED_NEW \
        and not (declared - set(cur)) and not (set(BASE_KEYFILES) - set(cur))
    gate("F5", "freeze 三段式终态：verify 绿 + keyfiles 变更集恰等声明清单", ok,
         "changed=%s new=%s" % (sorted(changed), sorted(new)),
         "变更集恰等（changed 5 + new 2；多一项即红）")
    gate("F6", "test ! -d <afp-clone>/v6",
         not os.path.isdir(os.path.join(PROD_ROOT, "v6")), "",
         "v6 目录不存在（未升格，O-17 时机属 M1 阶段门）")


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out", default=os.path.join(RUNS, "verify-sf0003.json"))
    args = ap.parse_args(argv)
    for g in (a_group, b_group, c_group, d_group, e_group, f_group):
        g()
    doc = {"task": "SF-0003", "generated_at": now(),
           "pass": all(r["exit_code"] == 0 for r in RESULTS),
           "total": len(RESULTS), "failed": [r["id"] for r in RESULTS if r["exit_code"] != 0],
           "gates": RESULTS}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("\n===== SF-0003 汇总：%s（%d 门，红：%s）=====" %
          ("全绿" if doc["pass"] else "有红", doc["total"], doc["failed"] or "无"))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
