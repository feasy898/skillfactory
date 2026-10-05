"""SF-0004 G6: secret scanner with a mandatory bidirectional selfcheck.

Discipline (acceptance G6 / TESTS MT-2):
  * --selfcheck must pass BOTH ways: a clean sample must NOT be flagged, and a planted
    `sk-FAKE...` MUST be flagged. A negative gate with no positive control is unverified.
  * On a hit the artifact is fixed (placeholder); the scanner is NEVER loosened to pass.

Patterns are the acceptance-file minimum set.
"""
import argparse
import os
import re
import sys

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
REPORT = r"D:\new-workspace\agent-asset\planning\reports\SF-0004-single-family-decision.md"
JSONOUT = r"D:\new-workspace\agent-asset\planning\reports\SF-0004-decision.json"

PATTERNS = [
    ("sk_key", re.compile(r"sk-[A-Za-z0-9]{8,}")),
    ("bearer_token", re.compile(r"Bearer [A-Za-z0-9_\-\.]{8,}")),
    ("assigned_secret", re.compile(r"(api_key|token|secret|password)\s*[:=]")),
]
TEXT_EXT = {".md", ".json", ".jsonl", ".py", ".txt", ".toml", ".cfg", ".ini", ".yaml", ".yml"}

# Clean sample: mentions the topic but contains no assignable secret.
CLEAN_SAMPLE = (
    "# clean sample\n"
    "The config has an api_key field. Its value is never printed.\n"
    "token_present is recorded as a boolean only.\n"
    "Model id: account:bigmodel-individual-coding-plan/GLM-5.3\n"
)
# Planted positives: one per pattern class. Built at runtime from fragments so the
# scanner's own source never contains a literal secret-shaped string -- that keeps this
# file inside its own scan coverage instead of requiring the scanner to be exempted.
# Detection strength is unchanged: the same assembled bytes are what gets scanned.
DIRTY_SAMPLES = [
    "sk" + "-" + "FAKE0123456789abcdefGHIJKL" + "\n",
    "Authorization: Bearer " + "abcdef0123456789XYZ" + "\n",
    "api_" + "key = " + "FAKEVALUE0123456789" + "\n",
]


def scan_text(text):
    hits = []
    for name, pat in PATTERNS:
        for m in pat.finditer(text):
            hits.append({"pattern": name, "match": m.group(0)[:80],
                         "offset": m.start()})
    return hits


def scan_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        return [{"path": path, "error": repr(e)}]
    hits = scan_text(text)
    return [{"path": path, **h} for h in hits]


def selfcheck():
    clean_hits = scan_text(CLEAN_SAMPLE)
    dirty_results = []
    for s in DIRTY_SAMPLES:
        h = scan_text(s)
        dirty_results.append({"sample_kind": "planted", "detected": bool(h),
                              "patterns": sorted({x["pattern"] for x in h})})
    ok = (len(clean_hits) == 0
          and all(r["detected"] for r in dirty_results))
    return {"clean_sample_flagged": bool(clean_hits), "planted": dirty_results,
            "selfcheck_pass": ok}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--roots", nargs="*", default=[])
    a = ap.parse_args(argv)

    if a.selfcheck:
        r = selfcheck()
        print("selfcheck: clean_sample_flagged=%s planted=%s => %s"
              % (r["clean_sample_flagged"],
                 [(x["sample_kind"], x["detected"]) for x in r["planted"]],
                 "PASS" if r["selfcheck_pass"] else "FAIL"))
        return 0 if r["selfcheck_pass"] else 1

    files = []
    for root in a.roots:
        if os.path.isfile(root):
            files.append(root)
            continue
        for dp, dn, fn in os.walk(root):
            for name in fn:
                files.append(os.path.join(dp, name))
    hits = []
    scanned = 0
    for p in files:
        if os.path.splitext(p)[1].lower() not in TEXT_EXT:
            continue
        scanned += 1
        hits.extend(scan_file(p))
    print("scanned %d text files under %s" % (scanned, a.roots))
    if hits:
        print("SECRET SCAN HITS: %d" % len(hits))
        for h in hits[:40]:
            print("  %s [%s] %r" % (h.get("path"), h.get("pattern"), h.get("match")))
        return 1
    print("no secret-shaped strings found")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
