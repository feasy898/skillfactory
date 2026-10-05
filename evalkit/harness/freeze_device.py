#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/freeze_device.py — 装置钉版（TESTS EI-23：装置钉版判分器指纹）。

冻结「改判分器/阈值凑绿」：把装置自身的关键文件（判分器、evaluators、harness）连同 sha256
写成 keyfiles.sha256，**相对路径**（旧版 19 条绝对 Linux 路径 + oracle/out 零覆盖，
实测不可照抄，轨迹10 C5）。`verify` 前后各跑一次，不一致即 fail。

用法：
    python freeze_device.py freeze --evalkit <根>
    python freeze_device.py verify --evalkit <根> [--record <keyfiles.sha256>]
退出码：0 通过 / 1 有漂移或缺件 / 2 用法错误。
"""

import argparse
import hashlib
import io
import os
import sys

KEY_GLOBS = [
    "packs/*/checks/run_check.py",
    "evaluators/*.py",
    "harness/*.py",
    "nc/*.py",
]


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def collect(evalkit):
    import glob
    out = {}
    for g in KEY_GLOBS:
        for p in sorted(glob.glob(os.path.join(evalkit, g))):
            rel = os.path.relpath(p, evalkit).replace(os.sep, "/")
            if "__pycache__" in rel:
                continue
            out[rel] = sha256_file(p)
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cmd", choices=["freeze", "verify"])
    ap.add_argument("--evalkit", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--record", default=None)
    args = ap.parse_args(argv)
    evalkit = os.path.abspath(args.evalkit)
    rec = args.record or os.path.join(evalkit, "harness", "keyfiles.sha256")

    cur = collect(evalkit)
    if not cur:
        print("没收集到关键文件，evalkit 路径可能不对: %s" % evalkit, file=sys.stderr)
        return 2

    if args.cmd == "freeze":
        with io.open(rec, "w", encoding="utf-8", newline="\n") as f:
            f.write("# evalkit 装置钉版（TESTS EI-23）· 相对路径 · 文本 LF 归一\n")
            for rel in sorted(cur):
                f.write("%s  %s\n" % (cur[rel], rel))
        print("已冻结 %d 个关键文件 -> %s" % (len(cur), rec))
        return 0

    if not os.path.isfile(rec):
        print("缺基线，先跑 freeze: %s" % rec, file=sys.stderr)
        return 2
    base = {}
    with io.open(rec, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sha, rel = line.split(None, 1)
            base[rel.strip()] = sha
    drift = []
    for rel in sorted(set(base) | set(cur)):
        if rel not in cur:
            drift.append({"path": rel, "issue": "missing_now"})
        elif rel not in base:
            drift.append({"path": rel, "issue": "new_file"})
        elif base[rel] != cur[rel]:
            drift.append({"path": rel, "issue": "changed"})
    if drift:
        print("装置漂移（判分器/阈值被改？）:")
        for d in drift:
            print("  %-10s %s" % (d["issue"], d["path"]))
        return 1
    print("装置钉版一致：%d 个关键文件 sha256 全对" % len(cur))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
