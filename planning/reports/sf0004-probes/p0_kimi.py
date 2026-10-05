"""SF-0004 P4: kimi CLI version + config.toml structure recon.

Secret discipline: only key names, provider ids, model ids are recorded.
api_key / token / secret values never enter any artifact or stdout.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

PROBE = r"D:\new-workspace\agent-asset\planning\reports\sf0004-probes"
KCFG = os.path.join(os.environ["USERPROFILE"], ".kimi-code", "config.toml")
KIMI = r"D:\tools\bin\kimi.exe"
SECRETISH = re.compile(r"(api[_-]?key|token|secret|password|credential)", re.I)


def w(path, obj):
    with open(os.path.join(PROBE, path), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return os.path.join(PROBE, path)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ---- version ----
ver = {}
for args in (["--version"], ["version"]):
    try:
        r = subprocess.run([KIMI] + args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        ver[args[0]] = {"exit_code": r.returncode, "stdout": (r.stdout or "").strip()[:2000],
                        "stderr": (r.stderr or "").strip()[:2000]}
    except Exception as e:
        ver[args[0]] = {"error": repr(e)}

# ---- config.toml structure (redacted) ----
try:
    import tomllib
    with open(KCFG, "rb") as f:
        data = tomllib.load(f)
except Exception as e:
    data = None
    ver["toml_parse_error"] = repr(e)

IDENT = ("id", "name", "model", "provider", "base_url", "kind", "type")


def redact(node, depth=0):
    """Return structure with secret-ish values replaced by a boolean marker."""
    if depth > 6:
        return "<depth-limit>"
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if SECRETISH.search(str(k)):
                out[k] = "<REDACTED:%s>" % ("present" if v else "absent")
            else:
                out[k] = redact(v, depth + 1)
        return out
    if isinstance(node, list):
        return [redact(v, depth + 1) for v in node]
    if isinstance(node, str):
        return node if len(node) <= 300 else node[:300] + "...<truncated>"
    return node


identifiers = {}


def collect_identifiers(node, trail=""):
    """Harvest only providerId / providerName / modelId style identifiers (allowed by card)."""
    if isinstance(node, dict):
        for k, v in node.items():
            t = trail + "." + str(k) if trail else str(k)
            if isinstance(v, (str, int, float, bool)) and any(
                    t.lower().endswith(s) for s in IDENT):
                identifiers[t] = v
            elif SECRETISH.search(str(k)):
                identifiers[t] = "<REDACTED:present>"
            else:
                collect_identifiers(v, t)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            collect_identifiers(v, trail)


if data is not None:
    collect_identifiers(data)

recon = {
    "kimi_exe": KIMI,
    "kimi_exists": os.path.isfile(KIMI),
    "kimi_sha256": sha256_file(KIMI) if os.path.isfile(KIMI) else None,
    "version_probe": ver,
    "config_path": KCFG,
    "config_sha256": sha256_file(KCFG) if os.path.isfile(KCFG) else None,
    "config_structure_redacted": redact(data) if data is not None else None,
    "identifiers_only": identifiers,
    "secret_policy": "api_key/token/secret/password values never recorded; only presence booleans",
}
w("p0-kimi-recon.json", recon)

print(json.dumps({
    "kimi_version_stdout": ver.get("--version", {}).get("stdout"),
    "kimi_version_exit": ver.get("--version", {}).get("exit_code"),
    "config_sha256_prefix": (recon["config_sha256"] or "")[:16],
    "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else None,
    "identifiers": identifiers,
}, ensure_ascii=False, indent=2)[:4000])
