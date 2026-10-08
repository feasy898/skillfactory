# -*- coding: utf-8 -*-
"""build — 落盘三包新任务集（task.json / brief.md / rubric.md）+ index.json + DESIGN.md。

用法：python gen/build.py    （在 minimax/ 目录下运行）
零模型调用；纯文件生成 + sha256 冻结。
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import spec_common  # noqa: E402
import spec_mm  # noqa: E402
import spec_office  # noqa: E402
import spec_hot  # noqa: E402

PKGS = [
    ("meeting-minutes-skill", spec_mm.TASKS),
    ("office-templates-skill", spec_office.TASKS),
    ("hot-templates-skill", spec_hot.TASKS),
]


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def dir_manifest_digest(pkg, pkg_dir):
    """包级 sha256：对包目录下全部文件按相对路径排序，拼 "<relpath>  <file_sha256>\\n" 后再哈希。"""
    items = []
    for root, _dirs, files in os.walk(pkg_dir):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, pkg_dir).replace(os.sep, "/")
            items.append((rel, sha256_file(p)))
    items.sort()
    blob = pkg + "\n" + "".join("%s  %s\n" % (r, d) for r, d in items)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest(), items


def dims_of(tasks):
    out = {}
    for t in tasks:
        out[t["dim"]] = out.get(t["dim"], 0) + 1
    return out


def build():
    index = {
        "project": "SF-0011 task-set-redesign（K-5 产线指令第 2 条）",
        "designer": "独立设计方 minimax族任务集设计师（未接触任何盲评结果）",
        "generated_by": "planning/taskset-redesign/minimax/gen/build.py（零模型调用）",
        "date": "2026-10-08",
        "spec_refs": [
            "EVAL-SPEC-v0.2 §3.1 任务规模：ab_tasks ≥5、目标 8；三维覆盖（能力/难度·边界/陷阱）",
            "EVAL-SPEC-v0.2 §3.3-1：加权分 = Σ(维度分×权重)/Σ权重（0–10）",
            "planning/test-cards-20261008/K5-ruling-20261008.md 产线指令第 2 条（仅该节）",
        ],
        "sha256_scope": "包级 sha256 = sha256(包名 + \"\\n\" + 按相对路径排序的 \"<relpath>  <file_sha256>\\n\" 串)。"
                        "复算：gen/build.py 重跑即可得同值（生成确定性，无时间戳入内容）。",
        "read_discipline": [
            "未读取 dist/*/eval/results/、**/ab_summary.json、**/benchmark.json、evidence/publish-approval-REQUEST.md",
            "K5 裁决文档仅读「产线指令」节第 2 条设计要求",
            "设计依据仅：三包 SKILL.md / references/*.md / eval/golden.json（旧 ab_tasks 作反饱和对照）/ 资产脚本",
        ],
        "global_rules": {
            "tasks_per_pkg": 8,
            "dims_required": ["能力", "边界", "陷阱"],
            "trap_min": "≥2（占 8 题的 1/4），实配 3",
            "nonce_policy": "每题关键实体（人名/部门/日期/金额/编号/主题）一次性注入；题面、判据、oracle 共用同一 nonce",
            "rubric": "五维加权分项（endpoint/semantic/structure/mechanical/discipline），权重和 = 100，红线封顶 ≤4",
            "baseline_target": "强裸模型（不挂 skill）通过率 ≤60%，逐题 design_note 已写入 task.json",
        },
        "packages": [],
    }

    for pkg, tasks in PKGS:
        pkg_dir = os.path.join(ROOT, pkg)
        entries = []
        for t in tasks:
            tdir = os.path.join(pkg_dir, t["task_id"])
            files = spec_common.build_task(pkg, t)
            for name, text in files.items():
                write(os.path.join(tdir, name), text)
            entries.append({
                "task_id": t["task_id"],
                "path": "%s/%s" % (pkg, t["task_id"]),
                "dim": t["dim"],
                "trap": t["dim"] == "陷阱",
                "title": t["title"],
                "nonce": t["nonce"],
                "weights": t.get("weights", spec_common.DEFAULT_W),
                "checks": len(t["checks"]),
                "sha256": {name: sha256_file(os.path.join(tdir, name)) for name in files},
            })
        digest, items = dir_manifest_digest(pkg, pkg_dir)
        index["packages"].append({
            "pkg": pkg,
            "task_count": len(tasks),
            "dims": dims_of(tasks),
            "dims_note": "能力/边界/陷阱三维覆盖，陷阱 %d 条（≥1/4）" % dims_of(tasks).get("陷阱", 0),
            "sha256": digest,
            "sha256_scope": index["sha256_scope"],
            "files": [{"relpath": r, "sha256": d} for r, d in items],
            "tasks": entries,
        })

    write(os.path.join(ROOT, "index.json"),
          json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return index


if __name__ == "__main__":
    idx = build()
    for p in idx["packages"]:
        print("%-24s tasks=%d dims=%s sha256=%s" % (
            p["pkg"], p["task_count"], p["dims"], p["sha256"]))
    print("index.json written")