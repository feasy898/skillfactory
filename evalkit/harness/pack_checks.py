#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/pack_checks.py — 跑批前置三断言（0 模型，全部在开跑前跑完）
  EI-7  brief 公平：两臂 brief 逐字相同 + brief/黄金输入 全文本扫资产名与暗示句式
  EI-9  臂间输入树公平：掩掉臂目录名后两棵输入树逐字节相同 + model_pin 五元组除 arm 外相等
  EI-20 任务包 conformance：六件齐 + oracle/ 不存在 + model_pin.json 五元组齐

黄金输入目录名（EI-20 双名兼容，SF-0003 修法 A 后口径）：fixtures/ 为本装置参照基线
同形态的规范名（sm-mapping-01 已改用）；通用格式沿用 PLAN §3.3 字面的 inputs/。
两名字面都放行（fixtures 优先），但**同一包/同一臂内两名字不得混用**。

用法：
    python pack_checks.py --pack <pack 目录> --arms <臂1目录> --arms <臂2目录> \
        [--model-pin <model_pin.json>] [--json <落盘路径>]
退出码：0 全过 / 1 有红（abort）/ 2 用法错误。
"""

import argparse
import hashlib
import json
import os
import sys

# 资产名清单（EI-7 负例句式库首版；标 [假设]，本扫描是兜底不是防线——TESTS EI-7 原文）
ASSET_NAMES = ["speaker-mapping", "speaker_mapping", "sm-mapping", "hotwords", "hot-templates",
               "deploy-pack", "acceptor-agent", "zctl-mcp", "office-templates", "office-guard-hooks",
               "meeting-minutes", "skillfactory", "evalkit"]
HINT_PHRASES = ["如果你有", "使用该技能", "使用本技能", "参考手册", "见 SKILL", "按技能说明",
                "资产包", "见 contract", "见 spec.md"]
PIN_KEYS = ["model_id", "provider_base_url", "cli_runtime", "date", "reasoning_variant"]


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


INPUT_DIR_NAMES = ("fixtures", "inputs")  # EI-20 双名兼容：fixtures 优先（SF-0003 修法 A）


def input_dir(root):
    """返回 root 下存在的黄金输入目录名（fixtures 优先）；都不存在返回 None。
    这是 EI-20 双名兼容的唯一合法实现处（装置侧对通用格式与包特例都放行）；
    两名并存视为结构红（防同一包内混用）。"""
    present = [n for n in INPUT_DIR_NAMES if os.path.isdir(os.path.join(root, n))]
    if len(present) > 1:
        return "AMBIGUOUS"
    return present[0] if present else None


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def tree_digest(root, mask):
    """掩掉臂目录名后，对整棵树做 {rel: sha256} 摘要（rel 也掩），用于逐字节公平比对。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            rel_masked = rel.replace(mask, "<ARM>") if mask else rel
            with open(full, "rb") as f:
                data = f.read()
            out[rel_masked] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    return out


def check_ei7(pack, arms):
    res = {"name": "EI-7 brief 公平", "pass": True, "gaps": []}
    brief = os.path.join(pack, "brief.md")
    if not os.path.isfile(brief):
        res["pass"] = False
        res["gaps"].append("brief.md 缺失")
        return res
    base_sha = sha256_file(brief)
    digests = {base_sha}
    for arm in arms:
        cand = os.path.join(arm, "brief.md")
        if os.path.isfile(cand):
            digests.add(sha256_file(cand))
        else:
            res["gaps"].append("臂目录缺 brief 副本: %s" % arm)
    if len(digests) != 1:
        res["pass"] = False
        res["gaps"].append("两臂 brief sha256 不等: %s" % sorted(digests))

    pdir = input_dir(pack)
    if pdir in (None, "AMBIGUOUS"):
        res["pass"] = False
        res["gaps"].append("黄金输入目录缺失或 inputs/fixtures 双名混用: %s" % pack)
        return res
    res["input_dir_name"] = pdir
    scan_files = [brief] + [os.path.join(pack, pdir, n)
                            for n in sorted(os.listdir(os.path.join(pack, pdir)))]
    hits = []
    for path in scan_files:
        if not os.path.isfile(path):
            continue
        text = read_text(path).lower()
        for name in ASSET_NAMES:
            if name.lower() in text:
                hits.append({"file": os.path.basename(path), "needle": name, "kind": "asset_name"})
        for ph in HINT_PHRASES:
            if ph.lower() in text:
                hits.append({"file": os.path.basename(path), "needle": ph, "kind": "hint_phrase"})
    res["scan_hits"] = hits
    if hits:
        res["pass"] = False
        res["gaps"].append("brief/黄金输入 文本扫描命中资产名或暗示句式 %d 处" % len(hits))
    return res


def check_ei9(pack, arms, model_pin):
    res = {"name": "EI-9 臂间输入树公平", "pass": True, "gaps": []}
    if len(arms) < 2:
        res["pass"] = False
        res["gaps"].append("不足两臂，无法比对")
        return res
    digests = []
    for arm in arms:
        adir = input_dir(arm)
        if adir == "AMBIGUOUS":
            res["pass"] = False
            res["gaps"].append("臂内 inputs/fixtures 双名混用: %s" % arm)
            return res
        inputs = os.path.join(arm, adir) if adir else arm
        digests.append((arm, tree_digest(inputs, os.path.basename(arm.rstrip("/\\")))))
    ref_arm, ref = digests[0]
    for arm, d in digests[1:]:
        if d != ref:
            only_ref = sorted(set(ref) - set(d))
            only_arm = sorted(set(d) - set(ref))
            diff = sorted(k for k in set(ref) & set(d) if ref[k] != d[k])
            res["pass"] = False
            res["gaps"].append("输入树不等: %s vs %s（仅前者=%s 仅后者=%s 内容不同=%s）"
                               % (ref_arm, arm, only_ref, only_arm, diff))
    if model_pin:
        pins = []
        for arm in arms:
            p = os.path.join(arm, "records", "model_pin.json")
            if os.path.isfile(p):
                pins.append((arm, json.loads(read_text(p))))
        if len(pins) >= 2:
            a0, p0 = pins[0]
            for arm, p in pins[1:]:
                for k in PIN_KEYS:
                    if p0.get(k) != p.get(k):
                        res["pass"] = False
                        res["gaps"].append("model_pin %s 字段 %s 不等: %r vs %r"
                                           % (k, k, p0.get(k), p.get(k)))
    else:
        res["note"] = "未提供 model_pin，五元组比对跳过（开跑后由 run_arm 落盘）"
    return res


def check_ei20(pack, model_pin):
    res = {"name": "EI-20 任务包 conformance", "pass": True, "gaps": []}
    pdir = input_dir(pack)
    if pdir == "AMBIGUOUS":
        res["pass"] = False
        res["gaps"].append("黄金输入目录 inputs/fixtures 双名混用: %s" % pack)
    elif pdir is None:
        res["pass"] = False
        res["gaps"].append("包内缺件: 黄金输入目录（fixtures/ 或通用 inputs/，一名即可）")
    else:
        res["input_dir_name"] = pdir
    for item in ["brief.md", "rubric.md", "out", "transcript", "records"]:
        if not os.path.exists(os.path.join(pack, item)):
            res["pass"] = False
            res["gaps"].append("包内缺件: %s" % item)
    if os.path.exists(os.path.join(pack, "oracle")):
        res["pass"] = False
        res["gaps"].append("包内出现 oracle/（oracle 不入包，PLAN §3.3）")
    if model_pin:
        pin = json.loads(read_text(model_pin))
        missing = [k for k in PIN_KEYS if not pin.get(k)]
        if missing:
            res["pass"] = False
            res["gaps"].append("model_pin 五元组缺字段: %s" % missing)
    else:
        res["note"] = "未提供 model_pin，五元组齐备性跳过（开跑后由 run_arm 落盘）"
    return res


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--arms", action="append", default=[])
    ap.add_argument("--model-pin", default=None)
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args(argv)
    if not args.pack or not os.path.isdir(args.pack):
        print("用法: python pack_checks.py --pack <pack 目录> --arms <臂目录> [--arms <臂目录> ...]",
              file=sys.stderr)
        return 2

    results = [check_ei7(args.pack, args.arms),
               check_ei9(args.pack, args.arms, args.model_pin),
               check_ei20(args.pack, args.model_pin)]
    report = {"pack": os.path.abspath(args.pack), "arms": args.arms,
              "results": results, "pass": all(r["pass"] for r in results)}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    print(text)
    if not report["pass"]:
        print("ABORT：跑批前置断言有红。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
