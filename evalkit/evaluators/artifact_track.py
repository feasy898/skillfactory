#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluators/artifact_track.py — 产物轨（PLAN §5.3）：最终交付物对不对。

零模型、亚秒级、每次必跑。装置钉版在文件层可查：不复制判分逻辑，只调
`packs/sm-mapping-01/checks/run_check.py`（薄封套 → import 资产树原版 runner），透传退出码。
判分器 sha256 落进记录（TESTS EI-23 装置钉版判分器指纹）。

用法：
    python artifact_track.py --pack <pack 目录> --product-root <臂的 out 目录> \
        [--reference <参照产物根>] [--out <记录落盘路径>]
退出码：0 产物轨绿 / 1 产物轨红（被测失败）/ 2 用法或装置错误。
"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--product-root", default=None)
    ap.add_argument("--reference", default=None)
    ap.add_argument("--out", dest="out_path", default=None)
    args = ap.parse_args(argv)
    if not args.pack or not args.product_root:
        print("用法: python artifact_track.py --pack <pack> --product-root <out 目录> "
              "[--reference <参照>] [--out <记录路径>]", file=sys.stderr)
        return 2
    wrapper = os.path.join(args.pack, "checks", "run_check.py")
    if not os.path.isfile(wrapper):
        print("薄封套不存在: %s" % wrapper, file=sys.stderr)
        return 2

    argv_cmd = [sys.executable, wrapper, args.product_root]
    if args.reference:
        argv_cmd.append(args.reference)
    rec_path = args.out_path or os.path.join(args.pack, "records", "artifact_track.json")

    try:
        proc = subprocess.run(argv_cmd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        record = {"track": "artifact", "verdict": "infra_error", "reason": "judge timeout"}
        _dump(rec_path, record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 2

    text = proc.stdout.decode("utf-8", errors="replace")
    try:
        result = json.loads(text)
    except Exception:  # noqa: BLE001
        record = {"track": "artifact", "verdict": "infra_error", "reason": "judge stdout 非 JSON",
                  "stdout_head": text[:800], "stderr_head": proc.stderr.decode("utf-8", "replace")[:800],
                  "judge_sha256": sha256_file(wrapper)}
        _dump(rec_path, record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 2

    record = {
        "track": "artifact",
        "verdict": "pass" if proc.returncode == 0 else "measured_failure",
        "exit_code": proc.returncode,
        "judge": wrapper,
        "judge_sha256": sha256_file(wrapper),
        "product_root": os.path.abspath(args.product_root),
        "product_file_count": _count_files(args.product_root),
        "runner_result": result,
    }
    _dump(rec_path, record)
    print(json.dumps({k: v for k, v in record.items() if k != "runner_result"},
                     ensure_ascii=False, indent=2))
    for c in result.get("checks", []):
        print("  %s %s" % ("PASS" if c["pass"] else "FAIL", c["name"]))
    return 0 if proc.returncode == 0 else 1


def _count_files(root):
    n = 0
    for _, _, files in os.walk(root):
        n += len(files)
    return n


def _dump(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
