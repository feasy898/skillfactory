#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 B 层冒烟第 2 轮编排器（evalkit/runs/sf0006-b-smoke-2/ 随卡证据，不在 freeze 钉版面）。

与第 1 轮（evalkit/runs/sf0006-b-smoke/，failed_infra）的差异：钉版机制改用钉版探针
（evalkit/runs/sf0006-pin-probe/，提交 d64a88b）实测验证过的双机制，照抄：
  minimax 臂 · M2：成对 env（ZCODE_BUILTIN_PROVIDER_CONFIG_FILE=builtin 原样副本 +
    ZCODE_PERSONAL_PROVIDER_CONFIG_FILE=personal 派生副本），副本设
    defaultModelSelection={providerId:"minimax", modelId:"Minimax-M3.1-Flash-Preview",
    options:{reasoningLevel:"enabled"}} + providerOrder 置顶 minimax。
  glm 臂 · M4：在 M2 基础上（defaultModelSelection={providerId:
    "account:bigmodel-individual-coding-plan", modelId:"GLM-5.3",
    options:{reasoningLevel:"max"}}）加 ZCODE_DATA_BASE_DIR=<scratch>/zcode-data，
    其 .zcode/v2/credentials.json = 全局凭据逐条目原样拷贝 + 注入一条明文
    account-provider:<id>:identity 条目（值从既有 api-key 条目名解析；
    凭据值全程不回显不进仓）。
  关键：options.reasoningLevel 缺失会被 runtime 0.16.9 质量门整体弃用（SF-0004 失效根因），
  不可省略（探针 verdict.md workingMechanism 节）。

全局配置零改动（B-03）：~/.zcode/cli/config.json、~/.zcode/v2/provider_config.json、
全局凭据 ~/.zcode/v2/credentials.json 三份只读；开工/收工 sha256 由外部记录比对；
派生副本与 scratch 跑完 rmtree 并断言不存在。

预算刚性（P5）：正式臂进程 ≤4；每臂仅 rate_limited 退避重试 1 次（重试进程单列披露）。
红线（B-01/SF-0004 DT-v1）：glm 臂 observed 落点 ≠ 契约 → redline_event=true 停跑后续臂。
退出码：0 全部臂完成且钉版全中 / 1 存在臂级失败或钉版漂移或红线 / 2 用法错误。
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-b-smoke-2")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
CRED_SRC = os.path.expanduser("~/.zcode/v2/credentials.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
SCRATCH = "/tmp/sf0006b2-pin-scratch"

# run_arm.py PROMPT 逐字；不提资产名、不给臂内差异暗示（EI-7）
PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800}   # run_arm.FAMILY_TIMEOUT 同源

# B-01 契约落点（逐字大小写敏感）
TARGET = {
    "glm": {"provider": "account:bigmodel-individual-coding-plan", "model": "GLM-5.3",
            "reasoning": "max"},
    "minimax": {"provider": "minimax", "model": "Minimax-M3.1-Flash-Preview",
                "reasoning": "enabled"},
}

ARMS = [
    {"name": "glm-baseline",      "family": "glm",     "arm": "baseline",
     "dir": os.path.join(RUN, "glm", "baseline"),      "mech": "m4"},
    {"name": "glm-treatment",     "family": "glm",     "arm": "treatment",
     "dir": os.path.join(RUN, "glm", "treatment"),     "mech": "m4"},
    {"name": "minimax-baseline",  "family": "minimax", "arm": "baseline",
     "dir": os.path.join(RUN, "minimax", "baseline"),  "mech": "m2"},
    {"name": "minimax-treatment", "family": "minimax", "arm": "treatment",
     "dir": os.path.join(RUN, "minimax", "treatment"), "mech": "m2"},
]

spec = importlib.util.spec_from_file_location(
    "run_arm", os.path.join(ROOT, "evalkit", "harness", "run_arm.py"))
run_arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_arm)
pull_telemetry = run_arm.pull_telemetry

BUDGET_PATH = os.path.join(RUN, "budget.json")
CAP_ARMS = 4   # P5：B 层 ≤4 个正式臂进程
RETRY_CAP_PER_ARM = 1

ENV_PROVIDER_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
                     "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
                     "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")


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


def load_budget():
    with open(BUDGET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_budget(b):
    write_json(BUDGET_PATH, b)


def derive_personal(fam_scratch, family):
    """M2 骨架：personal 派生副本（照探针 derive_personal，simplify=False）。
    只落 scratch；返回路径。绝不回显内容。"""
    t = TARGET[family]
    with open(PERSONAL_SRC, "r", encoding="utf-8") as f:
        personal = json.load(f)
    cfg = personal.setdefault("config", {})
    cfg["defaultModelSelection"] = {"providerId": t["provider"], "modelId": t["model"],
                                    "options": {"reasoningLevel": t["reasoning"]}}
    cfg["providerOrder"] = [t["provider"]] + [p for p in cfg.get("providerOrder", [])
                                              if p != t["provider"]]
    path = os.path.join(fam_scratch, "provider_config.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(personal, f, ensure_ascii=False, indent=2)
    return path


def derive_data_dir(fam_scratch, family):
    """M4：ZCODE_DATA_BASE_DIR 数据目录。凭据副本 = 全局凭据逐条目原样拷贝（加密 blob
    不动）+ 注入一条明文 identity 条目（探针实证：cipher 对无 enc:v1: 前缀的值原样返回）。
    identity 值从既有 api-key 条目名解析，全程留在 scratch，不回显不进仓。
    返回 (data_dir, note)；机制不可行时返回 (None, reason)。"""
    t = TARGET[family]
    with open(CRED_SRC, "r", encoding="utf-8") as f:
        creds = json.load(f)
    ident_key = "account-provider:%s:identity" % t["provider"]
    if ident_key in creds:
        return None, "identity 条目已存在（探针口径：无需注入，M4 短路）"
    api_keys = [k for k in creds
                if k.startswith("account-provider:coding-plan:%s:account:" % t["provider"])
                and k.endswith(":api-key")]
    if not api_keys:
        return None, "无 api-key 条目可解析 identity，M4 不可行"
    account_identity = api_keys[0].split(":account:")[-1][:-len(":api-key")]
    if not account_identity:
        return None, "api-key 条目名中 identity 段为空"
    creds[ident_key] = account_identity          # 明文条目（decrypt 原样返回）
    v2 = os.path.join(fam_scratch, "zcode-data", ".zcode", "v2")
    os.makedirs(v2, exist_ok=True)
    path = os.path.join(v2, "credentials.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(path, 0o600)
    note = ("注入明文 identity 条目 %s（值=<%d chars，从 …api-key 条目名解析>）；"
            "其余 %d 条原样拷贝（加密 blob 不动）"
            % (ident_key, len(account_identity), len(creds) - 1))
    return os.path.join(fam_scratch, "zcode-data"), note


def build_family_scratch(family):
    """建单族 scratch：builtin 原样副本 + personal 派生副本（+M4 数据目录）。"""
    fam_scratch = os.path.join(SCRATCH, family)
    os.makedirs(fam_scratch, exist_ok=True)
    builtin_path = os.path.join(fam_scratch, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)
    personal_path = derive_personal(fam_scratch, family)
    m4_note = None
    extra_env = {
        "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": builtin_path,
        "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": personal_path,
    }
    if TARGET[family]["provider"] == "account:bigmodel-individual-coding-plan":
        data_dir, m4_note = derive_data_dir(fam_scratch, family)
        if data_dir is None:
            return None, m4_note
        extra_env["ZCODE_DATA_BASE_DIR"] = data_dir
    return {"extra_env": extra_env, "m4_note": m4_note,
            "builtin_sha256": sha256_file(BUILTIN_SRC)}, None


def looks_rate_limited(text, tele):
    rows = tele.get("model_usage") or []
    for r in rows:
        if "rate_limited" in str(r.get("status") or ""):
            return True
    return bool(re.search(r"rate[_ ]?limit", text, re.I))


def dominant_row(rows):
    """B-01 观测行：按调用次数 n 降序取首（多行时全量落 records 供复核）。"""
    return sorted(rows, key=lambda r: (r.get("n") or 0), reverse=True)[0] if rows else None


def run_once(armcfg, extra_env):
    """spawn 一臂一进程；返回 record dict（不落盘，由调用方决定归档）。"""
    arm_dir = os.path.abspath(armcfg["dir"])
    timeout = FAMILY_TIMEOUT[armcfg["family"]]
    # headless CLI 入口：/usr/bin/zcode 是 electron 桌面 binary（第 1 轮 spawn#1 实测吞 -p）；
    # node + CLI bundle 是 headless 入口（--version 实测 0.16.9，探针同款）
    cmd = [shutil.which("node") or "/home/pan-ding/.local/bin/node",
           "/opt/ZCode/resources/glm/zcode.cjs",
           "-p", PROMPT, "--cwd", arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    # env 卫生（第 1 轮实测教训）：本 worker 会话跑在 zcode 宿主内，os.environ 携带宿主注入
    # 的 provider 覆盖变量；先剔除再显式覆盖，避免宿主 env 污染臂语义
    for k in ENV_PROVIDER_KEYS:
        env.pop(k, None)
    env.pop("ZCODE_DATA_BASE_DIR", None)
    env.update(extra_env)

    t0 = time.time()
    started = int(t0 * 1000)
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env,
                              shell=False, cwd=arm_dir)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)

    text = out.decode("utf-8", errors="replace")
    errtext = err.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None
    time.sleep(2)  # 活库写入稍滞后于进程退出（第 1 轮/探针同口径）
    tele = pull_telemetry(DB, session_id, arm_dir)
    if session_id and not (tele.get("model_usage") or []):
        # M4 可能改动 storage root：扫 scratch 内 db 兜底（探针同款）
        for root, _dirs, files in os.walk(SCRATCH):
            for fn in files:
                if fn.endswith(".sqlite"):
                    cand = pull_telemetry(os.path.join(root, fn), session_id, arm_dir)
                    if cand.get("session"):
                        tele = dict(cand, db_path_fallback=os.path.join(root, fn))
                        break
            if tele.get("session"):
                break
    rows = tele.get("model_usage") or []
    dom = dominant_row(rows)
    return {
        "name": armcfg["name"], "family": armcfg["family"], "arm": armcfg["arm"],
        "mechanism": armcfg["mech"],
        "command_shape": ["node", "zcode.cjs", "-p", "<PROMPT 逐字同 run_arm.py>", "--cwd",
                          arm_dir, "--json"],
        "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": started,
        "session_id": session_id,
        "directory_matches_arm": tele.get("directory_matches_arm"),
        "session_directory": (tele.get("session") or {}).get("directory"),
        "db_source": "global" if not tele.get("db_path_fallback") else "scratch-fallback",
        "model_id_observed": dom.get("model_id") if dom else None,
        "provider_id_observed": dom.get("provider_id") if dom else None,
        "variant_observed": dom.get("variant") if dom else None,
        "model_usage_rows": len(rows),
        "model_usage": rows,
        "input_tokens": sum((r.get("it") or 0) for r in rows),
        "output_tokens": sum((r.get("ot") or 0) for r in rows),
        "stdout_bytes": len(out), "stderr_bytes": len(err),
        "stderr_head": errtext[:2000],
        "stdout_tail": text[-1500:],
        "_raw_stdout": text, "_raw_stderr": errtext,
    }


def write_transcript(name, raw_stdout, raw_stderr):
    """照 run_arm 口径存 pack transcript/（污染扫描用）；r2 后缀防覆盖第 1 轮。
    非 JSON stdout 按 739e4a7 先例命名 .cli-error.txt（防 C-11 类 JSON 扫描误伤）。"""
    tdir = os.path.join(ROOT, "evalkit", "packs", "ws4-dev", "mm-01", "transcript",
                        "%s-r2" % name)
    os.makedirs(tdir, exist_ok=True)
    stripped = raw_stdout.lstrip()
    sname = "zcode_stdout.json" if stripped.startswith("{") else "zcode_stdout.cli-error.txt"
    with open(os.path.join(tdir, sname), "w", encoding="utf-8", newline="\n") as f:
        f.write(raw_stdout)
    with open(os.path.join(tdir, "zcode_stderr.txt"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(raw_stderr)
    return "evalkit/packs/ws4-dev/mm-01/transcript/%s-r2" % name


def classify_arm(rec, retried):
    """臂健康度三桶：装置原函数 classify_run 实跑（第 1 轮同口径）。
    钉版命中与否不在本函数——单列 pin_verdict，层判据在 B-01 汇总。"""
    spec2 = importlib.util.spec_from_file_location(
        "classify", os.path.join(ROOT, "evalkit", "evaluators", "classify.py"))
    classify = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(classify)
    events = []
    if rec["timed_out"]:
        events.append({"kind": "arm_timeout", "detail": "wall_ms=%d" % rec["wall_ms"]})
    elif rec["session_id"] is None and rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "no session / no model_usage"})
    elif rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "session without model_usage"})
    if retried:
        events.append({"kind": "rate_limited", "detail": "退避重试 1 次后重跑"})
    # 健康臂给空事件表：classify_run([]) → measured_failure（其余 → 正常计分）
    r = classify.classify_run(events, arm_id=rec["name"])
    return {"bucket": r["arm_verdict"],
            "buckets_detail": [b["bucket"] for b in r["buckets"]] or ["measured_failure"],
            "classify_module": "evalkit/evaluators/classify.py classify_run（装置原函数实跑）",
            "events_in": events}


def main():
    os.makedirs(RUN, exist_ok=True)
    # A-14 口径断言：oracle 根与所有臂目录互不为子路径
    oracle_root = os.path.abspath(os.path.join(RUN, "oracle", "mm-01-rep1"))
    for a in ARMS:
        ad = os.path.abspath(a["dir"])
        cp = os.path.commonpath([oracle_root, ad])
        if cp in (oracle_root, ad):
            print("ORACLE_PATH_VIOLATION: %s vs %s" % (oracle_root, ad))
            return 2

    if not os.path.isfile(BUDGET_PATH):
        save_budget({"cap_counted_arms": CAP_ARMS, "retry_cap_per_arm": RETRY_CAP_PER_ARM,
                     "counted_arm_procs": 0, "retry_procs": 0, "model_calls": 0,
                     "entries": []})
    b = load_budget()

    results, redline, stop = [], False, None
    scratch_ready = {}
    try:
        for armcfg in ARMS:
            if stop:
                results.append({"name": armcfg["name"], "attempted": False,
                                "stop_reason": stop})
                continue
            if b["counted_arm_procs"] + 1 > CAP_ARMS:
                stop = "预算触顶（P5 ≤4 正式臂进程），超额即停"
                results.append({"name": armcfg["name"], "attempted": False,
                                "stop_reason": stop})
                continue
            fam = armcfg["family"]
            if fam not in scratch_ready:
                built, err = build_family_scratch(fam)
                if built is None:
                    stop = "scratch 派生失败：%s" % err
                    results.append({"name": armcfg["name"], "attempted": False,
                                    "stop_reason": stop})
                    continue
                scratch_ready[fam] = built
            extra_env = dict(scratch_ready[fam]["extra_env"])

            slot = len(b["entries"]) + 1
            b["entries"].append({"slot": slot, "arm": armcfg["name"],
                                 "kind": "arm", "ts_intent": time.strftime("%H:%M:%S"),
                                 "status": "pending"})
            save_budget(b)
            rec = run_once(armcfg, extra_env)
            b = load_budget()
            b["counted_arm_procs"] += 1
            model_call = rec["model_usage_rows"] > 0
            if model_call:
                b["model_calls"] += 1
            b["entries"][-1].update({"status": "done" if model_call else "no-model-call",
                                     "model_call": model_call,
                                     "exit_code": rec["exit_code"],
                                     "session_id": rec["session_id"],
                                     "observed": {"model_id": rec["model_id_observed"],
                                                  "provider_id": rec["provider_id_observed"],
                                                  "variant": rec["variant_observed"]}})
            save_budget(b)

            failed = (rec["exit_code"] != 0 or rec["timed_out"]
                      or not rec["session_id"] or rec["model_usage_rows"] == 0)
            rl = failed and looks_rate_limited(rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            retried = False
            if rl and b["retry_procs"] + 1 <= RETRY_CAP_PER_ARM:
                att1 = {k: v for k, v in rec.items() if not k.startswith("_")}
                att1["attempt"] = 1
                write_json(os.path.join(RUN, "attempts",
                                        "%s.attempt1.json" % armcfg["name"]), att1)
                time.sleep(30)
                slot = len(b["entries"]) + 1
                b["entries"].append({"slot": slot, "arm": armcfg["name"],
                                     "kind": "rate_limited-retry",
                                     "ts_intent": time.strftime("%H:%M:%S"),
                                     "status": "pending"})
                save_budget(b)
                rec = run_once(armcfg, extra_env)
                b = load_budget()
                b["retry_procs"] += 1
                if rec["model_usage_rows"] > 0:
                    b["model_calls"] += 1
                b["entries"][-1].update({"status": "done" if rec["model_usage_rows"] > 0
                                         else "no-model-call",
                                         "exit_code": rec["exit_code"]})
                save_budget(b)
                rec = dict(rec, attempt=2, rate_limited_retry=True)
                retried = True

            # —— 落盘每臂 records（照 run_arm 口径；model_pin 五键齐）——
            arm_dir = os.path.abspath(armcfg["dir"])
            rec_dir = os.path.join(arm_dir, "records")
            judge = os.path.join(ROOT, "evalkit/packs/ws4-dev/mm-01/checks/run_check.py")
            pin = {
                "arm": armcfg["arm"], "run_label": "r1", "run_id": "sf0006-b-smoke-2",
                "model_id": rec["model_id_observed"] or "UNOBSERVED",
                "provider_base_url": rec["provider_id_observed"] or "UNOBSERVED",
                "cli_runtime": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9",
                "date": time.strftime("%Y-%m-%d"),
                "reasoning_variant": rec["variant_observed"]
                                     or ("max" if fam == "glm" else "enabled"),
                "judge_sha256": sha256_file(judge) if os.path.isfile(judge) else None,
                "family": fam,
                "mechanism": armcfg["mech"],
                "note": ("B-01 实测钉版：model_id/provider_base_url 抄 db model_usage join "
                         "落点（逐字大小写敏感）；reasoningVariant=observed variant"),
            }
            write_json(os.path.join(rec_dir, "model_pin.json"), pin)
            arm_run = {k: v for k, v in rec.items() if not k.startswith("_")}
            arm_run["mechanism_note"] = scratch_ready[fam]["m4_note"] or \
                "M2 成对 env + defaultModelSelection.options.reasoningLevel + providerOrder 置顶"
            write_json(os.path.join(rec_dir, "arm_run.json"), arm_run)
            tele_out = {"available": True, "session_id": rec["session_id"],
                        "session": {"directory": rec["session_directory"]},
                        "directory_matches_arm": rec["directory_matches_arm"],
                        "db_source": arm_run["db_source"],
                        "model_usage": rec["model_usage"]}
            write_json(os.path.join(rec_dir, "telemetry.json"), tele_out)
            arm_run["transcript_dir"] = write_transcript(
                armcfg["name"], rec["_raw_stdout"], rec["_raw_stderr"])
            write_json(os.path.join(rec_dir, "arm_run.json"), arm_run)

            # —— B-01 钉版核对（逐字大小写敏感）；仅 observed 且不匹配构成 glm 红线 ——
            observed = rec["model_usage_rows"] > 0
            t = TARGET[fam]
            pin_ok = (rec["model_id_observed"] == t["model"]
                      and rec["provider_id_observed"] == t["provider"])
            summary = {k: v for k, v in rec.items() if not k.startswith("_")}
            summary["pin_verdict"] = ("pass" if pin_ok else
                                      "drift" if observed else "unobserved")
            summary["attempted"] = True
            summary["classify"] = classify_arm(rec, retried)
            results.append(summary)

            if fam == "glm" and observed and not pin_ok:
                redline = True
                stop = ("glm 臂落点漂移（B-01 红线，SF-0004 DT-v1）：observed %s @ %s ≠ "
                        "GLM-5.3 @ account:bigmodel-individual-coding-plan，停跑后续臂"
                        % (rec["model_id_observed"], rec["provider_id_observed"]))
                break
    finally:
        if os.path.isdir(SCRATCH):
            shutil.rmtree(SCRATCH, ignore_errors=True)
        scratch_purged = not os.path.isdir(SCRATCH)

    hard_fail = redline or any(
        r.get("attempted") and (r["exit_code"] != 0 or r["timed_out"]
                                or not r["session_id"] or r["model_usage_rows"] == 0
                                or r["pin_verdict"] != "pass")
        for r in results)
    out = {"counted_arm_procs": b["counted_arm_procs"], "retry_procs": b["retry_procs"],
           "cap": CAP_ARMS, "budget_ok": b["counted_arm_procs"] <= CAP_ARMS,
           "model_calls": b["model_calls"],
           "redline_event": redline, "stop_reason": stop,
           "scratch_purged": scratch_purged, "scratch_path": SCRATCH,
           "arms": results, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_json(os.path.join(RUN, "orchestrator-result.json"), out)
    print(json.dumps({k: out[k] for k in ("counted_arm_procs", "retry_procs", "model_calls",
                                          "redline_event", "stop_reason", "scratch_purged")},
                     ensure_ascii=False, indent=2))
    for r in results:
        if r.get("attempted"):
            print("%-20s exit=%s model=%s provider=%s variant=%s pin=%s dir_match=%s" % (
                r["name"], r["exit_code"], r["model_id_observed"],
                r["provider_id_observed"], r["variant_observed"], r["pin_verdict"],
                r["directory_matches_arm"]))
        else:
            print("%-20s NOT ATTEMPTED (%s)" % (r["name"], r.get("stop_reason")))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
