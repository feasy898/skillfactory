#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-02（EI-0）独立复核：每臂 telemetry.json 含 session_id；db session.directory ==
臂目录绝对路径；model_usage 该 session ≥1 行。独立 sqlite ro join，不信任编排器自报。
退出码：0 全过 / 1 有红。"""

import importlib.util
import json
import os
import sqlite3
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0006-b-smoke-2")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
ARMS = {
    "glm-baseline": os.path.join(RUN, "glm", "baseline"),
    "glm-treatment": os.path.join(RUN, "glm", "treatment"),
    "minimax-baseline": os.path.join(RUN, "minimax", "baseline"),
    "minimax-treatment": os.path.join(RUN, "minimax", "treatment"),
}


def main():
    out = {}
    ok_all = True
    for name, arm_dir in ARMS.items():
        arm_abs = os.path.abspath(arm_dir)
        tele_path = os.path.join(arm_abs, "records", "telemetry.json")
        item = {"arm_dir": arm_abs, "telemetry_exists": os.path.isfile(tele_path)}
        if item["telemetry_exists"]:
            with open(tele_path, "r", encoding="utf-8") as f:
                tele = json.load(f)
            sid = tele.get("session_id")
            item["session_id"] = sid
            item["has_session_id"] = bool(sid)
            if sid:
                con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
                con.row_factory = sqlite3.Row
                try:
                    srow = con.execute("select directory from session where id=?",
                                       (sid,)).fetchone()
                    n = con.execute("select count(*) c from model_usage where session_id=?",
                                    (sid,)).fetchone()["c"]
                finally:
                    con.close()
                item["db_session_found"] = srow is not None
                item["db_directory"] = srow["directory"] if srow else None
                item["directory_eq_armdir"] = bool(srow) and (
                    os.path.normcase(srow["directory"]) == os.path.normcase(arm_abs))
                item["model_usage_rows"] = n
                item["ok"] = bool(sid) and item["directory_eq_armdir"] and n >= 1
            else:
                item["ok"] = False
        else:
            item["ok"] = False
        ok_all = ok_all and item["ok"]
        out[name] = item
    out["all_ok"] = ok_all
    dest = os.path.join(RUN, "precheck", "b02-db-join-verify.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
