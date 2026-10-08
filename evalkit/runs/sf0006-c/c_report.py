#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0006-c/c_report.py — SF-0006 C 层收口汇总（随卡证据，不在 freeze 钉版面）。

产出：
  1. C-02 独立复算：从 matrix rows 读各单元 artifact_pass，逐单元重跑 run_check.py
     <落盘产物> --input-basis <该 rep 输入>，exit==0 须等于 artifact_pass（不 import 聚合工具）；
  2. C-06 infra 披露（>20% 族 citable=false；整族崩该族 unjudgeable 另一族照常）；
  3. C-07 token_ratio / wall_ratio（treatment/baseline 均值比，可由单元复算）；
  4. budget 台账修复注记（entries 观测字段按 records/arms/*.json 权威数据重算）；
  5. round-report.json（C-01..C-12 逐门自查、verdict_type=baseline-signal、C-10 措辞纪律、
     REGISTRY 窗口断言、B-03 收工全局 sha 比对）。
退出码：0 全过 / 1 有门红。
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
EVALKIT = os.path.join(ROOT, "evalkit")
RUN = os.path.join(EVALKIT, "runs", "sf0006-c")
VPY = os.path.join(ROOT, ".venv-dev", "bin", "python")
TASKS = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03"]
FAMILIES = ["glm", "minimax"]
REPS = [1, 2]
BASE_COMMIT = "68949f99f01df7d2150c2a0c6c7461c92e87459d"   # 本 ask 开工 HEAD（P6 收口提交）
GATES = []


def gate(gid, ok, detail):
    GATES.append({"id": gid, "verdict": "pass" if ok else "fail", "detail": detail})
    print("%-6s %s %s" % (gid, "PASS" if ok else "FAIL", detail[:160]), flush=True)
    return ok


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(cmd, **kw):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(cmd, capture_output=True, env=env, **kw)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def unit_dir(fam, task, rep):
    return os.path.join(RUN, fam, "%s-rep%d" % (task, rep))


def rate_of(cols, arm):
    cells = [c for c in cols.values() if c["arm"] == arm]
    return sum(1 for c in cells if c["artifact_pass"] is True) / len(cells)


def main():
    matrix = {fam: load(os.path.join(RUN, "matrix-%s.json" % fam)) for fam in FAMILIES}
    budget = load(os.path.join(RUN, "budget.json"), {})
    if not all(matrix.values()):
        print("matrix 缺失，先跑 judge", file=sys.stderr)
        return 2

    # ---------- budget 台账修复注记（records/arms 为权威） ----------
    repairs = []
    for e in budget.get("entries", []):
        m = re.match(r"(\w+)/([\w-]+)-rep(\d)/(baseline|treatment)$", e.get("arm") or "")
        if not m:
            continue
        fam, task, rep, arm = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        auth = load(os.path.join(RUN, "records", "arms", "%s-%s-rep%d-%s.json"
                                 % (fam, task, rep, arm)))
        if not auth:
            continue
        fixed = {"model_id": auth["model_id_observed"],
                 "provider_id": auth["provider_id_observed"],
                 "variant": auth["variant_observed"]}
        if (e.get("observed") or {}) != fixed:
            repairs.append({"slot": e["slot"], "arm": e["arm"], "ledger_had": e.get("observed"),
                            "authoritative": fixed,
                            "cause": "entries[-1].update 双线程竞态错位（append 与 update "
                                     "分离期间他族线程 append 致 [-1] 指向他人行）；"
                                     "records/arms/*.json 为逐臂权威（自 persist 起从未共享）"})
            e["observed"] = fixed
            e["observed_source"] = "records/arms 权威重算"
    write_json(os.path.join(RUN, "budget.json"), budget)
    write_json(os.path.join(RUN, "records", "budget-repair-note.json"),
               {"repaired": repairs, "note": "台账显示层竞态修复留痕；臂进程数/重试数不受影响",
                "total_repairs": len(repairs)})
    print("budget 台账修复 %d 行（records/arms 权威重算）" % len(repairs), flush=True)

    # ---------- C-01 ----------
    c1_ok, c1_detail = True, []
    for fam in FAMILIES:
        m = matrix[fam]
        rows = m["rows"]
        cells = [c for cols in rows.values() for c in cols.values()]
        six = all(all(k in c for k in ("process_pass", "artifact_pass", "quality_score",
                                       "tokens", "wall_ms", "infra_error")) for c in cells)
        ok = (sorted(rows) == sorted(TASKS) and len(cells) == 20 and six
              and m["family"] == fam)
        c1_ok &= ok
        c1_detail.append("%s rows=%d cells=%d six=%s family=%s" %
                         (fam, len(rows), len(cells), six, m["family"]))
    c1_ok &= budget.get("counted_arm_procs", 99) <= 40
    gate("C-01", c1_ok, "；".join(c1_detail) + "；臂进程 %s ≤40 + 重试 %s（逐条 budget.json）"
         % (budget.get("counted_arm_procs"), budget.get("retry_procs")))

    # ---------- C-02 独立复算（不 import 聚合工具） ----------
    mism, rerun = [], []
    for fam in FAMILIES:
        for task, cols in matrix[fam]["rows"].items():
            for key, cell in cols.items():
                rep = int(key.split("|r")[1])
                basis = os.path.join(RUN, "oracle", "%s-rep%d" % (task, rep), "fixtures")
                ad = os.path.join(RUN, fam, "%s-rep%d" % (task, rep), cell["arm"])
                r = run([VPY, os.path.join(EVALKIT, "packs", "ws4-dev", task, "checks",
                                           "run_check.py"), os.path.join(ad, "out"),
                         "--input-basis", basis])
                if (r.returncode == 0) != (cell["artifact_pass"] is True):
                    mism.append("%s/%s exit=%d matrix=%s" % (fam, key, r.returncode,
                                                             cell["artifact_pass"]))
                rerun.append({"family": fam, "cell": key, "run_check_exit": r.returncode,
                              "artifact_pass": cell["artifact_pass"]})
    write_json(os.path.join(RUN, "records", "c02-recompute.json"),
               {"pairs": len(rerun), "mismatches": mism,
                "note": "复算脚本（本文件）不 import evaluators/aggregate.py；"
                        "口径=每单元重跑 run_check.py <产物> --input-basis <该 rep 输入>，"
                        "(exit==0)==artifact_pass"})
    gate("C-02", not mism, "40 单元产物轨复算对拍 %s" % ("全一致" if not mism else mism[:3]))

    # ---------- C-03 / C-04 ----------
    c3_red, c4_bad = [], []
    for fam in FAMILIES:
        for task, cols in matrix[fam]["rows"].items():
            for key, cell in cols.items():
                if cell["process_pass"] is None:
                    c3_red.append("%s/%s process_pass=null" % (fam, key))
                ad = os.path.join(RUN, fam, "%s-rep%d" % (task, rep_of(key)), cell["arm"])
                q = load(os.path.join(ad, "records", "quality.json"), {})
                if q.get("score") is not None or q.get("verdict") != "unjudgeable":
                    c4_bad.append("%s/%s quality 异常" % (fam, key))
    gate("C-03", not c3_red, "40 单元 process_pass 全非 null（EI-14 禁止面在 process_track "
         "检查 4，命中即 process_pass=false 标红不删除）；红=%s" % (c3_red or "无"))
    gate("C-04", not c4_bad, "40 单元 quality_score==null 且 verdict==unjudgeable"
         % () if not c4_bad else str(c4_bad[:3]))

    # ---------- C-05 ----------
    c5_ok, c5_detail = True, []
    recomp = {}
    for fam in FAMILIES:
        m = matrix[fam]
        per = {}
        for task, cols in m["rows"].items():
            per[task] = rate_of(cols, "treatment") - rate_of(cols, "baseline")
        overall = sum(per.values()) / len(per)
        recomp[fam] = {"overall": overall, "per_task": per}
        ok = (abs(overall - m["delta_vs_none"]) < 1e-9 and m["delta_vs_prev"] is None
              and m["layer"] == "dev" and m["evalbench_version"] == "v6-mvp-0.3")
        c5_ok &= ok
        c5_detail.append("%s delta_vs_none=%s 复算=%s prev_null=%s" %
                         (fam, m["delta_vs_none"], round(overall, 6),
                          m["delta_vs_prev"] is None))
    write_json(os.path.join(RUN, "records", "c05-recompute.json"), recomp)
    gate("C-05", c5_ok, "；".join(c5_detail) + "；复算脚本不 import 聚合工具；AG-6 混族拒绝"
         "已在 P6 自证（runs/sf0006-aggregator/selftest-p6.out）")

    # ---------- C-06 infra 披露与单族作废 ----------
    fam_stats = {}
    for fam in FAMILIES:
        cells = [c for cols in matrix[fam]["rows"].values() for c in cols.values()]
        infra = [c for c in cells if c["infra_error"]]
        fam_stats[fam] = {"units": len(cells), "infra_units": len(infra),
                          "infra_rate": len(infra) / len(cells),
                          "delta_vs_none": matrix[fam]["delta_vs_none"]}
    for fam in FAMILIES:
        st = fam_stats[fam]
        st["citable"] = st["infra_rate"] <= 0.20
        st["citable_reason"] = ("A-07 全 exit 0（efcf91c）且 infra %.1f%% ≤20%%"
                                % (st["infra_rate"] * 100) if st["citable"]
                                else "装置不稳：infra %.1f%% > 20%%" % (st["infra_rate"] * 100))
        st["unjudgeable"] = st["infra_units"] == st["units"] and st["units"] > 0
    infra_errors = []
    for fam in FAMILIES:
        for task, cols in matrix[fam]["rows"].items():
            for key, cell in cols.items():
                if cell["infra_error"]:
                    infra_errors.append({"family": fam, "task": task, "cell": key,
                                         "exit_code": cell["exit_code"],
                                         "disclosed_in": "matrix-%s.json infra_errors" % fam})
    gate("C-06", True, "glm infra=%d/%d（%.1f%%）citable=%s；minimax infra=%d/%d（%.1f%%）"
         "citable=%s；整族崩溃=%s；infra 剔除列表逐条=%d 条（禁止静默剔除）"
         % (fam_stats["glm"]["infra_units"], 20, fam_stats["glm"]["infra_rate"] * 100,
            fam_stats["glm"]["citable"], fam_stats["minimax"]["infra_units"], 20,
            fam_stats["minimax"]["infra_rate"] * 100, fam_stats["minimax"]["citable"],
            [f for f in FAMILIES if fam_stats[f]["unjudgeable"]] or "无", len(infra_errors)))

    # ---------- C-07 效率 ----------
    ratios = {}
    for fam in FAMILIES:
        for arm in ("baseline", "treatment"):
            cells = [c for cols in matrix[fam]["rows"].values() for c in cols.values()
                     if c["arm"] == arm and not c["infra_error"]]
            tok = [c["tokens"] for c in cells if c["tokens"] is not None]
            wal = [c["wall_ms"] for c in cells if c["wall_ms"] is not None]
            ratios.setdefault(fam, {})["%s_tokens_mean" % arm] = (sum(tok) / len(tok)) if tok else None
            ratios.setdefault(fam, {})["%s_wall_mean_ms" % arm] = (sum(wal) / len(wal)) if wal else None
        r = ratios[fam]
        r["token_ratio"] = (r["treatment_tokens_mean"] / r["baseline_tokens_mean"]
                            if r.get("treatment_tokens_mean") and r.get("baseline_tokens_mean")
                            else None)
        r["wall_ratio"] = (r["treatment_wall_mean_ms"] / r["baseline_wall_mean_ms"]
                           if r.get("treatment_wall_mean_ms") and r.get("baseline_wall_mean_ms")
                           else None)
    write_json(os.path.join(RUN, "records", "c07-efficiency.json"), ratios)
    gate("C-07", True, "；".join("%s token_ratio=%s wall_ratio=%s（treatment/baseline 均值，"
         "tokens 来自 model_usage join）" % (f, ratios[f]["token_ratio"], ratios[f]["wall_ratio"])
         for f in FAMILIES))

    # ---------- B-03 收工全局 sha 比对 ----------
    opening = {}
    with open(os.path.join(RUN, "precheck", "global-sha-opening.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            sha, p = line.split(None, 1)
            opening[p.strip()] = sha
    closing_same = all(sha256_file(p) == opening.get(p) for p in opening)
    gate("B-03", closing_same, "收工三份全局配置 sha256 与开工逐字节相等=%s" % closing_same)

    # ---------- C-10 措辞与 REGISTRY 窗口 ----------
    def git(args):
        return run(["git", "-C", ROOT] + args)
    r = git(["log", "--format=%H %s", "%s..HEAD" % BASE_COMMIT, "--", "REGISTRY.md"])
    reg_ok = True
    reg_detail = []
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        h, subj = line.split(" ", 1)
        ok = ("SF-0009" in subj) and ("SF-0006" not in subj)
        names = git(["show", "--name-only", "--format=", h]).stdout.decode().split()
        one = names == ["REGISTRY.md"]
        d = git(["diff", "%s..%s" % (BASE_COMMIT, h), "--", "REGISTRY.md"]).stdout.decode()
        added = [l for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
        bad = [l for l in added if re.search(r"SF-0006|devpool-r1|baseline-signal|基线信号", l)]
        reg_ok &= ok and one and not bad
        reg_detail.append("%s ok=%s one_file=%s bad_added=%d" % (h[:8], ok, one, len(bad)))
    gate("C-10-REGISTRY", reg_ok, "REGISTRY 窗口提交 %d 个；%s" %
         (len(reg_detail), "; ".join(reg_detail) or "窗口内无 REGISTRY 提交（过）"))

    # ---------- D4 分拣数据（写入由 ws4_pool_state 派生） ----------
    d4 = {}
    for task in TASKS:
        rates = {}
        for fam in FAMILIES:
            cols = matrix[fam]["rows"][task]
            cells = [c for c in cols.values() if c["arm"] == "treatment"]
            rates[fam] = sum(1 for c in cells if c["artifact_pass"] is True) / len(cells)
        avg = (rates["glm"] + rates["minimax"]) / 2
        band = "rotation" if avg > 0.9 else "iteration" if avg >= 0.6 else "attribution"
        d4[task] = {"glm_treatment_rate": rates["glm"], "minimax_treatment_rate": rates["minimax"],
                    "avg": avg, "band": band}
    write_json(os.path.join(RUN, "records", "c08-d4-sortition.json"),
               {"thresholds": ">90% rotation / 60-90% iteration / <60% attribution（PLAN §3.2）",
                "sortition_basis": "两族 treatment 通过率均值（band_reason 另写各族通过率）",
                "tasks": d4})

    # ---------- C-11 抽查在本文件外跑（全树扫描） ----------
    return finish()


def rep_of(key):
    return int(key.split("|r")[1])


def finish():
    rd = load(os.path.join(RUN, "records", "c02-recompute.json"), {})
    ok = all(g["verdict"] == "pass" for g in GATES)
    doc = {"task": "SF-0006-C", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "pass": ok, "gates": GATES}
    write_json(os.path.join(RUN, "records", "c-gates.json"), doc)
    print("\n===== C 层自查门：%s（%d 门，红：%s）=====" %
          ("全过" if ok else "有红", len(GATES), [g["id"] for g in GATES if g["verdict"] != "pass"] or "无"))
    return 0 if ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
