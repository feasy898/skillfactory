#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checks/run_check.py — 任务包薄封套：import 资产树里的**原版** runner 并透传 exit code。

零改动铁律（PLAN §3.3 / TASK.md:76）：资产树 `v5/assets/speaker-mapping/eval/runner.py`
一个字不改。本文件只做三件事：
  1) 用绝对路径把**原版** runner 模块 import 进来（装置钉版在文件层可查：runner 的
     sha256 由 harness/keyfiles.sha256 单独冻结，本文件不含任何判分逻辑副本）；
  2) 原样转发 main() 的返回码（0 全过 / 1 任一红 / 2 用法错误）；
  3) 额外落一份 JSON 结果到 --record 指定的路径（产物轨记录，PLAN §5.3）。

用法：
    python checks/run_check.py [<被测产物根> <参照产物根>] [--record <path>]

退出码：与原版 runner 完全一致（0 / 1 / 2）；--record 写盘失败记 infra_error 并返回 2。
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
import contextlib

# 资产根：本 evalkit 与 afp-clone **平级**都在工作区根下（PLAN §8 O-17：evalkit 不进 afp-clone），
# 所以资产树要从 evalkit 上一级找。用 __file__ 相对定位，整目录搬迁后不用改代码。
PACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # .../packs/sm-mapping-01
EVALKIT = os.path.dirname(os.path.dirname(PACK_DIR))                      # .../evalkit
# 拆仓迁移(2026-10-05)：产线根=本仓根(evalkit 上一级)，SF_ROOT 可覆盖
WORKSPACE = os.environ.get("SF_ROOT") or os.path.dirname(EVALKIT)         # .../skillfactory
ASSET_ROOT = os.path.join(
    WORKSPACE, "v5", "assets", "speaker-mapping")
RUNNER_PATH = os.path.join(ASSET_ROOT, "eval", "runner.py")


def load_original_runner():
    """从资产树按文件路径 import 原版 runner（不复制、不改写）。"""
    if not os.path.isfile(RUNNER_PATH):
        raise SystemExit("原版 runner 不存在: %s" % RUNNER_PATH)
    spec = importlib.util.spec_from_file_location("sm_original_runner", RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("roots", nargs="*")
    ap.add_argument("--record", default=None)
    args, unknown = ap.parse_known_args(argv)
    if unknown:
        print("未知参数: %s" % " ".join(unknown), file=sys.stderr)
        return 2
    if len(args.roots) not in (0, 2):
        print("用法: python checks/run_check.py [<被测产物根> <参照产物根>] [--record <path>]",
              file=sys.stderr)
        return 2

    mod = load_original_runner()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main(list(args.roots))
    stdout_text = buf.getvalue()

    record = {
        "track": "artifact",
        "device": "original_runner",
        "runner_path": RUNNER_PATH,
        "runner_sha256": file_sha256(RUNNER_PATH),
        "argv": list(args.roots),
        "exit_code": rc,
        "stdout": stdout_text,
    }
    if args.record:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.record)), exist_ok=True)
            with open(args.record, "w", encoding="utf-8", newline="\n") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            record["record_write_error"] = str(exc)
            print("记录落盘失败: %s" % exc, file=sys.stderr)
            return 2

    print(stdout_text, end="")
    return rc


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
