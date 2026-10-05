"""SF-0004 opening snapshot: G3 (porcelain), G4 (evalkit tree), G5 (global config sha256), env inventory.

Reads only. Writes only into $PROBE. No shell redirection (PLAN R-7).
"""
import hashlib
import json
import os
import subprocess
import sys

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
EK = r"D:\new-workspace\agent-asset\evalkit"
AFP = r"D:\new-workspace\agent-asset\afp-clone"
USERPROFILE = os.environ["USERPROFILE"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def w(path, obj):
    full = os.path.join(PROBE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    return full


# ---- G3: afp-clone porcelain ----
r = subprocess.run(["git", "-C", AFP, "status", "--porcelain"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
porcelain = r.stdout.splitlines()
w("g3-porcelain-before.json", {"cmd": "git -C afp-clone status --porcelain",
                               "exit_code": r.returncode, "line_count": len(porcelain),
                               "lines": porcelain})

# ---- G4: evalkit full tree relative-path listing ----
tree = []
for dirpath, dirnames, filenames in os.walk(EK):
    dirnames.sort()
    for fn in sorted(filenames):
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, EK).replace("\\", "/")
        tree.append(rel)
tree.sort()
w("g4-ek-tree-before.json", {"root": EK, "file_count": len(tree), "files": tree})

# ---- G5: global config sha256 (never modified by this card) ----
cfg = {
    "ZCFG": os.path.join(USERPROFILE, ".zcode", "cli", "config.json"),
    "V2CFG": os.path.join(USERPROFILE, ".zcode", "v2", "provider_config.json"),
    "KCFG": os.path.join(USERPROFILE, ".kimi-code", "config.toml"),
}
cfg_out = {}
for k, p in cfg.items():
    cfg_out[k] = {"path": p, "exists": os.path.isfile(p),
                  "sha256": sha256_file(p) if os.path.isfile(p) else None}
w("g5-config-sha256-before.json", cfg_out)

# ---- environment inventory ----
db = os.path.join(USERPROFILE, ".zcode", "cli", "db", "db.sqlite")
env = {
    "db": {"path": db, "exists": os.path.isfile(db),
           "size_bytes": os.path.getsize(db) if os.path.isfile(db) else None},
    "kimi": {"path": r"D:\tools\bin\kimi.exe", "exists": os.path.isfile(r"D:\tools\bin\kimi.exe")},
    "python": sys.version,
}
vendor = os.path.join(os.environ["APPDATA"], "npm", "node_modules", "zcode-app-cli", "vendor", "zcode.cjs")
env["vendor_bundle"] = {"path": vendor, "exists": os.path.isfile(vendor),
                        "size_bytes": os.path.getsize(vendor) if os.path.isfile(vendor) else None}
w("p0-env-inventory.json", env)

print(json.dumps({"porcelain_lines": len(porcelain),
                  "ek_files": len(tree),
                  "db_exists": env["db"]["exists"],
                  "db_size_gb": round(env["db"]["size_bytes"] / 1024**3, 2) if env["db"]["size_bytes"] else None,
                  "kimi_exists": env["kimi"]["exists"],
                  "vendor_exists": env["vendor_bundle"]["exists"],
                  "config_present": {k: v["exists"] for k, v in cfg_out.items()}},
                 ensure_ascii=False, indent=2))
