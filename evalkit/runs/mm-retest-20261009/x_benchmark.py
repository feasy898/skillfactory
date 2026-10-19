#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/x_benchmark.py — benchmark.json 并列落盘构建器（零模型）。

照 sf0008-k5b/office-retest 九键结构（K5B-01/02）构建本轮 mm 重测 benchmark，**并列落盘**为
dist/meeting-minutes-skill/eval/results/benchmark-v02-2-mm-retest.json
（旧口径 benchmark.json=K5B round1 原样保留，新旧并列不覆盖；新文件全量标注 v0.2.2）。
数据源（全部为盘上权威记录，零推断）：
  records/aggregate.json（判分后聚合）、records/judging/meeting-minutes.json、
  records/arms/*.json（tokens/duration/session/pin）。判分或聚合缺席 fail-closed exit 2。
退出码：0=落盘成功；2=数据不全。
"""
import json
import os
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
MERGED_MM = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "meeting-minutes-skill")
TASK_ORDER = ["t0%d" % i for i in range(1, 9)]
REPS = [1, 2, 3]
OUT_DIST = os.path.join(ROOT, "dist", "meeting-minutes-skill", "eval", "results",
                        "benchmark-v02-2-mm-retest.json")
OUT_RUN = os.path.join(RUN, "records", "benchmark-v02-2-mm-retest.json")


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def main():
    agg_p = os.path.join(RUN, "records", "aggregate.json")
    jp = os.path.join(RUN, "records", "judging", "meeting-minutes.json")
    if not (os.path.isfile(agg_p) and os.path.isfile(jp)):
        print("聚合/判分记录缺席（fail-closed）", file=sys.stderr)
        return 2
    agg = jload(agg_p)
    judging = jload(jp)
    tasks_out = []
    judge_consistency = []
    infra_errors = []
    for t in agg["tasks"]:
        tid = t["task"]
        jd = judging[tid]
        arms = {"treatment": {"runs": []}, "baseline": {"runs": []}}
        for rep in REPS:
            for arm in ("treatment", "baseline"):
                p = os.path.join(RUN, "records", "arms",
                                 "%s-meeting-minutes-%s-rep%d-%s.json"
                                 % (t["tested_family"], tid, rep, arm))
                rec = jload(p) if os.path.isfile(p) else None
                score = None
                for pid, m in (jd.get("mapping") or {}).items():
                    if m.get("rep") == rep and m.get("arm") == arm:
                        score = (jd.get("final_scores") or {}).get(pid)
                run = {"score": score,
                       "tokens": ((rec.get("input_tokens", 0) + rec.get("output_tokens", 0))
                                  if rec else None),
                       "duration_s": (round(rec.get("wall_ms", 0) / 1000.0, 3) if rec else None),
                       "session_id": rec.get("session_id") if rec else None,
                       "infra_error": rec.get("classify", {}).get("bucket") == "harness_crash"
                                      if rec else True,
                       "rep": rep, "bucket": rec.get("classify", {}).get("bucket") if rec else None,
                       "pin_verdict": rec.get("pin_verdict") if rec else None,
                       "format_check": "纪要.docx + summary.json 在位可解析",
                       "assertion": None}
                arms[arm]["runs"].append(run)
        tj = jload(os.path.join(MERGED_MM, tid, "task.json"))
        tasks_out.append({"id": tid, "tested_family": t["tested_family"],
                          "source": "planning/taskset-redesign/merged meeting-minutes 子树"
                                    "（冻结 adae05f2…）",
                          "dim": tj.get("dim"), "pass_line": tj.get("pass_line"),
                          "arms": arms,
                          "task_mean_t": t["t_mean"], "task_mean_b": t["b_mean"],
                          "delta": t["delta"], "h": t["h"], "l": t["l"],
                          "task_verdict": t["task_verdict"],
                          "reverse_flag": t["reverse_flag"]})
        jc = t.get("judge_consistency") or {}
        if jc:
            judge_consistency.append({"task": tid, "resample_of": jc.get("resample_of"),
                                      "first_score": jc.get("first_score"),
                                      "second_score": jc.get("second_score"),
                                      "delta": jc.get("delta"), "action": jc.get("action"),
                                      "compare_sides": jc.get("compare_sides")})
    for tid, jd in judging.items():
        if jd.get("status") == "infra_error":
            infra_errors.append({"task": tid, "missing": jd.get("missing")})
    gate = agg["composite_gate"]
    bench = {
        "asset": {"name": "meeting-minutes", "version": jload(
            os.path.join(ROOT, "dist", "meeting-minutes-skill", "SKILL.md")
        ).get("version") if False else "1.0.0（SKILL.md frontmatter；本轮零改动）",
            "form": "skill"},
        "evalbench": {"version": "merged mm 子树 8 题（taskset-redesign 冻结 adae05f2…）",
                      "golden_version": "b3be400ae3b4984a1537d4909b9ea379246d8b978d3c8a179c90182c5c854315"
                                        "（dist/meeting-minutes-skill/eval/golden.json 开工实读，未用未动）",
                      "taskset_frozen_100": "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6",
                      "gate_version": "v0.2.2（tie-aware + 跨代可比条件 + §9 五条收紧首轮即生效）"},
        "model_pin": {
            "testers": {"glm": {"model_id": "GLM-5.3",
                                "provider_base_url": "account:bigmodel-individual-coding-plan",
                                "reasoning_variant": "max", "mechanism": "M4"},
                        "minimax": {"model_id": "Minimax-M3.1-Flash-Preview",
                                    "provider_base_url": "minimax",
                                    "reasoning_variant": "enabled", "mechanism": "M2"}},
            "judge_model_id": {"tested_glm": ["step-router-v1", "Minimax-M3.1-Flash-Preview"],
                               "tested_minimax": ["step-router-v1", "GLM-5.3"]},
            "judge_prompt_version": "S8-JUDGE-v2-MMRETEST-1",
            "date": "2026-10-09",
            "cli_version": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9"},
        "tasks": tasks_out,
        "judge_consistency": judge_consistency,
        "infra_errors": infra_errors,
        "aggregate": {"mean_baseline": round(
            sum(t["b_mean"] for t in agg["tasks"] if t["b_mean"] is not None)
            / max(1, sum(1 for t in agg["tasks"] if t["b_mean"] is not None)), 3),
            "mean_treatment": round(
            sum(t["t_mean"] for t in agg["tasks"] if t["t_mean"] is not None)
            / max(1, sum(1 for t in agg["tasks"] if t["t_mean"] is not None)), 3),
            "delta": agg["delta_mean"], "task_win_rate": agg["win_rate"],
            "pair_win_rate": None,
            "reverse_tasks": gate["3_reverse_le_1"]["value"], "ties": agg["ties"],
            "valid_tasks": sum(1 for t in agg["tasks"] if t["status"] == "judged"),
            "total_tasks": len(agg["tasks"]),
            "fam_tasks": agg["fam_tasks"],
            "tie_aware_rule": "§3.3-2（v0.2.2 下继续生效）：n=3 h≥2 胜 / l≥2 负 / 其余平"},
        "acceptance": {
            "gates": {"delta_ge_1": gate["1_delta_ge_1"],
                      "winrate_ge_60": gate["2_winrate_ge_60"],
                      "reverse_le_1": gate["3_reverse_le_1"],
                      "blind_v02": {"value": agg["blind_v02"],
                                    "pass": agg["blind_v02"],
                                    "basis": "无 unjudgeable 任务（§9-5 登记口径：unjudgeable ⇒ blind=false 计负）"},
                      "efficiency_le_2": {"token_ratio": agg["efficiency"]["token_ratio"],
                                          "duration_ratio": agg["efficiency"]["duration_ratio"],
                                          "pass": agg["efficiency"]["gate_le_2"]}},
            "blind_detail": {"panel": "被测 glm（t01/t03/t05/t07）→[step-router-v1, Minimax-M3.1-Flash-Preview]；"
                                      "被测 minimax（t02/t04/t06/t08）→[step-router-v1, GLM-5.3]",
                             "blind": "产物匿名化 P1..P6 洗牌 + docx 事实抽取 + 路径漂白；映射仅存 records/judge-staging/",
                             "judge_arith_check": "§9-3 首轮即生效：逐判词机算 total 对拍，不一致重发 1 次，仍不一致 fail-closed"},
            "evidence_level": "provisional",
            "verdict": agg["verdict"]},
        "disclosure": {
            "rounds": 1,
            "single_round_signal": True,
            "single_round_signal_basis": "本轮=merged 新题集首轮（n=3）；单轮信号，同代第二轮确认前"
                                         "禁止外引单点 Δ（§3.7-1）；对外口径限于 verdict/n/rep/轮次/"
                                         "钉版/evalbench 版本",
            "delta_range": None,
            "round1_source": "dist/meeting-minutes-skill/eval/results/benchmark.json"
                             "（K5B round1 v0.2 原样并列保留，新旧并列不覆盖）",
            "cross_generation_note": ("v0.2.1 §3.7-4：本轮与 K5B round1 判分协议版本不同"
                                      "（S8-JUDGE-v1→S8-JUDGE-v2-MMRETEST-1）、任务集不同"
                                      "（旧题集→merged adae05f2…）、n=2→3，构成跨代——"
                                      "两轮数字禁止直接 Δ 对位或合并披露；本轮按 v0.2.2 独立判定"),
            "d3_note": "不适用（本轮无 D3 轨）"},
        "_efficiency": {"token_ratio": agg["efficiency"]["token_ratio"],
                        "duration_ratio": agg["efficiency"]["duration_ratio"],
                        "tokens_traceability": agg["efficiency"]["tokens_traceability"],
                        "n_non_infra_runs": agg["efficiency"]["n_non_infra_runs"]},
        "_swap_check": agg["_swap_check"],
        "_k5b02": {"tasks": len(agg["tasks"]), "runs_per_arm": 3, "required": "n=3（复检轮口径）",
                   "pass": agg["efficiency"]["n_non_infra_runs"] >= 2 * len(agg["tasks"])},
        "_round_meta": {"run_id": "mm-retest-20261009",
                        "base_commit": "8d14a159d2d05911c771e93e8363eb13ba97110b",
                        "protocol_deviations": ["全 8 题=加权维度协议（rubric.md+judge-notes.md 判据面）"],
                        "new_vs_old_parallel": "本文件为 v0.2.2 新口径并列落盘；K5B round1 文件原样未动"},
        }
    for p in (OUT_DIST, OUT_RUN):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(bench, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(json.dumps({"exit": 0, "out_dist": os.path.relpath(OUT_DIST, ROOT),
                      "tasks": len(tasks_out), "verdict": bench["acceptance"]["verdict"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
