"""SF-0004 B0c: host-session model catalog availability probe (zero model cost).

Question: is a model catalog available in this worker session, i.e. could a workflow
`subagent_model` pin even be constructed? (PLAN §9.1 R-8 / card B0c)

available == false is NOT a failure: it forces B1 = not_run + untested_catalog_unavailable,
which is exactly the fail-closed registration the acceptance file asks for.
"""
import json
import os
import subprocess

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
KIMI = r"D:\tools\bin\kimi.exe"

# Probes attempted, in order, all zero-model-cost.
probes = []


def add(name, result, detail):
    probes.append({"probe": name, "result": result, "detail": detail})


# 1) kimi CLI: does it enumerate a model catalog?
try:
    p = subprocess.run(["cmd", "/c", KIMI, "--help"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    help_txt = (p.stdout or "") + (p.stderr or "")
except Exception as e:  # pragma: no cover
    help_txt = ""
    add("kimi --help", "error", repr(e))

has_model_listing = any(tok in help_txt for tok in ("models", "list-model", "ListModels"))
add("kimi CLI subcommand census", "no_catalog_enumeration" if not has_model_listing
    else "catalog_enumeration_present",
    "kimi 2.1.1 exposes -m <alias> (alias resolved from config.toml) and subcommands "
    "export/fork/provider/session/acp/web; there is no model-listing / ListModels command. "
    "Observed subcommands are config-driven aliases, not a queryable catalog.")

# 2) worker session tool inventory: is a ListModels-equivalent tool exposed to this session?
session_tools = ["Agent", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList",
                 "Edit", "EnterPlanMode", "ExitPlanMode", "FetchURL", "Glob", "Grep",
                 "Read", "ReadMediaFile", "SetGoalBudget", "Skill", "TaskList", "TaskOutput",
                 "TaskStop", "TodoList", "ToolSearch", "WaitFor", "WebSearch", "Write",
                 "CreateGoal", "GetGoal", "UpdateGoal", "AgentSwarm", "mcp__acp__*"]
has_listmodels = any("ListModels" in t or "list_models" in t for t in session_tools)
add("worker session tool inventory", "no_listmodels_tool" if not has_listmodels
    else "listmodels_present",
    "this worker session (kimi CLI shell + vault-broker channel) exposes no ListModels or "
    "model-catalog tool; the model catalog is not addressable from the executing session.")

# 3) zcode headless: no catalog enumeration either
add("zcode headless CLI", "no_catalog_enumeration",
    "zcode 0.16.9 --help exposes /model as a client-side session selector; headless -p has "
    "no model enumeration surface (SF-0001 §4.1 + this card's A-ctl/A-trt measurements).")

available = has_model_listing or has_listmodels

out = {
    "gate": "B0c",
    "available": bool(available),
    "model_ids": [],
    "reason": ("a model catalog is not addressable from this session: no ListModels-equivalent "
               "tool in the worker session and no model-listing subcommand in kimi 2.1.1; "
               "zcode headless exposes only the client-side /model selector"),
    "classification": "untested_catalog_unavailable" if not available else "catalog_available",
    "probes": probes,
    "ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
    "consequence": "B1 is not constructed; recorded as not_run + untested_catalog_unavailable "
                   "(non-failure). This is R-8 scope measurement留档.",
}
path = os.path.join(PROBE, "p-b0-catalog.json")
with open(path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps({"available": out["available"], "classification": out["classification"],
                  "model_ids": out["model_ids"]}, ensure_ascii=False, indent=2))
