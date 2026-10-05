#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/run_all.py — 一键复跑整条管道（PLAN §5.4 四步 + 负控）。

顺序即纪律：装置自检 → 步 0（0 模型）→ 步 1（0 模型）→ 步 2（4 臂）→ 步 3（0 模型）→ 负控。
任一 abort 判据红即停，**不继续评分**（PLAN §3.3 参照区没了还在出全红报告是门的最坏形态）。

用法：
    python run_all.py --run-id <id> [--families glm] [--skip-arms] [--out <落盘目录>]
退出码：0 全流程过 / 1 某步 abort / 2 用法错误。
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time

EVALKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.dirname(EVALKIT)
ASSET = os.path.join(WORKSPACE, "afp-clone", "zcode-research", "skillfactory",
                      "v5", "assets", "speaker-mapping")
PACK = os.path.join(EVALKIT, "packs", "sm-mapping-01")
PY = sys.executable


def step(name, cmd, cwd=EVALKIT, expect=(0,), env=None):
    print("\n=== %s ===" % name, flush=True)
    e = dict(os.environ)
    e["MSYS_NO_PATHCONV"] = "1"
    if env:
        e.update(env)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, env=e, timeout=3600)
    out = p.stdout.decode("utf-8", "replace")
    print(out[-1500:])
    if p.stderr.strip():
        print("[stderr]", p.stderr.decode("utf-8", "replace")[-600:])
    ok = p.returncode in expect
    print("--> exit=%d expect=%s %s" % (p.returncode, list(expect), "OK" if ok else "ABORT"))
    return ok, p.returncode


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--families", default="glm")
    ap.add_argument("--skip-arms", action="store_true")
    ap.add_argument("--out", dest="out_dir", default=None)
    ap.add_argument("--evalbench-version", default="v6-mvp-0.2",
                    help="透传给 evaluators/aggregate.py（B2；O-6【已裁定】后的当前版本，SF-0003）")
    args = ap.parse_args(argv)
    if not args.run_id:
        print("用法: python run_all.py --run-id <id> [--skip-arms]", file=sys.stderr)
        return 2

    run_dir = os.path.join(EVALKIT, "runs", args.run_id)
    out_dir = args.out_dir or run_dir
    os.makedirs(out_dir, exist_ok=True)
    base_json = os.path.join(out_dir, "oracle_baseline.json")
    log = []

    def rec(name, ok, rc):
        log.append({"step": name, "ok": ok, "exit_code": rc, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})

    ok, rc = step("装置钉版自检", [PY, "harness/freeze_device.py", "verify"]); rec("device_verify", ok, rc)
    if not ok:
        return 1

    ok, rc = step("步0 绿路（期望 exit 0）", [PY, os.path.join(PACK, "checks", "run_check.py")]); rec("green", ok, rc)
    empty = os.path.join(out_dir, "step0_empty")
    os.makedirs(empty, exist_ok=True)
    ok, rc = step("步0 空目录红路（期望 exit 1）",
                  [PY, os.path.join(PACK, "checks", "run_check.py"), empty,
                   os.path.join(ASSET, "oracle", "out")], expect=(1,)); rec("red", ok, rc)
    ok, rc = step("步0 oracle 哈希基线",
                  [PY, "harness/oracle_gate.py", "hash", "--root", os.path.join(ASSET, "oracle"),
                   "--record", base_json]); rec("oracle_hash", ok, rc)
    if not ok:
        return 1
    ok, rc = step("步0 易变面三跑标定",
                  [PY, "harness/oracle_gate.py", "calibrate", "--root", os.path.join(ASSET, "oracle"),
                   "--runs", "3", "--record", os.path.join(out_dir, "oracle_calibration.json")])
    rec("oracle_calibrate", ok, rc)

    ok, rc = step("步1 建臂树",
                  [PY, "harness/make_arms.py", "--pack", PACK, "--run-id", args.run_id,
                   "--asset-skill", os.path.join(ASSET, "package")]); rec("make_arms", ok, rc)
    if not ok:
        return 1
    ok, rc = step("步1 baseline 隔离探针（期望零命中）",
                  [PY, "harness/isolation_probe.py", os.path.join(run_dir, "baseline"),
                   "--json", os.path.join(run_dir, "isolation_baseline.json")]); rec("isolation", ok, rc)
    ok, rc = step("步1 前置三断言",
                  [PY, "harness/pack_checks.py", "--pack", PACK,
                   "--arms", os.path.join(run_dir, "baseline"),
                   "--arms", os.path.join(run_dir, "treatment"),
                   "--json", os.path.join(run_dir, "preflight.json")]); rec("preflight", ok, rc)
    if not ok:
        return 1

    if not args.skip_arms:
        for arm in ("baseline", "treatment"):
            ok, rc = step("步2 跑臂 %s" % arm,
                          [PY, "harness/run_arm.py", "--run-id", args.run_id, "--arm", arm,
                           "--arm-dir", os.path.join(run_dir, arm), "--family", args.families.split(",")[0],
                           "--run-label", "r1", "--pack", PACK], expect=(0, 1))
            rec("arm_" + arm, ok, rc)

        for arm in ("baseline", "treatment"):
            step("步3 产物轨 %s" % arm,
                 [PY, "evaluators/artifact_track.py", "--pack", PACK,
                  "--product-root", os.path.join(run_dir, arm, "out"),
                  "--reference", os.path.join(ASSET, "oracle", "out"),
                  "--out", os.path.join(run_dir, arm, "records", "artifact_track.json")], expect=(0, 1, 2))
            step("步3 过程轨 %s" % arm,
                 [PY, "evaluators/process_track.py", "--arm-dir", os.path.join(run_dir, arm),
                  "--oracle-root", os.path.join(ASSET, "oracle"),
                  "--out", os.path.join(run_dir, arm, "records", "process_track.json")], expect=(0, 1, 2))
            step("步3 质量轨 %s" % arm,
                 [PY, "evaluators/quality_track.py", "--pack", PACK, "--arm", arm,
                  "--out", os.path.join(run_dir, arm, "records", "quality.json")], expect=(0,))

    ok, rc = step("步3 matrix.json",
                  [PY, "evaluators/aggregate.py", "--run-dir", run_dir, "--pack", PACK,
                   "--evalbench-version", args.evalbench_version])
    rec("matrix", ok, rc)
    ok, rc = step("步3 哈希终检（oracle 前后一致）",
                  [PY, "harness/oracle_gate.py", "verify", "--root", os.path.join(ASSET, "oracle"),
                   "--record", base_json]); rec("oracle_final", ok, rc)
    if not ok:
        print("ABORT：参照区在跑批中变化，本轮评分一律作废。")
        return 1

    ok, rc = step("负控 NC-1..NC-8 + 阴性对照", [PY, "nc/run_nc.py"]); rec("nc", ok, rc)
    ok, rc = step("装置钉版后检（跑批中不得改判分器）", [PY, "harness/freeze_device.py", "verify"])
    rec("device_verify_final", ok, rc)

    with io.open(os.path.join(out_dir, "run_all_log.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"run_id": args.run_id, "steps": log}, ensure_ascii=False, indent=2) + "\n")
    failed = [s["step"] for s in log if not s["ok"]]
    print("\n===== 汇总：%s =====" % ("全部通过" if not failed else "有红：%s" % failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
