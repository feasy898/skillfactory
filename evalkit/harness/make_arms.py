#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/make_arms.py — 建 treatment / baseline 两棵臂目录树（PLAN §5.4 步 1）。

硬不变量（PLAN §3.3-1）：每臂 cwd 是一份 **inputs-only 独立目录树**；臂要跑生成器必须先
复制到自己的 scratch 副本。本脚本据此建树，并在树上做差异化装载：

  baseline/   fixtures/ + brief.md                   —— 只有输入，什么都没有
  treatment/  fixtures/ + brief.md + .zcode/skills/<资产名>/
              .zcode/skills/ 是 zcode 客户端**产品级**的 skill 发现根
              （zcode-guide:diagnosing-skills §1 发现序第 4 级：Workspace `.zcode/skills`，
              从当前目录向上、相对 --cwd 解析）——这是 R-1 要实测的真实装载路径。

说明（规格判读，留痕）：PLAN §3.3 字面写「每臂 cwd 是 inputs-only 树，资产树不在其中」；
但 TESTS EI-6 的被测对象明确是「**baseline 臂**摸到资产文件」，且 treatment 臂按定义就是要
挂资产的臂。故本实现按「baseline 严格输入-only、treatment 用产品发现根挂载」执行，
隔离探针只对 baseline 树跑（见 harness/isolation_probe.py 调用处）。此判读在报告 §决策中留痕。
输入目录名：sm-mapping-01 包自 SF-0003（修法 A）起黄金输入目录为 **fixtures/**（与参照
基线生成形态同构，PLAN §3.1 L1 前提）；对 PLAN §3.3 通用字面 inputs/ 的偏离见包内
PACK-DEVIATIONS.md。通用格式（inputs/）包的兼容放行在 pack_checks.py（EI-20 双名）。

用法：
    python make_arms.py --pack <pack 目录> --run-id <run-id> --asset-skill <资产 skill 目录> [--out <runs 根>]
退出码：0 成功 / 1 资产目录缺失 / 2 用法错误
"""

import argparse
import json
import os
import shutil
import sys


DEFAULT_EXCLUDE = {"out", ".mimosa", "__pycache__", ".git", "eval", "oracle", "blind"}


def copytree(src, dst, exclude=DEFAULT_EXCLUDE):
    """只拷可交付面，排除参照区与历史产物。

    `out/` 必须排除：speaker-mapping 的 package/ 里带着上一轮跑批留下的 24 个基准产物，
    挂进臂树等于把答案连参照物一起递到 treatment 臂手上——这类泄漏是 L1 层的作弊，
    产物轨会全绿而增益是假的。`eval/`、`oracle/` 同理（oracle 永不入包，PLAN §3.3）。
    """
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        rel = os.path.relpath(dirpath, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1] in (".pyc",):
                continue
            shutil.copy2(os.path.join(dirpath, fn), os.path.join(target_dir, fn))


def skill_name_of(skill_dir):
    """skill 身份取 SKILL.md frontmatter 的 name（agentskills 规范：目录名 = name）。"""
    sk = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(sk):
        return os.path.basename(os.path.normpath(skill_dir))
    with open(sk, "rb") as f:
        lines = f.read().decode("utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return os.path.basename(os.path.normpath(skill_dir))
    for line in lines[1:]:
        line = line.strip()
        if line == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return os.path.basename(os.path.normpath(skill_dir))


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--asset-skill", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if not args.pack or not args.run_id or not args.asset_skill:
        print("用法: python make_arms.py --pack <pack> --run-id <id> --asset-skill <目录> [--out <runs 根>]",
              file=sys.stderr)
        return 2
    if not os.path.isdir(os.path.join(args.pack, "fixtures")):
        print("pack 无 fixtures/（sm-mapping-01 自 SF-0003 修法 A 起用 fixtures/；"
              "通用 inputs/ 包请先经 pack_checks.py 双名校验）: %s" % args.pack, file=sys.stderr)
        return 2
    if not os.path.isdir(args.asset_skill):
        print("资产 skill 目录不存在: %s" % args.asset_skill, file=sys.stderr)
        return 1

    evalkit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runs_root = args.out or os.path.join(evalkit, "runs")
    run_dir = os.path.join(runs_root, args.run_id)
    if os.path.isdir(run_dir):
        print("run 目录已存在，拒绝覆盖（并发互斥，TESTS EI-18）: %s" % run_dir, file=sys.stderr)
        return 1

    skill_name = skill_name_of(args.asset_skill)
    arms = {}
    for arm in ("baseline", "treatment"):
        arm_dir = os.path.join(run_dir, arm)
        os.makedirs(arm_dir, exist_ok=True)
        shutil.copytree(os.path.join(args.pack, "fixtures"), os.path.join(arm_dir, "fixtures"))
        shutil.copy2(os.path.join(args.pack, "brief.md"), os.path.join(arm_dir, "brief.md"))
        arms[arm] = arm_dir

    # treatment 专属：产品发现根挂载
    skill_dst = os.path.join(arms["treatment"], ".zcode", "skills", skill_name)
    os.makedirs(os.path.dirname(skill_dst), exist_ok=True)
    copytree(args.asset_skill, skill_dst)

    manifest = {
        "run_id": args.run_id,
        "run_dir": os.path.abspath(run_dir),
        "arms": {k: os.path.abspath(v) for k, v in arms.items()},
        "treatment_skill_mount": os.path.abspath(skill_dst),
        "baseline_has_skill": False,
        "pack": os.path.abspath(args.pack),
    }
    man_path = os.path.join(run_dir, "arms_manifest.json")
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
