#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/x_judge_repair.py — 裁判通道修复重判（照 K5B s8_jc_repair 先例）。

修复对象：step 通道 prefill 缺陷期的 no-verdict 调用（ab1 抽检、ab3 主判）。
原则：评分规则/brief/解析器零改动（判卷器不变）；只对**未产出 verdict**的调用做同裁判重发，
全部记账（kind=judge, note=channel-repair）；修复后从 per_judge_scores 重算 final_scores 与
judge_consistency；修复后仍 <2 名异族裁判得分 → 该任务 fail-closed 记 unjudgeable（不放宽）。
用法：python x_judge_repair.py <task> [<task>...]
退出码：0=修复完成；2=装置错误。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_judge_lib as J  # noqa: E402
import x_judges as G  # noqa: E402

ROOT = J.ROOT
RUN = J.RUN
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "office-templates-skill")
TASK_ORDER = G.TASK_ORDER


def load_staged(task):
    staging = os.path.join(RUN, "judge-work", "_staging", task)
    if not os.path.isdir(staging):
        raise RuntimeError("staging 缺失: %s" % staging)
    staged = []
    for pid in sorted((d for d in os.listdir(staging)
                       if d.startswith("P") and d[1:].isdigit()),
                      key=lambda d: int(d[1:])):
        pdir = os.path.join(staging, pid)
        staged.append({"pid": pid, "files": sorted(os.listdir(pdir))})
    return staging, staged


def main(argv):
    jp = os.path.join(RUN, "records", "judging", "office-templates.json")
    results = json.load(open(jp, encoding="utf-8"))
    for task in argv:
        rec = results[task]
        jp_task = os.path.join(RUN, "records", "judging", "%s.json" % task)
        d = json.load(open(jp_task, encoding="utf-8"))
        fam = d["tested_family"]
        is_ab = task in G.AB_SET
        panel = d["panel"]
        judge0 = panel[0]
        staging, staged = load_staged(task)
        G.STAGING_ROOTS[task] = staging
        G.STAGING_ROOTS[task + "-repair-main"] = staging
        # —— 1) 面板缺分裁判重发（同裁判、同 brief、同暂存）
        for judge in panel:
            v = d["verdicts"].get(judge)
            if v and isinstance(v.get("scores"), dict) \
                    and any(sv.get("total") is not None for sv in v["scores"].values()):
                continue
            wdir = os.path.join(RUN, "judge-work", task, judge.replace("/", "_") + "-repair")
            os.makedirs(wdir, exist_ok=True)
            brief = G.build_brief(task, staged, is_ab,
                                  pass_line=None)
            rec_call, v = G.judge_call(judge, wdir, brief, staged, task + "-repair-main")
            d["verdicts"][judge + "#repair"] = v
            if v and isinstance(v.get("scores"), dict):
                d["verdicts"][judge] = v   # 修复成功：替换原 no-verdict 位
        # —— 2) 重算 per_judge_scores / final_scores
        scores = {}
        for judge, v in d["verdicts"].items():
            if judge.endswith("#repair") and d["verdicts"].get(judge[:-7]):
                continue  # 修复成功后原位已替换，#repair 键仅留痕
            if not v or not isinstance(v.get("scores"), dict):
                continue
            for pid, sv in v["scores"].items():
                if sv.get("total") is not None:
                    scores.setdefault(pid, {})[judge] = sv.get("total")
        d["per_judge_scores"] = scores
        scored_judges = {j for dd in scores.values() for j in dd}
        final_scores = {pid: (round(sum(dd.values()) / len(dd), 2) if dd else None)
                        for pid, dd in scores.items()}
        d["final_scores"] = final_scores
        # —— 3) 抽检缺第二分则重发（同 judge0、Q1 匿名）
        jc = d.get("judge_consistency") or {}
        sampled = jc.get("resample_of")
        if sampled and jc.get("second_score") is None:
            staged2 = [{"pid": "Q1", "files": next(s["files"] for s in staged
                                                   if s["pid"] == sampled)}]
            rdir = os.path.join(RUN, "judge-work", task,
                                judge0.replace("/", "_") + "-resample-repair")
            os.makedirs(rdir, exist_ok=True)
            G.STAGING_ROOTS[task + "-repair-resample"] = os.path.join(staging, sampled + "_resample")
            brief2 = G.build_brief(task, staged2, is_ab)
            import shutil as _sh
            _sh.copytree(os.path.join(staging, sampled),
                         G.STAGING_ROOTS[task + "-repair-resample"], dirs_exist_ok=True)
            rec2, v2 = G.judge_call(judge0, rdir, brief2, staged2, task + "-repair-resample")
            d["verdicts"][judge0 + "#resample-repair"] = v2
            second = v2.get("scores", {}).get("Q1", {}).get("total") if v2 else None
        else:
            second = jc.get("second_score")
        # —— 4) 重算一致性
        first = scores.get(sampled, {}).get(judge0)
        delta = (abs(first - second) if (first is not None and second is not None) else None)
        action = "pass"
        if delta is None:
            action = "not_performed_channel_failure" if second is None else "pass"
        elif delta > 2:
            action = "re-judged"
            judge1 = panel[1]
            v1 = d["verdicts"].get(judge1)
            if v1 and isinstance(v1.get("scores"), dict):
                news = {pid: sv.get("total") for pid, sv in v1["scores"].items()}
                final_scores = {pid: news.get(pid) for pid in final_scores}
                d["final_scores"] = final_scores
                if news.get(sampled) is not None and first is not None \
                        and abs(news[sampled] - first) > 2:
                    action = "unjudgeable"
            else:
                action = "unjudgeable"
        d["judge_consistency"] = {"task": task, "resample_of": sampled,
                                  "first_score": first, "second_score": second,
                                  "delta": delta, "action": action,
                                  "repair": True}
        # —— 5) fail-closed：修复后仍 <2 名异族裁判 → unjudgeable
        if len(scored_judges) < 2:
            d["fail_closed"] = ("修复后异族裁判得分者 <2（登记 channel_failure_policy）")
        results[task] = {
            "status": ("unjudgeable" if (d.get("fail_closed") or action == "unjudgeable")
                       else "judged"),
            "tested_family": fam, "panel": panel,
            "final_scores": d["final_scores"], "mapping": rec.get("mapping"),
            "judge_consistency": d["judge_consistency"],
            "fail_closed": d.get("fail_closed")}
        J.write_json(jp_task, d)
        J.write_json(jp, results)
        print("REPAIRED %s status=%s judges=%s action=%s"
              % (task, results[task]["status"], sorted(scored_judges), action), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
