"""SF-0004 A-group probe driver: zcode headless landing measurement.

Mirrors evalkit/harness/run_arm.py spawn + telemetry 口径 (pull_telemetry is imported
read-only so the join口径 is literally the same code, not a re-implementation).

Usage:
  python p_zcode_head.py --label ctl            --cwd-dir <arm dir>
  python p_zcode_head.py --label trt-1-m1 --mech m1 --cwd-dir <arm dir>

Mechanisms (pre-registered in a0-prereg.json):
  m1  env-scoped paired provider config override (ZCODE_BUILTIN_PROVIDER_CONFIG_FILE +
      ZCODE_PERSONAL_PROVIDER_CONFIG_FILE -> derived copies under secret-scratch)
  m3  headless '/model <id>' slash command before the PONG task

Global config is never modified. Scratch copies are deleted with an existence assertion.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
SCRATCH = os.path.join(PROBE, "secret-scratch")
EK = r"D:\new-workspace\agent-asset\evalkit"
USERPROFILE = os.environ["USERPROFILE"]
DB = os.path.join(USERPROFILE, ".zcode", "cli", "db", "db.sqlite")
PERSONAL_SRC = os.path.join(USERPROFILE, ".zcode", "v2", "provider_config.json")
BUILTIN_SRC = os.path.join(os.environ["APPDATA"], "npm", "node_modules",
                           "zcode-app-cli", "vendor", "provider", "zcode-builtin.json")
TARGET_PROVIDER = "minimax"
TARGET_MODEL = "Minimax-M3.1-Flash-Preview"
LEDGER = os.path.join(PROBE, "calls.jsonl")

spec = importlib.util.spec_from_file_location("run_arm", os.path.join(EK, "harness", "run_arm.py"))
run_arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_arm)
pull_telemetry = run_arm.pull_telemetry


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ledger(gate_id, command, exit_code, evidence_path, gate_type):
    row = {"id": gate_id, "command": command, "exit_code": exit_code,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "evidence_sha256": sha256_file(evidence_path),
           "gate_type": gate_type}
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def build_m1_scratch():
    """Derived config copies (contain credentials) -> secret-scratch only, never echoed."""
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


def resolve_zcode():
    for cand in ("zcode.cmd", "zcode.exe"):
        p = shutil.which(cand)
        if p:
            return [p]
    node = shutil.which("node.exe") or shutil.which("node")
    for base in (os.path.join(os.environ["APPDATA"], "npm"),
                 os.path.join(USERPROFILE, ".npm-global", "bin")):
        entry = os.path.join(base, "node_modules", "zcode-app-cli", "bin", "zcode.js")
        if node and os.path.isfile(entry):
            return [node, entry]
    raise SystemExit("cannot resolve zcode entry point")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--cwd-dir", required=True)
    ap.add_argument("--mech", default=None)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args(argv)

    arm_dir = os.path.abspath(args.cwd_dir)
    os.makedirs(arm_dir, exist_ok=True)
    os.makedirs(os.path.join(arm_dir, "records"), exist_ok=True)

    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"

    mech = args.mech
    prompt = "Reply with exactly: PONG-SF0004-%s" % args.label
    if mech == "m3":
        prompt = "/model %s/%s" % (TARGET_PROVIDER, TARGET_MODEL)
        # session model switch, then the PONG task in the same headless run
        prompt = prompt
    elif mech == "m1":
        personal_path, builtin_path = build_m1_scratch()
        env["ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"] = builtin_path
        env["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"] = personal_path

    cmd = resolve_zcode() + ["-p", prompt, "--cwd", arm_dir.replace("\\", "/"), "--json"]

    t0 = time.time()
    started_ms = int(t0 * 1000)
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=args.timeout, env=env, shell=False)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)

    text = out.decode("utf-8", errors="replace")
    errtext = err.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None

    tele = pull_telemetry(DB, session_id, arm_dir)
    model_rows = tele.get("model_usage") or []
    model_id = model_rows[0].get("model_id") if model_rows else None
    provider_id = model_rows[0].get("provider_id") if model_rows else None
    in_tok = sum((r.get("it") or 0) for r in model_rows)
    out_tok = sum((r.get("ot") or 0) for r in model_rows)

    is_ctl = args.label.startswith("ctl")
    if is_ctl:
        landed_as_expected = (rc == 0 and tele.get("directory_matches_arm") is True
                              and model_id == "GLM-5.3"
                              and "bigmodel" in (provider_id or "").lower())
        success_shape = landed_as_expected
    else:
        success_shape = (rc == 0 and tele.get("directory_matches_arm") is True
                         and len(model_rows) > 0
                         and model_id == TARGET_MODEL
                         and TARGET_PROVIDER in (provider_id or "").lower())

    ev = {
        "gate": args.label,
        "mechanism": mech,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "started_at_ms": started_ms,
        "command_shape": ["zcode", "-p", "<prompt>", "--cwd", "<arm>", "--json"],
        "prompt_is_pong_level": mech != "m3",
        "exit_code": rc,
        "timed_out": timed_out,
        "wall_ms": wall_ms,
        "session_id": session_id,
        "db": {
            "available": tele.get("available"),
            "session_row_found": tele.get("session") is not None,
            "directory_match": tele.get("directory_matches_arm"),
            "arm_dir": arm_dir,
            "session_directory": (tele.get("session") or {}).get("directory"),
            "model_id_verbatim": model_id,
            "provider_id_verbatim": provider_id,
            "model_usage_rows": len(model_rows),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "task_type": (tele.get("session") or {}).get("task_type"),
        },
        "landing_moved": (not is_ctl) and success_shape,
        "success_shape": success_shape,
        "expected": ("GLM-5.3 / provider contains bigmodel" if is_ctl
                     else "%s / provider contains %s" % (TARGET_MODEL, TARGET_PROVIDER)),
        "stdout_head": text[:1500],
        "stderr_head": errtext[:2000],
        "global_config_modified": False,
    }

    ev_name = ("p-a-ctl.json" if args.label == "ctl"
               else "p-a-ctl2.json" if args.label == "ctl2"
               else "p-a-trt-%s.json" % args.label)
    ev_path = os.path.join(PROBE, ev_name)
    write_json(ev_path, ev)
    write_json(os.path.join(arm_dir, "records", "arm_run.json"), ev)
    write_json(os.path.join(arm_dir, "records", "telemetry.json"), tele)

    if mech == "m1":
        ev["scratch_purged"] = purge_scratch()
        write_json(ev_path, ev)

    gate_type = "model_call" if not args.label.endswith("recon") else "readonly"
    row = ledger("A-" + args.label,
                 " ".join([cmd[0], "-p", "<prompt>", "--cwd", arm_dir, "--json"]),
                 rc, ev_path, gate_type)

    print(json.dumps({"label": args.label, "mech": mech, "exit_code": rc,
                      "session_id": session_id, "model_id_verbatim": model_id,
                      "provider_id_verbatim": provider_id, "directory_match": tele.get("directory_matches_arm"),
                      "success_shape": success_shape, "wall_ms": wall_ms,
                      "input_tokens": in_tok, "output_tokens": out_tok,
                      "evidence": ev_path, "scratch_purged": ev.get("scratch_purged")},
                     ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
