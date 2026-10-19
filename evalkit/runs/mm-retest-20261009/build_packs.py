#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/build_packs.py — mm 重测 8 任务臂任务包构建（零模型）。

任务源（冻结）：planning/taskset-redesign/merged/meeting-minutes-skill/t01..t08
  （任务集冻结净荷 100 文件=adae05f2…，本轮开工实算复算相符）。
臂 brief.md = task.json.instruction 逐字（<outdir>→out 机械替换，唯一改动；
  照 sf0008-k5b meeting-minutes packs 与 office-retest 先例）。fixtures/ 空目录在位
  （make_arms 装置要求；输入转写稿内嵌 instruction，臂自存数据文件属任务面）。
判据面（rubric.md/judge-notes.md/golden/runner/reference）一律不进 pack。
退出码：0=8 包构建完成且校验过。
"""
import hashlib
import json
import os
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "meeting-minutes-skill")
FROZEN_100 = "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6"
TASK_ORDER = ["t0%d" % i for i in range(1, 9)]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    assert live == FROZEN_100, "任务集冻结哈希复算不符：%s" % live
    manifest = {"run": "mm-retest-20261009", "taskset_frozen_sha256_100": live,
                "taskset_frozen_cmd": cmd, "packs": []}
    for tid in TASK_ORDER:
        pd = os.path.join(RUN, "packs", "meeting-minutes-%s" % tid)
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)
        tj = json.load(open(os.path.join(MERGED, tid, "task.json"), encoding="utf-8"))
        assert tj["id"] == "mm-" + tid or tj["id"] == tid, "id 与目录名不符: %s" % tid
        brief = tj["instruction"].replace("<outdir>", "out")
        assert "<outdir>" not in brief, "%s 含未替换 <outdir> 占位符" % tid
        # 投喂面禁泄判据词汇（判官词汇扫描：rubric/judge-notes 专属词不得出现在 brief）
        for banned in ("judge-notes", "判官", "判挂点", "rubric"):
            assert banned not in brief, "%s brief 含判据词汇 %s" % (tid, banned)
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(brief + "\n")
        manifest["packs"].append({
            "task": tid, "pack": os.path.relpath(pd, ROOT),
            "source": "planning/taskset-redesign/merged/meeting-minutes-skill/%s/task.json.instruction"
                      "（<outdir>→out 机械替换，其余逐字）" % tid,
            "dim": tj.get("dim"), "pass_line": tj.get("pass_line"),
            "brief_sha256": sha256_file(os.path.join(pd, "brief.md")),
            "outdir_replaced": "<outdir>" in tj["instruction"],
            "brief_is_instruction_outdir_replaced_only":
                open(os.path.join(pd, "brief.md"), encoding="utf-8", newline="").read()
                == tj["instruction"].replace("<outdir>", "out") + "\n",
        })
    out = os.path.join(RUN, "records", "packs-manifest.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0, "packs": len(manifest["packs"]), "taskset_sha_ok": True},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
