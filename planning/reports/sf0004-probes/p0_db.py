"""SF-0004 P2 + P3: db schema (PRAGMA table_info) and read-only inventory.

Read-only: mode=ro URI. No COPY / VACUUM / CREATE INDEX. Writes only into $PROBE.
"""
import json
import os
import sqlite3
import sys

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
DB = os.path.join(os.environ["USERPROFILE"], ".zcode", "cli", "db", "db.sqlite")
TABLES = ["session", "model_usage", "tool_usage", "dwf_actor", "dwf_run"]


def w(path, obj):
    full = os.path.join(PROBE, path)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return full


con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()

# ---- P2: PRAGMA table_info verbatim for five tables ----
schema = {"db_path": DB, "open_mode": "mode=ro (URI)", "tables": {}, "rowcount": {}}
cols_by_table = {}
for t in TABLES:
    cols = cur.execute("PRAGMA table_info(%s)" % t).fetchall()
    cols_by_table[t] = [{"cid": c[0], "name": c[1], "type": c[2], "notnull": c[3],
                         "dflt_value": c[4], "pk": c[5]} for c in cols]
    schema["tables"][t] = cols_by_table[t]
    try:
        schema["rowcount"][t] = cur.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
    except Exception as e:  # pragma: no cover
        schema["rowcount"][t] = "ERROR: " + repr(e)

# missing_columns: card-carried facts vs actual reality (no same-kind substitution)
schema["card_fact_check"] = {
    "dwf_actor_has_cwd_column": any(c["name"] == "cwd" for c in cols_by_table["dwf_actor"]),
    "session_has_directory": any(c["name"] == "directory" for c in cols_by_table["session"]),
    "session_has_task_type": any(c["name"] == "task_type" for c in cols_by_table["session"]),
    "dwf_run_has_cwd": any(c["name"] == "cwd" for c in cols_by_table["dwf_run"]),
    "model_usage_has_model_id": any(c["name"] == "model_id" for c in cols_by_table["model_usage"]),
    "model_usage_has_provider_id": any(c["name"] == "provider_id" for c in cols_by_table["model_usage"]),
}
w("db-schema.json", schema)

# ---- P3: model_usage counts by (model_id, provider_id) ----
rows = cur.execute(
    "SELECT model_id, provider_id, count(*) AS n, "
    "sum(coalesce(input_tokens,0)), sum(coalesce(output_tokens,0)) "
    "FROM model_usage GROUP BY model_id, provider_id ORDER BY n DESC"
).fetchall()
inv = {
    "source_db": DB,
    "anchor_expected": "GLM-5.3 row must be present (positive control)",
    "group_by": ["model_id", "provider_id"],
    "total_rows": sum(r[2] for r in rows),
    "rows": [{"model_id": r[0], "provider_id": r[1], "count": r[2],
              "input_tokens": r[3], "output_tokens": r[4]} for r in rows],
}
inv["glm53_row_present"] = any(r[0] == "GLM-5.3" for r in rows)
inv["glm53_row_count"] = next((r[2] for r in rows if r[0] == "GLM-5.3"), None)
inv["glm53flash_row_count"] = next((r[2] for r in rows if r[0] == "GLM-5.3-Flash"), None)
w("p0-db-inventory.json", inv)

# ---- db channel anchor: distinct session task_type enumeration ----
tt = cur.execute("SELECT task_type, count(*) FROM session GROUP BY task_type ORDER BY 2 DESC").fetchall()

print(json.dumps({
    "dwf_actor_columns": [c["name"] for c in cols_by_table["dwf_actor"]],
    "dwf_run_rows": schema["rowcount"]["dwf_run"],
    "dwf_actor_rows": schema["rowcount"]["dwf_actor"],
    "model_usage_rows": inv["total_rows"],
    "glm53_row_present": inv["glm53_row_present"],
    "glm53_count": inv["glm53_row_count"],
    "glm53flash_count": inv["glm53flash_row_count"],
    "distinct_model_providers": len(rows),
    "task_type_enumeration": [{"task_type": r[0], "n": r[1]} for r in tt],
}, ensure_ascii=False, indent=2))
con.close()
