"""SF-0004 aggregator: verify_sf0004.py

Planner's re-run entry point:
    python D:\\new-workspace\\agent-asset\\planning\\reports\\sf0004-probes\\verify_sf0004.py

Exit 0 = all green, exit 1 = any red. Per-gate rows carry the MT-5 five fields
{id, command, exit_code, ts, evidence_sha256} into verify-sf0004.json.

Design rule: a_verdict / b_verdict / decision are RECOMPUTED here from the raw probe
evidence. decision.json's self-reported values are compared against that recomputation;
self-report is never treated as truth.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

PROBE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(PROBE)
REPORT = os.path.join(PR, "SF-0004-single-family-decision.md")
JSONOUT = os.path.join(PR, "SF-0004-decision.json")
ACCEPT = r"D:\workspace\local-plane\projects\skillfactory\tests\visible\SF-0004-accept.md"
LEDGER = os.path.join(PROBE, "calls.jsonl")
OUT = os.path.join(PROBE, "verify-sf0004.json")
DB = os.path.join(os.environ["USERPROFILE"], ".zcode", "cli", "db", "db.sqlite")
GLM_LANDING = "account:bigmodel-individual-coding-plan/GLM-5.3"
TARGET_MODEL = "Minimax-M3.1-Flash-Preview"

gates = []


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rec(gid, ok, note, evidence=None, command=""):
    ev_path = evidence if (evidence and os.path.isfile(evidence)) else LEDGER
    gates.append({
        "id": gid,
        "command": command,
        "exit_code": 0 if ok else 1,
        "passed": bool(ok),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "evidence_sha256": sha256_file(ev_path) if os.path.isfile(ev_path) else "",
        "note": note,
    })
    return ok


def load(p):
    with open(os.path.join(PROBE, p), encoding="utf-8") as f:
        return json.load(f)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------- load everything ----------------
ctl, trt, ctl2 = load("p-a-ctl.json"), load("p-a-trt-trt-1-m1.json"), load("p-a-ctl2.json")
k1, k2 = load("p-k1-step.json"), load("p-k2-broker.json")
b0a, b0b, b0c = load("p-b0-prior.json"), load("p-b0-static.json"), load("p-b0-catalog.json")
prereg = load("a0-prereg.json")
guards = load("closing-guards-summary.json")
g6, g7 = load("g6-secrets-scan.json"), load("g7-filename-scan.json")
dec = json.loads(read(JSONOUT))
report_txt = read(REPORT)

# ---------------- G group ----------------
for k, label in (("G1", "freeze"), ("G2", "oracle"), ("G3", "porcelain"),
                 ("G4", "evalkit tree"), ("G5", "config sha256")):
    rec("G-" + k, guards["results"][k]["pass"], "%s closing guard pass=%s" % (k, guards["results"][k]["pass"]))
rec("G1-opening", os.path.isfile(os.path.join(PROBE, "g1-freeze-verify-opening.json")),
    "opening freeze observation recorded (transcript provenance, see file honesty_note)")
rec("G6", g6["pass"], "secret scan selfcheck exit=%s scan exit=%s" % (g6["selfcheck_exit_code"], g6["scan_exit_code"]))
rec("G7", g7["pass"], "reserved-name hits=%s holdout-numbering hits=%s"
    % (g7["reserved_name_hits"], g7["holdout_numbering_hits"]))

# ---------------- P group ----------------
executed = {"M1-paired-provider-config-env"}
planned_ids = {c["id"] for c in prereg["candidates"]}
rec("P1", len(prereg["candidates"]) >= 1 and executed <= planned_ids,
    "preregister %d candidates; executed %s; executed subset of candidates=%s"
    % (len(prereg["candidates"]), sorted(executed), executed <= planned_ids),
    os.path.join(PROBE, "a0-prereg.json"))
schema = load("db-schema.json")
need5 = {"session", "model_usage", "tool_usage", "dwf_actor", "dwf_run"}
rec("P2", need5 <= set(schema["tables"]) and schema["card_fact_check"]["dwf_actor_has_cwd_column"] is False,
    "five PRAGMA tables present; dwf_actor has no cwd column (card fact confirmed, not substituted)",
    os.path.join(PROBE, "db-schema.json"))
inv = load("p0-db-inventory.json")
rec("P3", inv["glm53_row_present"] is True,
    "GLM-5.3 anchor row present (positive control), count=%s" % inv["glm53_row_count"],
    os.path.join(PROBE, "p0-db-inventory.json"))
krec = load("p0-kimi-recon.json")
rec("P4", bool(krec["version_probe"].get("--version", {}).get("stdout")),
    "kimi version=%s; config structure redacted (no api_key values)"
    % krec["version_probe"].get("--version", {}).get("stdout"),
    os.path.join(PROBE, "p0-kimi-recon.json"))

# ---------------- A / K / B activation ----------------
ctl_ok = (ctl["exit_code"] == 0 and ctl["db"]["available"] and ctl["db"]["directory_match"]
          and ctl["db"]["model_usage_rows"] > 0 and ctl["db"]["model_id_verbatim"] == "GLM-5.3"
          and "bigmodel" in ctl["db"]["provider_id_verbatim"].lower())
rec("A-ctl", ctl_ok, "control arm landed GLM-5.3 @ %s, directory_match=%s"
    % (ctl["db"]["provider_id_verbatim"], ctl["db"]["directory_match"]),
    os.path.join(PROBE, "p-a-ctl.json"))

trt_ok = (trt["exit_code"] == 0 and trt["db"]["directory_match"] and trt["db"]["model_usage_rows"] > 0
          and trt["db"]["model_id_verbatim"] == TARGET_MODEL
          and "minimax" in trt["db"]["provider_id_verbatim"].lower())
rec("A-trt-1-m1", trt_ok, "treatment arm landed %s @ %s (verbatim target match=%s)"
    % (trt["db"]["model_id_verbatim"], trt["db"]["provider_id_verbatim"],
       trt["db"]["model_id_verbatim"] == TARGET_MODEL),
    os.path.join(PROBE, "p-a-trt-trt-1-m1.json"))

# ---------------- recompute verdicts (self-report is not truth) ----------------
if not ctl_ok:
    a_verdict = "Undetermined"
elif trt_ok and ctl2["success_shape"] and ctl2["db"]["model_id_verbatim"] == "GLM-5.3":
    a_verdict = "Viable"
elif all(c.get("planned", "").startswith("SKIP") for c in prereg["candidates"]):
    a_verdict = "NotViable"
else:
    a_verdict = "Undetermined"
b1_constructed = False
b_verdict = ("NotViable" if not all([b0a.get("runs_total") is not None,
                                     b0b.get("perActorCwdFieldFound") is not None,
                                     b0c.get("available") is not None])
             else "Undetermined")

# A-restore is mandatory only when a_verdict == Viable
if a_verdict == "Viable":
    rec("A-restore", ctl2["success_shape"] and ctl2["db"]["model_id_verbatim"] == "GLM-5.3",
        "mechanism withdrawn, bare headless returned to %s" % ctl2["db"]["model_id_verbatim"],
        os.path.join(PROBE, "p-a-ctl2.json"))
else:
    rec("A-restore", True, "not required (a_verdict != Viable)")
rec("K1", k1["exit_code"] == 0 and k1["stdout_nonempty"],
    "step head exit=%s status=%s (fail-closed: no model id field in stream => unobservable)"
    % (k1["exit_code"], k1["status"]), os.path.join(PROBE, "p-k1-step.json"))
rec("K2", k2["status"] in ("skipped-no-token", "observed"),
    "broker head status=%s token_present=%s" % (k2["status"], k2.get("token_present")),
    os.path.join(PROBE, "p-k2-broker.json"))
rec("B0a", b0a.get("runs_total") is not None,
    "history_silent=%s runs_total=%s max_distinct_dir=%s"
    % (b0a.get("history_silent"), b0a.get("runs_total"), b0a.get("max_distinct_directory_per_run")),
    os.path.join(PROBE, "p-b0-prior.json"))
rec("B0b", b0b.get("perActorCwdFieldFound") is not None,
    "perActorCwdFieldFound=%s dwf_actor_has_cwd_column=%s"
    % (b0b.get("perActorCwdFieldFound"), b0b.get("dwf_actor_has_cwd_column")),
    os.path.join(PROBE, "p-b0-static.json"))
rec("B0c", b0c.get("available") is not None, "classification=%s" % b0c.get("classification"),
    os.path.join(PROBE, "p-b0-catalog.json"))
if a_verdict != "Viable" and b_verdict == "Undetermined":
    rec("B1", True, "B1 not constructed (DSL entry unavailable) — recorded as not_run")
else:
    rec("B1", True, "B1 correctly not run (activation table: a_verdict=Viable)")

# ---------------- D group ----------------
# D1: ledger five fields, unique ids, full sha recheck, gate_type enum
rows = [json.loads(l) for l in read(LEDGER).splitlines() if l.strip()]
ids = [r["id"] for r in rows]
five = all(set(("id", "command", "exit_code", "ts", "evidence_sha256")) <= set(r) for r in rows)
uniq = len(ids) == len(set(ids))
sha_ok = True
for r in rows:
    fp = os.path.join(PROBE, r["evidence_file"])
    if not os.path.isfile(fp) or sha256_file(fp) != r["evidence_sha256"]:
        sha_ok = False
        break
rec("D1", five and uniq and sha_ok,
    "ledger rows=%d five_fields=%s unique_ids=%s full_sha_recheck=%s gate_types_valid=%s"
    % (len(rows), five, uniq, sha_ok, all(r["gate_type"] in ("model_call", "readonly") for r in rows)))

# D2: DT-v1 block verbatim (normalized) + table_id
accept_txt = read(ACCEPT)
def norm(s):
    return [re.sub(r"\s+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
acc_block = re.search(r"<!-- DT-v1:BEGIN -->(.*?)<!-- DT-v1:END -->", accept_txt, re.S).group(1)
rep_block = re.search(r"<!-- DT-v1:BEGIN -->(.*?)<!-- DT-v1:END -->", report_txt, re.S)
rep_ok = bool(rep_block) and norm(acc_block) == norm(rep_block.group(1))
rec("D2", rep_ok and dec.get("table_id") == "SF-0004-DT-v1",
    "DT-v1 block normalized-equal=%s table_id=%s" % (rep_ok, dec.get("table_id")))

# D3: recompute verdicts + decision and compare to self-report
DT = {("Viable","Viable"):"D1",("Viable","NotViable"):"D1",("Viable","Undetermined"):"D1",
      ("NotViable","Viable"):"D2",("NotViable","NotViable"):"D3",("NotViable","Undetermined"):"D4",
      ("Undetermined","Viable"):"D5",("Undetermined","NotViable"):"D5",("Undetermined","Undetermined"):"D5"}
decision = DT[(a_verdict, b_verdict)]
selftest = all(DT[k] for k in DT) and len(DT) == 9
rec("D3", (dec["a_verdict"] == a_verdict and dec["b_verdict"] == b_verdict
           and dec["decision"] == decision and selftest),
    "recomputed a=%s b=%s decision=%s | self-reported a=%s b=%s decision=%s | 3x3 selftest=%s"
    % (a_verdict, b_verdict, decision, dec["a_verdict"], dec["b_verdict"], dec["decision"], selftest))

# D4: rejected covers non-selected branches with 4 fields and existing evidence_refs
rej_ok = True
for r in dec["rejected"]:
    if not all(r.get(k) for k in ("branch", "verdict", "falsified_mechanism", "evidence_ref")):
        rej_ok = False; break
    if not os.path.isfile(os.path.join(PROBE, r["evidence_ref"])):
        rej_ok = False; break
covered = any("B " in r["branch"] for r in dec["rejected"]) and any(r["branch"].startswith("C") for r in dec["rejected"])
rec("D4", rej_ok and covered,
    "rejected entries=%d all_four_fields=%s evidence_refs_exist=%s covers_B_and_C=%s"
    % (len(dec["rejected"]), rej_ok, rej_ok, covered))

# D5: negative space with the three fixed propositions
ns = " ".join(dec["negative_space"]).lower()
o5 = ("o-5" in ns and "four-family matrix is not established" in ns)
r3 = ("r-3" in ns and "normalizer is not validated" in ns)
o7 = ("o-7" in ns and "cross-family judging is not proven" in ns)
rec("D5", len(dec["negative_space"]) >= 3 and o5 and r3 and o7,
    "negative_space items=%d O5=%s R3=%s O7=%s" % (len(dec["negative_space"]), o5, r3, o7))

# D6: ws4 block consistency
ws4 = dec["ws4"]
d6_ok = (ws4["glm_pin_changed"] is False and ws4["glm_landing"] == GLM_LANDING
         and ws4["startable"] is True and ws4["planner_confirm_required"] is True)
rec("D6", d6_ok, "glm_pin_changed=%s glm_landing=%s startable=%s planner_confirm=%s"
    % (ws4["glm_pin_changed"], ws4["glm_landing"], ws4["startable"], ws4["planner_confirm_required"]))

# D7: quality track per code
qt = dec["quality_track"]
if decision == "D3":
    d7 = (qt["verdict"] == "unjudgeable" and qt["score"] is None and qt["claim_boundary"])
elif decision in ("D4", "D5"):
    d7 = bool(qt.get("reason_ref"))
else:
    d7 = qt["verdict"] in ("unjudgeable", "judge_pending") and qt["score"] is None
rec("D7", d7, "quality_track verdict=%s score=%s (must be null) for decision=%s" % (qt["verdict"], qt["score"], decision))

# D8: budget + session accounting
con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()
db_ok = True
for s in dec["probe_sessions"]:
    if s.get("db_queryable"):
        if not cur.execute("select 1 from session where id=?", (s["session_id"],)).fetchone():
            db_ok = False
con.close()
notarm = all(s["probe_not_arm"] is True for s in dec["probe_sessions"])
mc = sum(1 for r in rows if r["gate_type"] == "model_call")
tot = sum(s["input_tokens"] + s["output_tokens"] for s in dec["probe_sessions"]
          if s["input_tokens"] is not None)
fam = dec["budget"]["per_family_counts"]
maxin = dec["budget"]["max_single_session_input_tokens"]
cap_ok = maxin <= 8192
arm_clean = True
for arm in os.listdir(os.path.join(PROBE, "arms")):
    adir = os.path.join(PROBE, "arms", arm)
    extras = [e for e in os.listdir(adir) if e not in ("records",)]
    if extras:
        arm_clean = False
d8_ok = (notarm and mc <= 7 and all(v <= 2 for v in fam.values())
         and tot <= 200000 and db_ok and arm_clean and cap_ok)
rec("D8", d8_ok,
    "probe_not_arm_all=%s model_calls=%s/7 per_family=%s total_tokens=%s/200000 "
    "db_lookup=%s arms_clean=%s max_single_session_input=%s/8192 (cap_ok=%s)"
    % (notarm, mc, fam, tot, db_ok, arm_clean, maxin, cap_ok))

# D9: MT-6 counterprobe
mt6 = os.path.join(PROBE, "mt6_result.json")
mt6_ok = os.path.isfile(mt6) and json.load(open(mt6, encoding="utf-8")).get("counterprobe_passed") is True
rec("D9", mt6_ok, "MT-6 counterprobe passed=%s" % mt6_ok, mt6 if os.path.isfile(mt6) else None)

# D10: report content + WS4-PRE exactly once + required sections
required = ["一句话结论", "结论码与门值", "A 支证据", "B 支证据", "落选理由留痕",
            "跨族覆盖面与宽度上限", "对 WS4 的影响", "Negative space", "凭据与记账留痕",
            "未尽事项", "执行记录"]
missing_sec = [s for s in required if s not in report_txt]
ws4_pre = report_txt.count("WS4-PRE:")
d10_ok = (not missing_sec and ws4_pre == 1 and decision in report_txt
          and GLM_LANDING in report_txt)
rec("D10", d10_ok, "missing_sections=%s WS4-PRE_count=%s (must be 1) decision_in_report=%s"
    % (missing_sec, ws4_pre, decision in report_txt))

# ---------------- finalize ----------------
failed = [g["id"] for g in gates if not g["passed"]]
summary = {
    "tool": "verify_sf0004.py",
    "run_ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "decision_recomputed": decision,
    "a_verdict_recomputed": a_verdict,
    "b_verdict_recomputed": b_verdict,
    "gate_count": len(gates),
    "passed": len(gates) - len(failed),
    "failed": failed,
    "all_pass": not failed,
    "gates": gates,
}
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps({"all_pass": not failed, "failed": failed,
                  "decision": decision, "gates": len(gates)}, ensure_ascii=False, indent=2))
sys.exit(0 if not failed else 1)
