#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 step 族钉版探针执行器（evalkit/runs/sf0006-step-probe/，授权预算 ≤6 次真实模型调用）。

机制：M2 变体（照 sf0006-pin-probe 先例）——进程级成对 env（builtin 原样副本 +
personal 派生副本），派生副本设 defaultModelSelection={providerId, modelId,
options:{reasoningLevel}} + providerOrder 置顶目标 provider。禁止改 ~/.zcode 全局配置。

预算语义：真实模型调用以 db model_usage 实测行数>0 为准；spawn 前记账 pending，
spawn 后按实测回填；无模型调用的失败探针不消耗预算。

凭据纪律：personal 副本只落 /tmp scratch；记录落盘前剥离 access.apiKey；
scratch 子目录探针结束即 rmtree。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-step-probe")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
CLI = "/opt/ZCode/resources/glm/zcode.cjs"
NODE = shutil.which("node") or "/home/pan-ding/.local/bin/node"
BUDGET_PATH = os.path.join(RUN, "budget.json")
CAP = 6
ENV_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE", "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
            "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")


def load_budget():
    with open(BUDGET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_budget(b):
    with open(BUDGET_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def strip_secrets(obj):
    """深拷贝并剥离敏感值（仅记录结构）。"""
    if isinstance(obj, dict):
        return {k: ("<stripped:%d chars>" % len(str(v)))
                if re.search(r"apikey|api_key|secret|token", k, re.I) and v
                else strip_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_secrets(x) for x in obj]
    return obj


def derive_personal(scratch, provider, model, reasoning, extra_selection=None):
    """派生 personal 副本（M2 变体）：defaultModelSelection + providerOrder 置顶。
    extra_selection：可选 dict，合入 defaultModelSelection 顶层（反推适配用）。"""
    with open(PERSONAL_SRC, "r", encoding="utf-8") as f:
        personal = json.load(f)
    cfg = personal.setdefault("config", {})
    sel = {"providerId": provider, "modelId": model,
           "options": {"reasoningLevel": reasoning}}
    if extra_selection:
        sel.update(extra_selection)
    cfg["defaultModelSelection"] = sel
    cfg["providerOrder"] = [provider] + [p for p in cfg.get("providerOrder", [])
                                         if p != provider]
    path = os.path.join(scratch, "provider_config.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(personal, f, ensure_ascii=False, indent=2)
    return path, strip_secrets(sel)


def pull_telemetry(session_id, arm_dir, db=DB):
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    out = {"available": False}
    try:
        r = cur.execute("select directory, task_type, version from session where id=?",
                        (session_id,)).fetchone()
        out["session"] = dict(r) if r else None
        out["directory_matches_probe"] = bool(r) and os.path.normcase(r["directory"]) == \
            os.path.normcase(os.path.abspath(arm_dir))
        rows = cur.execute(
            "select model_id, provider_id, variant, status, sum(input_tokens) it, "
            "sum(output_tokens) ot, count(*) n from model_usage where session_id=? "
            "group by model_id, provider_id, variant, status", (session_id,)).fetchall()
        out["model_usage"] = [dict(x) for x in rows]
        out["available"] = True
    finally:
        con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-id", required=True)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--reasoning", required=True)
    ap.add_argument("--extra-selection", default=None,
                    help="JSON 对象，合入 defaultModelSelection 顶层（反推适配用）")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    pid, prov, model = args.probe_id, args.provider, args.model
    work = os.path.join(RUN, "work", pid)
    os.makedirs(work, exist_ok=True)
    scratch = "/tmp/sf0006-step-probe/%s" % pid
    if os.path.isdir(scratch):
        shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True)

    # —— 记账在前：预算刚性，触顶即停 ——
    b = load_budget()
    if b["model_calls"] + 1 > CAP:
        print("BUDGET_EXHAUSTED: %d/%d" % (b["model_calls"], CAP))
        return 2
    slot = len(b["entries"]) + 1
    b["entries"].append({"slot": slot, "probe_id": pid, "ts_intent": time.strftime("%H:%M:%S"),
                         "status": "pending"})
    save_budget(b)
    print("budget: slot=%d model_calls=%d/%d -> launching %s" %
          (slot, b["model_calls"] + 1, CAP, pid))

    extra_sel = json.loads(args.extra_selection) if args.extra_selection else None
    personal_path, sel_record = derive_personal(scratch, prov, model, args.reasoning, extra_sel)
    builtin_path = os.path.join(scratch, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)

    env = dict(os.environ)
    for k in ENV_KEYS:
        env.pop(k, None)
    env["ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"] = builtin_path
    env["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"] = personal_path
    env["MSYS_NO_PATHCONV"] = "1"

    cmd = [NODE, CLI, "-p", "回复 ok", "--cwd", work, "--json"]
    t0 = time.time()
    started_at = int(t0 * 1000)
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=args.timeout,
                              env=env, shell=False, cwd=work)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)
    text = out.decode("utf-8", errors="replace")
    errtext = err.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None
    time.sleep(2)
    tele = pull_telemetry(session_id, work) if session_id else {"available": False}
    rows = tele.get("model_usage") or []
    # 逐行判定（可能多 provider 混跑）：主判定取 model_usage 首行
    observed_model = rows[0]["model_id"] if rows else None
    observed_provider = rows[0]["provider_id"] if rows else None
    observed_variant = rows[0]["variant"] if rows else None
    model_call = len(rows) > 0

    rec = {
        "probe_id": pid,
        "mechanism": "M2-variant(reasoningLevel)",
        "target": {"provider_id": prov, "model_id": model, "reasoningLevel": args.reasoning},
        "defaultModelSelection_written": sel_record,
        "budget_slot": slot,
        "budget_model_calls_after": b["model_calls"] + (1 if model_call else 0),
        "command_shape": ["node", "zcode.cjs", "-p", "<最小 prompt：回复 ok>", "--cwd", work, "--json"],
        "env_paired": True, "builtin_src": BUILTIN_SRC, "builtin_sha256": sha256_file(BUILTIN_SRC),
        "personal_src": PERSONAL_SRC,
        "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": started_at, "session_id": session_id,
        "directory_matches_probe": tele.get("directory_matches_probe"),
        "session_directory": (tele.get("session") or {}).get("directory"),
        "model_call_confirmed": model_call,
        "observed": {"model_id": observed_model, "provider_id": observed_provider,
                     "variant": observed_variant, "model_usage_rows": len(rows)},
        "hit": bool(model_call and observed_model == model and observed_provider == prov),
        "model_usage": rows,
        "stderr_head": errtext[:1500], "stdout_tail": text[-1200:],
    }
    rec_path = os.path.join(RUN, "records", "%s.json" % pid)
    os.makedirs(os.path.dirname(rec_path), exist_ok=True)
    with open(rec_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
        f.write("\n")

    b = load_budget()
    if model_call:
        b["model_calls"] += 1
    for e in b["entries"]:
        if e.get("slot") == slot:
            e["status"] = "done" if model_call else "no-model-call"
            e["model_call"] = model_call
            e["hit"] = rec["hit"]
            e["observed"] = rec["observed"]
    save_budget(b)
    shutil.rmtree(scratch, ignore_errors=True)

    print("PROBE %s: hit=%s observed=%s@%s variant=%s rows=%d model_call=%s" %
          (pid, rec["hit"], observed_model, observed_provider, observed_variant,
           len(rows), model_call))
    return 0 if rec["hit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
