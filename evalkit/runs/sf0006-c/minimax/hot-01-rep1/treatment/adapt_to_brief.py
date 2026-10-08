#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 gen.py 的引擎产物适配成 brief.md 规定的 schema。

输入：_engine_raw/structure.json（scripts/gen.py 确定性渲染的原始产物）
输出：out/structure.json、out/骨架.md

要素文本、顺序、要点填充全部沿用引擎结果，不改写文案；此处只做两件事：
  1. schema/命名对齐 brief（platform_name、structure_name、要素 name、content 键、placeholder_stats）
  2. 合规改写：冻结标记「第一招：」含绝对化用语「第一」，按 brief 合规红线改为「招式一：」，等义改写。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "_engine_raw" / "structure.json"
OUT = ROOT / "out"

# 引擎 id -> brief 要素名（brief 冻结序列）
NAME_MAP = {
    "hook_3s": "钩子",
    "pain_point": "痛点",
    "value_1": "价值点1",
    "value_2": "价值点2",
    "value_3": "价值点3",
    "cta": "行动号召",
}

# 合规改写：「第一招」→「招式一」，避免绝对化用语「第一」
REWRITE = (("第一招：", "招式一："), ("第二招：", "招式二："), ("第三招：", "招式三："))

BANNED = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级", "独家",
          "万能", "百分百", "绝对", "永久有效", "全网第一"]


def main():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    assert src["platform"] == "dy", src["platform"]

    elements = []
    for el in src["elements"]:
        content = el["text"]
        for old, new in REWRITE:
            content = content.replace(old, new)
        assert content.strip(), el["id"]
        elements.append({"name": NAME_MAP[el["id"]], "content": content})

    assert [e["name"] for e in elements] == [
        "钩子", "痛点", "价值点1", "价值点2", "价值点3", "行动号召"]

    # 卖点槽位统计：3 槽位，全部由输入填充，0 残留
    used = [p for p in src["points_used"] if p is not None]
    slots = 3
    filled = min(len(used), slots)

    # 逐字包含校验
    points = json.loads((ROOT / "fixtures" / "input.json").read_text(encoding="utf-8"))["points"]
    for i, p in enumerate(points):
        assert p in elements[2 + i]["content"], p

    doc = {
        "template_version": src["template_version"],
        "platform": "dy",
        "platform_name": "短视频口播稿",
        "structure_name": "3秒钩子 + 痛点 + 价值点×3 + 行动号召",
        "topic": src["topic"],
        "points_input_count": src["points_input_count"],
        "points_used": src["points_used"],
        "points_unused": src["points_unused"],
        "element_count": len(elements),
        "elements": elements,
        "placeholder_stats": {"slots": slots, "filled": filled,
                              "placeholders": slots - filled},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "structure.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = "".join(f"【{e['name']}】{e['content']}\n" for e in elements)
    (OUT / "骨架.md").write_text(md, encoding="utf-8")

    blob = md + (OUT / "structure.json").read_text(encoding="utf-8")
    hits = [w for w in BANNED if w in blob]
    assert not hits, hits
    assert not re.search(r"\{\{.*?\}\}", blob)
    assert len(elements[0]["content"]) >= 8
    assert any(w in elements[5]["content"] for w in ("关注", "评论", "私信", "点击"))
    print(f"OK elements={len(elements)} banned=0 {{}}=0 -> {OUT}")


if __name__ == "__main__":
    main()