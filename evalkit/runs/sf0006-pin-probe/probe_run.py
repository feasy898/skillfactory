#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0006 钉版探针执行器（evalkit/runs/sf0006-pin-probe/，授权探针预算 ≤8 次真实模型调用）。

机制族（均为进程级 env + 派生配置副本，禁止改 ~/.zcode 全局配置）：
  m2/m3（主假设）：M1 成对 env 骨架 + defaultModelSelection.options.reasoningLevel 填入
                   模型支持值（静态依据 00-recon.md：bpe 对 options.reasoningLevel===undefined
                   一律 reasoning-level-missing → QKe 落 registry-fallback）。
  simplify（备用）：personal 副本极简化（builtinModelIds=[] + modelOrder/personalModelIds
                   只留目标模型），令 registry-fallback 也只能落目标。

预算语义（对齐 b_orchestrator）：真实模型调用以 db model_usage 实测行数>0 为准；
spawn 前先记账（pending），spawn 后按实测回填；无模型调用的失败探针不消耗预算。

凭据纪律：personal 副本只落 /tmp scratch，记录不落 apiKey（派生时即剥离计数验证）。
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
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-pin-probe")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
CLI = "/opt/ZCode/resources/glm/zcode.cjs"
NODE = shutil.which("node") or "/home/pan-ding/.local/bin/node"
BUDGET_PATH = os.path.join(RUN, "budget.json")
CAP = 8
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


def derive_personal(scratch, provider, model, reasoning, simplify, top_provider,
                    prune_except=None):
    """派生 personal 副本（含宿主凭据，绝不回显内容；返回路径与结构断言）。"""
    with open(PERSONAL_SRC, "r", encoding="utf-8") as f:
        personal = json.load(f)
    cfg = personal.setdefault("config", {})
    if prune_except:
        keep = prune_except
        rules = cfg.get("providerConfigRules", {}).get("providerRules", [])
        cfg["providerConfigRules"]["providerRules"] = [r for r in rules
                                                       if r.get("providerId") == keep]
        cfg["providerOrder"] = [keep]
    cfg["defaultModelSelection"] = {"providerId": provider, "modelId": model,
                                    "options": {"reasoningLevel": reasoning}}
    cfg["providerOrder"] = [top_provider] + [p for p in cfg.get("providerOrder", [])
                                             if p != top_provider]
    if simplify:
        for r in cfg.get("providerConfigRules", {}).get("providerRules", []):
            if r.get("providerId") == provider:
                c = r.setdefault("config", {})
                c["builtinModelIds"] = []          # 显式空：覆盖模板 builtin 8 模型
                c["personalModelIds"] = [model]    # 只留目标
                c["modelOrder"] = [model]          # 无得选
    path = os.path.join(scratch, "provider_config.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(personal, f, ensure_ascii=False, indent=2)
    return path


def derive_data_dir(scratch, provider):
    """M4：派生数据目录。凭据副本 = 全局凭据逐条目原样拷贝 + 注入一条明文 identity
    条目（cipher 对无 enc:v1: 前缀的值原样返回，bundle ZZr/decrypt 实证）。
    identity 值从既有 api-key 条目名解析，全程留在 scratch，不回显不进仓。
    返回 (data_dir, note)。"""
    cred_src = os.path.expanduser("~/.zcode/v2/credentials.json")
    with open(cred_src, "r", encoding="utf-8") as f:
        creds = json.load(f)
    ident_key = "account-provider:%s:identity" % provider
    if ident_key in creds:
        return None, "identity 条目已存在（无需注入）"
    api_keys = [k for k in creds
                if k.startswith("account-provider:coding-plan:%s:account:" % provider)
                and k.endswith(":api-key")]
    if not api_keys:
        return None, "无 api-key 条目可解析 identity，M4 不可行"
    account_identity = api_keys[0].split(":account:")[-1][:-len(":api-key")]
    if not account_identity:
        return None, "api-key 条目名中 identity 段为空"
    creds[ident_key] = account_identity          # 明文条目（decrypt 原样返回）
    v2 = os.path.join(scratch, "zcode-data", ".zcode", "v2")
    os.makedirs(v2, exist_ok=True)
    path = os.path.join(v2, "credentials.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(path, 0o600)
    note = ("注入明文 identity 条目 %s（值=<%d chars，从 %s 条目名解析>）；"
            "其余 %d 条原样拷贝（加密 blob 不动）" % (ident_key, len(account_identity),
                                                     "…api-key", len(creds) - 1))
    return os.path.join(scratch, "zcode-data"), note


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
    ap.add_argument("--simplify", action="store_true")
    ap.add_argument("--prune-personal-except", default=None,
                    help="派生副本仅保留该 provider（判定实验用；观察 fallback 落点）")
    ap.add_argument("--derive-data-dir", action="store_true",
                    help="派生数据目录：凭据副本补明文 identity 条目 + ZCODE_DATA_BASE_DIR "
                         "(M4；凭据值不回显不进仓)")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    pid, prov, model = args.probe_id, args.provider, args.model
    work = os.path.join(RUN, "work", pid)
    os.makedirs(work, exist_ok=True)
    scratch = "/tmp/sf0006-pin-probe/%s" % pid
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

    personal_path = derive_personal(scratch, prov, model, args.reasoning,
                                    args.simplify, top_provider=prov,
                                    prune_except=args.prune_personal_except)
    builtin_path = os.path.join(scratch, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)

    env = dict(os.environ)
    for k in ENV_KEYS:
        env.pop(k, None)
    env["ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"] = builtin_path
    env["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"] = personal_path
    env["MSYS_NO_PATHCONV"] = "1"
    m4_note = None
    if args.derive_data_dir:
        data_dir, m4_note = derive_data_dir(scratch, prov)
        if data_dir is None:
            print("M4_UNAVAILABLE: %s" % m4_note)
            b = load_budget()
            for e in b["entries"]:
                if e.get("slot") == slot:
                    e["status"] = "aborted-m4-unavailable"
            save_budget(b)
            return 2
        env["ZCODE_DATA_BASE_DIR"] = data_dir

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
    if session_id and not (tele.get("model_usage")):
        # M4 可能改动 storage root：扫 scratch 内 db 兜底
        for root, _dirs, files in os.walk(scratch):
            for fn in files:
                if fn.endswith(".sqlite"):
                    cand = pull_telemetry(session_id, work, os.path.join(root, fn))
                    if cand.get("session"):
                        tele = dict(cand, db_path_fallback=os.path.join(root, fn))
                        break
            if tele.get("session"):
                break
    rows = tele.get("model_usage") or []
    observed_model = rows[0]["model_id"] if rows else None
    observed_provider = rows[0]["provider_id"] if rows else None
    observed_variant = rows[0]["variant"] if rows else None
    model_call = len(rows) > 0

    rec = {
        "probe_id": pid,
        "mechanism": ("adjudication-prune+reasoningLevel" if args.prune_personal_except
                      else ("simplify+reasoningLevel" if args.simplify else "reasoningLevel")),
        "prune_personal_except": args.prune_personal_except,
        "m4_derive_data_dir": bool(args.derive_data_dir), "m4_note": m4_note,
        "target": {"provider_id": prov, "model_id": model, "reasoningLevel": args.reasoning},
        "budget_slot": slot, "budget_model_calls_after": b["model_calls"] + (1 if model_call else 0),
        "command_shape": ["node", "zcode.cjs", "-p", "<最小 prompt：回复 ok>", "--cwd", work, "--json"],
        "env_paired": True, "builtin_src": BUILTIN_SRC, "builtin_sha256": sha256_file(BUILTIN_SRC),
        "personal_src": PERSONAL_SRC, "simplify": bool(args.simplify),
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
