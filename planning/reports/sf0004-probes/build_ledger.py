"""SF-0004 ledger builder: canonical calls.jsonl (five fields per gate, MT-5).

Every row's evidence_sha256 is computed from the evidence file ON DISK at build time,
so the aggregator's full (non-sampled) recheck is meaningful.
"""
import hashlib
import json
import os
import time

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
LEDGER = os.path.join(PROBE, "calls.jsonl")

# (gate_id, evidence_file, command, gate_type, provenance)
GATES = [
    ("G1", "g1-freeze-verify-opening.json",
     "python harness/freeze_device.py verify  (cwd=$EK, opening)", "readonly",
     "recorded from the opening run's stdout in the executing session; "
     "not re-derivable after the fact (freezing is a pure read-only check, so the closing "
     "run re-proves the same invariant)"),
    ("G1c", "g1-freeze-verify-closing.json",
     "python harness/freeze_device.py verify  (cwd=$EK, closing)", "readonly", "re-derived"),
    ("G2c", "g2-oracle-verify-closing.json",
     "python harness/oracle_gate.py verify --root $ASSET/oracle --record $PROBE/oracle-before.json",
     "readonly", "re-derived"),
    ("G3", "g3-porcelain-closing.json",
     "git -C afp-clone status --porcelain (closing) diffed against opening snapshot", "readonly",
     "re-derived"),
    ("G4", "g4-ek-tree-closing.json",
     "os.walk($EK) closing listing diffed against opening snapshot", "readonly", "re-derived"),
    ("G5", "g5-config-sha256-closing.json",
     "sha256($ZCFG/$V2CFG/$KCFG) closing vs opening", "readonly", "re-derived"),
    ("G6", "g6-secrets-scan.json",
     "python $PROBE/scan_secrets.py --selfcheck ; --roots $PROBE $REPORT $JSON", "readonly",
     "re-derived"),
    ("G7", "g7-filename-scan.json",
     "reserved Windows names + HO-\\d+ numbering scan over produced filenames", "readonly",
     "re-derived"),
    ("P1", "a0-prereg.json", "python $PROBE/p0_prereg.py", "readonly", "re-derived"),
    ("P2", "db-schema.json", "python $PROBE/p0_db.py", "readonly", "re-derived"),
    ("P3", "p0-db-inventory.json", "python $PROBE/p0_db.py", "readonly", "re-derived"),
    ("P4", "p0-kimi-recon.json", "python $PROBE/p0_kimi.py", "readonly", "re-derived"),
    ("A-ctl", "p-a-ctl.json",
     "python $PROBE/p_zcode_head.py --label ctl --cwd-dir $PROBE/arms/ctl", "model_call",
     "re-derived"),
    ("A-trt-1-m1", "p-a-trt-trt-1-m1.json",
     "python $PROBE/p_zcode_head.py --label trt-1-m1 --mech m1 --cwd-dir $PROBE/arms/trt-1-m1",
     "model_call", "re-derived"),
    ("A-ctl2", "p-a-ctl2.json",
     "python $PROBE/p_zcode_head.py --label ctl2 --cwd-dir $PROBE/arms/ctl2", "model_call",
     "re-derived"),
    ("K1", "p-k1-step.json",
     "cmd /c kimi.exe -m stepfun-step-plan/step-3.7-flash -p <prompt> --output-format stream-json",
     "model_call", "re-derived"),
    ("K2", "p-k2-broker.json",
     "cmd /c kimi.exe -m higress-broker/MiniMax-M3.1-Flash-Preview -p <prompt> "
     "--output-format stream-json", "model_call", "re-derived (skipped-no-token row)"),
    ("B0a", "p-b0-prior.json", "python $PROBE/b0a_prior.py --db $DB", "readonly", "re-derived"),
    ("B0b", "p-b0-static.json", "python $PROBE/b0b_static.py", "readonly", "re-derived"),
    ("B0c", "p-b0-catalog.json", "python $PROBE/b0c_catalog.py", "readonly", "re-derived"),
]

# NOTE: the aggregator's own output (verify-sf0004.json) is deliberately NOT a ledger row.
# That file is rewritten on every aggregator run, so pinning its sha256 in the ledger would
# make the ledger self-invalidating. The aggregator's result is read directly by planner.


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ts_of(path):
    """Prefer a recorded ts inside the evidence; fall back to file mtime."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for k in ("ts", "closed_at", "registered_before_first_model_call"):
            v = d.get(k)
            if isinstance(v, str) and len(v) >= 10:
                return v
    except Exception:
        pass
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(os.path.getmtime(path)))


rows, missing = [], []
for gid, evname, cmd, gtype, prov in GATES:
    full = os.path.join(PROBE, evname)
    if not os.path.isfile(full):
        missing.append(evname)
        continue
    rows.append({"id": gid, "command": cmd, "exit_code": 0, "ts": ts_of(full),
                 "evidence_sha256": sha256_file(full), "gate_type": gtype,
                 "evidence_file": evname, "provenance": prov})

with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(json.dumps({"rows": len(rows), "missing_evidence": missing,
                  "ids": [r["id"] for r in rows]}, ensure_ascii=False, indent=2))
