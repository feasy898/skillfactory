#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/x_aggregate.py — office 重测聚合（EVAL-SPEC v0.2.1 口径，零模型）。

§3.3-2（v0.2.1，tie-aware n=3）：逐对比较 3 次重复，计更高次数 h 与更低次数 l（h+l+p=3）——
  h≥2 → 任务胜；l≥2 → 任务负；其余（h≤1 且 l≤1，含全平）→ 任务平。
§3.3-3：任务级胜率 = 任务胜数 ÷ 任务总数（平局计入分母、不计胜）。
§3.6 盲评门三条件【必须】同时满足：①均分差 Δ≥1.0；②任务级胜率 ≥60%（13 任务需 ≥8 胜）；
  ③反向任务 ≤1（平局不进反向计数；三条以最严格者裁决），逐条给实算值。
§3.7-4 跨代可比：本轮 judge_prompt_version=S8-JUDGE-v2-OFXRETEST-1 且任务集 5→13、n=2→3，
  与 K5B round1（v0.2/S8-JUDGE-v1/n=2/5 题）构成跨代——【禁止】与 K5B Δ 直接对位或合并披露。
效率门：token 比率与耗时比率 ≤2.0（db join 实测，测量项）。
退出码：0=聚合落盘；2=判分记录不全（fail-closed，不出数）。
"""

import json
import os
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "office-retest-20261009")
TASK_ORDER = ["ab1-standard-four-templates", "ab2-boundary-missing-required",
              "ab3-empty-and-string-lists", "ab4-invalid-input-rejection",
              "ab5-determinism-layout-selfeval",
              "t01", "t02", "t03", "t04", "t05", "t06", "t07", "t08"]
REPS = [1, 2, 3]


def main():
    jp = os.path.join(RUN, "records", "judging", "office-templates.json")
    if not os.path.isfile(jp):
        print("判分记录不存在（先跑 x_judges.py）: %s" % jp, file=sys.stderr)
        return 2
    results = json.load(open(jp, encoding="utf-8"))
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
        # mapping: pid -> {rep, arm}；scores 按 rep 配对（同 rep 的 treatment/baseline 比较）
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
        if unj:
            verdict = "unjudgeable"
        elif h >= 2:
            verdict = "win"
        elif l >= 2:
            verdict = "loss"
        else:
            verdict = "tie"     # §3.3-2 v0.2.1 tie 出口
        t_mean = sum(p["t"] for p in pairs if p["t"] is not None) / max(1, sum(1 for p in pairs if p["t"] is not None))
        b_mean = sum(p["b"] for p in pairs if p["b"] is not None) / max(1, sum(1 for p in pairs if p["b"] is not None))
        reverse = bool(verdict == "loss" or (t_mean == 0 and b_mean >= 0))
        tasks.append({"task": t, "tested_family": r.get("tested_family"),
                      "status": r.get("status"), "t_mean": round(t_mean, 2),
                      "b_mean": round(b_mean, 2), "delta": round(t_mean - b_mean, 2),
                      "pairs": pairs, "h": h, "l": l, "task_verdict": verdict,
                      "reverse_flag": reverse,
                      "judge_consistency": r.get("judge_consistency")})
    n_judged = [t for t in tasks if t["status"] == "judged"]
    wins = sum(1 for t in tasks if t["task_verdict"] == "win")
    losses = sum(1 for t in tasks if t["task_verdict"] == "loss")
    ties = sum(1 for t in tasks if t["task_verdict"] == "tie")
    denominator = len(tasks)
    delta_all = sum(t["delta"] for t in tasks) / len(tasks)
    reverse_n = sum(1 for t in tasks if t["reverse_flag"])
    gate = {"1_delta_ge_1": {"value": round(delta_all, 2), "pass": bool(delta_all >= 1.0)},
            "2_winrate_ge_60": {"value": round(wins / denominator, 4),
                                "wins": wins, "denominator": denominator,
                                "need_wins_13tasks": 8,
                                "pass": bool(wins / denominator >= 0.60)},
            "3_reverse_le_1": {"value": reverse_n, "pass": bool(reverse_n <= 1)},
            "unjudgeable_tasks": [t["task"] for t in tasks if t["status"] != "judged"],
            "note": "EVAL-SPEC v0.2.1 §3.6 三条件同时满足才 accepted；三条以最严格者裁决；"
                    "平局不进反向计数；反向任务=treatment 均分<baseline 或 treatment 任务均分=0"}
    agg = {"run": "office-retest-20261009", "spec": "EVAL-SPEC v0.2.1",
           "tie_aware": "§3.3-2：n=3 h≥2 胜 / l≥2 负 / 其余平（v0.2.1 勘误口径）",
           "tasks": tasks, "wins": wins, "losses": losses, "ties": ties,
           "win_rate": round(wins / denominator, 4),
           "delta_mean": round(delta_all, 2),
           "composite_gate": gate,
           "verdict": ("accepted" if (gate["1_delta_ge_1"]["pass"] and gate["2_winrate_ge_60"]["pass"]
                                      and gate["3_reverse_le_1"]["pass"]
                                      and not gate["unjudgeable_tasks"]) else "rejected"),
           "evidence_level": "provisional", "single_round_signal": True,
           "cross_generation_note": ("§3.7-4：本轮 judge_prompt_version=S8-JUDGE-v2-OFXRETEST-1、"
                                     "任务集 13（5ab+8new）、n=3，与 K5B round1（S8-JUDGE-v1、5 题、n=2）"
                                     "构成跨代——禁止与 K5B Δ 直接对位或合并披露；"
                                     "同代可比须两轮同 judge_model_id 与 judge_prompt_version")}
    out = os.path.join(RUN, "records", "aggregate.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0, "verdict": agg["verdict"],
                      "delta": agg["delta_mean"], "win_rate": agg["win_rate"],
                      "w/l/t": "%d/%d/%d" % (wins, losses, ties)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
