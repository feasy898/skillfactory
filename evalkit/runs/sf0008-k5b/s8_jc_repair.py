#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s8_jc_repair.py — §3.4 一致性抽检修配对：对 delta=None 的任务用 judge0（step）
对抽样产物做两次全新独立评分（两个新会话实例），delta=|两次差|，更新 judge_consistency。
调用逐次记账（kind=judge）。"""
import importlib.util, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s8_judge_lib as J
spec = importlib.util.spec_from_file_location("s8j", os.path.join(J.RUN, "s8_judges.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

REPS = {"meeting-minutes": [1, 2], "office-templates": [1, 2], "hot-templates": [1, 2, 3]}

def units_of(pkg, task, fam):
    out = []
    for rep in REPS[pkg]:
        for arm in ("baseline", "treatment"):
            out.append((rep, os.path.join(J.RUN, fam, "%s-%s-rep%d" % (pkg, task, rep), arm)))
    return out

def main():
    targets = []
    for pkg in ("meeting-minutes", "office-templates", "hot-templates"):
        jp = os.path.join(J.RUN, "records", "judging", "%s.json" % pkg)
        d = json.load(open(jp, encoding="utf-8"))
        for t, v in d.items():
            jc = v.get("judge_consistency") or {}
            if jc.get("delta") is None:
                targets.append((pkg, t, v))
    print("repair targets:", [(p, t) for p, t, _ in targets])
    for pkg, task, v in targets:
        fam = v["tested_family"]
        rubric = m.rubric_of(pkg, task)
        staging = os.path.join(J.RUN, "judge-work", "_staging", "%s-%s" % (pkg, task))
        pid = v["judge_consistency"]["resample_of"]
        import zlib
        # 与主驱动同确定性种子重建（若已存在则复用）
        if not os.path.isdir(staging):
            units = units_of(pkg, task, fam)
            m.stage_products(pkg, task, units, staging,
                             seed=zlib.crc32(("%s|%s" % (pkg, task)).encode()) & 0xffffff)
        sdir = os.path.join(staging, pid)
        fl = []
        for dp, _dn, fns in os.walk(sdir):
            for fn in fns:
                fl.append(os.path.relpath(os.path.join(dp, fn), sdir))
        staged2 = [{"pid": "Q1", "files": sorted(fl)}]
        brief = m.build_brief(pkg, task, staged2, rubric)
        scores = []
        for i in (1, 2):
            wdir = os.path.join(J.RUN, "judge-work", "%s-%s" % (pkg, task),
                                "jc-repair-%d" % i)
            os.makedirs(wdir, exist_ok=True)
            ST = {("%s-%s" % (pkg, task)): staging}
            m.STAGING_ROOTS[("%s-%s" % (pkg, task))] = staging
            import shutil as sh
            dst = os.path.join(wdir, "Q1")
            if os.path.isdir(sdir):
                sh.copytree(sdir, dst, dirs_exist_ok=True)
            slot = J.budget_judge({"judge": "step-router-v1", "channel": "step",
                                   "task": "%s-%s-jc-repair-%d" % (pkg, task, i),
                                   "judge_prompt_version": J.JUDGE_PROMPT_VERSION,
                                   "ts_intent": __import__("time").strftime("%H:%M:%S"),
                                   "status": "pending"})
            parts = ["【输出纪律（最高优先级）】你是评分器。禁止展示任何思考；直接以 { 开头。", "",
                     brief, "", "# 产物内容（暂存文件全文）"]
            for s2 in staged2:
                for fn in s2["files"]:
                    p = os.path.join(wdir, "Q1", fn)
                    if os.path.isfile(p):
                        parts.append("=== Q1/%s ===\n%s" % (fn, open(p, encoding="utf-8",
                                     errors="replace").read()[:24000]))
            pids = ", ".join('"Q1"')
            r = J.step_chat([{"role": "user", "content": "\n".join(parts + [
                "", '现在直接输出最终评分 JSON：必须恰好包含这些键：%s；每个键为 {"total": 0-10, "evidence": "≤150 字"}；除 JSON 外不得输出文字。' % pids])}],
                max_tokens=32000, assistant_prefill='{"scores": {"Q1": {"total": ')
            r["text"] = '{"scores": {"Q1": {"total": ' + (r["text"] or "")
            vv = m.parse_verdict_json(r["text"])
            with open(os.path.join(wdir, "response.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write(r["text"])
            sc = vv.get("scores", {}).get("Q1", {}).get("total") if vv else None
            J.budget_judge_update(slot, status="done" if sc is not None else "no-verdict",
                                  exit_code=0 if sc is not None else 1,
                                  wall_ms=r["wall_ms"], session_id=r.get("id"),
                                  tokens={"input": r.get("prompt_tokens"),
                                          "output": r.get("completion_tokens")},
                                  model_observed=r.get("model"))
            scores.append(sc)
        if None in scores:
            J.budget_judge_update(0, status="noop") if False else None
        jp = os.path.join(J.RUN, "records", "judging", "%s.json" % pkg)
        d = json.load(open(jp, encoding="utf-8"))
        jc = d[task]["judge_consistency"]
        if None not in scores:
            jc.update({"first_score": scores[0], "second_score": scores[1],
                       "delta": abs(scores[0] - scores[1]),
                       "action": ("re-judged" if abs(scores[0] - scores[1]) > 2 else "pass"),
                       "repair_note": "原配对因 step 首轮 no-verdict 残缺；本对为同一裁判两个全新会话实例对同一抽样产物的独立评分（s8_jc_repair.py）"})
        else:
            jc["repair_note"] = "repair 仍 no-verdict：%s" % scores
        json.dump(d, open(jp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
        f2 = os.path.join(J.RUN, "records", "judging", "%s-%s.json" % (pkg, task))
        if os.path.isfile(f2):
            d2 = json.load(open(f2, encoding="utf-8"))
            d2["judge_consistency"] = jc
            json.dump(d2, open(f2, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
        print("REPAIRED", pkg, task, "->", scores)
    return 0

if __name__ == "__main__":
    sys.exit(main())
