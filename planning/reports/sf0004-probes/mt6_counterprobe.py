"""SF-0004 MT-6 counterprobe (TESTS MT-6 / acceptance D9).

Discipline: "每批次随机挑 1 门把 expected 改错跑一次，确认它红，然后改回" and
"还原后 sha256 与改前相等". A gate that cannot go red is a rubber stamp.

Implementation: pick a random decision field, corrupt it, run the real aggregator as a
subprocess, assert it exits 1 (red), restore byte-for-byte, assert sha256 equality.
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import time

PROBE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(PROBE)
JSONOUT = os.path.join(PR, "SF-0004-decision.json")
OUT = os.path.join(PROBE, "mt6_result.json")
VERIFIER = os.path.join(PROBE, "verify_sf0004.py")

MUTATIONS = [
    ("a_verdict", lambda d: d.__setitem__("a_verdict", "NotViable")),
    ("b_verdict", lambda d: d.__setitem__("b_verdict", "Viable")),
    ("decision", lambda d: d.__setitem__("decision", "D3")),
    ("table_id", lambda d: d.__setitem__("table_id", "WRONG-TABLE")),
    ("ws4.glm_pin_changed", lambda d: d["ws4"].__setitem__("glm_pin_changed", True)),
    ("quality_track.score", lambda d: d["quality_track"].__setitem__("score", 0)),
    ("quality_track.verdict", lambda d: d["quality_track"].__setitem__("verdict", "judgeable")),
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run_verifier():
    r = subprocess.run([sys.executable, VERIFIER], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, (r.stdout or "")


def main():
    original = open(JSONOUT, "rb").read()
    before_sha = hashlib.sha256(original).hexdigest()

    target, mutator = random.choice(MUTATIONS)
    doc = json.loads(original.decode("utf-8"))
    mutator(doc)

    result = {"gate": "MT-6", "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "mutated_field": target, "sha256_before": before_sha,
              "counterprobe_passed": False}

    try:
        with open(JSONOUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        rc, out = run_verifier()
        result["mutated_verifier_exit_code"] = rc
        result["mutated_verifier_stdout"] = out.strip()[:1500]
        went_red = rc != 0
        result["went_red"] = went_red
    finally:
        with open(JSONOUT, "wb") as f:
            f.write(original)

    after_sha = hashlib.sha256(open(JSONOUT, "rb").read()).hexdigest()
    result["sha256_after"] = after_sha
    result["restored_identical"] = (after_sha == before_sha)

    # Re-run the verifier on the restored file so verify-sf0004.json reflects true state.
    rc2, out2 = run_verifier()
    result["restored_verifier_exit_code"] = rc2
    result["counterprobe_passed"] = bool(went_red and result["restored_identical"])

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"mutated_field": target, "went_red": went_red,
                      "restored_identical": result["restored_identical"],
                      "counterprobe_passed": result["counterprobe_passed"],
                      "restored_verifier_exit_code": rc2}, ensure_ascii=False, indent=2))
    return 0 if result["counterprobe_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
