#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0006-aggregator/selftest_p6.py — SF-0006 P6 聚合工具自证（构造物，非跑批产物）。

P6 四项 + C-01/C-05 的自证驱动（退出码为证）：
  1. 两族混合输入（C 层布局）→ 聚合工具非零退出，且输出目录不落任何 matrix 文件（AG-6）；
  2. 两族混合输入（单 pack 旧布局，即红先探针同形态）→ 非零退出不落盘（改造前 exit 0 为红先）；
  3. glm 单族 5 题 × 2 rep × 2 臂合成输入 → exit 0 产出 matrix-glm.json：
     rows 恰 5 题、20 单元六键齐、delta_vs_none 与手算一致、delta_vs_prev 显式 null；
  4. delta_vs_none 由**独立复算脚本**（本文件内实现，不 import 聚合工具）从单元复算，
     与 matrix 值差 <1e-9（C-05）；
  5. 同版本 --delta-from 被接受且 delta_vs_prev 仍为 null（AG-7 正向 + AG-4）。

用法：python selftest_p6.py   （在 evalkit/ 目录下执行；exit 0 = 全部自证过）
"""

import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(os.path.dirname(HERE))  # runs/sf0006-aggregator 上两级 = evalkit/
AGG = os.path.join(EVALKIT, "evaluators", "aggregate.py")  # evaluators/aggregate.py
TASKS = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03"]
# 通过率设计（glm treatment）：1.0 / 0.5 / 0.0 / 1.0 / 0.5 → 均值 0.6；baseline 全不过 → 0.0
TREAT_PASS = {"mm-01": [True, True], "mm-02": [True, False], "hot-01": [False, False],
              "hot-02": [True, True], "hot-03": [False, True]}
BASE_PASS = {t: [False, False] for t in TASKS}
EXPECT_DELTA = 0.6
FAILURES = []


def check(name, ok, detail=""):
    print("%-28s %s %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILURES.append(name)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_unit(root, fam, task, rep, treat_pass, base_pass, base_infra=False):
    """构造一个单元目录：<root>/<fam>/<task>-rep<rep>/{manifest,两臂 records}。"""
    unit = os.path.join(root, fam, "%s-rep%d" % (task, rep))
    write_json(os.path.join(unit, "arms_manifest.json"),
               {"pack": os.path.join(HERE, "..", "..", "packs", "ws4-dev", task),
                "note": "P6 自证构造物（非跑批产物）"})
    for arm, passes in (("treatment", treat_pass), ("baseline", base_pass)):
        arm_dir = os.path.join(unit, arm)
        infra = base_infra and arm == "baseline"
        write_json(os.path.join(arm_dir, "records", "arm_run.json"),
                   {"family": fam, "arm": arm, "exit_code": 1 if infra else 0,
                    "timed_out": False, "wall_ms": 4321,
                    "session_id": "synth-%s-%s-r%d" % (fam, task, rep)})
        write_json(os.path.join(arm_dir, "records", "telemetry.json"),
                   {"available": True, "session_id": "synth",
                    "model_usage": [{"it": 111, "ot": 11}]})
        write_json(os.path.join(arm_dir, "records", "process_track.json"), {"verdict": "pass"})
        # infra 单元不落 artifact_track（复刻 infra 臂产物轨缺件 → artifact_pass=None 计不通过）
        if not infra:
            write_json(os.path.join(arm_dir, "records", "artifact_track.json"),
                       {"verdict": "pass" if passes[rep - 1] else "fail"})


def build_family(root, fam):
    for task in TASKS:
        for rep in (1, 2):
            base_infra = (fam == "glm" and task == "mm-01" and rep == 2)  # 恰 1 个 infra 单元
            build_unit(root, fam, task, rep, TREAT_PASS[task], BASE_PASS[task], base_infra)


def run_agg(argv):
    p = subprocess.run([sys.executable, AGG] + argv, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def matrix_files(d):
    return sorted(f for f in os.listdir(d) if f.startswith("matrix") and f.endswith(".json"))


def recompute_delta(rows):
    """C-05 独立复算：每题 treatment 通过率 − baseline 通过率，再对题取均值。不 import 聚合工具。"""
    per = {}
    for task, cols in rows.items():
        rate = {}
        for arm in ("baseline", "treatment"):
            cells = [c for c in cols.values() if c["arm"] == arm]
            rate[arm] = sum(1 for c in cells if c["artifact_pass"] is True) / len(cells)
        per[task] = rate["treatment"] - rate["baseline"]
    return sum(per.values()) / len(per), per


def main():
    # ---------- 场景 1：两族混合输入（C 层布局）→ 非零退出 + 不落盘 ----------
    mixed = os.path.join(HERE, "selftest-mixed-families")
    shutil.rmtree(mixed, ignore_errors=True)
    build_family(mixed, "glm")
    for rep in (1, 2):  # minimax 侧给合规单元（两臂齐），恰好触发两族
        build_unit(mixed, "minimax", "mm-01", rep, [True, True], [False, False])
    before = set(matrix_files(mixed))
    for label, extra in (("无 --family", []), ("--family glm", ["--family", "glm"])):
        rc, _, err = run_agg(["--run-dir", mixed] + extra)
        leaked = set(matrix_files(mixed)) - before
        check("AG-6 混族(%s)非零退出" % label, rc != 0, "exit=%d" % rc)
        check("AG-6 混族(%s)零落盘" % label, not leaked, "err头=%s" % err.strip().splitlines()[0][:60] if err.strip() else "")
        check("AG-6 混族(%s)报AG-6" % label, "AG-6" in err, "")

    # ---------- 场景 2：单 pack 旧布局混族（红先同形态，改造前 exit 0）----------
    oldmixed = os.path.join(HERE, "red-probe-mixed")
    out2 = os.path.join(oldmixed, "matrix-must-not-exist.json")
    if os.path.exists(out2):
        os.remove(out2)
    rc, _, err = run_agg(["--run-dir", oldmixed, "--pack", "packs/ws4-dev/mm-01", "--out", out2])
    check("AG-6 旧布局混族非零退出", rc != 0, "exit=%d" % rc)
    check("AG-6 旧布局混族零落盘", not os.path.exists(out2), "")
    check("AG-6 旧布局拒绝报AG-6非崩溃", "AG-6" in err and "Traceback" not in err, "err头=%s" % err.strip().splitlines()[0][:60] if err.strip() else "")

    # ---------- 场景 3+4：glm 单族输入 → 正确 matrix + 独立复算 ----------
    single = os.path.join(HERE, "selftest-family-glm")
    shutil.rmtree(single, ignore_errors=True)
    build_family(single, "glm")
    out3 = os.path.join(single, "matrix-glm.json")
    rc, _, err = run_agg(["--run-dir", single, "--family", "glm"])
    check("单族输入 exit 0", rc == 0, err.strip()[:80])
    m = json.load(io.open(out3, encoding="utf-8"))
    cells = [c for cols in m["rows"].values() for c in cols.values()]
    six = ["process_pass", "artifact_pass", "quality_score", "tokens", "wall_ms", "infra_error"]
    check("rows 恰 5 题", len(m["rows"]) == 5 and sorted(m["rows"]) == sorted(TASKS), str(sorted(m["rows"])))
    check("每族 20 单元", len(cells) == 20, "cells=%d" % len(cells))
    check("六键齐", all(all(k in c for k in six) for c in cells), "")
    check("family 单族 glm", m["family"] == "glm" and all(c["family"] == "glm" for c in cells), "")
    check("delta_vs_none==手算0.6", abs(m["delta_vs_none"] - EXPECT_DELTA) < 1e-9,
          "delta=%r" % m["delta_vs_none"])
    check("delta_vs_prev 显式 null", m["delta_vs_prev"] is None, "repr=%r" % (m["delta_vs_prev"],))
    check("layer==dev", m["layer"] == "dev", "")
    check("evalbench v6-mvp-0.3", m["evalbench_version"] == "v6-mvp-0.3", "")
    check("质量轨 unjudgeable null", all(c["quality_score"] is None and c.get("quality_verdict") == "unjudgeable" for c in cells), "")
    infra = [c for c in cells if c["infra_error"]]
    check("infra 单元恰 1 且披露", len(infra) == 1 and len(m["infra_errors"]) == 1
          and m["infra_errors"][0]["task"] == "mm-01", json.dumps(m["infra_errors"], ensure_ascii=False)[:90])
    recomputed, per = recompute_delta(m["rows"])
    check("C-05 独立复算 <1e-9", abs(recomputed - m["delta_vs_none"]) < 1e-9,
          "复算=%r matrix=%r" % (recomputed, m["delta_vs_none"]))
    check("per_task 明细可对拍", all(abs(m["delta_vs_none_per_task"][t]["delta"] - per[t]) < 1e-12 for t in TASKS), "")
    check("缺省落盘名 matrix-glm.json", os.path.basename(out3) == "matrix-glm.json", "")

    # ---------- 场景 5：同版本 --delta-from 接受且 delta_vs_prev 仍 null ----------
    rc5, _, err5 = run_agg(["--run-dir", single, "--family", "glm",
                            "--delta-from", out3, "--out", os.path.join(single, "matrix-glm-prev.json")])
    m5 = json.load(io.open(os.path.join(single, "matrix-glm-prev.json"), encoding="utf-8")) if rc5 == 0 else {}
    check("AG-7 同版本接受 exit 0", rc5 == 0, err5.strip()[:80])
    check("AG-7 后 delta_vs_prev 仍 null", m5.get("delta_vs_prev") is None, "")

    # ---------- 场景 6：缺题 fail-closed（4 题 → 拒绝不落盘）----------
    short = os.path.join(HERE, "selftest-short-tasks")
    shutil.rmtree(short, ignore_errors=True)
    for task in TASKS[:4]:
        for rep in (1, 2):
            build_unit(short, "glm", task, rep, TREAT_PASS[task], BASE_PASS[task])
    before = set(matrix_files(short))
    rc, _, err = run_agg(["--run-dir", short, "--family", "glm"])
    check("缺题拒绝非零退出", rc != 0 and not (set(matrix_files(short)) - before),
          "exit=%d err头=%s" % (rc, err.strip().splitlines()[0][:50] if err.strip() else ""))

    print("\n===== P6 聚合工具自证：%s（红=%s）=====" %
          ("全过" if not FAILURES else "有红", FAILURES or "无"))
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
