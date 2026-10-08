#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/ws4_d3_gate.py — WS4 dev 池 D3 判分器化人工关卡门（SF-0005）。

PLAN §3.8 D3 = 判分器对人工金标对拍（准确率/召回各自 ≥95%），人工必须过、签署权
不下放给任何 agent。本门两种模式：

- 自环模式（默认）：判分器对机器 oracle 的对拍（self_loop=true）。这只是装置自证，
  **不替代人工金标**，不得据此把 d3_record 标为已过。
- --real 模式：读人工金标目录 bench/devpool-r1/goldens/<task>/
  （每个子目录 = 一份人工标注样本：sample_dir/product/ 产物 + sample_dir/verdict.json
   {expected_pass: bool, annotator: ...}）。目录不存在或样本未注入 → **fail-closed
   exit 3 + WAITING_OWNER 消息，绝不静默通过**（卡面明文）。
  ofc 线（task id 以 ofc- 开头）原硬编码 WAITING_WS3 作用域，已由 planner 裁决
  SF-0006-OFCD3（2026-10-08，planning/test-cards-20261008/
  ofc-d3-scope-and-ws3-harness-adjudication.md 第 1 条）解除：放行条件 =
  该题 goldens/<task>/ 下存在 verdict.json **且** 本裁决文件在盘（裁决文件缺席
  即回退 WAITING_WS3，fail-closed）；状态字段由 ws4_pool_state 按盘上记录派生
  （verdict 在 ∧ 对拍达标 ∧ signoff 非空 → D3_DONE；只有 verdict →
  ADJUDICATING；无 verdict → 维持 waiting），ofc 不因迁移而无条件放行。

用法：python ws4_d3_gate.py --task mm-01 [--real]
退出码：0 自环完成 / 1 对拍出现分歧（--real 下有样本但判分与金标不符）/ 3 WAITING（金标未注入或 ofc 裁决文件缺席）/ 2 用法错误。
"""

import argparse
import io
import json
import os
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(HARNESS_DIR)
WORKSPACE = os.path.dirname(EVALKIT)
WS4_ROOT = os.path.join(EVALKIT, "packs", "ws4-dev")
BENCH = os.path.join(WORKSPACE, "bench", "devpool-r1")

# ofc D3 作用域迁移的裁决授权文件（SF-0006-OFCD3）：在盘才解除 ofc 线 WAITING_WS3
ADJUDICATION_DOC = os.path.join(
    WORKSPACE, "planning", "test-cards-20261008",
    "ofc-d3-scope-and-ws3-harness-adjudication.md")


def golden_has_verdict(golden_root):
    """放行条件之一：金标目录下任一样本存在 verdict.json（只认目录样本）。"""
    if not os.path.isdir(golden_root):
        return False
    for sample in os.listdir(golden_root):
        sdir = os.path.join(golden_root, sample)
        if os.path.isdir(sdir) and os.path.isfile(os.path.join(sdir, "verdict.json")):
            return True
    return False


def self_loop(task_id):
    import ws4_gen
    import tempfile
    pack = os.path.join(WS4_ROOT, task_id)
    cfg = ws4_gen.load_task_cfg(task_id)
    tmp = tempfile.mkdtemp(prefix="ws4-d3-selfloop-")
    ws4_gen.generate(task_id, cfg["canonical_seed"], "A", tmp)
    rc, out = ws4_gen.run_checker(pack, os.path.join(tmp, "oracle"))
    return {
        "task": task_id, "mode": "self_loop", "checker_exit_on_machine_oracle": rc,
        "agreement": "1.0" if rc == 0 else "0.0",
        "self_loop": True,
        "note": "机器自环对拍不替代人工金标（卡面禁止条款）；d3 状态由盘上记录派生"
                "（ws4_pool_state：verdict 在 ∧ 对拍达标 ∧ signoff 非空 → D3_DONE）",
    }


def real_mode(task_id):
    golden_root = os.path.join(BENCH, "goldens", task_id)
    if task_id.startswith("ofc-") and not os.path.isfile(ADJUDICATION_DOC):
        # SF-0006-OFCD3：作用域解除以裁决文件在盘为前提；缺席即回退历史 WAITING_WS3
        msg = ("WAITING_WS3：%s 的金标对拍原属 WS3 范畴；SF-0006-OFCD3 作用域迁移裁决文件缺席"
               "（期望 planning/test-cards-20261008/ofc-d3-scope-and-ws3-harness-adjudication.md），"
               "fail-closed 维持 WAITING_WS3 不放行。") % task_id
        print(msg)
        return 3, {"task": task_id, "state": "WAITING_WS3", "exit": 3, "message": msg}
    if not golden_has_verdict(golden_root):
        msg = ("WAITING_OWNER：%s 人工金标未注入（期望目录 bench/devpool-r1/goldens/%s/，"
               "每样本一子目录：product/ 产物 + verdict.json {expected_pass, annotator}）；"
               "对拍准确率/召回 ≥95%% 才可签 D3；金标未注入即 fail-closed，绝不静默通过。") % (task_id, task_id)
        print(msg)
        return 3, {"task": task_id, "state": "WAITING_OWNER", "exit": 3, "message": msg}
    # 金标在位：逐样本对拍
    import ws4_gen
    pack = os.path.join(WS4_ROOT, task_id)
    agree, total = 0, 0
    mismatches = []
    for sample in sorted(os.listdir(golden_root)):
        sdir = os.path.join(golden_root, sample)
        if not os.path.isdir(sdir):
            # SF-0006-D3FIX 修3：样本枚举只认目录（以 product/ 存在为准）——
            # manifest.json 等登记文件不是样本条目，跳过、不报缺件
            continue
        vpath = os.path.join(sdir, "verdict.json")
        pdir = os.path.join(sdir, "product")
        if not (os.path.isfile(vpath) and os.path.isdir(pdir)):
            mismatches.append("%s: 样本结构缺件（verdict.json/product/）" % sample)
            continue
        verdict = json.load(io.open(vpath, encoding="utf-8"))
        rc, _ = ws4_gen.run_checker(pack, pdir)
        got_pass = rc == 0
        total += 1
        if got_pass == bool(verdict.get("expected_pass")):
            agree += 1
        else:
            mismatches.append("%s: checker=%s 金标=%s" % (sample, got_pass, verdict.get("expected_pass")))
    if total == 0:
        print("WAITING_OWNER：金标目录存在但零有效样本，fail-closed。")
        return 3, {"task": task_id, "state": "WAITING_OWNER", "exit": 3,
                   "message": "金标目录零有效样本"}
    acc = agree / total
    result = {"task": task_id, "mode": "real", "samples": total, "agree": agree,
              "accuracy": acc, "mismatches": mismatches}
    if task_id.startswith("ofc-"):
        # SF-0006-OFCD3：ofc 放行依据留痕（裁决文件 + verdict 在位），供审计
        result["release_basis"] = {
            "adjudication_doc": os.path.relpath(ADJUDICATION_DOC, WORKSPACE),
            "adjudication_present": True, "verdict_present": True,
        }
    if acc < 0.95 or mismatches:
        print("对拍未达 95%%：%s" % json.dumps(result, ensure_ascii=False))
        return 1, result
    print("对拍达标（待 owner 签署）：accuracy=%.3f samples=%d" % (acc, total))
    return 0, result


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--task", required=True)
    ap.add_argument("--real", action="store_true")
    args = ap.parse_args(argv)
    if args.real:
        code, result = real_mode(args.task)
        print(json.dumps({"d3_gate": result}, ensure_ascii=False, indent=2))
        return code
    result = self_loop(args.task)
    print(json.dumps({"d3_gate": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, HARNESS_DIR)
    sys.exit(main(sys.argv[1:]))
