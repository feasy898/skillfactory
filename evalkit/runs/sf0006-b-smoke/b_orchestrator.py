#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 B 层冒烟编排器（evalkit/runs/sf0006-b-smoke/ 随卡证据，不在 freeze 钉版面）。

一臂一进程 = 干净上下文 + 物理隔离（EVAL-SPEC §3.2-3；照 harness/run_arm.py spawn 口径）：
  cmd = [zcode, "-p", PROMPT, "--cwd", <臂绝对路径>, "--json"]，PROMPT 两臂逐字相同（EI-7）。
分族超时照 run_arm.FAMILY_TIMEOUT：minimax 1200s / GLM 1800s。

M1 钉版（SF-0004 报告 §0/§3 成对 env 契约；bundle 语义：单变量启动即抛错）：
  minimax 臂 env 注入 ZCODE_BUILTIN_PROVIDER_CONFIG_FILE + ZCODE_PERSONAL_PROVIDER_CONFIG_FILE
  同时指向 /tmp 派生副本（personal 派生：defaultModelSelection + providerOrder 置顶；
  builtin 原样拷贝）。凭据不进仓、不回显；跑完 rmtree 并断言不存在（B-03）。

预算刚性（P5）：臂进程 ≤4；每臂仅 rate_limited 退避重试 1 次（PLAN §5.6）。
红线（B-01/SF-0004 DT-v1）：glm 臂落点漂移 → redline_event=true 并停跑后续臂。
GLM 臂 / minimax 臂落点核对（B-01，逐字大小写敏感）用 db model_usage join 实测值。

退出码：0 全部臂完成 / 1 存在臂级失败或红线 / 2 用法错误。
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-b-smoke")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
SCRATCH = "/tmp/sf0006b-m1-scratch"

# run_arm.py:33-35 逐字；不提资产名、不给臂内差异暗示（EI-7）
PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800}   # run_arm.py:31 同源
TARGET_PROVIDER = "minimax"
TARGET_MODEL = "Minimax-M3.1-Flash-Preview"

ARMS = [
    {"name": "glm-baseline",      "family": "glm",     "arm": "baseline",
     "dir": os.path.join(ROOT, "evalkit/runs/sf0006-b-mm01-glm/baseline"), "mech": None},
    {"name": "glm-treatment",     "family": "glm",     "arm": "treatment",
     "dir": os.path.join(ROOT, "evalkit/runs/sf0006-b-mm01-glm/treatment"), "mech": None},
    {"name": "minimax-baseline",  "family": "minimax", "arm": "baseline",
     "dir": os.path.join(ROOT, "evalkit/runs/sf0006-b-mm01-minimax/baseline"), "mech": "m1"},
    {"name": "minimax-treatment", "family": "minimax", "arm": "treatment",
     "dir": os.path.join(ROOT, "evalkit/runs/sf0006-b-mm01-minimax/treatment"), "mech": "m1"},
]

spec = importlib.util.spec_from_file_location(
    "run_arm", os.path.join(ROOT, "evalkit", "harness", "run_arm.py"))
run_arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_arm)
pull_telemetry = run_arm.pull_telemetry


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def build_m1_scratch():
    """派生副本（含凭据）只落 /tmp scratch，绝不回显内容。照 sf0004-probes p_zcode_head.py:71-86。"""
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)
    with open(PERSONAL_SRC, "r", encoding="utf-8") as f:
        personal = json.load(f)
    cfg = personal.setdefault("config", {})
    cfg["defaultModelSelection"] = {"providerId": TARGET_PROVIDER, "modelId": TARGET_MODEL,
                                    "options": {}}
    cfg["providerOrder"] = [TARGET_PROVIDER] + [p for p in cfg.get("providerOrder", [])
                                                if p != TARGET_PROVIDER]
    personal_path = os.path.join(SCRATCH, "provider_config.json")
    with open(personal_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(personal, f, ensure_ascii=False, indent=2)
    builtin_path = os.path.join(SCRATCH, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)
    return personal_path, builtin_path


def purge_scratch():
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    return not os.path.isdir(SCRATCH)


def looks_rate_limited(text, tele):
    rows = tele.get("model_usage") or []
    for r in rows:
        if "rate_limited" in str(r.get("status") or ""):
            return True
    return bool(re.search(r"rate[_ ]?limit", text, re.I))


def run_once(armcfg, extra_env):
    """spawn 一臂一进程；返回 record dict（不落盘，由调用方决定 attempt 归档）。"""
    arm_dir = os.path.abspath(armcfg["dir"])
    timeout = FAMILY_TIMEOUT[armcfg["family"]]
    # headless CLI 入口：/usr/bin/zcode 是 electron 桌面 binary（-p 被 GUI 吞掉空转退出，
    # 2026-10-08 实测留痕 attempts/gui-misstart-note.json）；CLI bundle 才是 headless 入口
    # （shebang node，--version 实测 0.16.9，等价 zcode-app-cli bin/zcode.js）
    cmd = [shutil.which("node") or "/home/pan-ding/.local/bin/node",
           "/opt/ZCode/resources/glm/zcode.cjs",
           "-p", PROMPT, "--cwd", arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    # env 卫生（2026-10-08 实测教训，见 attempts/glm-baseline.envleak-step/note.json）：
    # 本 worker 会话本身跑在 zcode 宿主内，os.environ 携带宿主注入的成对 provider 覆盖
    # 变量；glm 臂语义是裸跑（SF-0004 A-ctl 形态），必须显式剔除这三个 bundle 认读的
    # provider 配置变量。minimax 臂随后显式覆盖为自己的派生副本。
    for k in ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE", "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
              "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE"):
        env.pop(k, None)
    env.update(extra_env)

    t0 = time.time()
    started = int(t0 * 1000)
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env, shell=False)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)

    text = out.decode("utf-8", errors="replace")
    errtext = err.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None
    time.sleep(2)  # 活库写入稍滞后于进程退出（SF-0004 同口径：进程退出后即查）
    tele = pull_telemetry(DB, session_id, arm_dir)
    rows = tele.get("model_usage") or []
    model_id = rows[0].get("model_id") if rows else None
    provider_id = rows[0].get("provider_id") if rows else None
    return {
        "name": armcfg["name"], "family": armcfg["family"], "arm": armcfg["arm"],
        "mechanism": armcfg["mech"],
        "command_shape": ["zcode", "-p", "<PROMPT 逐字同 run_arm.py:33-35>", "--cwd",
                          arm_dir, "--json"],
        "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": started,
        "session_id": session_id,
        "directory_matches_arm": tele.get("directory_matches_arm"),
        "session_directory": (tele.get("session") or {}).get("directory"),
        "model_id_observed": model_id, "provider_id_observed": provider_id,
        "model_usage_rows": len(rows),
        "model_usage": rows,
        "input_tokens": sum((r.get("it") or 0) for r in rows),
        "output_tokens": sum((r.get("ot") or 0) for r in rows),
        "stdout_bytes": len(out), "stderr_bytes": len(err),
        "stderr_head": errtext[:2000],
        "stdout_tail": text[-1500:],
        "_raw_stdout": text, "_raw_stderr": errtext,
    }


def main():
    results, proc_budget = [], {"arm_procs": 0, "retries": 0, "cap": 4}
    redline = False
    stop = None
    scratch_live = False
    try:
        for armcfg in ARMS:
            if stop:
                results.append({"name": armcfg["name"], "attempted": False, "stop_reason": stop})
                continue
            extra_env = {}
            if armcfg["mech"] == "m1" and not scratch_live:
                personal_path, builtin_path = build_m1_scratch()
                scratch_live = True
            if armcfg["mech"] == "m1":
                extra_env["ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"] = builtin_path
                extra_env["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"] = personal_path

            rec = run_once(armcfg, extra_env)
            proc_budget["arm_procs"] += 1
            failed = (rec["exit_code"] != 0 or rec["timed_out"]
                      or not rec["session_id"] or rec["model_usage_rows"] == 0)
            rl = failed and looks_rate_limited(
                rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            if rl and proc_budget["arm_procs"] + 1 <= proc_budget["cap"] + proc_budget["cap"]:
                # rate_limited 退避重试 1 次（P5/PLAN §5.6）；attempt1 归档后覆盖
                att1 = {k: v for k, v in rec.items() if not k.startswith("_")}
                att1["attempt"] = 1
                write_json(os.path.join(RUN, "attempts",
                                        "%s.attempt1.json" % armcfg["name"]), att1)
                time.sleep(30)
                rec2 = run_once(armcfg, extra_env)
                proc_budget["arm_procs"] += 1
                proc_budget["retries"] += 1
                failed2 = (rec2["exit_code"] != 0 or rec2["timed_out"]
                           or not rec2["session_id"] or rec2["model_usage_rows"] == 0)
                rec = dict(rec2, attempt=2, attempt1_summary={
                    "exit_code": att1["exit_code"], "session_id": att1["session_id"],
                    "model_usage_rows": att1["model_usage_rows"]})
                rec["rate_limited_retry"] = True
                failed = failed2
                rl = failed and looks_rate_limited(
                    rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            rec["rate_limited_detected"] = bool(rl)

            # —— 落盘每臂 records（照 run_arm.py:151-188 口径）——
            arm_dir = os.path.abspath(armcfg["dir"])
            rec_dir = os.path.join(arm_dir, "records")
            pin = {
                "arm": armcfg["arm"], "run_label": "r1", "run_id": "sf0006-b-smoke",
                "model_id": rec["model_id_observed"] or "UNOBSERVED",
                "provider_base_url": rec["provider_id_observed"]
                                     or "UNOBSERVED",
                "cli_runtime": "zcode-app-cli 3.14.4-30 / zcode-runtime 0.16.9",
                "date": time.strftime("%Y-%m-%d"),
                "reasoning_variant": "default(max)",
                "judge_sha256": None,
                "family": armcfg["family"],
                "mechanism": armcfg["mech"] or "default",
                "note": "B-01 实测钉版：model_id/provider_base_url 抄 db model_usage join 落点（逐字）",
            }
            judge = os.path.join(ROOT, "evalkit/packs/ws4-dev/mm-01/checks/run_check.py")
            if os.path.isfile(judge):
                pin["judge_sha256"] = sha256_file(judge)
            write_json(os.path.join(rec_dir, "model_pin.json"), pin)
            arm_run = {k: v for k, v in rec.items() if not k.startswith("_")}
            write_json(os.path.join(rec_dir, "arm_run.json"), arm_run)
            tele = {"available": True, "session_id": rec["session_id"],
                    "session": {"directory": rec["session_directory"]},
                    "directory_matches_arm": rec["directory_matches_arm"],
                    "model_usage": rec["model_usage"]}
            write_json(os.path.join(rec_dir, "telemetry.json"), tele)
            tdir = os.path.join(ROOT, "evalkit/packs/ws4-dev/mm-01/transcript",
                                "%s-r1" % armcfg["name"])
            os.makedirs(tdir, exist_ok=True)
            with open(os.path.join(tdir, "zcode_stdout.json"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(rec["_raw_stdout"])
            with open(os.path.join(tdir, "zcode_stderr.txt"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(rec["_raw_stderr"])

            # —— B-01 钉版核对（逐字大小写敏感）；unobserved=infra 不触发红线，只有
            # observed 且不匹配才是钉版漂移（B-01 红线语义：落点≠目标串）——
            observed = rec["model_usage_rows"] > 0
            if armcfg["family"] == "glm":
                pin_ok = (rec["model_id_observed"] == "GLM-5.3"
                          and rec["provider_id_observed"]
                          == "account:bigmodel-individual-coding-plan")
                if observed and not pin_ok:
                    redline = True
                    stop = "glm 臂落点漂移（B-01 红线，SF-0004 DT-v1）：停跑后续臂"
            else:
                pin_ok = (rec["model_id_observed"] == TARGET_MODEL
                          and rec["provider_id_observed"] == TARGET_PROVIDER)
            summary = {k: v for k, v in rec.items() if not k.startswith("_")}
            summary["pin_verdict"] = ("pass" if pin_ok else
                                      "drift" if observed else "unobserved")
            summary["attempted"] = True
            results.append(summary)

            if redline:
                break
    finally:
        scratch_purged = purge_scratch()

    out = {"arm_procs": proc_budget["arm_procs"], "retries": proc_budget["retries"],
           "cap": proc_budget["cap"],
           "budget_ok": proc_budget["arm_procs"] <= proc_budget["cap"],
           "redline_event": redline, "stop_reason": stop,
           "scratch_purged": scratch_purged, "scratch_path": SCRATCH,
           "arms": results, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_json(os.path.join(RUN, "orchestrator-result.json"), out)
    print(json.dumps({k: out[k] for k in ("arm_procs", "retries", "redline_event",
                                          "stop_reason", "scratch_purged")},
                     ensure_ascii=False, indent=2))
    for r in results:
        if r.get("attempted"):
            print("%-20s exit=%s model=%s provider=%s pin=%s dir_match=%s" % (
                r["name"], r["exit_code"], r["model_id_observed"],
                r["provider_id_observed"], r["pin_verdict"], r["directory_matches_arm"]))
        else:
            print("%-20s NOT ATTEMPTED (%s)" % (r["name"], r.get("stop_reason")))
    hard_fail = redline or any(
        r.get("attempted") and (r["exit_code"] != 0 or r["timed_out"]
                                or not r["session_id"] or r["model_usage_rows"] == 0)
        for r in results)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
