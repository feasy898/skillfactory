#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluators/aggregate.py — 落 matrix.json（PLAN §5.5 看板两层；TESTS AG-15 / EI-21）。

matrix.json 结构：rows=任务，cols={族×臂×run}，单元固定字段
    {process_pass, artifact_pass, quality_score, tokens, wall_ms, infra_error}
外加三层随附（PLAN 纪律，防一词三义）：
    delta_vs_none / delta_vs_prev（本 MVP 为 null——首轮基线轮无 A_old，按 §3.2 首轮显式标注）
    layer（本文件产出固定 "dev"；holdout 数字禁入，AG-14）
落盘后**立刻 json.load 回读**做写-读-断言往返（EI-21：hw_student_eval.json 是反面教材）。

用法：python aggregate.py --run-dir <run 目录> --pack <pack 目录> [--out <matrix.json 路径>]
      [--evalbench-version <版本>] [--delta-from <上一轮 matrix.json>]
退出码：0 聚合完成且 schema 往返过 / 1 schema 有缺键或 AG-7 跨版本拒绝 / 2 用法错误。
"""

import argparse
import io
import json
import os
import sys

CELL_REQUIRED = ["process_pass", "artifact_pass", "quality_score", "tokens", "wall_ms", "infra_error"]


def read_json(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def arm_cell(arm_dir, family):
    rec = read_json(os.path.join(arm_dir, "records", "arm_run.json"), {}) or {}
    tele = read_json(os.path.join(arm_dir, "records", "telemetry.json"), {}) or {}
    pin = read_json(os.path.join(arm_dir, "records", "model_pin.json"), {}) or {}
    proc = read_json(os.path.join(arm_dir, "records", "process_track.json"), {}) or {}
    art = read_json(os.path.join(arm_dir, "records", "artifact_track.json"), {}) or {}

    tokens = None
    for mu in (tele.get("model_usage") or []):
        tokens = (tokens or 0) + (mu.get("it") or 0) + (mu.get("ot") or 0)

    q = read_json(os.path.join(arm_dir, "records", "quality.json"), {}) or {}
    return {
        "family": family,
        "arm": os.path.basename(arm_dir),
        "model_id_observed": rec.get("model_id_observed") or pin.get("model_id"),
        "process_pass": (proc.get("verdict") == "pass") if proc else None,
        "artifact_pass": (art.get("verdict") == "pass") if art else None,
        "quality_score": q.get("score"),
        "quality_verdict": q.get("verdict", "unjudgeable" if not q else None),
        "tokens": tokens,
        "wall_ms": rec.get("wall_ms"),
        "infra_error": bool(rec.get("timed_out")) or (rec.get("exit_code") not in (0, None)),
        "exit_code": rec.get("exit_code"),
        "session_id": rec.get("session_id"),
    }


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--out", dest="out_path", default=None)
    # O-6【已裁定】（PLAN §8）：zcode headless 实测落点=GLM-5.3（非 GLM-5.3-Flash），
    # 触发条款后半句——evalbench 版本 bump 至 v6-mvp-0.2（旧版号全树清零），旧基线作废（SF-0003）。
    # v6-mvp-0.3（SF-0005，SYNTHESIS R-C5）：WS4 题池落池触发 bump——新增 packs/ws4-dev 8 题
    # 与 harness 判分器件，跨版本并列仍由 AG-7 拒绝门拦截；本行与 CHANGELOG 为卡面授权仅有的两处既有文件改动。
    ap.add_argument("--evalbench-version", default="v6-mvp-0.3")
    ap.add_argument("--delta-from", default=None,
                    help="上一轮 matrix.json 路径（delta_vs_prev 计算输入；"
                         "AG-7：与其 evalbench_version 不同即拒绝出数）")
    args = ap.parse_args(argv)
    if not args.run_dir or not os.path.isdir(args.run_dir):
        print("用法: python aggregate.py --run-dir <run 目录> --pack <pack 目录> [--out <matrix.json>]",
              file=sys.stderr)
        return 2

    pack_name = os.path.basename(os.path.normpath(args.pack)) if args.pack else None
    cols = {}
    for arm in ("baseline", "treatment"):
        arm_dir = os.path.join(args.run_dir, arm)
        if not os.path.isdir(arm_dir):
            continue
        rec = read_json(os.path.join(arm_dir, "records", "arm_run.json"), {}) or {}
        fam = rec.get("family_requested", "glm")
        cols["%s|%s|r1" % (fam, arm)] = arm_cell(arm_dir, fam)

    matrix = {
        "schema": "matrix.v6-mvp",
        "layer": "dev",
        "evalbench_version": args.evalbench_version,
        "run_id": os.path.basename(os.path.normpath(args.run_dir)),
        "rows": {pack_name or "sm-mapping-01": cols},
        "delta_vs_none": {pack_name or "sm-mapping-01": None},
        "delta_vs_prev": {pack_name or "sm-mapping-01": None},
        "delta_note": "首轮基线轮只有 none/treatment 两臂，无 A_old → delta_vs_prev=null（PLAN §3.2，"
                      "显式 null 而非 0，防「首轮误报 0」AG-4）；delta_vs_none 亦不计算，"
                      "因 n=1 单任务，MVP 产出只能称「管线验证信号」，不得称验收结论。",
        "cross_family_comparable": False,
        "cross_family_note": "跨族 Δ 不可比（被测模型本身是变量，PLAN §5.5）",
    }

    # AG-7 跨版本拒绝门（最小实现，SF-0003）：新旧 evalbench 版本禁止并列（EVAL-SPEC §4.4-2）。
    # 混版本输入 → exit 1 且报「版本」、不落任何 delta 输出；同版本 → 本 MVP 无质量分，
    # delta_vs_prev 保持显式 null（AG-4 首轮口径同样适用）。
    if args.delta_from:
        prev = read_json(args.delta_from)
        if not isinstance(prev, dict) or "evalbench_version" not in prev:
            print("AG-7 拒绝：--delta-from 输入缺少 evalbench_version 字段，拒绝计算 delta", file=sys.stderr)
            return 1
        if prev.get("evalbench_version") != args.evalbench_version:
            print("AG-7 跨版本拒绝：上一轮 evalbench 版本 %s 与本轮 %s 不同——"
                  "跨版本 Δ 禁止并列（EVAL-SPEC §4.4-2），已拒绝出数，不落 matrix。"
                  % (prev.get("evalbench_version"), args.evalbench_version), file=sys.stderr)
            return 1
        matrix["delta_prev_source"] = {
            "path": os.path.abspath(args.delta_from),
            "evalbench_version": prev.get("evalbench_version"),
            "note": "同版本输入被接受；本轮质量轨无分（unjudgeable），delta_vs_prev 保持显式 null（AG-4）",
        }

    # AG-15 / EI-21：逐必填键 schema 校验 + 写-读往返
    missing = []
    for key, cell in cols.items():
        for req in CELL_REQUIRED:
            if req not in cell:
                missing.append("%s.%s" % (key, req))
    if missing:
        print("schema 缺键: %s" % missing, file=sys.stderr)
        return 1

    out_path = args.out_path or os.path.join(args.run_dir, "matrix.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n")
    back = read_json(out_path)  # 往返：写完立刻读回
    if back != matrix:
        print("写-读往返不一致（EI-21）", file=sys.stderr)
        return 1
    print(json.dumps(matrix, ensure_ascii=False, indent=2))
    print("\n往返自测: 通过；schema 必填键: 齐")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
