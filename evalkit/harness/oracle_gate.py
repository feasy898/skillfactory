#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/oracle_gate.py — oracle 树哈希门（PLAN §3.3 硬不变量 2 / TESTS EI-3 EI-4 EI-5）。

三条断言合一（TESTS EI-3）：
  1. 整树 sha256（内容基准，写在产物里）
  2. 文件清单（相对路径 + 逐文件 sha256）
  3. 文件数

行尾基准显式声明（EI-4）：**文本类文件按 LF 归一后哈希，二进制原样**——这样换机能判
「基准漂移」而不是「资产变了」（peidian autocrlf 事故同构）。

易变面自标定三跑法（EI-3）：`calibrate --runs 3` 里，前两跑学出易变面（各跑都可能变的文件），
第三跑验冻结面。冻结面变了 = abort。

用法：
    python oracle_gate.py hash   --root <oracle 根> [--record <path>]
    python oracle_gate.py verify --root <oracle 根> --record <baseline.json>
                                 [--expect-changed]     # EI-5 红路：期望检测到变化
    python oracle_gate.py calibrate --root <oracle 根> --runs 3 [--record <path>]

退出码：0 = 通过（verify 模式下与基准一致）；1 = 不一致/abort（EI-5 红路成立）；2 = 用法错误。
"""

import argparse
import hashlib
import json
import os
import sys

TEXT_EXT = {".py", ".md", ".json", ".txt", ".mjs", ".js", ".ts", ".yaml", ".yml", ""}
BASIS = "text LF-normalized (CRLF->LF) + sha256; binary raw bytes + sha256"


def norm_bytes(rel, data):
    if os.path.splitext(rel)[1].lower() in TEXT_EXT:
        return data.replace(b"\r\n", b"\n")
    return data


def walk(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def hash_tree(root):
    rels = walk(root)
    files = []
    tree = hashlib.sha256()
    for rel in rels:
        with open(os.path.join(root, rel), "rb") as f:
            raw = f.read()
        norm = norm_bytes(rel, raw)
        fh = hashlib.sha256(norm).hexdigest()
        files.append({"path": rel, "bytes": len(raw), "sha256": fh})
        tree.update(rel.encode("utf-8"))
        tree.update(b"\0")
        tree.update(fh.encode("ascii"))
        tree.update(b"\0")
    return {
        "root": os.path.abspath(root),
        "file_count": len(rels),
        "tree_sha256": tree.hexdigest(),
        "basis": BASIS,
        "files": files,
    }


def diff_against(baseline, current):
    """返回 (changed_paths, missing_paths, extra_paths)。"""
    b = {f["path"]: f["sha256"] for f in baseline["files"]}
    c = {f["path"]: f["sha256"] for f in current["files"]}
    changed = sorted(p for p in set(b) & set(c) if b[p] != c[p])
    missing = sorted(set(b) - set(c))
    extra = sorted(set(c) - set(b))
    return changed, missing, extra


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_hash(args):
    cur = hash_tree(args.root)
    if args.record:
        write_json(args.record, cur)
    print(json.dumps({"file_count": cur["file_count"],
                      "tree_sha256": cur["tree_sha256"]}, ensure_ascii=False))
    return 0


def cmd_verify(args):
    with open(args.record, "r", encoding="utf-8") as f:
        base = json.load(f)
    cur = hash_tree(args.root)
    changed, missing, extra = diff_against(base, cur)
    same = cur["tree_sha256"] == base["tree_sha256"]
    report = {
        "root": cur["root"],
        "baseline_tree_sha256": base["tree_sha256"],
        "current_tree_sha256": cur["tree_sha256"],
        "baseline_file_count": base["file_count"],
        "current_file_count": cur["file_count"],
        "unchanged": same,
        "changed_paths": changed,
        "missing_paths": missing,
        "extra_paths": extra,
        "abort": not same,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.expect_changed:
        # EI-5 红路：门必须在变化时 abort 且不得继续评分
        return 0 if (not same) else 1
    return 0 if same else 1


def cmd_calibrate(args):
    runs = []
    for _ in range(args.runs):
        runs.append({f["path"]: f["sha256"] for f in hash_tree(args.root)["files"]})
    paths = sorted(set().union(*[set(r) for r in runs]))
    volatile = [p for p in paths
                if len({r.get(p) for r in runs}) > 1]
    frozen = [p for p in paths if p not in volatile]
    last = {f["path"]: f["sha256"] for f in hash_tree(args.root)["files"]}
    frozen_broken = [p for p in frozen if last.get(p) != runs[-1].get(p)]
    out = {
        "root": os.path.abspath(args.root),
        "runs": args.runs,
        "volatile_paths": volatile,
        "frozen_paths": frozen,
        "frozen_broken": frozen_broken,
        "stable": not volatile and not frozen_broken,
        "basis": BASIS,
    }
    if args.record:
        write_json(args.record, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["stable"] else 1


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cmd", choices=["hash", "verify", "calibrate"])
    ap.add_argument("--root", required=True)
    ap.add_argument("--record", default=None)
    ap.add_argument("--expect-changed", action="store_true")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print("根目录不存在: %s" % args.root, file=sys.stderr)
        return 2
    if args.cmd == "hash":
        return cmd_hash(args)
    if args.cmd == "verify":
        if not args.record or not os.path.isfile(args.record):
            print("verify 需要 --record <baseline.json>", file=sys.stderr)
            return 2
        return cmd_verify(args)
    return cmd_calibrate(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
