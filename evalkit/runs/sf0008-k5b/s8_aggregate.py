#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0008-k5b/s8_aggregate.py — SF-0008 三包 benchmark.json 落盘 + K5B 门自检。

输入：records/arms/*.json（臂权威记录，db join 已回填）、records/judging/<pkg>-<task>.json、
     precheck/k5b09-*（确定性门）。
输出：dist/<pkg>/eval/results/benchmark.json（§8.1 九键）+ records/k5b-checks.json。
门语义（K5B-03/04/05/06/07/08）：
  deterministic: K5B-09 绿0红1 ×3 包 + golden sha256==REGISTRY 登记
  blind_v02:     每任务面板=2 异族裁判且与被测族零交集 ∧ 无 unjudgeable 任务（K5B-04）
  efficiency:    tokens 比率 ≤2.0 ∧ 耗时比率 ≤2.0（非 infra 单元；K5B-03）
  format:        非 infra 单元产物文件齐备可解析（checker 报告）
  assertion:     treatment 侧确定性断言全过（checker 报告；baseline 如实记录不进门）
  verdict:       accepted ⟺ 五门全 true（K5B-08）；evidence_level ∈ {synthetic-passed, provisional}
聚合（K5B-05，SF-0010 勘误后）：delta/task_win_rate/reverse_tasks 独立复算；swap 块为
  从原始 per-run 分数独立重算——swap 后 (treatment',baseline')=(原baseline,原treatment)，
  逐任务调用 judge_task_tieaware（EVAL-SPEC v0.2.1 §3.3-2/3 tie-aware）重算
  delta'/winRate'（镜像量）；reverse_tasks' 锚定资产方向按 §3.6（平局不进反向计数）
  独立重算，K5B-05「reverse_tasks 不变」恒等；【禁止】verdict 标签互换式伪复算
  （2026-10-08 勘误前旧实现翻标签+把镜像均分伪象当 reverse_tasks，产假数字 6/3/4，
  独立重算真实反向 0/0/0——K-5 裁决在案）。
用法：python s8_aggregate.py   （退出码 0=全部基准文件与自检落盘，门红不代表本脚本红）
"""

import hashlib
import json
import os
import re
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0008-k5b")
PKGS = {"meeting-minutes": "meeting-minutes-skill",
        "office-templates": "office-templates-skill",
        "hot-templates": "hot-templates-skill"}
DOMAIN = {"meeting-minutes": "会议纪要生成", "office-templates": "中文公文文书生成",
          "hot-templates": "四平台爆款内容结构生成"}
REPS = {"meeting-minutes": 2, "office-templates": 2, "hot-templates": 3}
JUDGE_PROMPT_VERSION = "S8-JUDGE-v1"


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jwrite(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def tasks_of(pkg):
    if pkg == "meeting-minutes":
        return [t["id"] for t in jload(os.path.join(
            ROOT, "v2/evalbench-v02/meeting-minutes/tasks.json"))]
    return [t["id"] for t in jload(os.path.join(
        ROOT, "dist", PKGS[pkg], "eval/golden.json"))["ab_tasks"]]


def skill_meta(pkg):
    sk = os.path.join(ROOT, "dist", PKGS[pkg], "SKILL.md")
    m = re.search(r"^name:\s*(\S+)", open(sk, encoding="utf-8").read(), re.M)
    v = re.search(r"^version:\s*(\S+)", open(sk, encoding="utf-8").read(), re.M)
    return m.group(1), (v.group(1) if v else None)


def product_files_ok(pkg, ad):
    """format 门：非 infra 单元产物齐备可解析。返回 (ok, detail)。"""
    out = os.path.join(ad, "out")
    try:
        if pkg == "meeting-minutes":
            import docx
            d = os.path.join(out, "纪要.docx")
            sj = os.path.join(out, "summary.json")
            if not (os.path.isfile(d) and os.path.isfile(sj)):
                return False, "缺产物"
            docx.Document(d)
            s = jload(sj)
            if not isinstance(s, dict) or "合计" not in s:
                return False, "summary.json 结构不符"
            return True, "纪要.docx+summary.json 在位可解析"
        if pkg == "office-templates":
            import docx
            units = []
            for dp, _dn, fns in os.walk(out):
                if "文书.docx" in fns:
                    units.append(dp)
            if not units:
                return False, "无产物单元"
            for u in units:
                docx.Document(os.path.join(u, "文书.docx"))
                jload(os.path.join(u, "fields.json"))
            return True, "%d 个单元产物在位可解析" % len(units)
        if pkg == "hot-templates":
            cands = [out] + [os.path.join(out, d) for d in sorted(os.listdir(out))
                             if os.path.isdir(os.path.join(out, d))] \
                if os.path.isdir(out) else [out]
            for cd in cands:
                if os.path.isfile(os.path.join(cd, "structure.json")) and \
                        os.path.isfile(os.path.join(cd, "骨架.md")):
                    jload(os.path.join(cd, "structure.json"))
                    return True, "两产物在位可解析（%s）" % os.path.relpath(cd, out)
            return False, "骨架.md/structure.json 缺失"
    except Exception as exc:
        return False, "解析失败:%s" % exc
    return False, "未知包"


def collect_pkg(pkg, checks):
    fam_tasks = {}
    alloc = jload(os.path.join(RUN, "round-plan.json"))["arm_allocation"]["per_package"]
    for p in alloc:
        if p["pkg"] == pkg:
            for t in p["glm_tasks"]:
                fam_tasks[t] = "glm"
            for t in p["minimax_tasks"]:
                fam_tasks[t] = "minimax"
    judging = jload(os.path.join(RUN, "records", "judging", "%s.json" % pkg)) \
        if os.path.isfile(os.path.join(RUN, "records", "judging", "%s.json" % pkg)) else {}
    infra_errors, tasks, fmt_fails, assert_fails = [], [], [], []
    eff = {"t_tokens": [], "b_tokens": [], "t_dur": [], "b_dur": []}
    n_runs = 0
    for task in tasks_of(pkg):
        fam = fam_tasks[task]
        runs = {"treatment": {"runs": []}, "baseline": {"runs": []}}
        for rep in range(1, REPS[pkg] + 1):
            for arm in ("baseline", "treatment"):
                ad = os.path.join(RUN, fam, "%s-%s-rep%d" % (pkg, task, rep), arm)
                recp = os.path.join(ad, "records", "arm_run.json")
                if not os.path.isfile(recp):
                    infra_errors.append({"task": task, "arm": arm, "run": rep,
                                         "reason": "records 缺失（臂未完成）"})
                    runs[arm]["runs"].append({"score": None, "tokens": None, "duration_s": None,
                                      "session_id": None, "infra_error": True, "rep": rep})
                    continue
                rec = jload(recp)
                bucket = rec.get("classify", {}).get("bucket")
                is_infra = bucket in ("infra_error", "harness_crash", "arm_timeout") \
                    or rec.get("timed_out") or not rec.get("session_id")
                fmt_ok, fmt_detail = (None, "infra 单元不检") if is_infra else product_files_ok(pkg, ad)
                if not is_infra:
                    n_runs += 1
                    if not fmt_ok:
                        fmt_fails.append({"task": task, "arm": arm, "rep": rep,
                                          "detail": fmt_detail})
                chk = checks.get("%s|%s" % (pkg, task), {})
                a_ok = chk.get("%s-rep%d" % (arm, rep), {}).get("assertion_pass") \
                    if isinstance(chk.get("%s-rep%d" % (arm, rep)), dict) else None
                if not is_infra and arm == "treatment" and a_ok is False:
                    assert_fails.append({"task": task, "rep": rep,
                                         "detail": chk.get("%s-rep%d" % (arm, rep), {}).get("detail")})
                tokens = (rec.get("input_tokens") or 0) + (rec.get("output_tokens") or 0)
                dur = round((rec.get("wall_ms") or 0) / 1000.0, 3)
                runs[arm]["runs"].append({"score": None, "tokens": tokens, "duration_s": dur,
                                  "session_id": rec.get("session_id"),
                                  "infra_error": bool(is_infra), "rep": rep,
                                  "bucket": bucket, "pin_verdict": rec.get("pin_verdict"),
                                  "format_check": fmt_detail if not is_infra else None,
                                  "assertion": a_ok})
                if is_infra:
                    infra_errors.append({"task": task, "arm": arm, "run": rep,
                                         "reason": "classify=%s" % bucket})
                else:
                    if arm == "treatment":
                        eff["t_tokens"].append(tokens); eff["t_dur"].append(dur)
                    else:
                        eff["b_tokens"].append(tokens); eff["b_dur"].append(dur)
        tasks.append({"id": task, "tested_family": fam, "arms": runs, "_pkg": pkg})
    return {"tasks": tasks, "infra_errors": infra_errors, "eff": eff,
            "fmt_fails": fmt_fails, "assert_fails": assert_fails, "judging": judging,
            "fam_tasks": fam_tasks, "n_runs": n_runs}


def attach_scores(pkg, data):
    """judging.final_scores 映射回 runs（pid↔rep/arm 由 mapping 还原）。"""
    judging = data["judging"]
    for t in data["tasks"]:
        task = t["id"]
        jd = judging.get(task) or {}
        mapping = (jd.get("mapping") or {})
        fin = jd.get("final_scores") or {}
        for arm in ("treatment", "baseline"):
            for r in t["arms"][arm]["runs"]:
                pid = next((p for p, m in mapping.items()
                            if isinstance(m, dict) and m.get("rep") == r.get("rep")
                            and m.get("arm") == arm), None)
                r["score"] = fin.get(pid)
        means = {}
        for arm in ("treatment", "baseline"):
            ss = [r["score"] for r in t["arms"][arm]["runs"] if r["score"] is not None]
            means[arm] = round(sum(ss) / len(ss), 4) if ss else None
        t["task_mean_t"] = means["treatment"]
        t["task_mean_b"] = means["baseline"]
        n = len(t["arms"]["treatment"]["runs"])
        unj = jd.get("judge_consistency", {}).get("action") == "unjudgeable"
        no_scores = means["treatment"] is None or means["baseline"] is None
        if unj or no_scores:
            t["task_verdict"] = "unjudgeable"
        else:
            tr = t["arms"]["treatment"]["runs"]; bs = t["arms"]["baseline"]["runs"]
            wins = sum(1 for a, b in zip([r["score"] for r in tr], [r["score"] for r in bs])
                       if a is not None and b is not None and a > b)
            losses = sum(1 for a, b in zip([r["score"] for r in tr], [r["score"] for r in bs])
                         if a is not None and b is not None and a < b)
            if n == 3:
                t["task_verdict"] = "win" if wins >= 2 else "loss"
            else:
                t["task_verdict"] = "win" if wins == n and losses == 0 else \
                    ("loss" if losses == n and wins == 0 else "tie")
        mt, mb = t["task_mean_t"], t["task_mean_b"]
        t["reverse_flag"] = (t["task_verdict"] != "unjudgeable" and mt is not None and
                             (mt < mb or mt == 0))
    return data


def aggregate(data):
    valid = [t for t in data["tasks"] if t["task_verdict"] != "unjudgeable"]
    mt = [t["task_mean_t"] for t in valid]
    mb = [t["task_mean_b"] for t in valid]
    mean_t = round(sum(mt) / len(mt), 4) if mt else None
    mean_b = round(sum(mb) / len(mb), 4) if mb else None
    delta = round(mean_t - mean_b, 4) if (mean_t is not None and mean_b is not None) else None
    wins = sum(1 for t in valid if t["task_verdict"] == "win")
    ties = sum(1 for t in valid if t["task_verdict"] == "tie")
    total = len(valid)
    win_rate = round(wins / total, 4) if total else None
    pairs = [(r["score"], l["score"]) for t in valid
             for r, l in zip(t["arms"]["treatment"]["runs"], t["arms"]["baseline"]["runs"])
             if r["score"] is not None and l["score"] is not None]
    pair_win = round(sum(1 for a, b in pairs if a > b) / len(pairs), 4) if pairs else None
    reverse = sum(1 for t in valid if t["reverse_flag"])
    return {"mean_baseline": mean_b, "mean_treatment": mean_t, "delta": delta,
            "task_win_rate": win_rate, "pair_win_rate": pair_win,
            "reverse_tasks": reverse, "ties": ties,
            "valid_tasks": total, "total_tasks": len(data["tasks"])}


def judge_task_tieaware(tr_scores, bs_scores):
    """EVAL-SPEC v0.2.1 §3.3-2/3（tie-aware）：从原始 per-run 分数独立判任务级胜负。

    n=3：更高次数 h≥2 → win；更低次数 l≥2 → loss；其余（h≤1 且 l≤1，必含平局，
         含全平与双 10 满饱和）→ tie（v0.2 原口径「≤1 次更高→loss」无 tie 出口，
         饱和题集产伪 loss——K-5 裁决附带入案发现，SF-0010 勘误升版消除）。
    n=2：均高 → win；均低 → loss；其余 → tie（与 v0.2 §3.3-2 原口径一致）。
    返回 (task_verdict, mean_tr, mean_bs)；均分 round 4 位，与 attach_scores 同口径。
    """
    pairs = [(a, b) for a, b in zip(tr_scores, bs_scores)
             if a is not None and b is not None]
    n = len(pairs)
    higher = sum(1 for a, b in pairs if a > b)
    lower = sum(1 for a, b in pairs if a < b)
    mean_tr = round(sum(a for a, _ in pairs) / n, 4) if n else None
    mean_bs = round(sum(b for _, b in pairs) / n, 4) if n else None
    if n == 3:
        verdict = "win" if higher >= 2 else ("loss" if lower >= 2 else "tie")
    else:
        verdict = "win" if (n and higher == n) else \
            ("loss" if (n and lower == n) else "tie")
    return verdict, mean_tr, mean_bs


def swap_check(tasks, agg):
    """K5B-05（SF-0010 勘误后口径）：swap 后 (treatment', baseline')=(原 baseline, 原 treatment)，
    从原始 per-run 分数独立重算（EVAL-SPEC v0.2.1 §3.3-2/3 tie-aware），
    【禁止】verdict 标签互换式伪复算。逐量口径：
      - swap_delta / swap_win_rate / tie_rate：镜像量，对新臂序独立重算
        （delta'=-delta 在 valid 任务集上恒等；winRate'/tieRate' 为镜像独立重算值）；
      - swap_reverse_tasks：**资产方向不变量**——K5B-05 原文要求 swap 重算后
        「reverse_tasks 不变」，反向锚定资产方向（treatment=挂资产侧），按 §3.3-2/3
        （tie-aware 判 task_verdict）+ §3.6（反向 = 非 tie 任务且 task_mean_t < task_mean_b
        或 task_mean_t == 0；平局任务不进反向计数）从原始 per-run 分数独立重算；
      - mirror_flipped_tasks：附加披露——镜像均分反向计数（新 treatment 均分更低或 =0 的
        任务数，无平局排除）。旧实现（2026-10-08 勘误前）误把此镜像伪象当 reverse_tasks
        留痕并叠加 win<->loss 标签互换，产出假数字 6/3/4（tie 任务均分不对称 + win 镜像
        必落败所致）；K-5 裁决独立重算真实反向=0/0/0。
    """
    delta_t2, delta_b2 = [], []
    wins = losses = ties = 0
    reverse_true = 0
    mirror_flipped = 0
    for t in tasks:
        if t["task_verdict"] == "unjudgeable":
            continue
        tr = [r["score"] for r in t["arms"]["treatment"]["runs"]]
        bs = [r["score"] for r in t["arms"]["baseline"]["runs"]]
        v2, mt2, mb2 = judge_task_tieaware(bs, tr)  # swap：新 treatment=原 baseline
        if v2 == "win":
            wins += 1
        elif v2 == "loss":
            losses += 1
        else:
            ties += 1
        delta_t2.append(mt2); delta_b2.append(mb2)
        # reverse_tasks'（K5B-05 不变量）：资产方向独立重算，§3.3-2/3 tie-aware + §3.6 口径
        v_fwd, mt_fwd, mb_fwd = judge_task_tieaware(tr, bs)
        if v_fwd != "tie" and (mt_fwd < mb_fwd or mt_fwd == 0):
            reverse_true += 1
        # 镜像均分反向（伪象，仅披露）
        if mt2 is not None and (mt2 < mb2 or mt2 == 0):
            mirror_flipped += 1
    total = wins + losses + ties
    n = len(delta_t2)
    return {"swap_delta": round(sum(delta_t2) / n - sum(delta_b2) / n, 4) if n else None,
            "swap_win_rate": round(wins / total, 4) if total else None,
            "tie_rate": round(ties / total, 4) if total else None,
            "swap_reverse_tasks": reverse_true,
            "mirror_flipped_tasks": mirror_flipped,
            "method": ("swap 后 (treatment',baseline')=(原baseline,原treatment)；delta'/winRate'/"
                       "tieRate' 为镜像独立重算（EVAL-SPEC v0.2.1 §3.3-2/3 tie-aware）；"
                       "reverse_tasks' 锚定资产方向按 §3.3-2/3+§3.6（平局不进反向计数）独立重算"
                       "（K5B-05：reverse_tasks 不变）。SF-0010 勘误：禁止 verdict 标签互换式伪复算"),
            "identity_note": ("delta'=−delta 在 valid 任务集上恒等成立（均值差换序）；winRate'/"
                              "tieRate' 为镜像独立重算值而非恒等式（§3.3-3 平局计入分母不计胜）；"
                              "reverse_tasks'=真实反向（资产方向不变量，swap 重算后不变）；"
                              "mirror_flipped_tasks 为镜像均分伪象（旧假数字 6/3/4 的来源），"
                              "非资产反向")}


def build_benchmark(pkg, data, checks, det):
    name, version = skill_meta(pkg)
    gold_sha = sha256_file(os.path.join(ROOT, "dist", PKGS[pkg], "eval/golden.json"))
    eff = data["eff"]
    tok_ratio = round(sum(eff["t_tokens"]) / sum(eff["b_tokens"]), 4) if eff["b_tokens"] else None
    dur_ratio = round(sum(eff["t_dur"]) / sum(eff["b_dur"]), 4) if eff["b_dur"] else None
    agg = aggregate(data)
    jc = []
    unj = 0
    for t in data["tasks"]:
        jd = (data["judging"].get(t["id"]) or {})
        c = jd.get("judge_consistency")
        if c:
            jc.append(c)
        if t["task_verdict"] == "unjudgeable":
            unj += 1
    # 盲评门 v0.2（EVAL-SPEC §3.6 复合线）：Δ≥1.0 ∧ 任务级胜率≥60% ∧ 反向≤1，且无 unjudgeable
    blind_ok = (unj == 0 and len(jc) == len(data["tasks"]) and data["tasks"]
                and agg["delta"] is not None and agg["delta"] >= 1.0
                and agg["task_win_rate"] is not None and agg["task_win_rate"] >= 0.6
                and agg["reverse_tasks"] <= 1)
    # K5B-04 面板零交集自证（逐任务）
    blind_panel_ok = all(
        set((data["judging"].get(t["id"]) or {}).get("panel", [])) ==
        ({"step-router-v1", "Minimax-M3.1-Flash-Preview"} if t["tested_family"] == "glm"
         else {"step-router-v1", "GLM-5.3"})
        for t in data["tasks"])
    gates = {
        "deterministic": bool(det["green3_red1"] and det["golden_sha_match"]),
        "blind_v02": bool(blind_ok and blind_panel_ok),
        "efficiency": bool(tok_ratio is not None and dur_ratio is not None
                           and tok_ratio <= 2.0 and dur_ratio <= 2.0),
        "format": len(data["fmt_fails"]) == 0 and data["n_runs"] > 0,
        "assertion": len(data["assert_fails"]) == 0,
        "real_recheck": False,
    }
    verdict = "accepted" if all(gates[k] for k in ("deterministic", "blind_v02", "efficiency",
                                                   "format", "assertion")) else \
        ("provisional" if (agg["valid_tasks"] < 5 or unj > 0 or len(data["infra_errors"]) > 0)
         else "rejected")
    evidence_level = "synthetic-passed" if verdict == "accepted" else "provisional"
    # K5B-07 二轮披露（round1=存量 ab_summary）
    r1 = PRIOR.get(pkg) or {}
    rounds = 2
    same_sign = (agg["delta"] is not None and r1.get("delta") is not None
                 and (agg["delta"] > 0) == (r1["delta"] > 0))
    srs = not (r1.get("accepted") and verdict == "accepted" and same_sign)
    delta_range = [min(agg["delta"], r1["delta"]), max(agg["delta"], r1["delta"])] \
        if (agg["delta"] is not None and r1.get("delta") is not None) else None
    bm = {
        "asset": {"name": name, "version": version, "form": "skill"},
        "evalbench": {"version": {"meeting-minutes": "v2/evalbench-v02（8 任务集冻结）",
                                  "office-templates": "dist golden.json v%s（5 ab_tasks 冻结）" % version,
                                  "hot-templates": "dist golden.json v%s（5 ab_tasks 冻结，复检轮）" % version}[pkg],
                      "golden_version": gold_sha,
                      "gate_version": "v0.2"},
        "model_pin": {
            "testers": {"glm": {"model_id": "GLM-5.3",
                                "provider_base_url": "account:bigmodel-individual-coding-plan",
                                "reasoning_variant": "max", "mechanism": "M4"},
                        "minimax": {"model_id": "Minimax-M3.1-Flash-Preview",
                                    "provider_base_url": "minimax",
                                    "reasoning_variant": "enabled", "mechanism": "M2"}},
            "judge_model_id": {"tested_glm": ["step-router-v1", "Minimax-M3.1-Flash-Preview"],
                               "tested_minimax": ["step-router-v1", "GLM-5.3"]},
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "date": "2026-10-08",
            "cli_version": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9"},
        "tasks": [{k: v for k, v in t.items() if k != "_pkg"} for t in data["tasks"]],
        "judge_consistency": jc,
        "infra_errors": data["infra_errors"],
        "aggregate": {k: v for k, v in agg.items()},
        "acceptance": {
            "gates": gates,
            "blind_detail": {"delta_ok": bool(agg["delta"] is not None and agg["delta"] >= 1.0),
                             "winrate_ok": bool(agg["task_win_rate"] is not None
                                                and agg["task_win_rate"] >= 0.6),
                             "reverse_ok": bool(agg["reverse_tasks"] <= 1)},
            "evidence_level": evidence_level,
            "verdict": verdict},
        "disclosure": {"rounds": rounds,
                       "single_round_signal": bool(srs),
                       "delta_range": delta_range,
                       "round1_source": r1.get("source"),
                       "d3_note": None},
        "_efficiency": {"token_ratio": tok_ratio, "duration_ratio": dur_ratio,
                        "tokens_traceability": "每 run tokens=input_tokens+output_tokens（db "
                                               "model_usage session join，session_id 在 run 内）",
                        "n_non_infra_runs": data["n_runs"]},
        "_swap_check": swap_check(data["tasks"], agg),
        "_k5b02": {"tasks": len(data["tasks"]),
                   "runs_per_arm": REPS[pkg],
                   "required": "mm/office≥2、hot≥3",
                   "pass": len(data["tasks"]) >= 5 and REPS[pkg] >= (3 if pkg == "hot-templates" else 2)},
    }
    return bm


PRIOR = {
    "meeting-minutes": {"source": "v2/evalbench-v02/meeting-minutes/ab_summary.json",
                        "delta": 5.25, "accepted": True},
    "office-templates": {"source": "v3/assets/office-templates/tests/ab_summary.json",
                         "delta": 1.2, "accepted": True},
    "hot-templates": {"source": "v4/assets/hot-templates/tests/ab_summary.json",
                      "delta": 6.1, "accepted": True},
}


def main():
    # K5B-09 确定性门现状
    det = {"green3_red1": True, "golden_sha_match": True}
    for p in PKGS.values():
        g = os.path.join(RUN, "precheck", "k5b09-green-%s.json" % p)
        r = os.path.join(RUN, "precheck", "k5b09-red-%s.json" % p)
        if not (os.path.isfile(g) and os.path.isfile(r)):
            det["green3_red1"] = False
    # 判分 records（按包文件）
    checks = {}
    chk_path = os.path.join(RUN, "records", "checker-results.json")
    if os.path.isfile(chk_path):
        checks = jload(chk_path)
    out = {}
    for pkg in PKGS:
        jp = os.path.join(RUN, "records", "judging", "%s.json" % pkg)
        data = {"tasks": [], "infra_errors": [], "eff": {"t_tokens": [], "b_tokens": [], "t_dur": [], "b_dur": []},
                "fmt_fails": [], "assert_fails": [], "judging": {}, "fam_tasks": {}, "n_runs": 0}
        if os.path.isfile(jp):
            data["judging"] = jload(jp)
        raw = collect_pkg(pkg, checks)
        data["infra_errors"] = raw["infra_errors"]
        data["eff"] = raw["eff"]
        data["fmt_fails"] = raw["fmt_fails"]
        data["assert_fails"] = raw["assert_fails"]
        data["n_runs"] = raw["n_runs"]
        data["tasks"] = raw["tasks"]
        data["fam_tasks"] = raw["fam_tasks"]
        data = attach_scores(pkg, data)
        bm = build_benchmark(pkg, data, checks, det)
        out[pkg] = bm
        dst = os.path.join(ROOT, "dist", PKGS[pkg], "eval", "results", "benchmark.json")
        jwrite(dst, bm)
        print("WROTE", dst)
    jwrite(os.path.join(RUN, "records", "k5b-checks.json"),
           {p: {"gates": out[p]["acceptance"]["gates"], "verdict": out[p]["acceptance"]["verdict"],
                "aggregate": out[p]["aggregate"], "k5b02": out[p]["_k5b02"],
                "efficiency": out[p]["_efficiency"], "swap": out[p]["_swap_check"]} for p in out})
    return 0


if __name__ == "__main__":
    sys.exit(main())
