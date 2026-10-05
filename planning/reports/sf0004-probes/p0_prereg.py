"""SF-0004 A0: mechanism pre-registration (P1). Runs BEFORE any model call.

Candidates must be a superset of what is actually executed (card §4 / acceptance P1).
Static (zero-model-cost) evidence is gathered here for each candidate.
"""
import hashlib
import json
import os
import re
import subprocess

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
SCRATCH = os.path.join(PROBE, "secret-scratch")
VENDOR = os.path.join(os.environ["APPDATA"], "npm", "node_modules",
                      "zcode-app-cli", "vendor", "zcode.cjs")
TARGET_PROVIDER = "minimax"
TARGET_MODEL = "Minimax-M3.1-Flash-Preview"

WIN_RESERVED = re.compile(r"^(NUL|CON|PRN|AUX|COM[1-9]|LPT[1-9])(\.|$)", re.I)


def w(path, obj):
    full = os.path.join(PROBE, path)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return full


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def grep_count(pattern):
    """Count literal occurrences of pattern in the vendor bundle (static evidence)."""
    with open(VENDOR, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    return len(re.findall(re.escape(pattern), data))


# ---- static evidence per candidate ----
static = {
    "resolveNodeProviderRuntimePaths_pairing_rule": {
        "literal": 'ZCode Built-in \\u4E0E Personal Provider Config',
        "occurrences": grep_count("Personal Provider Config"),
        "finding": "resolveNodeProviderRuntimePaths throws unless BOTH "
                   "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE and ZCODE_PERSONAL_PROVIDER_CONFIG_FILE "
                   "are provided; single-variable use is an immediate startup error.",
    },
    "ZCODE_ENABLED_AGENT_PROVIDERS_schema": {
        "literal": 'gir=m.array(zO).transform(()=>[...qpe])',
        "occurrences": grep_count(".transform(()=>[...qpe])"),
        "finding": "The env var is parsed then transformed to the constant default ['glm']; "
                   "supplied input is DISCARDED. Mechanism is statically dead -> no model call spent.",
    },
    "cwd_relative_provider_config_discovery": {
        "literal": "process.cwd()",
        "occurrences": grep_count("process.cwd()"),
        "finding": "personalFilePath resolves from environmentConfigRoot (~/.zcode/v2); "
                   "no cwd-relative provider-config discovery path was found in the bundle scan. "
                   "Skills discovery IS cwd-relative (SF-0001 R-1) but provider config is not.",
    },
    "builtin_minimax_template_exists": {
        "literal": '"minimax"',
        "occurrences": grep_count('"minimax"'),
        "finding": "vendor/provider/zcode-builtin.json carries a templateRule templateId=minimax, "
                   "so minimax is a known builtin template, not an unknown provider.",
    },
    "headless_model_flag_absent": {
        "note": "zcode 0.16.9 --help full option list contains no --model; "
                "/model is a client-side session selector (SF-0001 §4.1).",
    },
}

candidates = [
    {
        "id": "M1-paired-provider-config-env",
        "mechanism": "env-scoped provider config override: set BOTH "
                     "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE and ZCODE_PERSONAL_PROVIDER_CONFIG_FILE "
                     "to derived copies under secret-scratch; personal copy adds "
                     "config.defaultModelSelection={providerId:'minimax', modelId:'%s'} and "
                     "providerOrder ['minimax','new-provider']" % TARGET_MODEL,
        "planned_cmd": "python $PROBE\\p_zcode_head.py --label trt-1-m1 --mech m1 "
                       "--cwd-dir $PROBE\\arms\\trt-1-m1 "
                       "(spawns zcode.cmd/.exe/node+zcode.js with MSYS_NO_PATHCONV=1 and the two env vars)",
        "criterion": "exit 0 AND session.directory==arm dir AND model_usage joinable AND "
                     "model_id verbatim == '%s' AND provider_id lowercased contains 'minimax'" % TARGET_MODEL,
        "cost": "1 model call",
        "mutates_global_config": False,
        "static_evidence": ["resolveNodeProviderRuntimePaths_pairing_rule",
                            "builtin_minimax_template_exists",
                            "headless_model_flag_absent"],
        "planned": "RUN",
    },
    {
        "id": "M2-enabled-agent-providers",
        "mechanism": "env ZCODE_ENABLED_AGENT_PROVIDERS=minimax to enable minimax as builtin agent CLI provider",
        "planned_cmd": "(not executed)",
        "criterion": "N/A - statically falsified before spending a model call",
        "cost": "0 model calls",
        "mutates_global_config": False,
        "static_evidence": ["ZCODE_ENABLED_AGENT_PROVIDERS_schema"],
        "planned": "SKIP_STATIC_FALSIFIED",
        "skip_reason": "schema transform discards supplied input and returns the constant ['glm']",
    },
    {
        "id": "M3-slash-model-command",
        "mechanism": "headless prompt '/model minimax/Minimax-M3.1-Flash-Preview' before the task",
        "planned_cmd": "python $PROBE\\p_zcode_head.py --label trt-2-m3 --mech m3 --cwd-dir $PROBE\\arms\\trt-2-m3",
        "criterion": "same success shape as M1",
        "cost": "1 model call (only if M1 fails)",
        "mutates_global_config": False,
        "static_evidence": ["headless_model_flag_absent"],
        "planned": "RUN_IF_M1_FAILS",
        "prior": "SF-0001 §4.1 already measured /model as a client-side selector that does not "
                 "route model processing; retained as the second attempt for exhaustiveness.",
    },
    {
        "id": "M4-cli-config-provider-entry",
        "mechanism": "add a provider entry to ~/.zcode/cli/config.json under try/finally "
                     "backup-sha256 -> modify -> run -> restore -> compare protocol",
        "planned_cmd": "(not executed)",
        "criterion": "N/A",
        "cost": "0 model calls",
        "mutates_global_config": True,
        "static_evidence": [],
        "planned": "SKIP_LOWEST_PRIORITY",
        "skip_reason": "card ranks this lowest priority and it mutates a global config file; "
                       "only reachable if M1 and M3 both fail AND budget remains.",
    },
    {
        "id": "M5-probe-cwd-config-discovery",
        "mechanism": "probe-cwd level config discovery (drop .zcode/ beside the probe arm and "
                     "rely on cwd-relative discovery)",
        "planned_cmd": "(not executed)",
        "criterion": "N/A - statically falsified before spending a model call",
        "cost": "0 model calls",
        "mutates_global_config": False,
        "static_evidence": ["cwd_relative_provider_config_discovery"],
        "planned": "SKIP_STATIC_FALSIFIED",
        "skip_reason": "no cwd-relative provider-config discovery exists; skills discovery being "
                       "cwd-relative does not transfer to provider config.",
    },
]

prereg = {
    "task": "SF-0004",
    "registered_before_first_model_call": True,
    "target_provider_id": TARGET_PROVIDER,
    "target_model_id": TARGET_MODEL,
    "target_model_id_source": "verbatim from ~/.zcode/v2/provider_config.json modelConfigRules "
                              "(providerId=minimax, modelId=Minimax-M3.1-Flash-Preview, enabled=true); "
                              "matches db model_usage literal 'Minimax-M3.1-Flash-Preview' (5392 rows)",
    "success_shape": {
        "exit_code": 0,
        "session_directory_equals_arm_dir": True,
        "model_usage_joinable": True,
        "model_id_verbatim": TARGET_MODEL,
        "provider_id_lowercased_contains": TARGET_PROVIDER,
    },
    "budget_cap_model_calls": {"zcode_headless": 3, "ctl": 1, "trt_attempts": 2},
    "global_config_policy": "no global config is modified; scratch derived copies live under "
                            "$PROBE\\secret-scratch and are deleted with an existence assertion",
    "candidates": candidates,
    "static_evidence": static,
    "executed_mechanisms": [],
}

w("a0-prereg.json", prereg)

# G7: reserved Windows names + holdout numbering in produced filenames
produced = sorted(os.listdir(PROBE))
g7 = {
    "files_scanned": len(produced),
    "reserved_name_hits": [f for f in produced if WIN_RESERVED.match(f)],
    "holdout_numbering_hits": [f for f in produced if re.search(r"HO-\d+", f)],
    "ac_pass": not any(WIN_RESERVED.match(f) for f in produced)
    and not any(re.search(r"HO-\d+", f) for f in produced),
}
w("g7-filename-scan-before.json", g7)

print(json.dumps({
    "candidates": [c["id"] + ":" + c["planned"] for c in candidates],
    "candidate_count": len(candidates),
    "target": TARGET_PROVIDER + "/" + TARGET_MODEL,
    "g7": g7,
}, ensure_ascii=False, indent=2))
