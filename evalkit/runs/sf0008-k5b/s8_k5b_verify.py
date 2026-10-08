#!/usr/bin/env python3
"""s8_k5b_verify.py — K5B-01/02/04/05/06/07/08/09 独立复核（从 benchmark.json/tasks 复算）。
退出码 0=全部断言成立；1=任一红。"""
import hashlib, json, os, re, sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
REGISTRY_SHA = {"meeting-minutes-skill": "b3be400ae3b4984a1537d4909b9ea379246d8b978d3c8a179c90182c5c854315",
                "office-templates-skill": "2fa58b07481b44bc2840b2fdd757ef19faa5ebe37e1918baf936b2b923f4ecbf",
                "hot-templates-skill": "19e4b6e11bee018ed8c0842a3a39a651a98c97f2fead0c8e16ee2ed6ddeff186"}
NINE = {"asset","evalbench","model_pin","tasks","judge_consistency","infra_errors","aggregate","acceptance","disclosure"}

def jload(p): return json.load(open(p, encoding="utf-8"))

def main():
    fails = []
    for pkg in ("meeting-minutes-skill", "office-templates-skill", "hot-templates-skill"):
        d = jload(os.path.join(ROOT, "dist", pkg, "eval/results/benchmark.json"))
        tag = pkg.split("-")[0]
        # K5B-01 九键 + model_pin 判分字段非空
        if not NINE.issubset(d.keys()):
            fails.append("%s K5B-01 九键缺 %s" % (pkg, NINE - set(d.keys())))
        mp = d["model_pin"]
        if not mp.get("judge_model_id") or not mp.get("judge_prompt_version"):
            fails.append("%s K5B-01 judge 字段空" % pkg)
        # K5B-02 任务数/重复数
        need_runs = 3 if "hot" in pkg else 2
        if len(d["tasks"]) < 5:
            fails.append("%s K5B-02 tasks<5" % pkg)
        for t in d["tasks"]:
            for arm in ("treatment", "baseline"):
                if len(t["arms"][arm]["runs"]) < need_runs:
                    fails.append("%s/%s %s %s runs<%d" % (pkg, t["id"], arm, need_runs,
                                 len(t["arms"][arm]["runs"])))
        # K5B-04 盲态：judge_model_id 按被测族无交集
        for t in d["tasks"]:
            fam = t["tested_family"]
            jm = mp["judge_model_id"]["tested_glm" if fam == "glm" else "tested_minimax"]
            bad = [j for j in jm if (fam == "glm" and "GLM" in j) or (fam == "minimax" and "Minimax" in j)]
            if bad:
                fails.append("%s/%s K5B-04 裁判含被测族标识 %s" % (pkg, t["id"], bad))
        # K5B-05 独立复算 + 标签互换
        valid = [t for t in d["tasks"] if t["task_verdict"] != "unjudgeable"]
        mt = sum(t["task_mean_t"] for t in valid) / len(valid)
        mb = sum(t["task_mean_b"] for t in valid) / len(valid)
        delta = round(mt - mb, 4)
        wins = sum(1 for t in valid if t["task_verdict"] == "win")
        ties = sum(1 for t in valid if t["task_verdict"] == "tie")
        winrate = round(wins / len(valid), 4)
        reverse = sum(1 for t in valid if t["reverse_flag"])
        ag = d["aggregate"]
        if abs(delta - ag["delta"]) > 1e-9: fails.append("%s K5B-05 delta 复算不等" % pkg)
        if abs(winrate - ag["task_win_rate"]) > 1e-9: fails.append("%s K5B-05 winrate 复算不等" % pkg)
        if reverse != ag["reverse_tasks"]: fails.append("%s K5B-05 reverse 复算不等" % pkg)
        sw = d["_swap_check"]
        if abs(sw["swap_delta"] + delta) > 1e-9: fails.append("%s K5B-05 swap delta 未变号" % pkg)
        if ties == 0 and abs(sw["swap_win_rate"] - (1 - winrate)) > 1e-9:
            fails.append("%s K5B-05 swap winrate 恒等不成立" % pkg)
        # K5B-06 judge_consistency 每任务 ≥1 条；delta>2 → action∈{re-judged,unjudgeable}
        seen = set()
        for c in d["judge_consistency"]:
            seen.add(c["task"])
            if c["delta"] is not None and c["delta"] > 2 and \
               c["action"] not in ("re-judged", "unjudgeable"):
                fails.append("%s/%s K5B-06 delta>2 未处置" % (pkg, c["task"]))
        if seen != {t["id"] for t in d["tasks"]}:
            fails.append("%s K5B-06 抽检未覆盖全任务" % pkg)
        # K5B-07 office rounds≥2；single_round_signal 规则
        if "office" in pkg:
            if d["disclosure"]["rounds"] < 2:
                fails.append("%s K5B-07 rounds<2" % pkg)
        srs_expected = not (d["disclosure"].get("round1_accepted", True)
                            and d["acceptance"]["verdict"] == "accepted")
        if d["disclosure"]["single_round_signal"] != True and d["acceptance"]["verdict"] != "accepted":
            pass  # rejected 轮必须为 true
        if d["acceptance"]["verdict"] != "accepted" and d["disclosure"]["single_round_signal"] is not True:
            fails.append("%s K5B-07/08 rejected 轮 single_round_signal 必须为 true" % pkg)
        # K5B-08 verdict ⟺ 五门；evidence_level
        g = d["acceptance"]["gates"]
        five = all(g[k] for k in ("deterministic", "blind_v02", "efficiency", "format", "assertion"))
        want = "accepted" if five else "rejected"
        if d["acceptance"]["verdict"] != want:
            fails.append("%s K5B-08 verdict 与五门不一致（want=%s）" % (pkg, want))
        if d["acceptance"]["evidence_level"] not in ("synthetic-passed", "provisional"):
            fails.append("%s K5B-08 evidence_level 越界" % pkg)
        if "real-verified" in json.dumps(d["acceptance"]):
            fails.append("%s K5B-08 出现 real-verified" % pkg)
        # K5B-09 golden sha
        got = hashlib.sha256(open(os.path.join(ROOT, "dist", pkg, "eval/golden.json"), "rb").read()).hexdigest()
        if got != REGISTRY_SHA[pkg]:
            fails.append("%s K5B-09 golden sha 与 REGISTRY 不符" % pkg)
        print(pkg, "| K5B-01..09 复核完成，tasks=%d" % len(d["tasks"]))
    # K5B-10 前置：publish-approval.md 不得存在
    if os.path.exists(os.path.join(ROOT, "evidence/publish-approval.md")):
        fails.append("K5B-10 evidence/publish-approval.md 不得存在")
    if fails:
        print("FAILS:")
        for f in fails: print(" -", f)
        return 1
    print("ALL K5B VERIFY PASS (0 fails)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
