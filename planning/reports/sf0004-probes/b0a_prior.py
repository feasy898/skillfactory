"""SF-0004 B0a: zero-cost historical prior for workflow per-actor cwd (PLAN §9.1 R-2).

Query caliber is fixed by the acceptance file:
    dwf_actor JOIN session, GROUP BY run_id, count(distinct directory)
NO time-window approximation is permitted (concurrent slots would misattribute arms).
"""
import argparse
import json
import os
import sqlite3

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(os.environ["USERPROFILE"], ".zcode",
                                                 "cli", "db", "db.sqlite"))
    a = ap.parse_args(argv)

    con = sqlite3.connect("file:" + a.db.replace("\\", "/") + "?mode=ro", uri=True)
    cur = con.cursor()

    rows = cur.execute(
        "select a.run_id, count(*) as actors, "
        "count(distinct s.directory) as n_distinct_dir, "
        "sum(case when s.directory is null then 1 else 0 end) as null_dirs "
        "from dwf_actor a left join session s on s.id = a.session_id "
        "group by a.run_id"
    ).fetchall()

    runs_total = len(rows)
    runs_with_ge2_actors = sum(1 for r in rows if (r[1] or 0) >= 2)
    max_nd = max((r[2] or 0) for r in rows) if rows else 0
    runs_gt1 = sum(1 for r in rows if (r[2] or 0) > 1)
    actors_null_dir = sum((r[3] or 0) for r in rows)
    actors_total = sum((r[1] or 0) for r in rows)

    hist = [{"run_id": r[0], "actors": r[1], "n_distinct_directory": r[2],
             "null_directory_rows": r[3]} for r in rows
            if (r[2] or 0) > 1]

    out = {
        "db": a.db,
        "open_mode": "mode=ro (URI)",
        "query": "select a.run_id, count(*), count(distinct s.directory), "
                 "sum(case when s.directory is null then 1 else 0 end) "
                 "from dwf_actor a left join session s on s.id = a.session_id group by a.run_id",
        "query_caliber": "dwf_actor JOIN session GROUP BY run_id count(distinct directory); "
                         "NO time-window approximation used",
        "runs_total": runs_total,
        "runs_with_ge2_actors": runs_with_ge2_actors,
        "max_distinct_directory_per_run": max_nd,
        "runs_with_distinct_gt1": runs_gt1,
        "history_silent": bool(max_nd <= 1),
        "dwf_actor_rows_total": actors_total,
        "actors_with_null_session_directory": actors_null_dir,
        "runs_with_multiple_directories": hist,
        "card_fact_check": "card asserts runs with distinct directory>1 == 0 (471 runs); "
                           "live db has grown since the card was written",
    }
    path = os.path.join(PROBE, "p-b0-prior.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    con.close()
    print(json.dumps({k: out[k] for k in ("runs_total", "runs_with_ge2_actors",
                                          "max_distinct_directory_per_run",
                                          "runs_with_distinct_gt1", "history_silent",
                                          "dwf_actor_rows_total",
                                          "actors_with_null_session_directory")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
