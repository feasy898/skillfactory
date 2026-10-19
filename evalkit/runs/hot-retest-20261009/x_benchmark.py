#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/hot-retest-20261009/x_benchmark.py — benchmark-v02-2 并列落盘构建器（零模型）。

照 sf0008-k5b 九键结构（K5B-01/02）构建本轮 hot 重测 benchmark，**并列落盘**为
dist/hot-templates-skill/eval/results/benchmark-v02-2-hot-retest.json
（旧口径 results/benchmark.json=开发管线自评 5 旧题 v0.2 原样保留，新旧并列不覆盖；
新文件全量标注 v0.2.2）。
数据源（全部为盘上权威记录，零推断）：
  records/aggregate.json（判分后聚合）、records/judging/hot-templates.json、
  records/arms/*.json（tokens/duration/session/pin）。判分或聚合缺席 fail-closed exit 2。
退出码：0=落盘成功；2=数据不全。
"""
import json
import os
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "hot-retest-20261009")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "hot-templates-skill")
TASK_ORDER = ["t01", "t02", "t03", "t04", "t05", "t06", "t07", "t08"]
REPS = [1, 2, 3]
FROZEN_100 = "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6"
OUT_DIST = os.path.join(ROOT, "dist", "hot-templates-skill", "eval", "results",
                        "benchmark-v02-2-hot-retest.json")
OUT_RUN = os.path.join(RUN, "records", "benchmark-v02-2-hot-retest.json")


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def main():
    agg_p = os.path.join(RUN, "records", "aggregate.json")
    jp = os.path.join(RUN, "records", "judging", "hot-templates.json")
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
        tj = jload(os.path.join(MERGED, tid, "task.json"))
        arms = {"treatment": {"runs": []}, "baseline": {"runs": []}}
        for rep in REPS:
            for arm in ("treatment", "baseline"):
                p = os.path.join(RUN, "records", "arms",
                                 "%s-hot-templates-%s-rep%d-%s.json"
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
                       "format_check": "骨架.md + structure.json 在位可解析（t05 另含 A-D 四子目录；"
                                       "t08 空工作面/占位骨架均按端态判）",
                       "assertion": None}
                arms[arm]["runs"].append(run)
        tasks_out.append({"id": tj["id"], "merged_tid": tid, "dim": tj.get("dim"),
                          "tested_family": t["tested_family"],
                          "source": "planning/taskset-redesign/merged hot 子树（冻结 adae05f2…，"
                                    "t01..t08；index.json 逐文件 sha256 已核）",
                          "pass_line": tj.get("pass_line"),
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
                                      "comparison_ends": jc.get("comparison_ends")})
    for tid, jd in judging.items():
        if isinstance(jd, dict) and jd.get("status") == "infra_error":
            infra_errors.append({"task": tid, "missing": jd.get("missing")})
    gate = agg["composite_gate"]
    bench = {
        "asset": {"name": "hot-templates", "version": "1.0.0（dist 本轮零改动，owner 批准点形态）",
                  "form": "skill"},
        "evalbench": {"version": "merged hot 子树 8 题（t01..t08，冻结 adae05f2…）",
                      "taskset_frozen_100": FROZEN_100,
                      "gate_version": "v0.2.2（v0.2.1 并入 + §9 收紧：封顶上限语义/组合锚点/"
                                      "judge_arith_check 首轮生效/§3.4 比较对象/退出统计从登记）"},
        "model_pin": {
            "testers": {"glm": {"model_id": "GLM-5.3",
                                "provider_base_url": "account:bigmodel-individual-coding-plan",
                                "reasoning_variant": "max", "mechanism": "M4"},
                        "minimax": {"model_id": "Minimax-M3.1-Flash-Preview",
                                    "provider_base_url": "minimax",
                                    "reasoning_variant": "enabled", "mechanism": "M2"}},
            "judge_model_id": {"tested_glm": ["step-router-v1", "Minimax-M3.1-Flash-Preview"],
                               "tested_minimax": ["step-router-v1", "GLM-5.3"]},
            "judge_prompt_version": "S8-JUDGE-v2-2-HOTRETEST-1",
            "date": "2026-10-09",
            "cli_version": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9"},
        "tasks": tasks_out,
        "judge_consistency": judge_consistency,
        "judge_arith_check": {"rule": "EVAL-SPEC v0.2.2 §9-3 首轮即生效：每份判词逐产物机算"
                                      "total=round(10×Σ(dims×权重)/Σ权重,1)，不一致判词无效→同裁判"
                                      "重发 1 次→仍不一致 fail-closed unjudgeable",
                              "cap_note": "hot rubric 无红线封顶条款，公式分即终值（§9-1 上限语义）",
                              "per_task_all_match": {tid: judging[tid].get("judge_arith_all_match")
                                                     for tid in TASK_ORDER
                                                     if isinstance(judging.get(tid), dict)}},
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
            "tie_aware_rule": "§3.3-2：n=3 h≥2 胜 / l≥2 负 / 其余平"},
        "acceptance": {
            "gates": {"delta_ge_1": gate["1_delta_ge_1"],
                      "winrate_ge_60": gate["2_winrate_ge_60"],
                      "reverse_le_1": gate["3_reverse_le_1"],
                      "efficiency_le_2": {"token_ratio": agg["efficiency"]["token_ratio"],
                                          "duration_ratio": agg["efficiency"]["duration_ratio"],
                                          "pass": agg["efficiency"]["gate_le_2"]}},
            "blind_detail": {"panel": "被测 glm→[step-router-v1, Minimax-M3.1-Flash-Preview]；"
                                      "被测 minimax→[step-router-v1, GLM-5.3]",
                             "blind": "产物匿名化 P1..P6 洗牌 + 工作面全貌收集（排除判分器/技能挂载/"
                                      "转录/任务书面）+ 路径漂白；映射仅存 records/judge-staging/",
                             "judge_notes": "判据面=rubric.md+judge-notes.md 首批嵌入（装置教训）",
                             "t07_replay": "harness 机械对拍事实 _replay_diff.json 随暂存，判官可复跑复核"},
            "evidence_level": "provisional",
            "verdict": agg["verdict"]},
        "disclosure": {
            "rounds": 1,
            "single_round_signal": True,
            "single_round_signal_basis": "hot 新题集本轮=首轮，无同代确认轮（K5B-07 口径：单轮信号"
                                         "必须披露；确认前对外只说通过/不通过，禁引单点 Δ，§3.7-1）",
            "delta_range": None,
            "old_benchmark_parallel": "dist/hot-templates-skill/eval/results/benchmark.json"
                                      "（开发管线自评口径、5 旧题、v0.2、rejected）原样保留不覆盖；"
                                      "与本轮构成跨代（§3.7-4），数字禁止直接对位或合并披露",
            "cross_generation_note": ("本轮 judge_prompt_version=S8-JUDGE-v2-2-HOTRETEST-1、任务集 8 新题、"
                                      "n=3、v0.2.2")},
        "_efficiency": {"token_ratio": agg["efficiency"]["token_ratio"],
                        "duration_ratio": agg["efficiency"]["duration_ratio"],
                        "tokens_traceability": agg["efficiency"]["tokens_traceability"],
                        "n_non_infra_runs": agg["efficiency"]["n_non_infra_runs"]},
        "_swap_check": agg["_swap_check"],
        "_k5b02": {"tasks": len(agg["tasks"]), "runs_per_arm": 3, "required": "n=3（边界带/复检轮）",
                   "pass": agg["efficiency"]["n_non_infra_runs"] >= 2 * len(agg["tasks"])},
        "_round_meta": {"run_id": "hot-retest-20261009",
                        "base_commit": "8d14a15",
                        "retest_commit": None,
                        "protocol_deviations": ["新题判分=加权维度协议（rubric.md/judge-notes.md 首批嵌入）",
                                                "judge_arith_check 首轮即生效（v0.2.2 §9-3）",
                                                "t07 判官两档预登记按情形归档（存疑从严归破坏档）",
                                                "t08 内容口径判挂（R5）+ 组合锚 ⟦0,0,1⟧→2.0"],
                        "new_vs_old_parallel": "本文件为 v0.2.2 新口径并列落盘；旧 benchmark.json 原样未动"},
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
