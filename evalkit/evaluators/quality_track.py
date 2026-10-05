#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluators/quality_track.py — 质量轨（PLAN §5.3）：达成任务目标态，消耗模型，rubric 裁判。

MVP 阶段的诚实处置（PLAN §5.4 三条纪律 + O-7 跨族裁判 + EVAL-SPEC §3.1-1）：
本 MVP 是 n=1、单任务、单族（zcode headless 实测只落 GLM-5.3，见报告 §模型钉版），
**没有第二个模型族可作跨族裁判**（O-7 要求裁判族与当轮被测集无交集）。因此本轨在拿到
外部裁判判定文件之前一律输出 `unjudgeable`，**不出分**——宁可不可判，不拿单裁判自偏好
冒充质量信号（轨迹 3 RC-10：同资产三轮 Δ 极差 2.66 = 验收线 2.66 倍）。

用法：
    python quality_track.py --pack <pack> --arm <臂名> --run-label r1 \
        [--verdict <裁判判定 json>] [--out <记录路径>]
裁判判定文件 schema（外部裁判产出）：{"scores":{"维度 1":10,...},"total":10,"reason":"..."}
退出码：0 已判定且通过 / 1 已判定但不通过 / 2 用法错误。**unjudgeable 时返回 0**（不判红，
但矩阵单元显式标 unjudgeable，禁渲染成 0 分）。
"""

import argparse
import io
import json
import os
import sys

RUBRIC_DIMS = ["交付形态正确", "只换标签的不变式", "告警忠实", "扫描草稿可用", "过程可复现"]


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--arm", default=None)
    ap.add_argument("--run-label", default="r1")
    ap.add_argument("--verdict", default=None)
    ap.add_argument("--out", dest="out_path", default=None)
    args = ap.parse_args(argv)
    if not args.pack or not args.arm:
        print("用法: python quality_track.py --pack <pack> --arm <臂名> [--verdict <裁判 json>]",
              file=sys.stderr)
        return 2

    rec_path = args.out_path or os.path.join(args.pack, "records",
                                             "quality_%s_%s.json" % (args.arm, args.run_label))
    if not args.verdict or not os.path.isfile(args.verdict):
        rec = {
            "track": "quality", "arm": args.arm, "run_label": args.run_label,
            "verdict": "unjudgeable", "score": None,
            "reason": "MVP 无跨族裁判可用（O-7 要求裁判族与被测集无交集；本轮被测集=GLM 族，"
                      "本机可用的第二族通道在 headless 下未打通）。按 EVAL-SPEC §3.1-1 出不可判，"
                      "不出分；不得用单裁判自偏好冒充质量信号。",
            "rubric": os.path.abspath(os.path.join(args.pack, "rubric.md")),
            "rubric_dims": RUBRIC_DIMS,
        }
    else:
        with io.open(args.verdict, encoding="utf-8") as f:
            v = json.load(f)
        total = v.get("total")
        rec = {"track": "quality", "arm": args.arm, "run_label": args.run_label,
               "verdict": "judged", "score": total, "scores": v.get("scores"),
               "reason": v.get("reason", ""), "judge_file": os.path.abspath(args.verdict)}

    os.makedirs(os.path.dirname(os.path.abspath(rec_path)), exist_ok=True)
    with io.open(rec_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if rec["verdict"] == "unjudgeable":
        return 0
    return 0 if (rec.get("score") or 0) >= 6 else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
