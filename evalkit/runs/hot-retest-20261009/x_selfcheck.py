#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/hot-retest-20261009/x_selfcheck.py — 开工自证 + mock 三分支干跑（零模型）。

自证内容：
  [1] 锚点机算：round-plan.judging.anchors_preregistered 全部锚点用 x_judges.arith_total
      机算复核（公式=round(10×Σ(dims×权重)/Σ权重,1)，hot 无封顶），期望 total 全命中且
      全部 < 各题通过线（§9-2 锚点跌破通过线要求）。
  [2] 权重交叉核对：round-plan 预登记权重 vs build_packs 已核 rubric 表（复跑 weights_from_rubric）。
  [3] mock 三分支干跑（提交前必过；真 judge_call/通道/staging 一律 mock，零模型调用）：
      分支A 主判：两裁判 verdict arith 一致 → judged、final=双裁均值、§3.4 复评 |Δ|=0 pass；
      分支B 重发：panel[0] 首评 arith 不一致 → 同裁判新会话重发 1 次一致 → 重发判词整份替代；
      分支C fail-closed：重发仍不一致 → 失格 → 有效异族裁判 <2 → unjudgeable（禁择优）。
      走 x_judges.main() 真代码路径（stage_products/build_brief/arith/resend/resample），
      RUN 指向 /tmp mock 目录、budget fixture 同真结构。
  [4] mock 聚合干跑：x_aggregate.main() 在 mock 判分记录上跑通 tie-aware 聚合（TASK_ORDER=[t01]）。
退出码：0 全过 / 1 有失败（如实列红项）。
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # .../skillfactory
RUN = os.path.join(ROOT, "evalkit", "runs", "hot-retest-20261009")
MOCK = "/tmp/hot-retest-20261009-selfcheck"

import x_judge_lib as J          # noqa: E402
import x_judges as xj            # noqa: E402
import x_aggregate as xag        # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    if not ok:
        FAILS.append(name)


def stage1_anchor_arith():
    rp = json.load(open(os.path.join(RUN, "round-plan.json"), encoding="utf-8"))
    anchors = rp["judging"]["anchors_preregistered"]["anchors"]
    pass_lines = json.load(open(os.path.join(RUN, "records", "packs-manifest.json"),
                                encoding="utf-8"))["pass_lines"]
    n_ok = 0
    bad = []
    below = True
    for tid, lst in sorted(anchors.items()):
        for a in lst:
            body = a["dims"].strip("⟦⟧")
            d = [float(x) for x in body.split(",")]
            dims = {"正确性": d[0], "完整性": d[1], "可验证性": d[2]}
            comp = xj.arith_total(tid, dims)
            if comp is None or abs(comp - a["expected_total"]) > 0.050001:
                bad.append((tid, a["dims"], a["expected_total"], comp))
            if comp is not None and comp >= pass_lines[tid]:
                below = False
                bad.append((tid, a["dims"], "≥pass_line", comp))
            n_ok += 1
    check("锚点机算 %d 条全命中" % n_ok, not bad, str(bad[:4]))
    check("锚点期望总分全部 < 通过线（§9-2）", below)


def stage2_weights():
    sys.path.insert(0, RUN)
    import importlib.util
    spec = importlib.util.spec_from_file_location("bp", os.path.join(RUN, "build_packs.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    ok = all(bp.weights_from_rubric(t) == bp.WEIGHTS_PREREG[t] for t in bp.TASKS)
    check("权重交叉核对（rubric 表 vs 预登记表）8 题", ok)


def make_mock_env():
    if os.path.isdir(MOCK):
        shutil.rmtree(MOCK)
    os.makedirs(MOCK)
    J.write_json(os.path.join(MOCK, "budget.json"),
                 {"run_id": "mock", "arm_calls": {"counted_so_far": 0},
                  "retry_policy": {"used": 0}, "judge_calls": {"used_so_far": 0},
                  "ledger_entries": []})
    # mock 臂树：3 rep × 2 臂，工作面含 骨架.md + structure.json（t01 型产物）
    for rep in (1, 2, 3):
        for arm in ("baseline", "treatment"):
            ad = os.path.join(MOCK, "glm", "hot-templates-t01-rep%d" % rep, arm)
            os.makedirs(os.path.join(ad, "out"), exist_ok=True)
            os.makedirs(os.path.join(ad, "records"), exist_ok=True)
            J.write_json(os.path.join(ad, "records", "arm_run.json"), {"mock": True})
            open(os.path.join(ad, "out", "骨架.md"), "w", encoding="utf-8").write(
                "# 宿舍省电费\n一、是什么…【占位:x】\n")
            open(os.path.join(ad, "out", "structure.json"), "w", encoding="utf-8").write(
                json.dumps({"elements": [], "placeholder_stats": {"total_open": 10,
                                                                  "total_filled_from_input": 7}},
                           ensure_ascii=False))
    # monkeypatch：RUN→MOCK、任务→t01、臂目录→mock、judge_call→预设序列
    J.RUN = MOCK
    xj.RUN = MOCK
    xj.TASK_ORDER = ["t01"]
    xj.task_unit_dirs = lambda task, fam, reps: [
        (rep, os.path.join(MOCK, "glm", "hot-templates-t01-rep%d" % rep, arm))
        for rep in reps for arm in ("baseline", "treatment")]


def _verdict_of(task, pids, dims, total):
    return {"scores": {p: {"total": total, "dims": dims,
                           "evidence": "mock 证据"} for p in pids}}


def run_branch(label, script, expect_status, expect_resend, expect_resample_pass):
    """script: list of (judge_tag, verdict or None)——按调用顺序弹出。"""
    calls = {"i": 0}

    def fake_judge_call(judge, workdir, brief, staged, task_label):
        tag, v = script[min(calls["i"], len(script) - 1)]
        calls["i"] += 1
        os.makedirs(workdir, exist_ok=True)
        if v is not None:
            pids = ["P%d" % i for i in range(1, 7)] if "resample" not in task_label else ["Q1"]
            v = _verdict_of("t01", pids, *v)
            J.write_json(os.path.join(workdir, "verdict.json"), v)
        return {"exit_code": 0, "wall_ms": 1, "session_id": "mock-%s-%d" % (judge, calls["i"]),
                "channel": "mock", "input_tokens": 0, "output_tokens": 0}, v

    xj.judge_call = fake_judge_call
    jp = os.path.join(MOCK, "records", "judging", "hot-templates.json")
    if os.path.isfile(jp):
        os.remove(jp)
    rc = xj.main()
    res = json.load(open(jp, encoding="utf-8"))["t01"]
    det_p = os.path.join(MOCK, "records", "judging", "t01.json")
    det = json.load(open(det_p, encoding="utf-8")) if os.path.isfile(det_p) else {}
    ok = (rc == (1 if expect_status == "unjudgeable" else 0)
          and res["status"] == expect_status)
    detail = "status=%s" % res["status"]
    if expect_resend is not None:
        if expect_status == "unjudgeable":   # 早退路径：resend 证据=重发 workdir 在案
            has = os.path.isdir(os.path.join(MOCK, "judge-work", "t01",
                                             "step-router-v1#resend"))
        else:
            has = any("#resend" in k for k in (det.get("verdicts") or {}))
        ok = ok and (has == expect_resend)
        detail += " resend=%s" % has
    if expect_status == "judged":
        jc = res.get("judge_consistency") or {}
        ok = ok and (jc.get("action") == ("pass" if expect_resample_pass else "re-judged"))
        detail += " resample_action=%s" % jc.get("action")
        check("%s final=双裁均值" % label,
              res.get("final_scores") and all(v == 10.0 for v in res["final_scores"].values()),
              str(res.get("final_scores")))
    check("分支%s（%s）" % (label, expect_status), ok, detail)
    if "judge_arith_check" in res:
        rows = res["judge_arith_check"]
        mism = [r for r in rows if not r["match"]]
        if label == "B":
            check("分支B arith 记录：首评不一致行 + 重发一致行",
                  any(r["call"] == "main" and not r["match"] for r in mism or rows)
                  and all(r["match"] for r in rows if r["call"] == "resend"),
                  "rows=%d mismatch=%d" % (len(rows), len(mism)))
        if label == "C":
            check("分支C arith 记录：main 与 resend 均不一致行在案",
                  sum(1 for r in rows if not r["match"]) >= 4,
                  "rows=%d mismatch=%d" % (len(rows), len(mism)))


def stage3_mock_branches():
    good = ({"正确性": 1.0, "完整性": 1.0, "可验证性": 1.0}, 10.0)
    bad_total = ({"正确性": 1.0, "完整性": 1.0, "可验证性": 1.0}, 7.5)  # dims 满但 total 错 → arith 不一致
    # A：主判双裁一致 + 复评一致
    make_mock_env()
    run_branch("A", [("step", good), ("minimax", good), ("step", good)],
               "judged", False, True)
    # B：step 首评 arith 不一致 → resend 一致（整份替代）
    make_mock_env()
    run_branch("B", [("step", bad_total), ("step", good), ("minimax", good), ("step", good)],
               "judged", True, True)
    # C：step 首评+resend 均不一致 → 失格 → <2 有效 → unjudgeable fail-closed
    make_mock_env()
    run_branch("C", [("step", bad_total), ("step", bad_total), ("minimax", good)],
               "unjudgeable", True, False)
    # [4] mock 聚合（TASK_ORDER=[t01]）
    xag.RUN = MOCK
    xag.TASK_ORDER = ["t01"]
    rc = xag.main()
    check("mock 聚合 tie-aware 跑通", rc == 0)


def main():
    stage1_anchor_arith()
    stage2_weights()
    stage3_mock_branches()
    print("SELFCHECK %s（fails=%s）" % ("EXIT=0" if not FAILS else "EXIT=1", FAILS))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
