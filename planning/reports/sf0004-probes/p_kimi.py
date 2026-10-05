"""SF-0004 K-group: kimi dual-head channel facts (K1 step head, K2 broker head).

K组 is fact-layer only: it never flips a branch. K1 is mandatory; K2 runs only when a
planner-minted short-term token was injected into the process environment.

Fail-closed (acceptance K1): exit 0 with NO model self-report field in the stream
=> 'unobservable' (registered honestly, counts as neither pass nor fail; R-3 debt).

kimi.exe is invoked via cmd /c (never directly from Git Bash -- Windows incident family).
No token value is ever read, printed or stored; only token_present booleans.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
KIMI = r"D:\tools\bin\kimi.exe"
KCFG = os.path.join(os.environ["USERPROFILE"], ".kimi-code", "config.toml")
LEDGER = os.path.join(PROBE, "calls.jsonl")

# Names only. A vault-injected short-term broker token would arrive under one of these.
TOKEN_ENV_NAMES = ["MINIMAX_API_KEY", "HIGRESS_BROKER_API_KEY", "VAULT_TOKEN",
                   "BROKER_TOKEN", "MINIMAX_TOKEN", "SF0004_BROKER_TOKEN"]


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ledger(gate_id, command, exit_code, evidence_path, gate_type="model_call"):
    row = {"id": gate_id, "command": command, "exit_code": exit_code,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "evidence_sha256": sha256_file(evidence_path), "gate_type": gate_type}
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def token_present():
    """Boolean only. Values are never read."""
    return {n: (n in os.environ and bool(os.environ.get(n))) for n in TOKEN_ENV_NAMES}


def run_kimi(model_id, label):
    prompt = "Reply with exactly: PONG-SF0004-%s" % label
    cmd = ["cmd", "/c", KIMI, "-m", model_id, "-p", prompt, "--output-format", "stream-json"]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=600, shell=False)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err = -1, (exc.stdout or b""), (exc.stderr or b""), True
    return cmd, rc, out, err, int((time.time() - t0) * 1000)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", choices=["step", "broker"], required=True)
    args = ap.parse_args(argv)

    tok = token_present()
    tok_any = any(tok.values())

    if args.head == "broker" and not tok_any:
        ev = {"gate": "K2", "channel": "kimi broker head (higress-broker/MiniMax-M3.1-Flash-Preview)",
              "status": "skipped-no-token", "token_present": False,
              "token_env_names_checked": tok,
              "reason": "no planner-minted short-term broker token present in the process "
                        "environment (env-name scan only; no value read). Per card §4 this is an "
                        "explicit non-failure row and does not block the decision.",
              "config_sha256": sha256_file(KCFG) if os.path.isfile(KCFG) else None,
              "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        path = os.path.join(PROBE, "p-k2-broker.json")
        write_json(path, ev)
        ledger("K2", "cmd /c kimi.exe -m higress-broker/MiniMax-M3.1-Flash-Preview -p <prompt> "
                     "--output-format stream-json", 0, path, gate_type="model_call")
        print(json.dumps({"gate": "K2", "status": "skipped-no-token", "token_present": False},
                         ensure_ascii=False, indent=2))
        return 0

    model_id = ("stepfun-step-plan/step-3.7-flash" if args.head == "step"
                else "higress-broker/MiniMax-M3.1-Flash-Preview")
    gate = "K1" if args.head == "step" else "K2"
    cmd, rc, out, err, wall_ms = run_kimi(model_id, gate)

    stream_path = os.path.join(PROBE, "p-k1-stream.jsonl" if args.head == "step"
                               else "p-k2-stream.jsonl")
    os.makedirs(os.path.dirname(stream_path), exist_ok=True)
    with open(stream_path, "wb") as f:
        f.write(out)

    text = out.decode("utf-8", errors="replace")
    # model self-report field search (fail-closed: absence => unobservable)
    observed = None
    for pat in (r'"model"\s*:\s*"([^"]+)"', r'"model_id"\s*:\s*"([^"]+)"',
                r'"modelId"\s*:\s*"([^"]+)"'):
        m = re.search(pat, text)
        if m:
            observed = m.group(1)
            break

    if observed is None:
        status = "unobservable"
    elif observed == model_id or observed.split("/")[-1] == model_id.split("/")[-1]:
        status = "observed"
    else:
        status = "mismatch"

    ev = {"gate": gate, "channel": "kimi CLI head",
          "requested_model_id_verbatim": model_id,
          "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
          "exit_code": rc, "wall_ms": wall_ms, "stdout_nonempty": len(out) > 0,
          "stdout_bytes": len(out), "stderr_head": err.decode("utf-8", errors="replace")[:1500],
          "model_self_reported": observed, "status": status,
          "stream_file": stream_path, "stream_sha256": sha256_file(stream_path),
          "token_present": tok_any, "token_env_names_checked": tok,
          "r3_note": "kimi CLI has no db accounting; landing is observable only via stream "
                     "self-report. This probe does NOT validate the R-3 normalizer itself.",
          "config_sha256": sha256_file(KCFG) if os.path.isfile(KCFG) else None}
    path = os.path.join(PROBE, "p-k1-step.json" if args.head == "step" else "p-k2-broker.json")
    write_json(path, ev)
    ledger(gate, "cmd /c kimi.exe -m %s -p <prompt> --output-format stream-json" % model_id,
           rc, path)
    print(json.dumps({"gate": gate, "exit_code": rc, "status": status,
                      "model_self_reported": observed, "stdout_bytes": len(out),
                      "stream_file": stream_path}, ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
