#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build/make_deliverables.py — 把 hot-templates 引擎（gen.py, xhs）的骨架产物
确定性转换为 brief.md 要求的交付格式，并就地跑全部判定要点自检。

内容来源链：fixtures/input.json → scripts/gen.py（确定性渲染）→ build/xhs-engine/
→ 本脚本（仅做结构映射与换行压平，不改写任何文案/占位 token）→ out/。

映射：title→标题、hook_block→开头、point_block_N→要点N、tag_group→标签；
summary_block 不在 brief 的 6 要素清单内，按 brief 契约不纳入。
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "fixtures", "input.json")
ENGINE_OUT = os.path.join(ROOT, "build", "xhs-engine", "structure.json")
OUTDIR = os.path.join(ROOT, "out")

ID_TO_NAME = [
    ("title", "标题"),
    ("hook_block", "开头"),
    ("point_block_1", "要点1"),
    ("point_block_2", "要点2"),
    ("point_block_3", "要点3"),
    ("tag_group", "标签"),
]
PLATFORM_NAME = "图文笔记"
STRUCTURE_NAME = "数字标题 + 开头 + 要点×3 + 标签"
TOP_KEYS = ["template_version", "platform", "platform_name", "structure_name", "topic",
            "points_input_count", "points_used", "points_unused", "element_count",
            "elements", "placeholder_stats"]
BANNED = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级", "独家", "万能",
          "百分百", "绝对", "永久有效", "全网第一"]


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    fixture = load(FIXTURE)
    engine = load(ENGINE_OUT)

    # ---- 与引擎产物对账（topic/platform/卖点覆盖必须一致，防错源）----
    assert fixture["platform"] == "xhs" == engine["platform"], "platform 来源不一致"
    assert fixture["topic"] == engine["topic"], "topic 来源不一致"
    in_points = [p.strip() for p in fixture["points"]]
    used = [p for p in engine["points_used"] if p is not None]
    unused = list(engine["points_unused"])
    assert sorted(used + unused) == sorted(in_points), "引擎卖点覆盖与输入不一致"

    by_id = {el["id"]: el for el in engine["elements"]}
    elements = [{"name": name, "content": by_id[eid]["text"].replace("\n", " ")}
                for eid, name in ID_TO_NAME]

    slots = len(engine["points_used"])
    filled = len(used)
    structure = {
        "template_version": engine["template_version"],
        "platform": "xhs",
        "platform_name": PLATFORM_NAME,
        "structure_name": STRUCTURE_NAME,
        "topic": fixture["topic"],
        "points_input_count": len(fixture["points"]),
        "points_used": used,
        "points_unused": unused,
        "element_count": len(elements),
        "elements": elements,
        "placeholder_stats": {"slots": slots, "filled": filled,
                              "placeholders": slots - filled},
    }
    md_lines = ["【%s】%s" % (el["name"], el["content"]) for el in elements]

    os.makedirs(OUTDIR, exist_ok=True)
    sj_path = os.path.join(OUTDIR, "structure.json")
    md_path = os.path.join(OUTDIR, "骨架.md")
    with open(sj_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md_lines) + "\n")

    # ================================================= 判定要点自检
    results = []

    def check(ok, label):
        results.append((bool(ok), label))

    sj_text = open(sj_path, encoding="utf-8").read()
    md_text = open(md_path, encoding="utf-8").read()
    sj = json.loads(sj_text)
    content = {el["name"]: el["content"] for el in sj["elements"]}

    # 1. structure.json 顶层键序与取值
    check(list(sj.keys()) == TOP_KEYS, "1 顶层键依次与 brief 一致")
    check(sj["platform"] == "xhs" and sj["platform_name"] == PLATFORM_NAME
          and sj["structure_name"] == STRUCTURE_NAME and sj["topic"] == fixture["topic"],
          "2 platform/platform_name/structure_name/topic 取值")
    # 2. 卖点全集
    pool = sj["points_used"] + sj["points_unused"]
    check(len(pool) == len(set(pool)) == len(in_points)
          and sorted(pool) == sorted(in_points), "3 points_used+unused 恰等于输入全集（不重不漏）")
    # 3. 要素序列
    names = [el["name"] for el in sj["elements"]]
    check(names == ["标题", "开头", "要点1", "要点2", "要点3", "标签"]
          and sj["element_count"] == 6 == len(sj["elements"])
          and all(list(el.keys()) == ["name", "content"] for el in sj["elements"]),
          "4 elements 名序列/数量/双键结构")
    # 4. placeholder_stats
    check(sj["placeholder_stats"] == {"slots": 3, "filled": 3, "placeholders": 0},
          "5 placeholder_stats 三键取值")
    # 5. 标题：数字 + emoji
    title = content["标题"]
    check(bool(re.search(r"[0-9]", title)), "6 标题含阿拉伯数字")
    check(bool(re.search(r"[\u2705\u2B50\U0001F300-\U0001FAFF]", title)), "7 标题含 emoji")
    # 6. 标签 3-8 个
    tags = re.findall(r"#[^\s#]+", content["标签"])
    check(3 <= len(tags) <= 8, "8 标签数在 3-8（实测 %d 个: %s）" % (len(tags), " ".join(tags)))
    # 7. 要点N 逐字包含第 N 条卖点
    for i, p in enumerate(in_points, 1):
        check(p in content["要点%d" % i], "9 要点%d 逐字包含第 %d 条卖点" % (i, i))
    # 8. 合规红线（两份产物全文）
    for name, text in (("structure.json", sj_text), ("骨架.md", md_text)):
        hits = [w for w in BANNED if w in text]
        check(not hits, "10 %s 无绝对化用语（命中: %s）" % (name, hits or "无"))
    # 9. 无 {{ }} 残留
    check("{{" not in sj_text and "}}" not in sj_text and "{{" not in md_text,
          "11 两份产物无 {{ }} 模板占位残留")
    # 10. 骨架.md 行格式与 structure.json 一致
    lines = md_text.split("\n")
    check(lines[-1] == "" and len([l for l in lines if l != ""]) == 6,
          "12 骨架.md 恰 6 行有效内容、文件尾换行")
    ok_lines = all(l == "【%s】%s" % (el["name"], el["content"])
                   for l, el in zip([l for l in lines if l != ""], sj["elements"]))
    check(ok_lines, "13 骨架.md 每行【要素名】内容且与 structure.json 逐字一致")
    # 11. out/ 只含两份交付物
    check(sorted(os.listdir(OUTDIR)) == ["structure.json", "骨架.md"],
          "14 out/ 目录仅含两份交付物")

    failed = [label for ok, label in results if not ok]
    for ok, label in results:
        print("%s  %s" % ("PASS" if ok else "FAIL", label))
    print("----")
    print("合计 %d 项，失败 %d 项" % (len(results), len(failed)))
    if failed:
        sys.exit(1)
    print("OK -> %s" % OUTDIR)


if __name__ == "__main__":
    main()
