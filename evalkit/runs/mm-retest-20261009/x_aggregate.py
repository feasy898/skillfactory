#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/x_aggregate.py — mm 重测聚合（EVAL-SPEC v0.2.2 口径，零模型）。

§3.3-2（v0.2.1 tie-aware，§9 生效版）：逐对比较 3 次重复，计更高次数 h 与更低次数 l（h+l+p=3）——
  h≥2 → 任务胜；l≥2 → 任务负；其余（h≤1 且 l≤1，含全平与双 10 满饱和）→ 任务平。
§3.3-3：任务级胜率 = 任务胜数 ÷ 任务总数（平局计入分母、不计胜）。
§3.6 盲评门三条件【必须】同时满足：①均分差 Δ≥1.0；②任务级胜率 ≥60%（8 任务需 ≥5 胜）；
  ③反向任务 ≤1（反向=任务级 treatment 均分 < baseline 或 treatment 任务均分=0；
  平局不进反向计数；三条以最严格者裁决），逐条给实算值。
按族 matrix：glm 被测 4 题（t01/t03/t05/t07）/ minimax 被测 4 题（t02/t04/t06/t08）分列（fam_tasks）。
swap 独立重算（K5B-05 勘误口径）：从原始 per-pair 分数独立重算 swap 侧聚合——
  swap_delta + delta ≈ 0（恒等式）、swap_reverse_tasks（资产方向真实反向的镜像）
  从分数直算而非 verdict 标签互换。
效率门：token 比率与耗时比率 ≤2.0（records/arms/* 实测回填，测量项）。
unjudgeable/infra 任务退出本轮统计且 blind=false 计负（§9-5 本轮登记口径，轮后禁放宽）。
退出码：0=聚合落盘；2=判分记录不全（fail-closed，不出数）。
"""

import json
import os
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
TASK_ORDER = ["t0%d" % i for i in range(1, 9)]
REPS = [1, 2, 3]


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def arm_rec(fam, task, rep, arm):
    p = os.path.join(RUN, "records", "arms",
                     "%s-meeting-minutes-%s-rep%d-%s.json" % (fam, task, rep, arm))
    return jload(p) if os.path.isfile(p) else None


def main():
    jp = os.path.join(RUN, "records", "judging", "meeting-minutes.json")
    if not os.path.isfile(jp):
        print("判分记录不存在（先跑 x_judges.py）: %s" % jp, file=sys.stderr)
        return 2
    results = jload(jp)
    missing = [t for t in TASK_ORDER
               if not (isinstance(results.get(t), dict)
                       and results[t].get("status") in ("judged", "unjudgeable"))]
    if missing:
        print("判分记录不全（fail-closed）: %s" % missing, file=sys.stderr)
        return 2
    tasks = []
    for t in TASK_ORDER:
        r = results[t]
        fs = r.get("final_scores") or {}
        mapping = r.get("mapping") or {}
        by_rep = {}
        for pid, s in fs.items():
            if s is None:
                continue
            m = mapping.get(pid) or {}
            by_rep.setdefault(m.get("rep"), {})[m.get("arm")] = s
        pairs = []
        for rep in REPS:
            b = (by_rep.get(rep) or {}).get("baseline")
            tr = (by_rep.get(rep) or {}).get("treatment")
            if b is None or tr is None:
                pairs.append({"rep": rep, "t": tr, "b": b,
                              "task_verdict": "unjudgeable_pair"})
                continue
            pairs.append({"rep": rep, "t": tr, "b": b,
                          "task_verdict": "win" if tr > b else "loss" if tr < b else "tie"})
        h = sum(1 for p in pairs if p["task_verdict"] == "win")
        l = sum(1 for p in pairs if p["task_verdict"] == "loss")
        unj = sum(1 for p in pairs if p["task_verdict"] == "unjudgeable_pair")
        if unj or r.get("status") == "unjudgeable":
            verdict = "unjudgeable"
        elif h >= 2:
            verdict = "win"
        elif l >= 2:
            verdict = "loss"
        else:
            verdict = "tie"     # §3.3-2 tie-aware 出口
        t_vals = [p["t"] for p in pairs if p["t"] is not None]
        b_vals = [p["b"] for p in pairs if p["b"] is not None]
        t_mean = sum(t_vals) / len(t_vals) if t_vals else None
        b_mean = sum(b_vals) / len(b_vals) if b_vals else None
        delta = (t_mean - b_mean) if (t_mean is not None and b_mean is not None) else None
        # 反向（K5B-05 口径，从分数直算）：任务级 treatment 均分 < baseline，或 treatment 任务均分=0
        reverse = bool(delta is not None and (delta < 0 or t_mean == 0))
        tasks.append({"task": t, "tested_family": r.get("tested_family"),
                      "status": r.get("status"), "t_mean": t_mean, "b_mean": b_mean,
                      "delta": delta, "pairs": pairs, "h": h, "l": l,
                      "task_verdict": verdict, "reverse_flag": reverse,
                      "judge_consistency": r.get("judge_consistency"),
                      "fail_closed": r.get("fail_closed")})
    n_tasks = len(tasks)
    wins = sum(1 for t in tasks if t["task_verdict"] == "win")
    losses = sum(1 for t in tasks if t["task_verdict"] == "loss")
    ties = sum(1 for t in tasks if t["task_verdict"] == "tie")
    deltas = [t["delta"] for t in tasks if t["delta"] is not None]
    delta_all = sum(deltas) / len(deltas) if deltas else None
    reverse_n = sum(1 for t in tasks if t["reverse_flag"])
    gate = {"1_delta_ge_1": {"value": round(delta_all, 2) if delta_all is not None else None,
                             "pass": bool(delta_all is not None and delta_all >= 1.0)},
            "2_winrate_ge_60": {"value": round(wins / n_tasks, 4),
                                "wins": wins, "denominator": n_tasks,
                                "need_wins_8tasks": 5,
                                "pass": bool(wins / n_tasks >= 0.60)},
            "3_reverse_le_1": {"value": reverse_n, "pass": bool(reverse_n <= 1)},
            "unjudgeable_tasks": [t["task"] for t in tasks if t["status"] != "judged"],
            "note": "EVAL-SPEC v0.2.2 §3.6 三条件同时满足才 accepted；三条以最严格者裁决；"
                    "平局不进反向计数；反向任务=任务级 treatment 均分<baseline 或 treatment 任务均分=0；"
                    "unjudgeable 任务退出统计且 blind=false 计负（§9-5 本轮登记口径）"}
    # 按族 matrix
    fam_tasks = {}
    for fam in ("glm", "minimax"):
        sub = [t for t in tasks if t["tested_family"] == fam]
        fd = [t["delta"] for t in sub if t["delta"] is not None]
        fw = sum(1 for t in sub if t["task_verdict"] == "win")
        fam_tasks[fam] = {"n_tasks": len(sub),
                          "tasks": [t["task"] for t in sub],
                          "wins": fw,
                          "losses": sum(1 for t in sub if t["task_verdict"] == "loss"),
                          "ties": sum(1 for t in sub if t["task_verdict"] == "tie"),
                          "delta_mean": round(sum(fd) / len(fd), 2) if fd else None,
                          "win_rate": round(fw / len(sub), 4) if sub else None,
                          "reverse": sum(1 for t in sub if t["reverse_flag"]),
                          "task_verdicts": {t["task"]: t["task_verdict"] for t in sub}}
    # swap 独立重算（K5B-05 口径）：从 per-pair 分数直算，不互换 verdict 标签
    sh_vals = 0
    sl_vals = 0
    swap_wins = 0
    swap_reverse = 0
    swap_deltas = []
    for t in tasks:
        sp = [{"t": p["b"], "b": p["t"]} for p in t["pairs"]]
        sh = sum(1 for p in sp if p["t"] is not None and p["b"] is not None and p["t"] > p["b"])
        sl = sum(1 for p in sp if p["t"] is not None and p["b"] is not None and p["t"] < p["b"])
        sh_vals += sh
        sl_vals += sl
        if sh >= 2:
            swap_wins += 1
        st = [p["t"] for p in sp if p["t"] is not None]
        sb = [p["b"] for p in sp if p["b"] is not None]
        sm_t = sum(st) / len(st) if st else None
        sm_b = sum(sb) / len(sb) if sb else None
        if sm_t is not None and sm_b is not None and (sm_t < sm_b or sm_t == 0):
            swap_reverse += 1
        if st and sb:
            swap_deltas.append(sum(st) / len(st) - sum(sb) / len(sb))
    swap_delta = sum(swap_deltas) / len(swap_deltas) if swap_deltas else None
    swap_check = {"swap_delta": round(swap_delta, 6) if swap_delta is not None else None,
                  "swap_win_rate": round(swap_wins / n_tasks, 4),
                  "tie_rate": round(ties / n_tasks, 4),
                  "swap_reverse_tasks": swap_reverse,
                  "identity_abs_swap_delta_plus_delta": (round(abs(swap_delta + delta_all), 9)
                                                         if (swap_delta is not None and delta_all is not None) else None),
                  "note": "从原始 per-pair 分数独立重算（EVAL-SPEC v0.2.1 §3.3-2/3 tie-aware，"
                          "K5B-05 勘误口径，禁止 verdict 标签互换）；恒等式 swap_delta + delta ≈ 0；"
                          "swap_reverse_tasks=swap 侧资产方向真实反向数"}
    # 效率（records/arms 回填）
    t_tok = b_tok = t_dur = b_dur = 0
    n_runs = 0
    for t in tasks:
        for rep in REPS:
            for arm, acc_t, acc_b in (("treatment", True, False), ("baseline", False, True)):
                rec = arm_rec(t["tested_family"], t["task"], rep, arm)
                if rec and rec.get("model_usage_rows", 0) > 0 and not rec.get("timed_out"):
                    n_runs += 1
                    if acc_t:
                        t_tok += rec.get("input_tokens", 0) + rec.get("output_tokens", 0)
                        t_dur += rec.get("wall_ms", 0) / 1000.0
                    else:
                        b_tok += rec.get("input_tokens", 0) + rec.get("output_tokens", 0)
                        b_dur += rec.get("wall_ms", 0) / 1000.0
    eff = {"token_ratio": round(t_tok / b_tok, 3) if b_tok else None,
           "duration_ratio": round(t_dur / b_dur, 3) if b_dur else None,
           "tokens_traceability": "records/arms/* db model_usage join 实测回填（input+output）",
           "n_non_infra_runs": n_runs,
           "gate_le_2": None}
    if eff["token_ratio"] is not None:
        eff["gate_le_2"] = bool(eff["token_ratio"] <= 2.0 and eff["duration_ratio"] <= 2.0)
    accepted = (gate["1_delta_ge_1"]["pass"] and gate["2_winrate_ge_60"]["pass"]
                and gate["3_reverse_le_1"]["pass"] and not gate["unjudgeable_tasks"])
    agg = {"run": "mm-retest-20261009", "spec": "EVAL-SPEC v0.2.2（§9 五条收紧首轮即生效）",
           "tie_aware": "§3.3-2：n=3 h≥2 胜 / l≥2 负 / 其余平（v0.2.1 勘误口径，v0.2.2 下继续生效）",
           "tasks": tasks, "wins": wins, "losses": losses, "ties": ties,
           "win_rate": round(wins / n_tasks, 4),
           "delta_mean": round(delta_all, 2) if delta_all is not None else None,
           "fam_tasks": fam_tasks,
           "composite_gate": gate, "efficiency": eff, "_swap_check": swap_check,
           "verdict": ("accepted" if accepted else "rejected"),
           "evidence_level": "provisional", "single_round_signal": True,
           "blind_v02": not gate["unjudgeable_tasks"],
           "cross_generation_note": ("§3.7-4：本轮 judge_prompt_version=S8-JUDGE-v2-MMRETEST-1、"
                                     "任务集=merged mm 子树 8 题（adae05f2…）、n=3、v0.2.2，"
                                     "与 K5B round1（S8-JUDGE-v1、旧题集、n=2、v0.2）构成跨代——"
                                     "禁止与 K5B Δ 直接对位或合并披露；同代可比须两轮同 "
                                     "judge_model_id 与 judge_prompt_version")}
    out = os.path.join(RUN, "records", "aggregate.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0, "verdict": agg["verdict"],
                      "delta": agg["delta_mean"], "win_rate": agg["win_rate"],
                      "w/l/t": "%d/%d/%d" % (wins, losses, ties),
                      "fam": {k: {"d": v["delta_mean"], "wr": v["win_rate"]}
                              for k, v in fam_tasks.items()},
                      "swap_identity": swap_check["identity_abs_swap_delta_plus_delta"],
                      "eff": {"token_ratio": eff["token_ratio"],
                              "duration_ratio": eff["duration_ratio"]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
