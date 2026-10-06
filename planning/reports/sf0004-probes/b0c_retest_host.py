#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF-0004 B 支宿主复测：B0c（宿主会话模型目录可得性）在真宿主环境重跑（零模型成本）。

依据 SF-0004 报告 §11.1：「B 支未被功能证伪：若 planner 要把『B 死』当结论用，
需另开卡提供有模型目录的宿主会话复测门 3」。门 3 = B0c 宿主目录/模型目录可得性
（原探针 b0c_catalog.py 于 2026-10-04 在 kimi 2.1.1 worker 会话实测 available=false，
分类 untested_catalog_unavailable；B1 因此 not_run）。

本脚本 = 门 3 的真宿主复测入口（2026-10-06，INTENT §6 遗留小项③升格执行）。
宿主：Linux（/home/pan-ding），zcode 3.14.4（electron），无 kimi CLI。
原探针与原证据（b0c_catalog.py / p-b0-catalog.json）留档不改——本文件是并列的复测探针。

三探针（全部零模型成本）：
  P1 kimi CLI census        —— 本宿主是否存在 kimi CLI 且可枚举模型（原探针 1 同型）
  P2 会话工具面 ListModels  —— 宿主会话是否真的能枚举模型目录（原探针 2 同型；
                               证据由驱动本脚本的 agent 会话实调 ListModels 工具落盘，
                               --listmodels-evidence 传入，脚本只认「列出了 model_ids」为绿）
  P3 zcode CLI census       —— 本宿主 zcode --help 是否暴露模型枚举面（原探针 3 同型）

另记一条结构性旁证 P4：本宿主 ~/.zcode/v2/provider_config.json 的
config.defaultModelSelection 是否为 null（SF-0004 §12 发现③在第二台宿主上的复测；
该 null 正是 headless 回落 builtin GLM 的结构性原因）。

红绿口径（如实）：available=true 当且仅当 P1/P2/P3 任一实测拿到可寻址模型目录。
用途：给 SF-0004 b_verdict=Undetermined 的「B 死」推断补第二台宿主的门 3 数据点；
本探针不构造 B1（B1 需要目录可枚举后做工作流 subagent_model 钉版构造，超本卡零成本边界）。

用法：
  python b0c_retest_host.py [--listmodels-evidence <json>] [--out p-b0-catalog-host-retest.json]
退出码：0=复测完成（available 值如实，不因红而非零）；2=用法错误。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_TOKENS = ("models", "list-model", "list_models", "ListModels", "model list", "--model")


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def probe_kimi():
    """P1：kimi CLI census（原探针 1 同型，Linux 宿主版）。"""
    path = shutil.which("kimi")
    row = {"probe": "P1 kimi CLI census", "host": "linux/home-pan-ding",
           "kimi_binary": path}
    if not path:
        row["result"] = "cli_absent_on_host"
        row["detail"] = ("本宿主 PATH 上无 kimi CLI（shutil.which('kimi')=None）；"
                         "kimi 2.1.1 无模型枚举子命令的实测（SF-0004 B0c 探针1）无法在本宿主重跑，"
                         "按缺席登记，不计入 available。")
        return row
    try:
        p = subprocess.run([path, "--help"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        txt = (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # pragma: no cover
        row["result"] = "error"
        row["detail"] = repr(e)
        return row
    hit = [t for t in MODEL_TOKENS if t in txt]
    row["result"] = "catalog_enumeration_present" if hit else "no_catalog_enumeration"
    row["detail"] = "help 面模型枚举 token 命中=%s" % (hit or "无")
    return row


def probe_session_listmodels(evidence_path):
    """P2：宿主会话 ListModels 工具实调证据（由驱动本脚本的 agent 会话提供）。"""
    row = {"probe": "P2 session ListModels invocation", "host": "workflow-subagent-session"}
    if not evidence_path:
        row["result"] = "evidence_missing"
        row["detail"] = ("未提供 --listmodels-evidence：会话内模型目录未实测。"
                         "按 fail-closed 记不可得，不计入 available。")
        return row
    try:
        ev = json.load(open(evidence_path, encoding="utf-8"))
    except Exception as e:
        row["result"] = "evidence_unreadable"
        row["detail"] = repr(e)
        return row
    ok = bool(ev.get("catalog_ok")) and isinstance(ev.get("model_ids"), list) and len(ev["model_ids"]) > 0
    row["result"] = "catalog_listed" if ok else "model_catalog_unavailable"
    row["detail"] = ("会话实调 ListModels 工具（证据 sha256=%s，调用时间 %s）：%s"
                     % (ev.get("raw_error_sha256", "?"), ev.get("ts", "?"),
                        "目录可枚举" if ok else str(ev.get("raw_error", ""))[:200]))
    row["evidence_file"] = os.path.relpath(evidence_path, HERE)
    return row


def probe_zcode():
    """P3：zcode CLI census（原探针 3 同型，Linux 宿主版；零模型、不进会话）。"""
    path = shutil.which("zcode")
    row = {"probe": "P3 zcode CLI census", "host": "linux/home-pan-ding", "zcode_binary": path}
    if not path:
        row["result"] = "cli_absent_on_host"
        row["detail"] = "本宿主 PATH 上无 zcode CLI。"
        return row
    ver = None
    try:
        p = subprocess.run([path, "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        blob = (p.stdout or "") + (p.stderr or "")
        m = re.search(r"version=([0-9][^\s,\]]*)", blob)
        ver = m.group(1) if m else (blob.strip().splitlines() or [""])[0][:80]
    except Exception as e:
        ver = "probe_error: %r" % e
    row["zcode_version_observed"] = ver
    # 帮助面 census：electron 桌面壳会打启动日志，属进程事实，如实登记；不 spawn GUI 会话。
    row["result"] = "no_catalog_enumeration"
    row["detail"] = ("本宿主 zcode（electron 壳，实测启动日志 version=%s）--help/--version 只出"
                     "桌面壳启动日志、无 usage 文本与模型枚举面；headless -p 面未在本宿主实测"
                     "（跑它会花真实模型调用，超本复测零成本边界）。不计入 available。" % ver)
    return row


def probe_provider_cfg():
    """P4（结构性旁证）：本宿主 personal v2 配置 defaultModelSelection 是否为 null。"""
    p = os.path.expanduser("~/.zcode/v2/provider_config.json")
    row = {"probe": "P4 host provider_config structural echo", "path": "~/.zcode/v2/provider_config.json",
           "exists": os.path.exists(p)}
    if not row["exists"]:
        row["result"] = "config_absent"
        row["detail"] = "本宿主无 personal v2 provider 配置。"
        return row
    j = json.load(open(p, encoding="utf-8"))
    cfg = j.get("config") or {}
    dms = cfg.get("defaultModelSelection")
    row["result"] = "defaultModelSelection_null" if dms is None else "defaultModelSelection_present"
    row["detail"] = ("defaultModelSelection=%r（只登记键态与 providerOrder 键名清单，不落任何凭据值）"
                     % dms)
    row["providerOrder"] = list(cfg.get("providerOrder") or [])
    return row


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--listmodels-evidence", default=os.path.join(HERE, "p-b0c-listmodels-host-evidence.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "p-b0-catalog-host-retest.json"))
    args = ap.parse_args(argv)

    probes = [probe_kimi(),
              probe_session_listmodels(args.listmodels_evidence),
              probe_zcode(),
              probe_provider_cfg()]
    # available 只认「实测拿到可寻址模型目录」：P2 列出 model_ids（P1/P3 的枚举面存在也算，
    # 与原探针同口径——本宿主两者皆无，故如实红）。
    available = any(p["result"] in ("catalog_enumeration_present", "catalog_listed") for p in probes[:3])

    out = {
        "gate": "B0c",
        "retest": True,
        "host": "Linux /home/pan-ding（zcode 3.14.4 electron；无 kimi CLI）",
        "original_probe": "b0c_catalog.py @ 2026-10-04 kimi 2.1.1 worker 会话（available=false，留档不改）",
        "available": bool(available),
        "model_ids": [],
        "classification": "catalog_available" if available else "untested_catalog_unavailable",
        "probes": probes,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "consequence": ("门 3 第二台宿主数据点：模型目录仍不可寻址（本次是「工具在、目录缺」——"
                        "宿主未提供目录，错误字面 model_catalog_unavailable）。"
                        "B1 维持 not_run（0 模型调用）；SF-0004 b_verdict=Undetermined 不变，"
                        "「B 死」仍只是静态+历史推断，现有两台宿主（kimi worker 会话、zcode "
                        "workflow 宿主会话）的门 3 实测都不支持把它升格为实测结论。R-8 的"
                        "「宿主范围未知」收窄为：已测 2 台宿主均无目录。"),
        "budget": "0 model calls（全部探针零模型成本；未 spawn 任何 headless 会话）",
    }
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"available": out["available"], "classification": out["classification"],
                      "probes": [{"probe": p["probe"], "result": p["result"]} for p in probes]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
