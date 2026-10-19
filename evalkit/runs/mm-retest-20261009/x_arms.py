#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/x_arms.py — mm 重测臂批编排器（照 office-retest-20261009/x_arms.py 机制移植）。

范围（登记文件 round-plan.json/budget.json 为准）：
  meeting-minutes-skill 8 任务（merged/mm/t01..t08）× 2 臂 × n=3 = 48 臂调用上限（ask 刚性）。
  任务级 1-based 序号奇偶轮换按族分配：奇=glm（t01/t03/t05/t07，24 调用）、偶=minimax（t02/t04/t06/t08，24）。
  treatment 挂 dist/meeting-minutes-skill 的可交付面过滤副本（MOUNTABLE=
  SKILL.md/references/scripts/requirements.txt；禁 reference/（含 reference/out 参照产物=oracle 面）、
  eval/、EVALUATION.md 进臂——「任何臂不得带参照物」；canonical 源与 dist 包零改动）。
钉版照 sf0006-b-smoke-2/office-retest 实测：glm=M4（ZCODE_DATA_BASE_DIR 派生+identity 注入）
  @GLM-5.3/max、minimax=M2（进程级成对 env）@Minimax-M3.1-Flash-Preview/enabled；
  两臂 prompt 逐字同；glm 落点漂移 → redline 停全批。
预算：budget.json 台账态（spawn 前 pending、事后 db join 回填；只增不改历史行）；
  每臂 rate_limited 退避重试 ≤1，重试进程不占 48 正式额度、逐条留痕；超额进程不计入结果。
D2 纪律：唯一新工作目录（本 run 树 + /tmp/mm-retest-20261009-pin-scratch，不复用历史轮）。
任务书：packs/ 由 build_packs.py 预先构建（本脚本只校验在位），brief.md 两臂逐字同。

用法：
  python x_arms.py prep      # 零模型：过滤资产+单元树+隔离断言+全局sha开工快照+freeze verify
  python x_arms.py canary    # 金丝雀：仅 glm 首个任务 rep1（2 个正式臂调用）
  python x_arms.py run       # 余量全批（幂等续跑：已有权威 records 的臂跳过）
  python x_arms.py close     # 收工：freeze verify + 全局 sha 收工比对（零模型）
退出码：0 成功 / 1 有臂级失败或断言红 / 2 用法或装置错误。
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
EVALKIT = os.path.join(ROOT, "evalkit")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
CRED_SRC = os.path.expanduser("~/.zcode/v2/credentials.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
GLOBAL_SHA_FILES = [os.path.expanduser("~/.zcode/cli/config.json"),
                    os.path.expanduser("~/.zcode/v2/provider_config.json"),
                    os.path.expanduser("~/.zcode/v2/credentials.json")]
SCRATCH = "/tmp/mm-retest-20261009-pin-scratch"       # D2 纪律：唯一新 scratch

PKG_DIST = "meeting-minutes-skill"
N_REPS = 3
TASK_ORDER = ["t0%d" % i for i in range(1, 9)]
MOUNTABLE = ["SKILL.md", "references", "scripts", "requirements.txt"]
FAMILIES = ["glm", "minimax"]
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800}
TARGET = {
    "glm": {"provider": "account:bigmodel-individual-coding-plan", "model": "GLM-5.3",
            "reasoning": "max"},
    "minimax": {"provider": "minimax", "model": "Minimax-M3.1-Flash-Preview",
                "reasoning": "enabled"},
}
CAP_ARMS = 48
RETRY_CAP_PER_ARM = 1
ENV_PROVIDER_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
                     "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
                     "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")
PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")

LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
STOP = threading.Event()
THREAD_ERROR = {"glm": None, "minimax": None}
PROGRESS = os.path.join(RUN, "progress.log")
QUEUE = {"items": [], "idx": 0}
SCRATCH_ENV = {}
BUDGET_LOCK = threading.Lock()


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    with LOG_LOCK:
        with open(PROGRESS, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    print(line, flush=True)


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


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_arm = load_mod("run_arm", os.path.join(EVALKIT, "harness", "run_arm.py"))
pull_telemetry = run_arm.pull_telemetry
make_arms = load_mod("make_arms", os.path.join(EVALKIT, "harness", "make_arms.py"))
classify_mod = load_mod("classify", os.path.join(EVALKIT, "evaluators", "classify.py"))


def plan_allocation():
    """任务级 1-based 序号奇偶轮换（奇=glm、偶=minimax）；同一任务两臂与全部重复同族
    （EVAL-SPEC §4.2 双臂同模型）。序=TASK_ORDER（merged/mm t01..t08）。"""
    fam_of = {}
    for i, t in enumerate(TASK_ORDER, 1):
        fam_of[("meeting-minutes", t)] = "glm" if i % 2 == 1 else "minimax"
    return {"rule": "8 任务 1-based 序号奇偶轮换（奇=glm、偶=minimax），序=TASK_ORDER"
                    "（merged/mm t01..t08）"}, fam_of


def tasks_of():
    return list(TASK_ORDER)


def check_packs():
    made = []
    for tid in tasks_of():
        pd = os.path.join(RUN, "packs", "meeting-minutes-%s" % tid)
        if not os.path.isfile(os.path.join(pd, "brief.md")):
            raise RuntimeError("pack 缺 brief.md（先跑 build_packs.py）: %s" % pd)
        made.append(pd)
    return made


def build_filtered_assets():
    """dist 顶层包 → 可交付面过滤副本（MOUNTABLE 白名单）；源零改动，登记清单与 sha256。"""
    manifest = {}
    src = os.path.join(ROOT, "dist", PKG_DIST)
    dst = os.path.join(RUN, "assets", PKG_DIST)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    files = []
    for item in MOUNTABLE:
        s = os.path.join(src, item)
        if not os.path.exists(s):
            raise RuntimeError("dist 包缺可挂载面 %s: %s" % (item, s))
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
            for dp, _dn, fns in os.walk(d):
                for fn in fns:
                    files.append(os.path.relpath(os.path.join(dp, fn), dst))
        else:
            shutil.copyfile(s, d)
            files.append(item)
    files.sort()
    manifest[PKG_DIST] = {
        "source": os.path.relpath(src, ROOT),
        "source_note": "dist 包（owner 批准点状态；本轮零改动，开工 sha256 快照见 precheck/）",
        "source_untouched": True,
        "filter_whitelist": MOUNTABLE,
        "excluded": ["reference", "eval", "EVALUATION.md", "CHANGELOG.md",
                     "README.md", "MANIFEST.md", "LICENSE"],
        "files": files,
        "file_sha256": {f: sha256_file(os.path.join(dst, f)) for f in files},
    }
    write_json(os.path.join(RUN, "records", "mount-manifest.json"), manifest)
    return manifest


def mount_name(pkg=None):
    """treatment 臂内技能挂载名 = SKILL.md frontmatter name（make_arms skill_name_of 口径）。"""
    sk = os.path.join(RUN, "assets", PKG_DIST, "SKILL.md")
    m = re.search(r"^name:\s*(\S+)", open(sk, encoding="utf-8").read(), re.M)
    return m.group(1) if m else PKG_DIST


def unit_dir(fam, task, rep):
    return os.path.join(RUN, fam, "meeting-minutes-%s-rep%d" % (task, rep))


def arm_dir_of(fam, task, rep, arm):
    return os.path.join(unit_dir(fam, task, rep), arm)


# ---------------------------------------------------------------- M2/M4 scratch（照 office-retest）
def derive_personal(fam_scratch, family):
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
    creds[ident_key] = account_identity
    v2 = os.path.join(fam_scratch, "zcode-data", ".zcode", "v2")
    os.makedirs(v2, exist_ok=True)
    path = os.path.join(v2, "credentials.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(path, 0o600)
    note = ("注入明文 identity 条目 %s（值=<%d chars>）；其余 %d 条原样拷贝"
            % (ident_key, len(account_identity), len(creds) - 1))
    return os.path.join(fam_scratch, "zcode-data"), note


def build_family_scratch(family):
    fam_scratch = os.path.join(SCRATCH, family)
    os.makedirs(fam_scratch, exist_ok=True)
    builtin_path = os.path.join(fam_scratch, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)
    personal_path = derive_personal(fam_scratch, family)
    extra_env = {"ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": builtin_path,
                 "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": personal_path}
    m4_note = None
    if TARGET[family]["provider"] == "account:bigmodel-individual-coding-plan":
        data_dir, m4_note = derive_data_dir(fam_scratch, family)
        if data_dir is None:
            raise RuntimeError("M4 不可行: " + m4_note)
        extra_env["ZCODE_DATA_BASE_DIR"] = data_dir
    return {"extra_env": extra_env, "m4_note": m4_note}


# ---------------------------------------------------------------- run（照 office-retest 机制）
def looks_rate_limited(text, tele):
    for r in (tele.get("model_usage") or []):
        if "rate_limited" in str(r.get("status") or ""):
            return True
    return bool(re.search(r"rate[_ ]?limit", text, re.I))


def dominant_row(rows):
    return sorted(rows, key=lambda r: (r.get("n") or 0), reverse=True)[0] if rows else None


def run_once(arm_dir, family):
    arm_dir = os.path.abspath(arm_dir)
    timeout = FAMILY_TIMEOUT[family]
    cmd = [shutil.which("node") or "/home/pan-ding/.local/bin/node",
           "/opt/ZCode/resources/glm/zcode.cjs", "-p", PROMPT,
           "--cwd", arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    for k in ENV_PROVIDER_KEYS:
        env.pop(k, None)
    env.pop("ZCODE_DATA_BASE_DIR", None)
    env.update(SCRATCH_ENV[family])
    t0 = time.time()
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
    time.sleep(2)
    tele = pull_telemetry(DB, session_id, arm_dir)
    if session_id and not (tele.get("model_usage") or []):
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
        "family": family, "arm": os.path.basename(arm_dir),
        "mechanism": "m4" if family == "glm" else "m2",
        "command_shape": ["node", "zcode.cjs", "-p", "<PROMPT 逐字同 run_arm.py>", "--cwd",
                          arm_dir, "--json"],
        "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": int(t0 * 1000), "session_id": session_id,
        "directory_matches_arm": tele.get("directory_matches_arm"),
        "session_directory": (tele.get("session") or {}).get("directory"),
        "db_source": "global" if not tele.get("db_path_fallback") else "scratch-fallback",
        "model_id_observed": dom.get("model_id") if dom else None,
        "provider_id_observed": dom.get("provider_id") if dom else None,
        "variant_observed": dom.get("variant") if dom else None,
        "model_usage_rows": len(rows), "model_usage": rows,
        "input_tokens": sum((r.get("it") or 0) for r in rows),
        "output_tokens": sum((r.get("ot") or 0) for r in rows),
        "stdout_bytes": len(out), "stderr_bytes": len(err),
        "stderr_head": errtext[:2000], "stdout_tail": text[-1500:],
        "_raw_stdout": text, "_raw_stderr": errtext,
    }


def budget_append(entry):
    with BUDGET_LOCK:
        p = os.path.join(RUN, "budget.json")
        b = json.load(open(p, encoding="utf-8"))
        b.setdefault("ledger_entries", [])
        entry["slot"] = len(b["ledger_entries"]) + 1
        b["ledger_entries"].append(entry)
        if entry.get("kind") == "arm" and entry.get("status") == "pending":
            b["arm_calls"]["counted_so_far"] = b["arm_calls"].get("counted_so_far", 0) + 1
        if entry.get("kind") == "rate_limited-retry":
            b["retry_policy"]["used"] = b["retry_policy"].get("used", 0) + 1
        write_json(p, b)
        return entry["slot"]


def budget_reserved_arms():
    """占位即计数（pending+done+no-model-call）：防并发超预算。装置 bug/无效尝试条目不占额度。"""
    p = os.path.join(RUN, "budget.json")
    b = json.load(open(p, encoding="utf-8"))
    return sum(1 for e in b.get("ledger_entries", [])
               if e.get("kind") == "arm"
               and e.get("status") in ("pending", "done", "no-model-call"))


def budget_update(slot, **kw):
    with BUDGET_LOCK:
        p = os.path.join(RUN, "budget.json")
        b = json.load(open(p, encoding="utf-8"))
        for e in b["ledger_entries"]:
            if e.get("slot") == slot:
                e.update(kw)
                break
        write_json(p, b)


def persist_arm(fam, task, rep, arm, rec, asset_dist):
    ad = arm_dir_of(fam, task, rep, arm)
    rec_dir = os.path.join(ad, "records")
    pin = {
        "arm": arm, "run_label": "rep%d" % rep, "run_id": "mm-retest-20261009",
        "model_id": rec["model_id_observed"] or "UNOBSERVED",
        "provider_base_url": rec["provider_id_observed"] or "UNOBSERVED",
        "cli_runtime": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9",
        "date": time.strftime("%Y-%m-%d"),
        "reasoning_variant": rec["variant_observed"]
                             or ("max" if fam == "glm" else "enabled"),
        "asset_mount": (os.path.join(ad, ".zcode", "skills", mount_name())
                        if arm == "treatment" else None),
        "family": fam, "mechanism": rec["mechanism"],
        "pkg": "meeting-minutes", "task": task, "rep": rep,
        "note": ("mm 重测实测钉版：model_id/provider_base_url 抄 db model_usage join 落点"
                 "（逐字大小写敏感）；机制 glm=M4、minimax=M2（照 sf0006-b-smoke-2/sf0008-k5b/"
                 "office-retest）"),
    }
    write_json(os.path.join(rec_dir, "model_pin.json"), pin)
    arm_run = {k: v for k, v in rec.items() if not k.startswith("_")}
    write_json(os.path.join(rec_dir, "arm_run.json"), arm_run)
    write_json(os.path.join(rec_dir, "telemetry.json"),
               {"available": True, "session_id": rec["session_id"],
                "session": {"directory": rec["session_directory"]},
                "directory_matches_arm": rec["directory_matches_arm"],
                "db_source": rec["db_source"], "model_usage": rec["model_usage"]})
    stripped = rec["_raw_stdout"].lstrip()
    sname = "transcript_stdout.json" if stripped.startswith("{") else "transcript_stdout.cli-error.txt"
    with open(os.path.join(rec_dir, sname), "w", encoding="utf-8", newline="\n") as f:
        f.write(rec["_raw_stdout"])
    with open(os.path.join(rec_dir, "transcript_stderr.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(rec["_raw_stderr"])
    return pin


def classify_arm(rec, retried):
    events = []
    if rec["timed_out"]:
        events.append({"kind": "arm_timeout", "detail": "wall_ms=%d" % rec["wall_ms"]})
    elif rec["session_id"] is None and rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "no session / no model_usage"})
    elif rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "session without model_usage"})
    if retried:
        events.append({"kind": "rate_limited", "detail": "退避重试 1 次后重跑"})
    r = classify_mod.classify_run(events, arm_id=rec["arm"])
    return {"bucket": r["arm_verdict"],
            "buckets_detail": [b["bucket"] for b in r["buckets"]] or ["measured_failure"],
            "classify_module": "evalkit/evaluators/classify.py classify_run（装置原函数实跑）",
            "events_in": events}


def family_worker(fam, fam_queue, redline):
    try:
        _family_worker(fam, fam_queue, redline)
    except Exception as exc:
        import traceback
        THREAD_ERROR[fam] = traceback.format_exc()[-1500:]
        log("WORKER CRASH %s: %s" % (fam, exc))
        STOP.set()


def _family_worker(fam, fam_queue, redline):
    for (task, rep) in fam_queue:
        if STOP.is_set():
            return
        for arm in ("baseline", "treatment"):
            if STOP.is_set():
                return
            if os.path.isfile(os.path.join(arm_dir_of(fam, task, rep, arm), "records",
                                           "arm_run.json")):
                log("SKIP 已完成臂 %s/meeting-minutes-%s-rep%d/%s" % (fam, task, rep, arm))
                continue
            with LOCK:
                if budget_reserved_arms() >= CAP_ARMS or STOP.is_set():
                    STOP.set()
                    return
                slot = budget_append({"arm": "%s/meeting-minutes-%s-rep%d/%s" % (fam, task, rep, arm),
                                      "kind": "arm", "pkg": "meeting-minutes", "task": task,
                                      "family": fam, "rep": rep,
                                      "ts_intent": time.strftime("%H:%M:%S"), "status": "pending"})
            ad = arm_dir_of(fam, task, rep, arm)
            rec = None
            try:
                rec = run_once(ad, fam)
            except Exception as exc:   # 装置级异常：如实标 failed，不留悬置 pending
                import traceback
                budget_update(slot, status="failed_harness_exception",
                              error=type(exc).__name__ + ":" + str(exc)[:200])
                write_json(os.path.join(RUN, "attempts",
                                        "%s-meeting-minutes-%s-rep%d-%s.harness-exception.json"
                                        % (fam, task, rep, arm)),
                           {"error": traceback.format_exc()[-2000:]})
                STOP.set()
                return
            retried = False
            failed = (rec["exit_code"] != 0 or rec["timed_out"]
                      or not rec["session_id"] or rec["model_usage_rows"] == 0)
            rl = failed and looks_rate_limited(rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            if rl and RETRY_CAP_PER_ARM >= 1:
                att1 = {k: v for k, v in rec.items() if not k.startswith("_")}
                att1["attempt"] = 1
                write_json(os.path.join(RUN, "attempts",
                                        "%s-meeting-minutes-%s-rep%d-%s.attempt1.json"
                                        % (fam, task, rep, arm)), att1)
                log("rate_limited 退避 30s 后重试 1 次：%s/meeting-minutes-%s-rep%d/%s"
                    % (fam, task, rep, arm))
                time.sleep(30)
                rslot = budget_append({"arm": "%s/meeting-minutes-%s-rep%d/%s"
                                               % (fam, task, rep, arm),
                                       "kind": "rate_limited-retry", "pkg": "meeting-minutes",
                                       "task": task, "family": fam, "rep": rep,
                                       "ts_intent": time.strftime("%H:%M:%S"), "status": "pending"})
                rec = run_once(ad, fam)
                rec["attempt"] = 2
                rec["rate_limited_retry"] = True
                retried = True
                budget_update(rslot, status="done" if rec["model_usage_rows"] else "no-model-call",
                              exit_code=rec["exit_code"], session_id=rec["session_id"])
            pin = persist_arm(fam, task, rep, arm, rec, PKG_DIST)
            observed = rec["model_usage_rows"] > 0
            t = TARGET[fam]
            pin_ok = (rec["model_id_observed"] == t["model"]
                      and rec["provider_id_observed"] == t["provider"])
            summary = {k: v for k, v in rec.items() if not k.startswith("_")}
            summary.update({"pin_verdict": "pass" if pin_ok else "drift" if observed else "unobserved",
                            "attempted": True, "retried": retried,
                            "classify": classify_arm(rec, retried),
                            "pkg": "meeting-minutes", "task": task, "rep": rep, "slot": slot})
            write_json(os.path.join(RUN, "records", "arms",
                                    "%s-meeting-minutes-%s-rep%d-%s.json" % (fam, task, rep, arm)),
                       summary)
            budget_update(slot, status="done" if observed else "no-model-call",
                          exit_code=rec["exit_code"], session_id=rec["session_id"],
                          observed={"model_id": rec["model_id_observed"],
                                    "provider_id": rec["provider_id_observed"],
                                    "variant": rec["variant_observed"]},
                          pin_verdict=summary["pin_verdict"])
            if fam == "glm" and observed and not pin_ok:
                redline["event"] = True
                redline["detail"] = ("glm 臂落点漂移（红线）：observed %s @ %s ≠ %s @ %s，停全批"
                                     % (rec["model_id_observed"], rec["provider_id_observed"],
                                        t["model"], t["provider"]))
                STOP.set()
                return
            log("ARM done %s/meeting-minutes-%s-rep%d/%s exit=%d tokens=%d+%d pin=%s"
                % (fam, task, rep, arm, rec["exit_code"], rec["input_tokens"],
                   rec["output_tokens"], summary["pin_verdict"]))


def budget_counted():
    p = os.path.join(RUN, "budget.json")
    b = json.load(open(p, encoding="utf-8"))
    return sum(1 for e in b.get("ledger_entries", [])
               if e.get("kind") == "arm" and e.get("status") in ("done", "no-model-call"))


def global_sha(tag):
    lines = ["# mm-retest-20261009 全局配置 sha256（%s，%s）"
             % (tag, time.strftime("%Y-%m-%dT%H:%M:%S%z"))]
    for p in GLOBAL_SHA_FILES:
        lines.append("%s  %s" % (sha256_file(p), p))
    with open(os.path.join(RUN, "precheck", "global-sha-%s.txt" % tag), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- stages
def stage_prep():
    fails = []
    alloc, fam_of = plan_allocation()
    global_sha("opening")
    fr = subprocess.run([sys.executable, os.path.join(EVALKIT, "harness", "freeze_device.py"),
                         "verify", "--evalkit", EVALKIT], capture_output=True)
    with open(os.path.join(RUN, "precheck", "freeze-verify-opening.out"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("exit=%d\n%s" % (fr.returncode, fr.stdout.decode("utf-8", "replace")))
    if fr.returncode != 0:
        fails.append("freeze verify 开工非 0")
    # dist 包零改动快照（canonical 源 sha256 开工留痕）
    dist_files = {}
    for dp, _dn, fns in os.walk(os.path.join(ROOT, "dist", PKG_DIST)):
        for fn in fns:
            p = os.path.join(dp, fn)
            dist_files[os.path.relpath(p, os.path.join(ROOT, "dist"))] = sha256_file(p)
    write_json(os.path.join(RUN, "precheck", "dist-opening-sha256.json"),
               {"pkg": PKG_DIST, "files": dist_files})
    build_filtered_assets()
    packs = check_packs()
    log("packs: %d（build_packs.py 预构建，本步校验在位）" % len(packs))

    # 单元树（make_arms：fixtures+brief 两臂同、treatment 挂 .zcode/skills/<name>）；幂等：已有单元只验证
    units = 0
    asset = os.path.join(RUN, "assets", PKG_DIST)
    for tid in tasks_of():
        fam = fam_of[("meeting-minutes", tid)]
        for rep in range(1, N_REPS + 1):
            ud = unit_dir(fam, tid, rep)
            if os.path.isdir(ud):
                units += 1
                continue
            rc = make_arms.main(["--pack", os.path.join(RUN, "packs", "meeting-minutes-%s" % tid),
                                 "--run-id", "%s/meeting-minutes-%s-rep%d" % (fam, tid, rep),
                                 "--asset-skill", asset, "--out", RUN])
            if rc != 0:
                fails.append("make_arms %s-rep%d exit=%d" % (tid, rep, rc))
                continue
            units += 1
            # 隔离断言（照 sf0008-k5b/office-retest stage_prep）：任何臂树禁 reference|oracle；
            # baseline 禁 .zcode；brief.md 两臂逐字同；treatment 必有技能挂载
            for arm in ("baseline", "treatment"):
                ad = arm_dir_of(fam, tid, rep, arm)
                for ban in ("reference", "oracle"):
                    for dp, dns, _fns in os.walk(ad):
                        if os.path.basename(dp) == ban:
                            fails.append("臂含 %s/: %s" % (ban, dp))
                if not os.path.isfile(os.path.join(ad, "brief.md")):
                    fails.append("臂缺 brief.md: %s" % ad)
                # 判分器/参照面文件不进臂（runner/golden/rubric/judge-notes/oracle）
                for dp, _dns, fns in os.walk(ad):
                    for fn in fns:
                        if fn in ("runner.py", "golden.json", "rubric.md", "judge-notes.md"):
                            fails.append("臂含判分器/参照面文件 %s: %s" % (fn, dp))
            b1 = os.path.join(arm_dir_of(fam, tid, rep, "baseline"), "brief.md")
            b2 = os.path.join(arm_dir_of(fam, tid, rep, "treatment"), "brief.md")
            if sha256_file(b1) != sha256_file(b2):
                fails.append("两臂 brief.md 不同: %s-rep%d" % (tid, rep))
            if os.path.isdir(os.path.join(arm_dir_of(fam, tid, rep, "baseline"), ".zcode")):
                fails.append("baseline 臂含 .zcode: %s-rep%d" % (tid, rep))
            if not os.path.isdir(os.path.join(arm_dir_of(fam, tid, rep, "treatment"),
                                              ".zcode", "skills", mount_name())):
                fails.append("treatment 臂缺技能挂载: %s-rep%d" % (tid, rep))
    if fails:
        print("PREP FAIL:\n" + "\n".join(fails), file=sys.stderr)
        write_json(os.path.join(RUN, "records", "prep-fails.json"), {"fails": fails})
        return 1
    n_units = len(tasks_of()) * N_REPS
    fam_tasks = {f: [t for t in tasks_of() if fam_of[("meeting-minutes", t)] == f]
                 for f in FAMILIES}
    write_json(os.path.join(RUN, "records", "prep-summary.json"),
               {"units": n_units, "arm_calls_planned": 2 * n_units,
                "cap_arms": CAP_ARMS, "allocation": {"task_order": TASK_ORDER,
                                                     "glm_tasks": fam_tasks["glm"],
                                                     "minimax_tasks": fam_tasks["minimax"],
                                                     "by_family": {"glm": len(fam_tasks["glm"]) * 2 * N_REPS,
                                                                   "minimax": len(fam_tasks["minimax"]) * 2 * N_REPS}},
                "mountable": MOUNTABLE,
                "opened_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    log("PREP 完成：%d 单元（%d 臂目录），隔离断言全过" % (n_units, 2 * n_units))
    return 0


def build_queue(fam_of, only_canary=False):
    q = {"glm": [], "minimax": []}
    for tid in tasks_of():
        fam = fam_of[("meeting-minutes", tid)]
        for rep in range(1, N_REPS + 1):
            q[fam].append((tid, rep))
    if only_canary:
        q = {"glm": [q["glm"][0]], "minimax": []}
    return q


def stage_run(only_canary=False):
    global SCRATCH_ENV
    alloc, fam_of = plan_allocation()
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    for fam in FAMILIES:
        SCRATCH_ENV[fam] = build_family_scratch(fam)["extra_env"]
    write_json(os.path.join(RUN, "records", "scratch-env-names.json"),
               {f: sorted(SCRATCH_ENV[f].keys()) for f in FAMILIES})
    q = build_queue(fam_of, only_canary)
    redline = {"event": False, "detail": None}
    th = threading.Thread(target=family_worker, args=("glm", q["glm"], redline))
    th2 = threading.Thread(target=family_worker, args=("minimax", q["minimax"], redline))
    th.start(); th2.start(); th.join(); th2.join()
    write_json(os.path.join(RUN, "records", "run-stage-summary.json"),
               {"redline_event": redline["event"], "redline_detail": redline["detail"],
                "thread_errors": {k: v for k, v in THREAD_ERROR.items() if v},
                "counted_arms": budget_counted(),
                "closed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "canary": only_canary})
    log("RUN 阶段结束：counted=%d redline=%s thread_error=%s"
        % (budget_counted(), redline["event"], [k for k, v in THREAD_ERROR.items() if v]))
    if redline["event"] or any(THREAD_ERROR.values()):
        return 1
    return 0


def stage_close():
    r = subprocess.run([sys.executable, os.path.join(EVALKIT, "harness", "freeze_device.py"),
                        "verify", "--evalkit", EVALKIT], capture_output=True)
    with open(os.path.join(RUN, "precheck", "freeze-verify-closing.out"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("exit=%d\n%s" % (r.returncode, r.stdout.decode("utf-8", "replace")))
    log("freeze verify closing exit=%d" % r.returncode)
    global_sha("closing")
    a = open(os.path.join(RUN, "precheck", "global-sha-opening.txt"), encoding="utf-8").read()
    b = open(os.path.join(RUN, "precheck", "global-sha-closing.txt"), encoding="utf-8").read()
    same = all(l.split("  ")[0] in b for l in a.splitlines() if "  " in l)
    log("全局配置 sha 开工/收工逐字节一致=%s" % same)
    write_json(os.path.join(RUN, "precheck", "b03-global-sha-equal.json"),
               {"byte_identical": bool(same)})
    # 任务集冻结收工复算（goldens/pool-state 签署不动证明）
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    ok = live == "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6"
    write_json(os.path.join(RUN, "precheck", "taskset-closing-verify.json"),
               {"live": live, "match": bool(ok)})
    log("任务集冻结收工复算 %s（%s）" % ("PASS" if ok else "FAIL", live[:16]))
    # dist 包收工零改动对拍
    op = os.path.join(RUN, "precheck", "dist-opening-sha256.json")
    opening = json.load(open(op, encoding="utf-8"))["files"]
    drift = []
    for rel, h in opening.items():
        p = os.path.join(ROOT, "dist", rel)
        if not os.path.isfile(p) or sha256_file(p) != h:
            drift.append(rel)
    write_json(os.path.join(RUN, "precheck", "dist-closing-verify.json"),
               {"drift": drift, "untouched": not drift})
    log("dist 包收工零改动=%s（drift=%d）" % (not drift, len(drift)))
    return 0 if (r.returncode == 0 and same and ok and not drift) else 1


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("prep", "canary", "run", "close"):
        print(__doc__, file=sys.stderr)
        return 2
    os.makedirs(os.path.join(RUN, "records"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "records", "arms"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "attempts"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "precheck"), exist_ok=True)
    return {"prep": stage_prep, "canary": lambda: stage_run(True),
            "run": lambda: stage_run(False), "close": stage_close}[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
