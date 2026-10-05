#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/isolation_probe.py — 臂隔离探针（TESTS EI-6；PLAN §5.4 步 1 abort 判据）。

对每棵臂目录树做 walk，查四类越界物：
    SKILL.md / oracle/ / eval/ / holdout/
零命中 = 通过；任一命中 = abort（不得开跑）。

为什么是 find 而不是看 CLI 报没报错：臂有没有摸到资产，看的是**目录树里有没有那些文件**，
不是它嘴上说什么。baseline 树能摸到 SKILL.md = 对照失效，整轮作废。

用法：python isolation_probe.py <arm 目录树> [<arm 目录树> ...] [--json <落盘路径>]
退出码：0 全绿 / 1 有命中（abort）/ 2 用法错误。
"""

import argparse
import json
import os
import sys

FORBIDDEN_NAMES = {"skill.md", "contract.md", "spec.md", "runner.py", "map_speakers.py"}
FORBIDDEN_DIRS = {"oracle", "eval", "holdout", "assets", "blind"}
# 只判路径段，不判普通业务目录里恰好叫 out/ 的东西
NEEDLE_DIRS = {"oracle", "eval", "holdout", "blind"}


def scan(root):
    hits = []
    if not os.path.isdir(root):
        return [{"path": root, "kind": "arm_dir_missing", "detail": "臂目录树不存在"}]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for d in list(dirnames):
            if d.lower() in NEEDLE_DIRS:
                hits.append({"path": os.path.relpath(os.path.join(dirpath, d), root).replace(os.sep, "/"),
                             "kind": "forbidden_dir", "detail": d})
        for fn in sorted(filenames):
            if fn.lower() in FORBIDDEN_NAMES:
                hits.append({"path": os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"),
                             "kind": "forbidden_file", "detail": fn})
    return hits


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args(argv)
    if not args.arms:
        print("用法: python isolation_probe.py <臂目录树> [...] [--json <路径>]", file=sys.stderr)
        return 2

    report = {"arms": {}, "total_hits": 0}
    rc = 0
    for arm in args.arms:
        hits = scan(arm)
        report["arms"][arm] = {"hits": hits, "hit_count": len(hits), "pass": not hits}
        report["total_hits"] += len(hits)
        if hits:
            rc = 1
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    print(text)
    if report["total_hits"]:
        print("ABORT：基线/臂目录树命中资产或参照物，对照失效。", file=sys.stderr)
    return rc


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
