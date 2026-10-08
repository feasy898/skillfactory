#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0006-c/c_orchestrator.py — SF-0006 C 层基线轮编排器（随卡证据，不在 freeze 钉版面）。

范围（卡面）：ready 5 题（pool-state 为准）× 2 族 × 2 臂 × 2 rep = 40 单元（臂进程）。
钉版机制照抄 B 层第 2 轮（runs/sf0006-b-smoke-2/b2_orchestrator.py，layers.B=passed）：
glm=M4、minimax=M2，options.reasoningLevel 不可省（runtime 0.16.9 质量门）。

阶段：
  prep  零模型：全局配置 sha 快照（B-03）+ freeze verify 开工快照（A-04 跑批期不漂移基准）
        + 10 棵 oracle 树生成与 A-14 哈希登记 + 40 单元建树（make_arms，treatment 挂
        dist/build/standard 合规变体）+ A-13 输入互异/同 rep 相等断言 + A-12 isolation/
        treatment 禁 reference|oracle
  run   模型批：预算刚性 ≤40 正式臂进程（每臂 rate_limited 退避重试 ≤1，逐条登记 budget.json），
        按族双线程并行（族内串行）；glm 臂 observed 漂移 → redline 停全批（B-01/SF-0004 DT-v1）；
        每完成一题×rep 向 progress.log 记一行；幂等续跑（已有 records 的臂跳过）；
        update 按 slot 定位（v1 entries[-1] 双线程错位教训，见 records/budget-repair-note.json）
  judge 零模型：每臂 run_check 直调（--input-basis 该 rep 输入，C-02；artifact_track.py 不支持
        --input-basis 故直调并包装 verdict，留痕）+ process_track（C-03，EI-14 禁止面）+
        质量轨显式 unjudgeable（C-04）+ oracle verify（C-09）+ pack_checks（A-12）+
        aggregate.py 模式二出 matrix-glm.json / matrix-minimax.json（C-01/C-05）

布局：runs/sf0006-c/{<family>/<task>-rep<k>/{arms_manifest.json,baseline,treatment},
oracle/<task>-rep<k>/{fixtures,oracle,manifest.json}, oracle/<task>-rep<k>.json(A-14 记录),
budget.json, progress.log, precheck/, records/, matrix-glm.json, matrix-minimax.json}
退出码：0 所涉阶段成功 / 1 有臂级失败或断言红 / 2 用法或装置错误。
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
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-c")
EVALKIT = os.path.join(ROOT, "evalkit")
VPY = os.path.join(ROOT, ".venv-dev", "bin", "python")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
CRED_SRC = os.path.expanduser("~/.zcode/v2/credentials.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
GLOBAL_SHA_FILES = [os.path.expanduser("~/.zcode/cli/config.json"),
                    os.path.expanduser("~/.zcode/v2/provider_config.json"),
                    os.path.expanduser("~/.zcode/v2/credentials.json")]
SCRATCH = "/tmp/sf0006c-pin-scratch"

TASKS = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03"]   # pool-state ready=5（prep 复核）
FAMILIES = ["glm", "minimax"]
REPS = [1, 2]
SEED = {"mm-01": 4201, "mm-02": 4202, "hot-01": 4203, "hot-02": 4204, "hot-03": 4205}
VARIANT = {"mm-01": "meeting-minutes", "mm-02": "meeting-minutes",
           "hot-01": "hot-templates", "hot-02": "hot-templates", "hot-03": "hot-templates"}

PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800}
TARGET = {
    "glm": {"provider": "account:bigmodel-individual-coding-plan", "model": "GLM-5.3",
            "reasoning": "max"},
    "minimax": {"provider": "minimax", "model": "Minimax-M3.1-Flash-Preview",
                "reasoning": "enabled"},
}
CAP_ARMS = 40
RETRY_CAP_PER_ARM = 1
ENV_PROVIDER_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
                     "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
                     "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")

LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
STOP = threading.Event()
PROGRESS = os.path.join(RUN, "progress.log")
QUEUE = {"items": [], "idx": 0}
UNIT_STATE = {}   # (task, rep) -> {fam: {"wall_ms":…, "pins": […], "buckets": […]}}
SCRATCH_ENV = {}


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


oracle_gate = load_mod("oracle_gate", os.path.join(EVALKIT, "harness", "oracle_gate.py"))
classify_mod = load_mod("classify", os.path.join(EVALKIT, "evaluators", "classify.py"))
run_arm = load_mod("run_arm", os.path.join(EVALKIT, "harness", "run_arm.py"))
pull_telemetry = run_arm.pull_telemetry


def run_cmd(cmd, **kw):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(cmd, capture_output=True, env=env, **kw)


def unit_dir(fam, task, rep):
    return os.path.join(RUN, fam, "%s-rep%d" % (task, rep))


def arm_dir_of(fam, task, rep, arm):
    return os.path.join(unit_dir(fam, task, rep), arm)


# ---------------------------------------------------------------- prep
def stage_prep():
    fails = []
    ps = json.load(open(os.path.join(ROOT, "bench/devpool-r1/pool-state.json"), encoding="utf-8"))
    ready = [t["id"] for t in ps["tasks"] if t.get("ready")]
    if sorted(ready) != sorted(TASKS):
        fails.append("pool-state ready=%s ≠ 卡面 5 题" % ready)
    for tid in TASKS:
        seed = next(t for t in ps["tasks"] if t["id"] == tid)["canonical_seed"]
        if seed != SEED[tid]:
            fails.append("%s canonical_seed %s ≠ 编排器 %s" % (tid, seed, SEED[tid]))

    lines = ["# SF-0006 C 层开工全局配置 sha256（B-03；收工逐字节比对）"]
    for p in GLOBAL_SHA_FILES:
        lines.append("%s  %s" % (sha256_file(p), p))
    with open(os.path.join(RUN, "precheck", "global-sha-opening.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    r = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "freeze_device.py"),
                 "verify", "--evalkit", EVALKIT])
    with open(os.path.join(RUN, "precheck", "freeze-verify-opening.out"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("exit=%d\n%s" % (r.returncode, r.stdout.decode("utf-8", "replace")))
    if r.returncode != 0:
        fails.append("freeze verify 开工非 0")

    for v in sorted(set(VARIANT.values())):
        vd = os.path.join(ROOT, "dist", "build", "standard", v)
        if not os.path.isfile(os.path.join(vd, "SKILL.md")):
            fails.append("变体缺 SKILL.md: %s" % vd)

    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)

    for tid in TASKS:
        for rep in REPS:
            odir = os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep))
            nonce = "A" if rep == 1 else "B"
            if os.path.isdir(odir):
                shutil.rmtree(odir)
            r = run_cmd([VPY, os.path.join(EVALKIT, "packs", "ws4-dev", tid, "gen_oracle.py"),
                         "--seed", str(SEED[tid]), "--nonce-set", nonce, "--out", odir])
            if r.returncode != 0:
                fails.append("gen_oracle %s rep%d exit=%d %s" % (tid, rep, r.returncode,
                                                                 r.stderr.decode()[-200:]))
                continue
            rec_path = os.path.join(RUN, "oracle", "%s-rep%d.json" % (tid, rep))
            r2 = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "oracle_gate.py"),
                          "hash", "--root", os.path.join(odir, "oracle"), "--record", rec_path])
            if r2.returncode != 0:
                fails.append("oracle_gate hash %s rep%d exit=%d" % (tid, rep, r2.returncode))
    fx_sha = {}
    for tid in TASKS:
        for rep in REPS:
            tree = os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep), "fixtures")
            fx_sha[(tid, rep)] = oracle_gate.hash_tree(tree)["tree_sha256"]
        pack_sha = oracle_gate.hash_tree(os.path.join(EVALKIT, "packs", "ws4-dev", tid,
                                                      "fixtures"))["tree_sha256"]
        if fx_sha[(tid, 1)] != pack_sha:
            fails.append("A-13 %s rep1 fixtures 树哈希 ≠ 包内 canonical" % tid)
        if fx_sha[(tid, 1)] == fx_sha[(tid, 2)]:
            fails.append("A-13 %s 两 rep 输入相同（nonce 未变）" % tid)
    write_json(os.path.join(RUN, "records", "a13-input-tree-sha256.json"),
               {"algorithm": "oracle_gate.hash_tree（A-08 同算法）",
                "fixtures": {"%s-rep%d" % k: v for k, v in fx_sha.items()}})

    for tid in TASKS:
        for fam in FAMILIES:
            for rep in REPS:
                ud = unit_dir(fam, tid, rep)
                if os.path.isdir(ud):
                    fails.append("单元目录已存在（EI-18 拒绝重建）: %s" % ud)
                    continue
                asset = os.path.join(ROOT, "dist", "build", "standard", VARIANT[tid])
                r = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "make_arms.py"),
                             "--pack", os.path.join(EVALKIT, "packs", "ws4-dev", tid),
                             "--run-id", "%s/%s-rep%d" % (fam, tid, rep),
                             "--asset-skill", asset, "--out", RUN])
                if r.returncode != 0:
                    fails.append("make_arms %s %s rep%d exit=%d %s" % (fam, tid, rep,
                                  r.returncode, r.stderr.decode()[-150:]))
                    continue
                if rep == 2:
                    src_fx = os.path.join(RUN, "oracle", "%s-rep2" % tid, "fixtures")
                    for arm in ("baseline", "treatment"):
                        dst = os.path.join(ud, arm, "fixtures")
                        shutil.rmtree(dst)
                        shutil.copytree(src_fx, dst)
                for arm in ("baseline", "treatment"):
                    ad = os.path.join(ud, arm)
                    for ban in ("reference", "oracle"):
                        if os.path.isdir(os.path.join(ad, ban)):
                            fails.append("A-12 %s 臂含 %s/" % (ad, ban))
                    got = oracle_gate.hash_tree(os.path.join(ad, "fixtures"))["tree_sha256"]
                    if got != fx_sha[(tid, rep)]:
                        fails.append("A-13 %s/%s 输入哈希 ≠ rep%d 基准" % (fam, tid, rep))
    if fails:
        print("PREP FAIL:\n" + "\n".join(fails), file=sys.stderr)
        write_json(os.path.join(RUN, "records", "prep-fails.json"), {"fails": fails})
        return 1

    for tid in TASKS:
        for rep in REPS:
            oroot = os.path.abspath(os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep)))
            for fam in FAMILIES:
                for arm in ("baseline", "treatment"):
                    cp = os.path.commonpath([oroot, os.path.abspath(arm_dir_of(fam, tid, rep, arm))])
                    if cp in (oroot, os.path.abspath(arm_dir_of(fam, tid, rep, arm))):
                        print("ORACLE_PATH_VIOLATION %s %s" % (oroot, fam), file=sys.stderr)
                        return 2

    pairs = {}
    for tid in TASKS:
        for rep in REPS:
            shas = {fam + "|" + arm: oracle_gate.hash_tree(
                        os.path.join(arm_dir_of(fam, tid, rep, arm), "fixtures"))["tree_sha256"]
                    for fam in FAMILIES for arm in ("baseline", "treatment")}
            ok = len(set(shas.values())) == 1
            pairs["%s-rep%d" % (tid, rep)] = {"equal": ok, "sha256": shas}
            if not ok:
                fails.append("A-13 %s-rep%d 同 rep 各臂输入不相等" % (tid, rep))
    write_json(os.path.join(RUN, "records", "a13-same-rep-equal.json"), pairs)

    iso_fails = []
    for tid in TASKS:
        for fam in FAMILIES:
            for rep in REPS:
                b = arm_dir_of(fam, tid, rep, "baseline")
                r = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "isolation_probe.py"),
                             b, "--json", os.path.join(RUN, "records", "a12-isolation",
                                                       "%s-%s-rep%d.json" % (fam, tid, rep))])
                if r.returncode != 0:
                    iso_fails.append("%s %s rep%d exit=%d" % (fam, tid, rep, r.returncode))
    if iso_fails:
        fails.extend("isolation_probe " + s for s in iso_fails)
    if fails:
        print("PREP FAIL(2):\n" + "\n".join(fails), file=sys.stderr)
        write_json(os.path.join(RUN, "records", "prep-fails.json"), {"fails": fails})
        return 1
    write_json(os.path.join(RUN, "records", "prep-summary.json"),
               {"ready5": TASKS, "units": 40, "oracle_trees": 10,
                "a13": "rep1==canonical / rep2!=rep1 / 同 rep 四臂两两相等",
                "a12_isolation": "20 baseline 臂全 exit 0",
                "opened_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    log("PREP 完成：10 oracle 树 + 40 单元 + A-12/13/14 断言全过")
    return 0


# ---------------------------------------------------------------- run（照 b2 机制）
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
            return None, m4_note
        extra_env["ZCODE_DATA_BASE_DIR"] = data_dir
    return {"extra_env": extra_env, "m4_note": m4_note}, None


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
           "/opt/ZCode/resources/glm/zcode.cjs",
           "-p", PROMPT, "--cwd", arm_dir.replace("\\", "/"), "--json"]
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


def persist_arm(fam, task, rep, arm, rec, task_pack):
    ad = arm_dir_of(fam, task, rep, arm)
    rec_dir = os.path.join(ad, "records")
    pin = {
        "arm": arm, "run_label": "rep%d" % rep, "run_id": "sf0006-c",
        "model_id": rec["model_id_observed"] or "UNOBSERVED",
        "provider_base_url": rec["provider_id_observed"] or "UNOBSERVED",
        "cli_runtime": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9",
        "date": time.strftime("%Y-%m-%d"),
        "reasoning_variant": rec["variant_observed"]
                             or ("max" if fam == "glm" else "enabled"),
        "judge_sha256": sha256_file(os.path.join(task_pack, "checks", "run_check.py")),
        "family": fam,
        "mechanism": rec["mechanism"],
        "task": task, "rep": rep,
        "note": ("C-01 实测钉版：model_id/provider_base_url 抄 db model_usage join 落点"
                 "（逐字大小写敏感）；机制照 b2（glm=M4、minimax=M2）；db 行 variant 字段"
                 "本轮为 None，reasoning_variant 按族契约默认回退（如实记非实测）"),
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


def family_worker(fam, budget):
    while not STOP.is_set():
        with LOCK:
            pick = None
            for i in range(len(QUEUE["items"])):
                f2, t2, r2 = QUEUE["items"][i]
                if f2 == fam:
                    pick = (t2, r2)
                    QUEUE["items"][i] = (None, None, None)   # 占位防重领
                    break
            if pick is None:
                return
            task, rep = pick
        if STOP.is_set():
            return
        fam_arms = {"wall_ms": 0, "pins": [], "buckets": []}
        for arm in ("baseline", "treatment"):
            # 幂等：已有权威 records 的臂跳过（续跑口径；被杀臂无 records 会重跑）
            if os.path.isfile(os.path.join(arm_dir_of(fam, task, rep, arm), "records",
                                           "arm_run.json")):
                log("SKIP 已完成臂 %s/%s-rep%d/%s" % (fam, task, rep, arm))
                continue
            with LOCK:
                if budget["counted_arm_procs"] + 1 > CAP_ARMS or STOP.is_set():
                    budget["entries"].append({"slot": len(budget["entries"]) + 1,
                                              "arm": "%s/%s-rep%d/%s" % (fam, task, rep, arm),
                                              "kind": "arm", "status": "skipped_budget_or_stop"})
                    write_json(os.path.join(RUN, "budget.json"), budget)
                    return
                slot = len(budget["entries"]) + 1
                budget["entries"].append({"slot": slot, "arm": "%s/%s-rep%d/%s" % (fam, task, rep, arm),
                                          "kind": "arm", "ts_intent": time.strftime("%H:%M:%S"),
                                          "status": "pending"})
                budget["counted_arm_procs"] += 1
                write_json(os.path.join(RUN, "budget.json"), budget)
            ad = arm_dir_of(fam, task, rep, arm)
            rec = run_once(ad, fam)
            retried = False
            failed = (rec["exit_code"] != 0 or rec["timed_out"]
                      or not rec["session_id"] or rec["model_usage_rows"] == 0)
            rl = failed and looks_rate_limited(rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            if rl:
                att1 = {k: v for k, v in rec.items() if not k.startswith("_")}
                att1["attempt"] = 1
                write_json(os.path.join(RUN, "attempts", "%s-%s-rep%d-%s.attempt1.json"
                                        % (fam, task, rep, arm)), att1)
                log("rate_limited 退避 30s 后重试 1 次：%s/%s-rep%d/%s" % (fam, task, rep, arm))
                time.sleep(30)
                with LOCK:
                    budget["retry_procs"] += 1
                    budget["entries"].append({"slot": len(budget["entries"]) + 1,
                                              "arm": "%s/%s-rep%d/%s" % (fam, task, rep, arm),
                                              "kind": "rate_limited-retry",
                                              "ts_intent": time.strftime("%H:%M:%S"),
                                              "status": "pending"})
                    write_json(os.path.join(RUN, "budget.json"), budget)
                rec = run_once(ad, fam)
                rec["attempt"] = 2
                rec["rate_limited_retry"] = True
                retried = True
            task_pack = os.path.join(EVALKIT, "packs", "ws4-dev", task)
            pin = persist_arm(fam, task, rep, arm, rec, task_pack)
            observed = rec["model_usage_rows"] > 0
            t = TARGET[fam]
            pin_ok = (rec["model_id_observed"] == t["model"]
                      and rec["provider_id_observed"] == t["provider"])
            summary = {k: v for k, v in rec.items() if not k.startswith("_")}
            summary.update({"pin_verdict": "pass" if pin_ok else "drift" if observed else "unobserved",
                            "attempted": True, "retried": retried,
                            "classify": classify_arm(rec, retried),
                            "task": task, "rep": rep, "slot": slot})
            with LOCK:
                for e in budget["entries"]:
                    if e["slot"] == slot and e["kind"] == "arm":
                        e.update({
                            "status": "done" if observed else "no-model-call",
                            "exit_code": rec["exit_code"], "session_id": rec["session_id"],
                            "observed": {"model_id": rec["model_id_observed"],
                                         "provider_id": rec["provider_id_observed"],
                                         "variant": rec["variant_observed"]},
                            "pin_verdict": summary["pin_verdict"]})
                        break
                write_json(os.path.join(RUN, "budget.json"), budget)
                write_json(os.path.join(RUN, "records", "arms",
                                        "%s-%s-rep%d-%s.json" % (fam, task, rep, arm)), summary)
            if fam == "glm" and observed and not pin_ok:
                reason = ("glm 臂落点漂移（B-01 红线，SF-0004 DT-v1）：observed %s @ %s ≠ %s @ %s，"
                          "停全批" % (rec["model_id_observed"], rec["provider_id_observed"],
                                      t["model"], t["provider"]))
                with LOCK:
                    budget["redline_event"] = True
                    budget["redline_reason"] = reason
                    write_json(os.path.join(RUN, "budget.json"), budget)
                log("REDLINE: " + reason)
                STOP.set()
            fam_arms["wall_ms"] += rec["wall_ms"]
            fam_arms["pins"].append(summary["pin_verdict"])
            fam_arms["buckets"].append(summary["classify"]["bucket"])
        with LOCK:
            UNIT_STATE.setdefault((task, rep), {})[fam] = dict(fam_arms)
            done = len(UNIT_STATE[(task, rep)]) == 2
            g = UNIT_STATE[(task, rep)].get("glm")
            m = UNIT_STATE[(task, rep)].get("minimax")
        if done:
            log("UNIT %s rep%d 完成：glm wall=%sms pin=%s bucket=%s | minimax wall=%sms "
                "pin=%s bucket=%s" % (task, rep, g["wall_ms"], "/".join(g["pins"]),
                                      "/".join(g["buckets"]),
                                      m["wall_ms"], "/".join(m["pins"]),
                                      "/".join(m["buckets"])))


def stage_run():
    if not os.path.isfile(os.path.join(RUN, "budget.json")):
        write_json(os.path.join(RUN, "budget.json"),
                   {"cap_counted_arms": CAP_ARMS, "retry_cap_per_arm": RETRY_CAP_PER_ARM,
                    "counted_arm_procs": 0, "retry_procs": 0, "model_calls": 0, "entries": []})
    with open(os.path.join(RUN, "budget.json"), encoding="utf-8") as f:
        budget = json.load(f)
    for fam in FAMILIES:
        built_scratch, err = build_family_scratch(fam)
        if built_scratch is None:
            print("scratch 派生失败：%s" % err, file=sys.stderr)
            return 2
        SCRATCH_ENV[fam] = built_scratch["extra_env"]
    threads = []
    # 40 项队列（fam, task, rep）：每单元由其族 worker 跑 baseline+treatment 两臂。
    # 续跑口径：worker 对已有 records/arm_run.json 的臂幂等跳过，budget 按既有台账续计。
    QUEUE["items"] = [(fam, t, r) for t in TASKS for r in REPS for fam in FAMILIES]
    for fam in FAMILIES:
        th = threading.Thread(target=family_worker, args=(fam, budget), daemon=True)
        threads.append(th)
    log("RUN 开始/续跑：40 单元队列（正式臂进程上限 %d；已计 %d；rate_limited 退避重试 ≤1/臂）"
        % (CAP_ARMS, budget["counted_arm_procs"]))
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    scratch_purged = not os.path.isdir(SCRATCH)
    with open(os.path.join(RUN, "budget.json"), encoding="utf-8") as f:
        budget = json.load(f)
    budget["scratch_purged"] = scratch_purged
    budget["closed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_json(os.path.join(RUN, "budget.json"), budget)
    ok = budget["counted_arm_procs"] <= CAP_ARMS and not budget.get("redline_event")
    log("RUN 结束：counted=%s retry=%s scratch_purged=%s redline=%s" %
        (budget["counted_arm_procs"], budget["retry_procs"], scratch_purged,
         budget.get("redline_event", False)))
    return 0 if ok else 1


# ---------------------------------------------------------------- judge
def stage_judge():
    fails = []
    for tid in TASKS:
        for fam in FAMILIES:
            for rep in REPS:
                basis = os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep), "fixtures")
                oroot = os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep), "oracle")
                for arm in ("baseline", "treatment"):
                    ad = arm_dir_of(fam, tid, rep, arm)
                    rec_dir = os.path.join(ad, "records")
                    if not os.path.isfile(os.path.join(rec_dir, "arm_run.json")):
                        fails.append("缺臂记录 %s/%s-rep%d/%s（跑批未完成）" % (fam, tid, rep, arm))
                        continue
                    out_dir = os.path.join(ad, "out")
                    os.makedirs(out_dir, exist_ok=True)
                    rec_json = os.path.join(rec_dir, "run_check_record.json")
                    r = run_cmd([VPY, os.path.join(EVALKIT, "packs", "ws4-dev", tid, "checks",
                                                   "run_check.py"), out_dir,
                                 "--input-basis", basis, "--record", rec_json])
                    rc_rec = {}
                    if os.path.isfile(rec_json):
                        rc_rec = json.load(open(rec_json, encoding="utf-8"))
                    write_json(os.path.join(rec_dir, "artifact_track.json"), {
                        "track": "artifact",
                        "verdict": "pass" if r.returncode == 0 else "fail",
                        "run_check_exit": r.returncode,
                        "checks_pass": rc_rec.get("checks_pass"),
                        "input_basis": basis,
                        "checks": rc_rec.get("checks") or [],
                        "l1_registered_not_judged": rc_rec.get("l1_registered_not_judged"),
                        "source": ("packs/ws4-dev/%s/checks/run_check.py 直调 --input-basis"
                                   "（C-02 口径；evaluators/artifact_track.py 不支持"
                                   " --input-basis，rep2 会误判，故直调+包装 verdict，如实留痕）" % tid),
                    })
                    p = run_cmd([sys.executable, os.path.join(EVALKIT, "evaluators", "process_track.py"),
                                 "--arm-dir", ad, "--oracle-root", oroot,
                                 "--out", os.path.join(rec_dir, "process_track.json")])
                    if p.returncode == 2:
                        fails.append("process_track 装置错 %s/%s-rep%d/%s" % (fam, tid, rep, arm))
                    write_json(os.path.join(rec_dir, "quality.json"), {
                        "score": None, "verdict": "unjudgeable",
                        "reason": "异族裁判不可满足（SF-0004 报告 §7）；质量轨不出分",
                    })
    if fails:
        print("JUDGE FAIL:\n" + "\n".join(fails), file=sys.stderr)
        return 1

    c9 = {}
    for tid in TASKS:
        for rep in REPS:
            r = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "oracle_gate.py"), "verify",
                         "--root", os.path.join(RUN, "oracle", "%s-rep%d" % (tid, rep), "oracle"),
                         "--record", os.path.join(RUN, "oracle", "%s-rep%d.json" % (tid, rep))])
            c9["%s-rep%d" % (tid, rep)] = {"exit": r.returncode,
                                           "out": r.stdout.decode("utf-8", "replace")[:200]}
            if r.returncode != 0:
                fails.append("C-09 oracle verify %s rep%d exit=%d" % (tid, rep, r.returncode))
    write_json(os.path.join(RUN, "records", "c09-oracle-verify.json"), c9)
    if fails:
        print("JUDGE FAIL(C-09):\n" + "\n".join(fails), file=sys.stderr)
        return 1

    pk_fails = []
    for tid in TASKS:
        for fam in FAMILIES:
            for rep in REPS:
                ud = unit_dir(fam, tid, rep)
                pin = os.path.join(ud, "baseline", "records", "model_pin.json")
                r = run_cmd([sys.executable, os.path.join(EVALKIT, "harness", "pack_checks.py"),
                             "--pack", os.path.join(EVALKIT, "packs", "ws4-dev", tid),
                             "--arms", os.path.join(ud, "baseline"),
                             "--arms", os.path.join(ud, "treatment"),
                             "--model-pin", pin,
                             "--json", os.path.join(RUN, "records", "a12-pack-checks",
                                                    "%s-%s-rep%d.json" % (fam, tid, rep))])
                if r.returncode != 0:
                    pk_fails.append("%s %s rep%d exit=%d" % (fam, tid, rep, r.returncode))
    if pk_fails:
        print("JUDGE FAIL(pack_checks):\n" + "\n".join(pk_fails), file=sys.stderr)
        write_json(os.path.join(RUN, "records", "judge-fails.json"), {"pack_checks": pk_fails})
        return 1

    for fam in FAMILIES:
        r = run_cmd([sys.executable, os.path.join(EVALKIT, "evaluators", "aggregate.py"),
                     "--run-dir", RUN, "--family", fam,
                     "--out", os.path.join(RUN, "matrix-%s.json" % fam)])
        if r.returncode != 0:
            print("aggregate %s exit=%d: %s" % (fam, r.returncode,
                  r.stderr.decode("utf-8", "replace")[-400:]), file=sys.stderr)
            return 1
    log("JUDGE 完成：40 臂三轨判定 + C-09 oracle verify + A-12 pack_checks + 两族 matrix 落盘")
    return 0


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(RUN, exist_ok=True)
    os.makedirs(os.path.join(RUN, "records", "arms"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "records", "a12-isolation"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "records", "a12-pack-checks"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "attempts"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "precheck"), exist_ok=True)
    if stage == "prep":
        return stage_prep()
    if stage == "run":
        return stage_run()
    if stage == "judge":
        return stage_judge()
    print("用法: c_orchestrator.py prep|run|judge", file=sys.stderr)
    return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
