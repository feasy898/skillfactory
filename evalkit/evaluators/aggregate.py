#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluators/aggregate.py — 落 matrix.json（PLAN §5.5 看板两层；TESTS AG-15 / EI-21）。

双模式（SF-0006 P6 改造：单 run_dir 单 pack MVP → 多题 × 单族聚合工具）：

【模式一：单 pack MVP（--pack 显式）】——行为保持 SF-0003 卡面口径：
matrix.json 结构：rows=任务，cols={族×臂×run}，单元固定字段
    {process_pass, artifact_pass, quality_score, tokens, wall_ms, infra_error}
外加三层随附（PLAN 纪律，防一词三义）：
    delta_vs_none / delta_vs_prev（本 MVP 为 null——首轮基线轮无 A_old，按 §3.2 首轮显式标注）
    layer（本文件产出固定 "dev"；holdout 数字禁入，AG-14）
新增：AG-6 跨族拒绝——两臂 family_requested 不同族时非零退出且不落任何 matrix。

【模式二：devpool 基线轮按族聚合（SF-0006 P6/C-01/C-05；缺省无 --pack 时启用）】
输入布局（C 层 run 根；族目录/单元目录/两臂）：
    <run-dir>/<family>/<task>-rep<k>/arms_manifest.json   （pack 键=题包路径，make_arms 产物）
    <run-dir>/<family>/<task>-rep<k>/{baseline,treatment}/records/arm_run.json
产出：按族**各一份** matrix（缺省 <run-dir>/matrix-<family>.json，即 C-01 的
matrix-glm.json / matrix-minimax.json），rows 恰 --expect-tasks 题（缺省 5）、
每题 {baseline,treatment}×r1..r2（--expect-reps，缺省 2）= 每族 20 单元六键齐。
四项硬口径（P6；owner-delegated-signing-20261008 §三 SF-0006）：
  1. 按族各出一份 matrix，覆盖 5 题（缺题/缺 rep/多 rep 一律拒绝，fail-closed）；
  2. delta_vs_none 按 PLAN §3.2 + C-05 复算口径：每题 treatment 通过率 − baseline
     通过率，再对题取均值。通过 = 该单元 artifact_pass is True（产物轨 checker 是
     唯一计分来源，SF-0004 §7；infra_error 单元 artifact_pass=None 计不通过、分母
     含之——**不做 infra 剔除**，与复算口径逐位一致，infra 单元另在 infra_errors
     逐条披露，C-06）；
  3. delta_vs_prev 保持显式 null（不是 0；AG-4 首轮口径；--delta-from 同版本输入
     被接受后仍为 null——本轮质量轨 unjudgeable 无分）；
  4. AG-6 跨族拒绝：输入含两族单元（或 --family 之外的族）→ 非零退出且**不落盘
     任何 matrix 文件**（TESTS AG-6：拒绝出数，不是除一下完事；EVAL-SPEC §4.4-2）。
所有拒绝路径（AG-6 / AG-7 / 布局错 / 缺题缺 rep / schema 缺键）都在落盘之前判定，
拒绝时输出目录零写入。
落盘后**立刻 json.load 回读**做写-读-断言往返（EI-21：hw_student_eval.json 是反面教材）。

用法（模式一）：python aggregate.py --run-dir <run 目录> --pack <pack 目录> [--out <matrix.json 路径>]
用法（模式二）：python aggregate.py --run-dir <C 层 run 根> [--family <glm|minimax>]
               [--expect-tasks 5] [--expect-reps 2] [--out <matrix-<family>.json 路径>]
公共：[--evalbench-version <版本>] [--delta-from <上一轮 matrix.json>]
退出码：0 聚合完成且 schema 往返过 / 1 拒绝（AG-6 跨族、AG-7 跨版本、布局错、
        缺题缺 rep、schema 缺键、写读往返失败）/ 2 用法错误。
"""

import argparse
import io
import json
import os
import re
import sys

CELL_REQUIRED = ["process_pass", "artifact_pass", "quality_score", "tokens", "wall_ms", "infra_error"]
UNIT_NAME_RE = re.compile(r"^(?P<task>.+)-rep(?P<rep>\d+)$")


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


def reject(msg):
    """拒绝出口：打 stderr、返回退出码 1。调用方必须在任何落盘之前使用。"""
    print(msg, file=sys.stderr)
    return 1


def scan_family_units(run_dir, want_family, expect_tasks, expect_reps):
    """模式二：扫描 C 层 run 根，返回 (family, rows, infra_errors) 或 (None, err, None)。

    以 arms_manifest.json 为单元锚（make_arms 产物，天然避开 oracle/、records/ 等非臂目录）；
    全部校验 fail-closed，任何不合规返回错误消息，不产生输出。

    扫描范围（SF-0006 C-01/C-05 实跑修正 2026-10-08）：--family 显式时范围限定为
    <run-dir>/<family>/ 子树——按族各出一份 matrix 是对同一物理 run 根的两次调用
    （matrix-glm.json / matrix-minimax.json），族子树内混入他族单元仍由「族一致性」
    检查拒绝（AG-6 否定式测试见 runs/sf0006-aggregator/selftest_p6.py 场景 1/1b）；
    不给 --family 时扫全根，发现 ≥2 族即 AG-6 拒绝出数。
    """
    units = {}       # (task, rep) -> {arm: arm_dir}
    families = set()
    problems = []
    roots = [os.path.join(run_dir, want_family)] if want_family else [run_dir]
    for root in roots:
        if not os.path.isdir(root):
            return None, ("布局错：聚合范围不存在：%s" % root), None
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in (".zcode", "__pycache__"))
            if "arms_manifest.json" not in filenames:
                continue
            rel = os.path.relpath(dirpath, run_dir).replace(os.sep, "/")
            fam_dir = rel.split("/")[0]
            m = UNIT_NAME_RE.match(os.path.basename(dirpath))
            if not m:
                problems.append("布局错：%s 单元目录名不形如 <task>-rep<k>" % rel)
                continue
            task, rep = m.group("task"), int(m.group("rep"))
            man = read_json(os.path.join(dirpath, "arms_manifest.json"), {}) or {}
            pack = man.get("pack")
            if not pack or os.path.basename(os.path.normpath(str(pack))) != task:
                problems.append("布局错：%s arms_manifest.pack(%r) 与目录名 task(%r) 不一致"
                                % (rel, pack, task))
                continue
            for arm in ("baseline", "treatment"):
                arm_dir = os.path.join(dirpath, arm)
                arm_rec = read_json(os.path.join(arm_dir, "records", "arm_run.json"), {}) or {}
                if not arm_rec:
                    problems.append("缺件：%s/%s/records/arm_run.json 不存在或为空" % (rel, arm))
                    continue
                fam_rec = arm_rec.get("family") or arm_rec.get("family_requested")
                if fam_rec != fam_dir:
                    problems.append("族不一致：%s/%s 目录族=%r arm_run 族=%r（AG-6 前置一致性）"
                                    % (rel, arm, fam_dir, fam_rec))
                    continue
                families.add(fam_dir)
                units.setdefault((task, rep), {})[arm] = arm_dir
    if problems:
        return None, "；".join(problems[:10]), None

    # AG-6 跨族拒绝（TESTS AG-6；EVAL-SPEC §4.4-2）：拒绝出数，不是除一下完事
    if len(families) >= 2:
        return None, ("AG-6 跨族拒绝：输入含 %d 族单元 {%s}——跨族 Δ 不可比"
                      "（被测模型本身是变量，PLAN §5.5；EVAL-SPEC §4.4-2）。"
                      "按族各跑一次聚合（--family 单族），本次拒绝出数，不落任何 matrix。"
                      % (len(families), ", ".join(sorted(families)))), None
    if not families:
        return None, ("AG-6/布局错：输入中未发现任何合规单元（ arms_manifest.json + "
                      "baseline/treatment 两臂 arm_run.json），无法确定族。"), None
    family = next(iter(families))
    if want_family and family != want_family:
        return None, ("AG-6 跨族拒绝：--family=%s 与输入实际族 {%s} 不符——本次拒绝出数，"
                      "不落任何 matrix。" % (want_family, family)), None

    tasks = sorted(set(t for t, _ in units))
    reps = sorted(set(r for _, r in units))
    if len(tasks) != expect_tasks:
        return None, ("覆盖不足：实际 %d 题 {%s} ≠ 期望 --expect-tasks=%d——"
                      "matrix 须覆盖全部题（P6/C-01），拒绝出数，不落任何 matrix。"
                      % (len(tasks), ", ".join(tasks), expect_tasks)), None
    want_reps = list(range(1, expect_reps + 1))
    for task in tasks:
        for rep in reps:
            arms = units.get((task, rep))
            if arms is None or set(arms) != {"baseline", "treatment"}:
                return None, ("缺单元：%s-rep%d 两臂不齐（实得 %s）——每题须 "
                              "baseline+treatment × r1..r%d，拒绝出数，不落任何 matrix。"
                              % (task, rep, sorted(arms or {}), expect_reps)), None
    for task, rep in units:
        if rep not in want_reps:
            return None, ("多余重复：%s-rep%d 超出 --expect-reps=%d——拒绝出数（防脏单元混入"
                          " delta 分母），不落任何 matrix。" % (task, rep, expect_reps)), None

    rows = {}
    infra_errors = []
    for task in tasks:
        cols = {}
        for rep in reps:
            for arm in ("baseline", "treatment"):
                cell = arm_cell(units[(task, rep)][arm], family)
                cols["%s|%s|r%d" % (family, arm, rep)] = cell
                if cell["infra_error"]:
                    infra_errors.append({
                        "task": task, "rep": rep, "arm": arm, "family": family,
                        "exit_code": cell["exit_code"], "timed_out": None,
                        "reason": "arm_run.timed_out 或 exit_code!=0（PLAN §5.5 三桶；"
                                  "逐条披露，禁止静默剔除，C-06/EI-19）",
                    })
        rows[task] = cols
    return {"family": family, "rows": rows, "infra_errors": infra_errors}, None, None


def delta_vs_none_calc(rows):
    """PLAN §3.2 + C-05 口径：每题 treatment 通过率 − baseline 通过率，再对题取均值。

    通过 = artifact_pass is True；分母 = 该臂全部单元（不做 infra 剔除，与复算口径
    逐位一致；infra 单元在 infra_errors 另行披露）。
    """
    per_task = {}
    for task, cols in rows.items():
        rates = {}
        for arm in ("baseline", "treatment"):
            cells = [c for k, c in cols.items() if c["arm"] == arm]
            rates[arm] = sum(1 for c in cells if c["artifact_pass"] is True) / len(cells)
        per_task[task] = {"treatment_rate": rates["treatment"],
                          "baseline_rate": rates["baseline"],
                          "delta": rates["treatment"] - rates["baseline"]}
    overall = sum(v["delta"] for v in per_task.values()) / len(per_task)
    return overall, per_task


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--family", default=None,
                    help="模式二：期望族（glm|minimax）。缺省时自动检测——检测到 ≥2 族即 AG-6 拒绝")
    ap.add_argument("--expect-tasks", type=int, default=5,
                    help="模式二：期望题数（P6/C-01：覆盖 5 题；缺题即拒绝，fail-closed）")
    ap.add_argument("--expect-reps", type=int, default=2)
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
        print("用法: python aggregate.py --run-dir <run 目录> --pack <pack 目录>（模式一）\n"
              "      python aggregate.py --run-dir <C 层 run 根> [--family <族>]（模式二）",
              file=sys.stderr)
        return 2
    if args.pack and args.family:
        print("用法错：--pack（模式一单 pack）与 --family（模式二按族聚合）互斥", file=sys.stderr)
        return 2

    # AG-7 跨版本拒绝门（最小实现，SF-0003）：新旧 evalbench 版本禁止并列（EVAL-SPEC §4.4-2）。
    # 混版本输入 → exit 1 且报「版本」、不落任何 delta 输出；同版本 → delta_vs_prev 保持
    # 显式 null（AG-4：本轮质量轨 unjudgeable 无分，null 而非 0，防「首轮误报 0」）。
    delta_prev_source = None
    if args.delta_from:
        prev = read_json(args.delta_from)
        if not isinstance(prev, dict) or "evalbench_version" not in prev:
            return reject("AG-7 拒绝：--delta-from 输入缺少 evalbench_version 字段，拒绝计算 delta")
        if prev.get("evalbench_version") != args.evalbench_version:
            return reject("AG-7 跨版本拒绝：上一轮 evalbench 版本 %s 与本轮 %s 不同——"
                          "跨版本 Δ 禁止并列（EVAL-SPEC §4.4-2），已拒绝出数，不落 matrix。"
                          % (prev.get("evalbench_version"), args.evalbench_version))
        delta_prev_source = {
            "path": os.path.abspath(args.delta_from),
            "evalbench_version": prev.get("evalbench_version"),
            "note": "同版本输入被接受；本轮质量轨无分（unjudgeable），delta_vs_prev 保持显式 null（AG-4）",
        }

    if args.pack:
        return _mode_single_pack(args, delta_prev_source)
    return _mode_family(args, delta_prev_source)


def _mode_single_pack(args, delta_prev_source):
    """模式一：单 pack MVP（SF-0003 卡面口径）+ AG-6 混族拒绝。"""
    pack_name = os.path.basename(os.path.normpath(args.pack)) if args.pack else None
    cols = {}
    for arm in ("baseline", "treatment"):
        arm_dir = os.path.join(args.run_dir, arm)
        if not os.path.isdir(arm_dir):
            continue
        rec = read_json(os.path.join(arm_dir, "records", "arm_run.json"), {}) or {}
        fam = rec.get("family_requested", "glm")
        cols["%s|%s|r1" % (fam, arm)] = arm_cell(arm_dir, fam)

    # AG-6 跨族拒绝（SF-0006 P6 红先：改造前此形态 exit 0 落混族 matrix——2026-10-08 补出口）。
    # 在落盘之前判定：混族输入非零退出且不落任何 matrix 文件。
    fams = sorted({k.split("|")[0] for k in cols})
    if len(fams) >= 2:
        return reject("AG-6 跨族拒绝：单次聚合输入含 %d 族单元 {%s}（cols=%s）——跨族 Δ 不可比"
                      "（被测模型本身是变量，PLAN §5.5；EVAL-SPEC §4.4-2；TESTS AG-6）。"
                      "拒绝出数，不落任何 matrix。"
                      % (len(fams), ", ".join(fams), ", ".join(sorted(cols))))

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
    if delta_prev_source:
        matrix["delta_prev_source"] = delta_prev_source

    # AG-15 / EI-21：逐必填键 schema 校验 + 写-读往返
    missing = []
    for key, cell in cols.items():
        for req in CELL_REQUIRED:
            if req not in cell:
                missing.append("%s.%s" % (key, req))
    if missing:
        return reject("schema 缺键: %s" % missing)
    return _write_matrix(matrix, args.out_path or os.path.join(args.run_dir, "matrix.json"))


def _mode_family(args, delta_prev_source):
    """模式二：devpool 基线轮按族聚合（SF-0006 P6/C-01/C-05）。"""
    scanned, err, _ = scan_family_units(args.run_dir, args.family,
                                        args.expect_tasks, args.expect_reps)
    if err:
        return reject(err)
    family, rows, infra_errors = scanned["family"], scanned["rows"], scanned["infra_errors"]

    overall, per_task = delta_vs_none_calc(rows)
    matrix = {
        "schema": "matrix.v6-mvp",
        "matrix_kind": "devpool-baseline",
        "layer": "dev",
        "evalbench_version": args.evalbench_version,
        "run_id": os.path.basename(os.path.normpath(args.run_dir)),
        "family": family,
        "rows": rows,
        "delta_vs_none": overall,
        "delta_vs_none_per_task": per_task,
        "delta_vs_prev": None,
        "delta_note": "首轮基线轮两臂（none/treatment），无 A_old → delta_vs_prev=显式 null"
                      "（不是 0，防「首轮误报 0」AG-4；PLAN §3.2）。delta_vs_none 口径"
                      "（PLAN §3.2 + C-05）：每题 treatment 通过率 − baseline 通过率，再对题"
                      "取均值；通过 = artifact_pass is True（产物轨 checker 唯一计分来源，"
                      "SF-0004 §7；质量轨 unjudgeable 不出分）；infra_error 单元 "
                      "artifact_pass=None 计不通过、分母含全部单元——不做 infra 剔除，与"
                      "独立复算口径逐位一致（复算脚本不得 import 本工具），infra 单元在 "
                      "infra_errors 逐条披露（C-06/EI-19）。本轮只出基线信号，不出验收结论。",
        "cross_family_comparable": False,
        "cross_family_note": "跨族 Δ 不可比（被测模型本身是变量，PLAN §5.5；AG-6：混族输入"
                             "拒绝出数，单份 matrix 内只有一个族）",
        "delta_prev_source": delta_prev_source,
        "infra_errors": infra_errors,
        "unit_counts": {"tasks": len(rows),
                        "cells": sum(len(c) for c in rows.values())},
    }
    if matrix["delta_prev_source"] is None:
        del matrix["delta_prev_source"]  # 未给 --delta-from 时不落该键，delta_vs_prev 保持顶层 null

    # AG-15 / EI-21：逐必填键 schema 校验（六键 × 每单元）+ 写-读往返
    missing = []
    for key, cell in (kv for cols in rows.values() for kv in cols.items()):
        for req in CELL_REQUIRED:
            if req not in cell:
                missing.append("%s.%s" % (key, req))
    if missing:
        return reject("schema 缺键: %s" % missing)
    out_path = args.out_path or os.path.join(args.run_dir, "matrix-%s.json" % family)
    return _write_matrix(matrix, out_path)


def _write_matrix(matrix, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n")
    back = read_json(out_path)  # 往返：写完立刻读回
    if back != matrix:
        return reject("写-读往返不一致（EI-21）")
    print(json.dumps(matrix, ensure_ascii=False, indent=2))
    print("\n往返自测: 通过；schema 必填键: 齐")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
