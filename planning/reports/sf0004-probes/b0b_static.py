"""SF-0004 B0b: static census for workflow per-actor cwd support (zero model cost).

1) PRAGMA dwf_actor must have no cwd column.
2) Declared token-set grep over the vendor bundle for a per-actor directory field.
   The token set is declared HERE, before the run, so the gate cannot be tuned to pass.
"""
import json
import os
import re
import sqlite3

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
DB = os.path.join(os.environ["USERPROFILE"], ".zcode", "cli", "db", "db.sqlite")
VENDOR = os.path.join(os.environ["APPDATA"], "npm", "node_modules",
                      "zcode-app-cli", "vendor", "zcode.cjs")

DECLARED_TOKENS = [
    "actor_cwd", "actorCwd", "perActorCwd", "per_actor_cwd",
    "actorWorkingDirectory", "actor_working_directory",
    "actorDir", "actor_dir", "actorPath", "actor_path",
]


def main():
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(dwf_actor)").fetchall()]
    con.close()
    has_cwd = "cwd" in cols

    with open(VENDOR, "r", encoding="utf-8", errors="replace") as f:
        bundle = f.read()

    hits = {}
    for t in DECLARED_TOKENS:
        n = len(re.findall(re.escape(t), bundle))
        if n:
            hits[t] = n

    out = {
        "dwf_actor_columns": cols,
        "dwf_actor_has_cwd_column": has_cwd,
        "declared_token_set": DECLARED_TOKENS,
        "token_hits": hits,
        "perActorCwdFieldFound": bool(hits),
        "vendor_bundle": VENDOR,
        "note": "A hit would only mean the string exists somewhere in a 14.8MB bundle; "
                "a functional per-actor cwd would additionally require the field to reach "
                "dwf_actor / the actor runtime. Absent column plus absent per-actor "
                "directory field: static negative.",
    }
    path = os.path.join(PROBE, "p-b0-static.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"dwf_actor_has_cwd_column": has_cwd,
                      "perActorCwdFieldFound": bool(hits),
                      "token_hits": hits, "columns": cols},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
