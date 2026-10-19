#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/hot-retest-20261009/build_packs.py — hot 重测 8 任务臂任务包构建（零模型）。

任务源（冻结）：planning/taskset-redesign/merged/hot-templates-skill/t01..t08
  本轮开工冻结校验：merged 净荷复算=adae05f2…（index.json frozen_sha256）exit 0；
  hot 子树 32 文件逐文件 sha256 对照 index PASS 32/32。
臂 brief.md = task.json.instruction 逐字 + <outdir>→out 机械替换（照 office/meeting-minutes
  packs 先例）；merged brief.md ≡ instruction 原文（含 <outdir>），故臂书取 instruction 替换生成。
fixtures/ 空目录在位（make_arms 装置要求；hot 全部题输入数据内嵌于 instruction，臂自存数据
  文件属任务面——t05 三份自备 JSON、t08 不存在的 ./data/ 路径系题目构造）。
判据面（rubric.md/judge-notes.md/golden rubric/runner/oracle）一律不进 pack。
另做权重交叉核对：从 merged 各题 rubric.md 表格正则抽权重，与 round-plan 预登记权重表逐值
  核对，不一致即 exit 3（防装置权重与冻结 rubric 脱钩，EVAL-SPEC v0.2.2 §9-3 前置）。
退出码：0=8 包构建完成且校验过；2=冻结哈希不符；3=权重表不符。
"""
import hashlib
import json
import os
import re
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "hot-retest-20261009")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "hot-templates-skill")
FROZEN_100 = "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6"
TASKS = ["t%02d" % i for i in range(1, 9)]
WEIGHTS_PREREG = {
    "t01": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t02": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t03": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t04": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t05": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t06": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t07": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t08": {"正确性": 0.5, "完整性": 0.3, "可验证性": 0.2},
}
DIM_ALIAS = {"正确性": "正确性", "完整性": "完整性", "可验证性": "可验证性"}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def weights_from_rubric(tid):
    """从 rubric.md 表格行抽维度权重（行形如 | 正确性（…） | 0.4 | …）。"""
    text = open(os.path.join(MERGED, tid, "rubric.md"), encoding="utf-8").read()
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(0\.\d+)\s*\|", line)
        if not m:
            continue
        name = m.group(1)
        w = float(m.group(2))
        for key in DIM_ALIAS:
            if name.startswith(key):
                out[key] = w
                break
    return out


def main():
    # 冻结复算（开工自证，同 office build_packs 口径但用本包冻结值）
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    if live != FROZEN_100:
        print("任务集冻结哈希复算不符：%s != %s" % (live, FROZEN_100), file=sys.stderr)
        return 2
    manifest = {"run": "hot-retest-20261009", "taskset_frozen_sha256_100": live,
                "taskset_frozen_cmd": cmd, "packs": [], "weights_crosscheck": {}}
    for tid in TASKS:
        pd = os.path.join(RUN, "packs", "hot-templates-%s" % tid)
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)
        tj = json.load(open(os.path.join(MERGED, tid, "task.json"), encoding="utf-8"))
        assert tj["id"] == "ht-" + tid, "id 与目录名不符: %s" % tid
        brief = tj["instruction"].replace("<outdir>", "out")
        assert "<outdir>" not in brief, "%s 含未替换 <outdir> 占位符" % tid
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(brief)
        # 权重交叉核对（rubric 表 vs 预登记表）
        wr = weights_from_rubric(tid)
        ok = wr == WEIGHTS_PREREG[tid]
        manifest["weights_crosscheck"][tid] = {"rubric_table": wr,
                                               "preregistered": WEIGHTS_PREREG[tid],
                                               "match": ok}
        if not ok:
            print("权重交叉核对不符 %s: rubric=%s 预登记=%s" % (tid, wr, WEIGHTS_PREREG[tid]),
                  file=sys.stderr)
            return 3
        manifest["packs"].append({
            "task": tid, "pack": os.path.relpath(pd, ROOT),
            "source": ("planning/taskset-redesign/merged/hot-templates-skill/%s/"
                       "task.json.instruction（<outdir>→out 机械替换；merged brief.md≡instruction"
                       " 逐字已核）" % tid),
            "dim": tj.get("dim"), "pass_line": tj.get("pass_line"),
            "instruction_sha256": sha256_file(os.path.join(MERGED, tid, "task.json")),
            "brief_sha256": sha256_file(os.path.join(pd, "brief.md")),
        })
    # 通过线登记（hot/t07 盘面 8.5；简报历史记 8.0，两档锚 6.0/0.9 均低于两值，按盘面从严登记）
    manifest["pass_lines"] = {t: json.load(open(os.path.join(MERGED, t, "task.json"),
                                                encoding="utf-8"))["pass_line"] for t in TASKS}
    out = os.path.join(RUN, "records", "packs-manifest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0, "packs": len(manifest["packs"]),
                      "taskset_frozen_ok": True, "weights_crosscheck_ok": True,
                      "pass_lines": manifest["pass_lines"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
