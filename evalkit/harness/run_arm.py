#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/run_arm.py — 臂驱动（PLAN §5.2 MVP 拓扑：外部脚本按臂 spawn 独立 zcode 进程）。

一臂一进程 = 干净上下文 + 物理隔离的最强形态（EVAL-SPEC §3.2-3 / §4.3-1）。
本脚本只做四件事：
  1) 以**臂目录为 cwd** spawn `zcode -p <prompt>`（prompt 两臂逐字相同，R-1 由 cwd 树差异决定，
     不在 prompt 里提资产名——EI-7 公平性）；
  2) 分族超时（PLAN §5.6：minimax 1200s / GLM 1800s，**不拿 idleTimeout 当臂超时**）；
  3) 落 records：model_pin.json 五元组 / exit_code / wall_ms / telemetry（db join）；
  4) 跑完把 stdout 原样存进 pack 的 transcript/（污染扫描用；主证据是结构化遥测）。

用法：
    python run_arm.py --run-id <id> --arm <baseline|treatment> --arm-dir <目录> \
        [--run-label r1] [--family glm] [--timeout 1800] [--db <db.sqlite>] [--pack <pack>]
退出码：0 臂完成且被测进程 exit 0 / 非 0 见 records/exit_code；2 用法错误。
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time

DEFAULT_DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
# PLAN §5.6 分族超时（实测单请求 max：step 441s / minimax 2031s / GLM 3786s）
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800, "step": 600, "kimi": 600}
# 两臂逐字相同；不提资产名、不提 skill、不给任何臂内差异的暗示（EI-7）
PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")


def now_ms():
    return int(time.time() * 1000)


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pull_telemetry(db, session_id, arm_dir):
    """结构化遥测：session 目录 + model_usage 聚合 + 逐命令 tool_usage（双源交叉的「结构化」侧）。"""
    if not session_id or not os.path.isfile(db):
        return {"available": False, "reason": "no session id or db missing"}
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    out = {"available": True, "session_id": session_id}
    try:
        r = cur.execute("select directory, task_type, version from session where id=?",
                        (session_id,)).fetchone()
        out["session"] = dict(r) if r else None
        out["directory_matches_arm"] = bool(r) and os.path.normcase(r["directory"]) == \
            os.path.normcase(os.path.abspath(arm_dir))
        rows = cur.execute(
            "select model_id, provider_id, status, attempt_index, sum(input_tokens) it, "
            "sum(output_tokens) ot, sum(duration_ms) dur, count(*) n "
            "from model_usage where session_id=? group by model_id, provider_id, status, attempt_index",
            (session_id,)).fetchall()
        out["model_usage"] = [dict(x) for x in rows]
        tu = cur.execute(
            "select tool_name, read_only, destructive, status, exit_code, started_at, completed_at, "
            "duration_ms, output_bytes, stderr_bytes, error_type from tool_usage "
            "where session_id=? order by started_at", (session_id,)).fetchall()
        out["tool_usage"] = [dict(x) for x in tu]
    finally:
        con.close()
    return out


def resolve_zcode():
    """解析 zcode 的真可执行入口。

    本机 `zcode` 在 Git Bash 里是 npm 的 sh shim（无扩展名），Windows CreateProcess 不能直接
    exec 它（实测 WinError 2）。按序尝试：npm 的 .cmd shim → node + 包内入口。
    整个解析过程不写任何凭据、不改 PATH。
    """
    for cand in ("zcode.cmd", "zcode.exe"):
        p = shutil.which(cand)
        if p:
            return [p]
    node = shutil.which("node.exe") or shutil.which("node")
    bases = [os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm"),
             os.path.join(os.path.expanduser("~"), ".npm-global", "bin")]
    for base in bases:
        entry = os.path.join(base, "node_modules", "zcode-app-cli", "bin", "zcode.js")
        if node and os.path.isfile(entry):
            return [node, entry]
    raise SystemExit("找不到 zcode 可执行入口（试过 zcode.cmd/zcode.exe 与 npm 包内 zcode.js）")


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--arm", default=None)
    ap.add_argument("--arm-dir", default=None)
    ap.add_argument("--run-label", default="r1")
    ap.add_argument("--family", default="glm")
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--pack", default=None)
    args = ap.parse_args(argv)
    if not args.arm or not args.arm_dir or not os.path.isdir(args.arm_dir):
        print("用法: python run_arm.py --arm <名> --arm-dir <目录> [--run-id <id>] "
              "[--run-label r1] [--family glm] [--timeout 秒]", file=sys.stderr)
        return 2

    timeout = args.timeout or FAMILY_TIMEOUT.get(args.family, 1800)
    rec_dir = os.path.join(args.arm_dir, "records")
    os.makedirs(rec_dir, exist_ok=True)
    model_id_observed = None

    t0 = time.time()
    started = now_ms()
    cmd = resolve_zcode() + ["-p", PROMPT, "--cwd", args.arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"   # 否则 Git Bash 会把 prompt 里的路径形参改写成 Windows 路径
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env, shell=False)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = -1
        out, err = (exc.stdout or b""), (exc.stderr or b"")
        timed_out = True
    wall_ms = int((time.time() - t0) * 1000)

    text = out.decode("utf-8", errors="replace")
    session_id = None
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    if m:
        session_id = m.group(1)

    tele = pull_telemetry(args.db, session_id, args.arm_dir)
    if tele.get("available") and tele.get("model_usage"):
        model_id_observed = tele["model_usage"][0].get("model_id")

    # model_pin 五元组（PLAN §5.1 钉版纪律：模型 ID 逐字抄 resolved 落点）
    # 另钉判分器指纹（TESTS EI-23：改判分器/阈值凑绿 → 判分器 sha256 与臂一同冻结）
    judge = os.path.join(args.pack, "checks", "run_check.py") if args.pack else None
    judge_sha = None
    if judge and os.path.isfile(judge):
        import hashlib as _h
        with open(judge, "rb") as f:
            judge_sha = _h.sha256(f.read()).hexdigest()
    pin = {
        "arm": args.arm,
        "run_label": args.run_label,
        "run_id": args.run_id,
        "model_id": model_id_observed or "UNOBSERVED",
        "provider_base_url": "builtin:bigmodel-coding-plan (zcode 内部，CLI 不暴露 baseURL)",
        "cli_runtime": "zcode-app-cli 3.14.4-30 / zcode-runtime 0.16.9",
        "date": time.strftime("%Y-%m-%d"),
        "reasoning_variant": "default(max)",
        "judge_sha256": judge_sha,
    }
    write_json(os.path.join(rec_dir, "model_pin.json"), pin)

    record = {
        "arm": args.arm, "run_label": args.run_label, "family_requested": args.family,
        "timeout_s": timeout, "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": started, "session_id": session_id,
        "model_id_observed": model_id_observed, "stdout_bytes": len(out), "stderr_bytes": len(err),
        "stderr_head": err.decode("utf-8", errors="replace")[:2000],
    }
    write_json(os.path.join(rec_dir, "arm_run.json"), record)
    write_json(os.path.join(rec_dir, "telemetry.json"), tele)

    if args.pack:
        tdir = os.path.join(args.pack, "transcript", "%s-%s" % (args.arm, args.run_label))
        os.makedirs(tdir, exist_ok=True)
        with open(os.path.join(tdir, "zcode_stdout.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        with open(os.path.join(tdir, "zcode_stderr.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(err.decode("utf-8", errors="replace"))

    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
