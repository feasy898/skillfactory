"""SF-0004 A0 recon: structure of the personal provider config (redacted).

Rules: config.api / config.access values NEVER enter any artifact or stdout.
Only providerId / providerName / modelId identifiers and structure are recorded.
"""
import json
import os
import re

V2 = os.path.join(os.environ["USERPROFILE"], ".zcode", "v2", "provider_config.json")
BUILTIN = os.path.join(os.environ["APPDATA"], "npm", "node_modules",
                       "zcode-app-cli", "vendor", "provider", "zcode-builtin.json")
SECRETISH = re.compile(r"(api[_-]?key|token|secret|password|credential|access|headers)", re.I)


def shape(node, depth=0):
    if depth > 5:
        return "<depth>"
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if SECRETISH.search(str(k)):
                out[k] = "<REDACTED:%s>" % ("present" if v not in (None, "", [], {}) else "absent")
            else:
                out[k] = shape(v, depth + 1)
        return out
    if isinstance(node, list):
        return [shape(v, depth + 1) for v in node]
    if isinstance(node, str):
        return node if len(node) <= 200 else node[:200] + "..."
    return node


out = {}
for tag, path in (("personal_v2", V2), ("builtin_bundled", BUILTIN)):
    if not os.path.isfile(path):
        out[tag] = {"path": path, "exists": False}
        continue
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = data.get("config", data)
    pcr = cfg.get("providerConfigRules", {}) or {}
    mcr = cfg.get("modelConfigRules", {}) or {}
    out[tag] = {
        "path": path,
        "exists": True,
        "top_level_keys": sorted(data.keys()),
        "config_keys": sorted(cfg.keys()),
        "schemaVersion": data.get("schemaVersion"),
        "providerOrder": cfg.get("providerOrder"),
        "defaultModelSelection": cfg.get("defaultModelSelection"),
        "provider_ids": [p.get("providerId") for p in pcr.get("providerRules", [])],
        "provider_model_rules": [
            {"providerId": p.get("providerId"), "modelId": p.get("modelId"),
             "enabled": (p.get("config") or {}).get("enabled")}
            for p in (mcr.get("providerModelRules") or [])
        ],
        "manual_provider_model_rules": [
            {"providerId": p.get("providerId"), "modelId": p.get("modelId"),
             "enabled": (p.get("config") or {}).get("enabled")}
            for p in (mcr.get("manualProviderModelRules") or [])
        ],
        "shape_redacted": shape(data),
    }

print(json.dumps(out, ensure_ascii=False, indent=2))
