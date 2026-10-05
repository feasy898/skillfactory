"""SF-0004 closing guards: G1 freeze, G2 oracle verify, G3 porcelain, G4 evalkit tree, G5 config sha256.

Each guard writes its own evidence file under $PROBE and records the diff against the
opening snapshot, so the verdict is machine-checkable rather than narrated.
"""
import hashlib
import json
import os
import subprocess

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
EK = r"D:\new-workspace\agent-asset\evalkit"
AFP = r"D:\new-workspace\agent-asset\afp-clone"
ASSET_ORACLE = os.path.join(AFP, "zcode-research", "skillfactory", "v5",
                            "assets", "speaker-mapping", "oracle")
USERPROFILE = os.environ["USERPROFILE"]


def w(path, obj):
    with open(os.path.join(PROBE, path), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


results = {}

# ---- G1: device freeze ----
rc, out, err = run(["python", "harness/freeze_device.py", "verify"], cwd=EK)
results["G1"] = {"command": "python harness/freeze_device.py verify (cwd=$EK)",
                 "exit_code": rc, "stdout": out.strip()[:800], "stderr": err.strip()[:400],
                 "pass": rc == 0 and "钉版一致" in out}
w("g1-freeze-verify-closing.json", results["G1"])

# ---- G2: oracle verify against opening record ----
rc, out, err = run(["python", "harness/oracle_gate.py", "verify", "--root", ASSET_ORACLE,
                    "--record", os.path.join(PROBE, "oracle-before.json")], cwd=EK)
try:
    gj = json.loads(out.strip())
except Exception as e:
    gj = {"parse_error": repr(e)}
results["G2"] = {"command": "python harness/oracle_gate.py verify --record $PROBE/oracle-before.json",
                 "exit_code": rc, "stdout": out.strip()[:1200], "stderr": err.strip()[:400],
                 "unchanged": gj.get("unchanged"),
                 "baseline_tree_sha256": gj.get("baseline_tree_sha256"),
                 "current_tree_sha256": gj.get("current_tree_sha256"),
                 "file_count": gj.get("current_file_count"),
                 "pass": rc == 0 and gj.get("unchanged") is True
                 and gj.get("current_tree_sha256") == gj.get("baseline_tree_sha256")}
w("g2-oracle-verify-closing.json", results["G2"])

# ---- G3: porcelain diff ----
rc, out, err = run(["git", "-C", AFP, "status", "--porcelain"])
now = out.splitlines()
with open(os.path.join(PROBE, "g3-porcelain-before.json"), encoding="utf-8") as f:
    before = json.load(f)
before_set, now_set = set(before["lines"]), set(now)
added, removed = sorted(now_set - before_set), sorted(before_set - now_set)
FROZEN = ["peidian", "qw-arena2", "ohos-tailscale", "video-capability", "chenmai8", "xuexing-agent"]
results["G3"] = {"command": "git -C afp-clone status --porcelain (closing) vs opening",
                 "exit_code": rc, "before_count": len(before_set), "after_count": len(now_set),
                 "added": added, "removed": removed,
                 "frozen_area_intersection": [x for x in added + removed
                                              if any("/" + z + "/" in x or x.lstrip(" ?").startswith(z)
                                                     for z in FROZEN)],
                 "pass": rc == 0 and not added and not removed}
w("g3-porcelain-closing.json", results["G3"])

# ---- G4: evalkit tree diff ----
tree = []
for dirpath, dirnames, filenames in os.walk(EK):
    dirnames.sort()
    for fn in sorted(filenames):
        tree.append(os.path.relpath(os.path.join(dirpath, fn), EK).replace("\\", "/"))
tree.sort()
with open(os.path.join(PROBE, "g4-ek-tree-before.json"), encoding="utf-8") as f:
    before_tree = json.load(f)["files"]
a, b = set(tree), set(before_tree)
results["G4"] = {"root": EK, "before_count": len(before_tree), "after_count": len(a),
                 "added": sorted(a - b), "removed": sorted(b - a),
                 "pass": not (a - b) and not (b - a)}
w("g4-ek-tree-closing.json", results["G4"])

# ---- G5: global config sha256 equality ----
cfg = {"ZCFG": os.path.join(USERPROFILE, ".zcode", "cli", "config.json"),
       "V2CFG": os.path.join(USERPROFILE, ".zcode", "v2", "provider_config.json"),
       "KCFG": os.path.join(USERPROFILE, ".kimi-code", "config.toml")}
with open(os.path.join(PROBE, "g5-config-sha256-before.json"), encoding="utf-8") as f:
    before_cfg = json.load(f)
now_cfg, same = {}, True
for k, p in cfg.items():
    now_cfg[k] = {"path": p, "sha256": sha256_file(p) if os.path.isfile(p) else None}
    if now_cfg[k]["sha256"] != before_cfg[k]["sha256"]:
        same = False
results["G5"] = {"before": before_cfg, "after": now_cfg, "all_equal": same,
                 "pass": same,
                 "note": "no try/finally temporary modification was declared or needed; "
                         "M1 used env-scoped derived copies under secret-scratch, never the "
                         "global files, so no config-restore.json is required."}
w("g5-config-sha256-closing.json", results["G5"])

summary = {k: results[k]["pass"] for k in results}
w("closing-guards-summary.json", {"results": results, "pass": summary,
                                  "all_pass": all(summary.values())})
print(json.dumps({"pass": summary, "all_pass": all(summary.values()),
                  "g3_added": added, "g4_added": results["G4"]["added"]},
                 ensure_ascii=False, indent=2))
