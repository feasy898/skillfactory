#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0008-k5b/s8_swap_recheck.py — SF-0010 swap 修复断言（K5B-05 勘误后自证）。

对 sf0008-k5b 盘上原始数据（records/arms/*、records/judging/*.json、各臂 arm_run 记录）
独立重算 swap 后聚合，断言 K-5 alpha 裁决结论：
  1) 重建 per-run 分数 ≡ 盘上 dist/<pkg>/eval/results/benchmark.json 的分数（输入一致，
     排除「改输入凑结论」）；
  2) 重建正向 aggregate/task_verdict ≡ 盘上值（证明本次勘误未动正向判定路径与已落盘 verdict）；
  3) 修复后 swap_check（从原始 run 独立重算，EVAL-SPEC v0.2.1 §3.3-2/3 tie-aware）：
     三包 swap_reverse_tasks（资产方向真实反向，K5B-05「reverse_tasks 不变」）== 0/0/0；
     swap_delta + delta ≈ 0（恒等式 |·|≤1e-6）；mirror_flipped_tasks == 勘误前盘上
     假数字 6/3/4（旧假数字来源审计）；
  4) alpha 附带发现复证：正向按 v0.2.1 tie-aware 重判，三包 task_win_rate 与盘上不变
     （12.5%/40%/40%），逐任务给出 verdict 迁移清单（伪 loss→tie）。
输出：records/s8-swap-recheck.json（留档）。全部断言过 exit 0，任一失败 exit 1。
用法：python s8_swap_recheck.py   （只读盘上数据，不写 benchmark.json）
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s8_aggregate as S

RUN = S.RUN
OUT = os.path.join(RUN, "records", "s8-swap-recheck.json")


def bench_of(pkg):
    return S.jload(os.path.join(S.ROOT, "dist", S.PKGS[pkg], "eval",
                                "results", "benchmark.json"))


def rebuild(pkg):
    """与 s8_aggregate.main 同路径从盘上原始数据重建 data（不写任何文件）。"""
    checks = {}
    chk_path = os.path.join(RUN, "records", "checker-results.json")
    if os.path.isfile(chk_path):
        checks = S.jload(chk_path)
    jp = os.path.join(RUN, "records", "judging", "%s.json" % pkg)
    data = {"tasks": [], "infra_errors": [], "eff": {"t_tokens": [], "b_tokens": [], "t_dur": [], "b_dur": []},
            "fmt_fails": [], "assert_fails": [], "judging": {}, "fam_tasks": {}, "n_runs": 0}
    if os.path.isfile(jp):
        data["judging"] = S.jload(jp)
    raw = S.collect_pkg(pkg, checks)
    data["infra_errors"] = raw["infra_errors"]
    data["eff"] = raw["eff"]
    data["fmt_fails"] = raw["fmt_fails"]
    data["assert_fails"] = raw["assert_fails"]
    data["n_runs"] = raw["n_runs"]
    data["tasks"] = raw["tasks"]
    data["fam_tasks"] = raw["fam_tasks"]
    return S.attach_scores(pkg, data)


def main():
    results, failures = {}, []
    for pkg in S.PKGS:
        bm = bench_of(pkg)
        data = rebuild(pkg)
        agg = S.aggregate(data)
        rep = {"pkg": pkg, "checks": {}, "tie_aware_rejudge": []}

        # 1) 重建 per-run 分数 ≡ 盘上 benchmark.json（逐任务逐臂逐 rep）
        mism = []
        bt = {t["id"]: t for t in bm["tasks"]}
        for t in data["tasks"]:
            b = bt[t["id"]]
            for arm in ("treatment", "baseline"):
                for r_new, r_old in zip(t["arms"][arm]["runs"], b["arms"][arm]["runs"]):
                    if r_new["score"] != r_old["score"]:
                        mism.append("%s/%s/rep%s: %r != %r" % (
                            t["id"], arm, r_new.get("rep"), r_new["score"], r_old["score"]))
        rep["checks"]["rebuild_scores_match_bench"] = (not mism, mism[:5])

        # 2) 正向 aggregate 与 task_verdict ≡ 盘上（正向路径未被本次勘误改动）
        bm_agg = bm["aggregate"]
        same_agg = all(agg[k] == bm_agg.get(k)
                       for k in ("mean_baseline", "mean_treatment", "delta",
                                 "task_win_rate", "reverse_tasks", "ties"))
        v_mism = [t["id"] for t in data["tasks"] if t["task_verdict"] != bt[t["id"]]["task_verdict"]]
        rep["checks"]["forward_aggregate_match_bench"] = (same_agg, {k: (agg[k], bm_agg.get(k)) for k in agg})
        rep["checks"]["forward_verdicts_match_bench"] = (not v_mism, v_mism)

        # 3) 修复后 swap_check：从原始 run 独立重算
        sw = S.swap_check(data["tasks"], agg)
        delta = agg["delta"]
        ident = sw["swap_delta"] is not None and delta is not None and \
            abs(sw["swap_delta"] + delta) <= 1e-6
        rep["swap_independent_recompute"] = sw
        rep["checks"]["swap_reverse_tasks_zero"] = (sw["swap_reverse_tasks"] == 0,
                                                    sw["swap_reverse_tasks"])
        rep["checks"]["swap_delta_negation_identity"] = (ident,
                                                         {"swap_delta": sw["swap_delta"], "delta": delta})
        # 3b) 旧假数字来源审计：mirror_flipped_tasks 应恰等于勘误前盘上 _swap_check.swap_reverse_tasks
        old_val = (bm.get("_swap_check") or {}).get("swap_reverse_tasks")
        rep["checks"]["mirror_flipped_matches_legacy_artifact"] = (
            sw["mirror_flipped_tasks"] == old_val,
            {"mirror_flipped_tasks": sw["mirror_flipped_tasks"], "legacy_swap_reverse_tasks": old_val})

        # 4) alpha 附带发现复证：正向 v0.2.1 tie-aware 重判，胜率不变、伪 loss→tie 迁移清单
        wins = ties = total = 0
        for t in data["tasks"]:
            if t["task_verdict"] == "unjudgeable":
                continue
            tr = [r["score"] for r in t["arms"]["treatment"]["runs"]]
            bs = [r["score"] for r in t["arms"]["baseline"]["runs"]]
            v1, v2 = t["task_verdict"], S.judge_task_tieaware(tr, bs)[0]
            if v2 == "win":
                wins += 1
            elif v2 == "tie":
                ties += 1
            total += 1
            if v1 != v2:
                rep["tie_aware_rejudge"].append({"task": t["id"], "bench_verdict": v1,
                                                 "v021_verdict": v2,
                                                 "task_mean_t": t["task_mean_t"],
                                                 "task_mean_b": t["task_mean_b"]})
        wr21 = round(wins / total, 4) if total else None
        rep["tie_aware_win_rate"] = wr21
        rep["checks"]["tie_aware_winrate_unchanged"] = (wr21 == bm_agg["task_win_rate"],
                                                        {"v021": wr21, "bench": bm_agg["task_win_rate"]})

        ok = all(v[0] for v in rep["checks"].values())
        rep["pass"] = ok
        results[pkg] = rep
        if not ok:
            failures.append(pkg)

    jwrite = S.jwrite
    jwrite(OUT, {"date": "2026-10-08",
                 "basis": "SF-0010 勘误卡 / K-5 alpha 裁决 planning/test-cards-20261008/K5-ruling-20261008.md",
                 "spec": "EVAL-SPEC-v0.2.1 §3.3-2/3（tie-aware）；K5B-05 swap 独立重算",
                 "packages": results,
                 "conclusion": ("三包 swap_reverse_tasks 独立重算=0/0/0；swap_delta=-delta 恒等成立；"
                                "正向 aggregate/verdict 与盘上逐值相符（正向路径与已落盘 verdict 未动）；"
                                "正向 v0.2.1 tie-aware 重判胜率不变（12.5%/40%/40%），仅伪 loss→tie 迁移"
                                if not failures else "存在失败断言：%s" % failures)})
    for pkg, rep in results.items():
        print("[%s] pass=%s" % (pkg, rep["pass"]))
        for k, (ok, detail) in rep["checks"].items():
            print("  %-34s %s  %s" % (k, "OK" if ok else "FAIL",
                                      json.dumps(detail, ensure_ascii=False)[:200]))
        if rep["tie_aware_rejudge"]:
            print("  tie_aware_rejudge:", json.dumps(rep["tie_aware_rejudge"], ensure_ascii=False))
    print("WROTE", OUT)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
