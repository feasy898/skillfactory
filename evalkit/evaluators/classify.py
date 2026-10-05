#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluators/classify.py — 三桶分类 + 降级链（PLAN §5.5 infra_error 补丁 / §5.6 降级链；TESTS EI-15/16/17/19）。

三桶（口径固定，防「infra 吞噬一切」与「被测失败误标 infra」两个方向）：
  infra_error        rate_limited 重试 1 次后仍失败 / stream_idle_timeout 连续 2 次 / harness 崩溃 / 非被测超时
                     → 剔除并**披露**（禁静默剔除）
  装置设计缺陷        context_exceeded → 该臂作废 + 任务包瘦身动作；**不是资产无效**
  被测失败           其余 → 正常计分

降级链：rate_limited → 退避重试 1 次 → 仍失败则 infra_error 剔除；
        stream_idle_timeout 连续 2 次 → **该臂作废**（不是该 run 剔除，粒度差异独立断言）；
        单族整列作废 → 其余族照常出结论，禁止因单族失败宣布整轮无效（EI-19）。

本模块是纯函数，负控 NC-5/6/7/8 直接对它做注入测试——分类器本身要有阳性对照（MT-2）。

用法：
    python classify.py --case <case.json>            # 喂一串事件，拿分类结果
    python classify.py --selftest                    # 跑内置用例（含 NC-5/6/7/8 对应用例）
退出码：0 自测全过 / 1 有用例不过 / 2 用法错误。
"""

import argparse
import io
import json
import os
import sys

RATE_LIMITED = "rate_limited"
IDLE_TIMEOUT = "stream_idle_timeout"
CONTEXT_EXCEEDED = "context_exceeded"
HARNESS_CRASH = "harness_crash"
ARM_TIMEOUT = "arm_timeout"


def classify_run(events, arm_id="arm"):
    """把一个臂的一串遥测事件分类。返回 dict。"""
    attempts = 0
    idle_streak = 0
    buckets = []
    for ev in events:
        kind = ev.get("kind")
        if kind == RATE_LIMITED:
            attempts += 1
            if attempts >= 2:
                buckets.append({"event": ev, "bucket": "infra_error",
                                "reason": "rate_limited 重试 1 次后仍失败（剔除并披露）"})
            else:
                buckets.append({"event": ev, "bucket": "retrying",
                                "reason": "rate_limited 退避重试 1 次（不计 infra）"})
        elif kind == IDLE_TIMEOUT:
            idle_streak += 1
            if idle_streak >= 2:
                buckets.append({"event": ev, "bucket": "arm_void",
                                "reason": "stream_idle_timeout 连续 2 次 → 该臂作废"})
            else:
                buckets.append({"event": ev, "bucket": "retrying", "reason": "idle_timeout 第 1 次"})
        elif kind == CONTEXT_EXCEEDED:
            buckets.append({"event": ev, "bucket": "device_design_flaw",
                            "reason": "context_exceeded = 装置设计缺陷（任务包太大），不是资产无效"})
        elif kind in (HARNESS_CRASH, ARM_TIMEOUT):
            buckets.append({"event": ev, "bucket": "infra_error", "reason": kind})
        else:
            buckets.append({"event": ev, "bucket": "measured_failure", "reason": "正常计分"})

    # 臂级裁决：任一 arm_void → 臂作废；任一 device_design_flaw → 臂作废但归装置；否则按最重桶
    buckets_set = {b["bucket"] for b in buckets}
    if "arm_void" in buckets_set:
        arm_verdict = "arm_void"
    elif "device_design_flaw" in buckets_set:
        arm_verdict = "arm_void_device_flaw"
    elif "infra_error" in buckets_set:
        arm_verdict = "infra_error"
    else:
        arm_verdict = "measured_failure"
    return {"arm": arm_id, "events": len(events), "buckets": buckets, "arm_verdict": arm_verdict}


def aggregate_round(arms):
    """单族整列作废（EI-19）：某族整体崩 → 该族标 unjudgeable，其余族照常出结论。
    绝不返回「整轮无效」。"""
    by_family = {}
    for a in arms:
        by_family.setdefault(a.get("family", "unknown"), []).append(a)
    families, voided = [], []
    for fam, rows in by_family.items():
        verdicts = [r.get("arm_verdict") for r in rows]
        all_bad = all(v in ("infra_error", "arm_void") for v in verdicts)
        if all_bad:
            families.append({"family": fam, "status": "unjudgeable", "n": len(rows)})
            voided.append(fam)
        else:
            families.append({"family": fam, "status": "ok", "n": len(rows),
                             "measured": sum(1 for v in verdicts if v == "measured_failure")})
    return {"families": families, "voided_families": voided,
            "round_invalid": False,  # 硬编码 false：禁止因单族失败宣布整轮无效
            "note": "单族整列作废，其余族照常出结论（TESTS EI-19）"}


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--case", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.case:
        with io.open(args.case, encoding="utf-8") as f:
            doc = json.load(f)
        if "round" in doc:
            print(json.dumps(aggregate_round(doc["round"]), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(classify_run(doc.get("events", []), doc.get("arm", "arm")),
                             ensure_ascii=False, indent=2))
        return 0

    if not args.selftest:
        print("用法: python classify.py --case <case.json> | --selftest", file=sys.stderr)
        return 2

    # 内置用例：正例+反例各配（MT-2 阳性对照纪律）
    cases = [
        ("NC-5 注入一次 rate_limited 后成功", classify_run([{"kind": RATE_LIMITED}, {"kind": "ok"}]),
         lambda r: r["arm_verdict"] == "measured_failure" and any(b["bucket"] == "retrying" for b in r["buckets"])),
        ("反例 两次 rate_limited", classify_run([{"kind": RATE_LIMITED}, {"kind": RATE_LIMITED}]),
         lambda r: r["arm_verdict"] == "infra_error"),
        ("NC-6 连续 2 次 idle_timeout", classify_run([{"kind": IDLE_TIMEOUT}, {"kind": IDLE_TIMEOUT}]),
         lambda r: r["arm_verdict"] == "arm_void"),
        ("反例 单次 idle_timeout", classify_run([{"kind": IDLE_TIMEOUT}, {"kind": "ok"}]),
         lambda r: r["arm_verdict"] == "measured_failure"),
        ("NC-8 人为做坏产物 = 被测失败", classify_run([{"kind": "ok"}, {"kind": "ok"}]),
         lambda r: r["arm_verdict"] == "measured_failure"),
        ("反例 一切都是 infra（防呆）", classify_run([{"kind": HARNESS_CRASH}]),
         lambda r: r["arm_verdict"] == "infra_error"),
        ("context_exceeded = 装置缺陷非资产无效", classify_run([{"kind": CONTEXT_EXCEEDED}]),
         lambda r: r["arm_verdict"] == "arm_void_device_flaw"),
    ]
    results = []
    ok = True
    for name, got, pred in cases:
        passed = bool(pred(got))
        ok &= passed
        results.append({"case": name, "pass": passed, "got": got["arm_verdict"]})
        print("%s %s -> %s" % ("PASS" if passed else "FAIL", name, got["arm_verdict"]))

    # NC-7: 3 族全绿 + 1 族全崩
    round_arms = ([{"family": f, "arm_verdict": "measured_failure"} for f in ("glm", "minimax", "step")]
                  + [{"family": "broken", "arm_verdict": "infra_error"}])
    agg = aggregate_round(round_arms)
    nc7_ok = (len(agg["voided_families"]) == 1 and agg["voided_families"][0] == "broken"
              and agg["round_invalid"] is False)
    ok &= nc7_ok
    results.append({"case": "NC-7 3 族全绿 + 1 族全崩", "pass": nc7_ok, "got": agg["voided_families"]})
    print("%s NC-7 3 族全绿 + 1 族全崩 -> 作废=%s 整轮无效=%s"
          % ("PASS" if nc7_ok else "FAIL", agg["voided_families"], agg["round_invalid"]))

    print("\nself-test: %s" % ("全部通过" if ok else "有用例不通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
