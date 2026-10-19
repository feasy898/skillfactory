#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/x_judge_lib.py — mm 重测裁判通道库（移植 office-retest-20261009/x_judge_lib.py）。

三族面板（round-plan.judging.panel）：
  step     step-router-v1 @ new-provider：OpenAI 兼容 chat/completions 直调（模型 API，
           不经 headless 臂——owner 指令）。endpoint/apiKey 运行时从全局 provider 配置
           读入内存，零落盘、零回显、全局配置零修改。不用 assistant-prefill（D2 教训）。
  glm      GLM-5.3 @ account:bigmodel-individual-coding-plan：headless M4
  minimax  Minimax-M3.1-Flash-Preview @ minimax：headless M2
每次调用前在 budget.json 记 pending（kind=judge），事后回填 tokens/exit/verdict。
盲态纪律：裁判对两臂来源与顺序不知情；产物匿名化+混洗；rubric 判分必附实测证据。
"""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
CRED_SRC = os.path.expanduser("~/.zcode/v2/credentials.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
SCRATCH = "/tmp/mm-retest-20261009-judge-scratch"      # D2 纪律：唯一新 scratch，不复用历史轮
JUDGE_PROMPT_VERSION = "S8-JUDGE-v2-MMRETEST-1"
TARGET = {
    "glm": {"provider": "account:bigmodel-individual-coding-plan", "model": "GLM-5.3",
            "reasoning": "max"},
    "minimax": {"provider": "minimax", "model": "Minimax-M3.1-Flash-Preview",
                "reasoning": "enabled"},
}
ENV_PROVIDER_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
                     "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
                     "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")
JUDGE_PROMPT = ("Read the file brief.md in the current working directory and complete the "
                "judging task it describes exactly. Write the required verdict.json in the "
                "current working directory. Do not ask questions.")
FAMILY_TIMEOUT = {"glm": 1800, "minimax": 1200}
HTTP_TIMEOUT = 900

_SCRATCH_ENV = {}


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_mod(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pull_telemetry = load_mod("run_arm", os.path.join(ROOT, "evalkit/harness/run_arm.py")).pull_telemetry


def budget_judge(entry):
    """记账：append 后返回 slot；entry 含 judge/model/task/kind=judge/status。"""
    p = os.path.join(RUN, "budget.json")
    with open(p, encoding="utf-8") as f:
        b = json.load(f)
    b.setdefault("ledger_entries", [])
    entry["slot"] = len(b["ledger_entries"]) + 1
    entry.setdefault("kind", "judge")
    b["ledger_entries"].append(entry)
    if entry["status"] == "pending":
        b["judge_calls"] = b.get("judge_calls", {})
        b["judge_calls"]["used_so_far"] = b["judge_calls"].get("used_so_far", 0) + 1
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return entry["slot"]


def budget_judge_update(slot, **kw):
    p = os.path.join(RUN, "budget.json")
    with open(p, encoding="utf-8") as f:
        b = json.load(f)
    for e in b.get("ledger_entries", []):
        if e.get("slot") == slot:
            e.update(kw)
            break
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- step（模型 API 直调）
def _step_endpoint():
    """从全局 provider 配置读 new-provider 的 baseUrl 与 apiKey（仅内存，零落盘零回显）。"""
    with open(PERSONAL_SRC, encoding="utf-8") as f:
        pc = json.load(f)
    for r in pc["config"]["providerConfigRules"]["providerRules"]:
        if r.get("providerId") == "new-provider":
            cfg = r["config"]
            return cfg["api"]["baseUrl"], cfg["access"]["apiKey"]
    raise RuntimeError("provider_config 无 new-provider 规则，step 裁判通道不可用")


def step_chat(messages, max_tokens=8000, temperature=0.2):
    """step 通道：无 assistant-prefill（office D2 教训：prefill 续写产生双层嵌套 JSON）。"""
    base, key = _step_endpoint()
    body = json.dumps({"model": "step-router-v1", "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature}).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    wall_ms = int((time.time() - t0) * 1000)
    u = data.get("usage") or {}
    msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
    txt = msg.get("content") or ""
    if not txt.strip():
        txt = msg.get("reasoning_content") or msg.get("reasoning") or ""
    return {"text": txt, "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "total_tokens": u.get("total_tokens"), "wall_ms": wall_ms,
            "model": data.get("model"), "id": data.get("id"),
            "finish": ((data.get("choices") or [{}])[0].get("finish_reason"))}


# ---------------------------------------------------------------- glm/minimax（headless M4/M2）
def _derive_personal(fam_scratch, family):
    t = TARGET[family]
    with open(PERSONAL_SRC, encoding="utf-8") as f:
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


def _derive_data_dir(fam_scratch, family):
    t = TARGET[family]
    with open(CRED_SRC, encoding="utf-8") as f:
        creds = json.load(f)
    ident_key = "account-provider:%s:identity" % t["provider"]
    if ident_key in creds:
        return None, "identity 已存在，M4 短路"
    api_keys = [k for k in creds
                if k.startswith("account-provider:coding-plan:%s:account:" % t["provider"])
                and k.endswith(":api-key")]
    if not api_keys:
        raise RuntimeError("M4 不可行：无 api-key 条目")
    account_identity = api_keys[0].split(":account:")[-1][:-len(":api-key")]
    creds[ident_key] = account_identity
    v2 = os.path.join(fam_scratch, "zcode-data", ".zcode", "v2")
    os.makedirs(v2, exist_ok=True)
    path = os.path.join(v2, "credentials.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(path, 0o600)
    return os.path.join(fam_scratch, "zcode-data"), "注入 identity（%d chars）" % len(account_identity)


def ensure_cli_scratch():
    if _SCRATCH_ENV:
        return
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    for family in ("glm", "minimax"):
        fam_scratch = os.path.join(SCRATCH, family)
        os.makedirs(fam_scratch, exist_ok=True)
        builtin_path = os.path.join(fam_scratch, "zcode-builtin.json")
        shutil.copyfile(BUILTIN_SRC, builtin_path)
        personal_path = _derive_personal(fam_scratch, family)
        extra = {"ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": builtin_path,
                 "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": personal_path}
        if TARGET[family]["provider"].startswith("account:"):
            data_dir, _note = _derive_data_dir(fam_scratch, family)
            if data_dir:
                extra["ZCODE_DATA_BASE_DIR"] = data_dir
        _SCRATCH_ENV[family] = extra


def cli_judge(workdir, family):
    """headless 裁判会话：返回 rec（同 run_once 形状）。"""
    ensure_cli_scratch()
    import sys as _sys
    _sys.path.insert(0, os.path.join(ROOT, "evalkit", "harness"))
    arm_dir = os.path.abspath(workdir)
    cmd = [shutil.which("node") or "/home/pan-ding/.local/bin/node",
           "/opt/ZCode/resources/glm/zcode.cjs", "-p", JUDGE_PROMPT,
           "--cwd", arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    for k in ENV_PROVIDER_KEYS:
        env.pop(k, None)
    env.pop("ZCODE_DATA_BASE_DIR", None)
    env.update(_SCRATCH_ENV[family])
    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=FAMILY_TIMEOUT[family],
                              env=env, shell=False, cwd=arm_dir)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)
    text = out.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None
    time.sleep(2)
    tele = pull_telemetry(DB, session_id, arm_dir)
    rows = tele.get("model_usage") or []
    dom = sorted(rows, key=lambda r: (r.get("n") or 0), reverse=True)[0] if rows else None
    return {"exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
            "session_id": session_id, "model_usage_rows": len(rows),
            "model_id_observed": dom.get("model_id") if dom else None,
            "provider_id_observed": dom.get("provider_id") if dom else None,
            "variant_observed": dom.get("variant") if dom else None,
            "input_tokens": sum((r.get("it") or 0) for r in rows),
            "output_tokens": sum((r.get("ot") or 0) for r in rows),
            "_raw_stdout": text, "_raw_stderr": err.decode("utf-8", errors="replace")}
