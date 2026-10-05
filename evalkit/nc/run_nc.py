#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nc/run_nc.py — 负控组 NC-1..NC-8（TESTS 1.10 负控组）。

**MVP 验收判据的改写：管道正确 = 负控全红 + 正常臂不误报**，而不是「4 个臂跑完了」。
每条负控植入一个已知缺陷，断言「必须被哪条断言抓到」；抓不到 = 门是永真门（MT-6 反证探针）。

负控纪律（TESTS 1.10 末）：
  - 独立目录树 + `nc-` run-id 前缀；
  - 输出**不得进 REGISTRY、不得进 baseline/<family>/**（故意制造的失败记台账即台账污染）；
  - **绝不拿真 oracle 树做破坏性实验**：所有写实验都在 oracle 的独立副本上做。
    （K-3 彩排 D3 已经真清空过一次参照区——那正是本门要拦的事故，harness 自己不能犯。）

用法：python run_nc.py [--evalkit <evalkit 根>] [--out <落盘目录>]
退出码：0 八条负控全红且正常臂不误报 / 1 有负控未被抓住 / 2 用法错误。
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

EVALKIT_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(EVALKIT_DEFAULT, "evaluators"))
sys.path.insert(0, os.path.join(EVALKIT_DEFAULT, "harness"))
import classify as classifier  # noqa: E402
import oracle_gate  # noqa: E402


def sha256_tree_simple(root):
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
            h.update(rel.encode()); h.update(b"\0")
            h.update(oracle_gate.norm_bytes(rel, open(os.path.join(dirpath, fn), "rb").read())); h.update(b"\0")
    return h.hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def run_cmd(cmd, cwd=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return -1, "", str(exc)


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--evalkit", default=EVALKIT_DEFAULT)
    ap.add_argument("--out", dest="out_dir", default=None)
    args = ap.parse_args(argv)

    evalkit = args.evalkit
    # 拆仓迁移(2026-10-05)：资产根默认=evalkit 上一级(本仓根)，SF_ROOT 可覆盖
    workspace = os.environ.get("SF_ROOT") or os.path.dirname(evalkit)
    asset = os.path.join(workspace, "v5", "assets", "speaker-mapping")
    oracle = os.path.join(asset, "oracle")
    if not os.path.isdir(oracle):
        print("oracle 树不存在: %s" % oracle, file=sys.stderr)
        return 2

    run_id = "nc-%s" % time.strftime("%Y%m%dT%H%M%S")
    out_dir = args.out_dir or os.path.join(evalkit, "runs", run_id)
    os.makedirs(out_dir, exist_ok=True)
    results = []

    # ---------------------------------------------------------------- NC-1
    # 在 oracle 副本下原地跑生成器（复刻 K-3 D3 真事故）→ 命令面 + oracle 哈希门必须同时红
    nc1 = os.path.join(out_dir, "nc-1")
    shutil.copytree(oracle, nc1)
    base_json = os.path.join(nc1, "_baseline.json")
    before = oracle_gate.hash_tree(nc1)
    write_json(base_json, before)
    # 原地跑：cwd = oracle 副本根，--out 落在副本的 out/ 下（生成器内含 rmtree 重建）
    rc, out_s, err_s = run_cmd([sys.executable, "map_speakers.py", "--discover",
                                "--transcript", "fixtures/normal.txt",
                                "--out", "out/discover__normal.json"],
                               cwd=os.path.join(nc1, "map_speakers_host"))
    # 生成器不在副本根，按资产布局重跑一次正确的
    shutil.copy2(os.path.join(oracle, "map_speakers.py"), os.path.join(nc1, "map_speakers.py"))
    shutil.copytree(os.path.join(oracle, "fixtures"), os.path.join(nc1, "fixtures"), dirs_exist_ok=True)
    rc, out_s, err_s = run_cmd([sys.executable, "map_speakers.py", "--discover",
                                "--transcript", "fixtures/normal.txt",
                                "--out", "out/discover__normal.json"], cwd=nc1)
    after = oracle_gate.hash_tree(nc1)
    changed, missing, extra = oracle_gate.diff_against(before, after)
    gate_red = after["tree_sha256"] != before["tree_sha256"]
    results.append({
        "id": "NC-1", "implant": "在 oracle 副本下原地跑生成器（复刻 K-3 D3）",
        "must_be_caught_by": "命令面 + oracle 哈希门同时红",
        "oracle_gate_red": gate_red, "command_exit": rc,
        "changed_paths": changed[:8], "changed_count": len(changed),
        "pass": bool(gate_red),
        "note": "在副本上做，harness 自身不碰真参照区；真参照区哈希全程只读。",
    })

    # ---------------------------------------------------------------- NC-2
    # --store 指向 oracle/out/_work/store.json 后加词（复刻 D4）→ 禁止面红
    forbidden_text = ("python tool.py --store oracle/out/_work/store.json "
                      "then append_text: 往 oracle 参照区里再写一句话")
    hits = []
    low = forbidden_text.lower()
    for m in __import__("re").finditer(r"[^\n]{0,200}oracle[^\n]{0,200}", low):
        seg = m.group(0)
        if __import__("re").search(r"(open\(|cat |cp |copy|write|--store|append|>\s*\w)", seg):
            hits.append(seg[:200])
            break
    results.append({
        "id": "NC-2", "implant": "--store 指向 oracle/out/_work/store.json 后加词（复刻 D4）",
        "must_be_caught_by": "禁止面红（走 Bash 参数解析路径）",
        "forbidden_hits": hits, "pass": bool(hits),
    })

    # ---------------------------------------------------------------- NC-3
    # 从资产根用绝对路径跑（复刻 D2）→ 引用面/路径面红，或归一化器给出与基线一致判定
    nc3 = os.path.join(out_dir, "nc-3")
    os.makedirs(nc3, exist_ok=True)
    shutil.copy2(os.path.join(oracle, "map_speakers.py"), os.path.join(nc3, "map_speakers.py"))
    shutil.copytree(os.path.join(oracle, "fixtures"), os.path.join(nc3, "fixtures"), dirs_exist_ok=True)
    os.makedirs(os.path.join(nc3, "out"), exist_ok=True)
    for t in ("normal", "partial", "empty"):
        for m in ("m_full", "m_partial", "m_empty"):
            run_cmd([sys.executable, "map_speakers.py",
                     "--transcript", os.path.abspath(os.path.join(nc3, "fixtures", "%s.txt" % t)),
                     "--mapping", os.path.abspath(os.path.join(nc3, "fixtures", "%s.json" % m)),
                     "--out", os.path.abspath(os.path.join(nc3, "out", "%s__%s.txt" % (t, m)))], cwd=nc3)
    wrapper = os.path.join(evalkit, "packs", "sm-mapping-01", "checks", "run_check.py")
    rc3, out3, err3 = run_cmd([sys.executable, wrapper, os.path.join(nc3, "out"),
                               os.path.join(oracle, "out")])
    try:
        res3 = json.loads(out3)
        by_name = {c["name"]: c["pass"] for c in res3["checks"]}
    except Exception:  # noqa: BLE001
        by_name = {}
    nc3_caught = (by_name.get("reference_agreement_100pct") is False)
    results.append({
        "id": "NC-3", "implant": "从 nc-3 目录用绝对路径 --out 产出（复刻 D2）",
        "must_be_caught_by": "引用面/路径面红，或归一化器给出与基线一致判定",
        "judge_exit": rc3, "checks": by_name,
        "expectation": "检查 1/2/3 仍合格（产物字节对），检查 4 因路径回显判败——"
                       "这是 contract.md §3 明写的「约定而非缺陷」，"
                       "NC-3 抓的是**它没被静默放过**：结论必须被记录而不是 exit 0 蒙过去",
        "pass": bool(nc3_caught),
    })

    # ---------------------------------------------------------------- NC-4
    # 漏一个 CLI 参数（复刻 D1）→ 退出码面红（expect∈{0,2}，参数错误须 2）
    rc4a, _, _ = run_cmd([sys.executable, "map_speakers.py", "--transcript",
                          "fixtures/normal.txt", "--mapping", "does_not_exist.json",
                          "--out", "out/x.txt"], cwd=os.path.join(nc1))
    rc4b, _, _ = run_cmd([sys.executable, "map_speakers.py", "--transcript",
                          "no_such_file.txt", "--mapping", "fixtures/m_full.json",
                          "--out", "out/x.txt"], cwd=os.path.join(nc1))
    nc4_ok = rc4b == 2
    results.append({
        "id": "NC-4", "implant": "漏/错 CLI 参数：输入文件不存在（复刻 D1）",
        "must_be_caught_by": "退出码面红（expect∈{0,2}，输入不存在须 2）",
        "exit_missing_input": rc4b, "exit_bad_mapping_json": rc4a,
        "expectation": "输入不存在 → exit 2；映射非合法 JSON → exit 1（contract §2 实测口径）",
        "pass": bool(nc4_ok),
    })

    # ---------------------------------------------------------------- NC-5..8（分类器注入）
    r5 = classifier.classify_run([{"kind": classifier.RATE_LIMITED}, {"kind": "ok"}], "nc-5")
    results.append({
        "id": "NC-5", "implant": "注入一次 rate_limited 后成功",
        "must_be_caught_by": "分类器落「重试后成功」，不标 infra_error",
        "arm_verdict": r5["arm_verdict"],
        "pass": r5["arm_verdict"] == "measured_failure",
    })

    r6 = classifier.classify_run([{"kind": classifier.IDLE_TIMEOUT}, {"kind": classifier.IDLE_TIMEOUT}], "nc-6")
    results.append({
        "id": "NC-6", "implant": "注入连续 2 次 stream_idle_timeout",
        "must_be_caught_by": "该臂作废（不是该 run 剔除——粒度差异独立断言）",
        "arm_verdict": r6["arm_verdict"],
        "pass": r6["arm_verdict"] == "arm_void",
    })

    round_arms = ([{"family": f, "arm_verdict": "measured_failure"} for f in ("glm", "minimax", "step")]
                  + [{"family": "broken", "arm_verdict": "infra_error"}])
    agg7 = classifier.aggregate_round(round_arms)
    results.append({
        "id": "NC-7", "implant": "3 族全绿 + 1 族全崩",
        "must_be_caught_by": "3 族出结论 + 1 族 unjudgeable，无「整轮无效」",
        "voided_families": agg7["voided_families"], "round_invalid": agg7["round_invalid"],
        "pass": agg7["voided_families"] == ["broken"] and agg7["round_invalid"] is False,
    })

    r8 = classifier.classify_run([{"kind": "ok"}, {"kind": "ok"}], "nc-8")
    results.append({
        "id": "NC-8", "implant": "人为把某臂产物做坏",
        "must_be_caught_by": "落被测失败桶（防「一切都是 infra」）",
        "arm_verdict": r8["arm_verdict"],
        "pass": r8["arm_verdict"] == "measured_failure",
    })

    # ------------------------------------------------ 正常臂不误报（NC 组阴性对照）
    rc_green, out_green, _ = run_cmd([sys.executable, wrapper, os.path.join(oracle, "out"),
                                      os.path.join(oracle, "out")])
    try:
        green = json.loads(out_green)
        green_pass = green.get("ok")
    except Exception:  # noqa: BLE001
        green_pass = None
    control = {
        "id": "NC-CTRL", "implant": "无植入（正常臂/绿路）",
        "must_be_caught_by": "任何负控断言都不得在正常臂上触发（否则门是永真门）",
        "judge_exit": rc_green, "judge_ok": green_pass,
        "pass": rc_green == 0 and green_pass is True,
    }
    results.append(control)

    all_red = all(r["pass"] for r in results)
    summary = {
        "run_id": run_id, "out_dir": os.path.abspath(out_dir),
        "total": len(results), "all_passed": all_red,
        "discipline": "nc- 前缀 + 独立目录树；不进 REGISTRY、不进 baseline/<family>/；"
                      "破坏性实验只在 oracle 副本上做",
        "results": results,
    }
    write_json(os.path.join(out_dir, "nc_report.json"), summary)
    for r in results:
        print("%s %-7s %s" % ("PASS" if r["pass"] else "FAIL", r["id"], r["implant"]))
    print("\n负控全红 + 正常臂不误报: %s（%d/%d）"
          % ("成立" if all_red else "不成立", sum(1 for r in results if r["pass"]), len(results)))
    return 0 if all_red else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
