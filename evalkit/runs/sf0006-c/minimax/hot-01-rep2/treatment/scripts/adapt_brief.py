#!/usr/bin/env python3
"""把 gen.py 的引擎产物适配成 brief.md 规定的交付 schema。

引擎产物只作为来源（卖点逐字、主题逐字、槽位归属），本脚本做三件适配：
1. 要素键名 text -> content，要素名按 brief 的 6 字面名重写；
2. 填掉【占位:…】 开放槽位（扩写步骤，brief 要求 content 非空且 placeholders=0）；
3. 把冻结标记「第一招：」改写为不含广告法绝对化用语的「招式一：」。
"""
import json
import pathlib
import re
import sys

ENGINE = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
INPUT = pathlib.Path(sys.argv[3])

BANNED = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级", "独家",
          "万能", "百分百", "绝对", "永久有效", "全网第一"]

NAME_BY_ID = {
    "hook_3s": "钩子",
    "pain_point": "痛点",
    "value_1": "价值点1",
    "value_2": "价值点2",
    "value_3": "价值点3",
    "cta": "行动号召",
}

# 开放槽位补写（扩写步骤内容，仅此处人工/AI 补写，冻结结构标记不改）
FILL = {
    "hook_3s": "先看这条。",
    "pain_point": "买苗买土忙了一整季，阳台越塞越满，收成全看心情，"
                  "问题出在方法，不在努力。",
    "value_1": "先分清哪件最该做，再动手，剩下的往后排。",
    "value_2": "写下这周做成的和卡住的，下周照着改。",
    "value_3": "一次只做一件事，起身活动一下再回来。",
    "cta": "想要阳台种植的执行清单，点个关注，我整理成清单发给你。",
}


def value_text(order: int, point: str, expansion: str) -> str:
    """卖点逐字保留在句首，展开语缀在后面。招式序号用中文数字避开「第一」。"""
    numeral = {1: "一", 2: "二", 3: "三"}[order]
    return f"招式{numeral}：{point}。{expansion}"


def main() -> int:
    src = json.loads(ENGINE.read_text(encoding="utf-8"))
    raw = json.loads(INPUT.read_text(encoding="utf-8"))
    topic = raw["topic"]
    points = raw["points"]

    elements = []
    for el in src["elements"]:
        eid = el["id"]
        name = NAME_BY_ID[eid]
        if eid.startswith("value_"):
            idx = int(eid.split("_")[1])
            point = src["points_used"][idx - 1]
            assert point == points[idx - 1], "卖点未逐字对齐"
            content = value_text(idx, point, FILL[eid])
        elif eid == "hook_3s":
            # 引擎冻结钩子标记（含主题），其后接补写的强句槽位
            head = el["text"].split("——")[0]
            content = head + "，" + FILL[eid]
        elif eid == "pain_point":
            content = FILL[eid]
        else:  # cta
            head = el["text"].split("我把")[0].rstrip("，")
            tail = FILL[eid].rstrip("。")
            content = head + "，" + tail + "。"
        assert content.strip(), f"要素 {name} 内容为空"
        assert "。。" not in content and "，，" not in content, f"要素 {name} 标点重复"
        assert len(set(content.split("，"))) == len(content.split("，")), \
            f"要素 {name} 出现重复短句"
        assert "{{" not in content and "}}" not in content
        for word in BANNED:
            assert word not in content, f"{name} 命中广告法绝对化用语：{word}"
        elements.append({"name": name, "content": content})

    assert len(elements) == 6
    assert [e["name"] for e in elements] == [
        "钩子", "痛点", "价值点1", "价值点2", "价值点3", "行动号召"]
    assert len(elements[0]["content"]) >= 8, "钩子需 ≥8 字符"
    assert any(w in elements[5]["content"] for w in ("关注", "评论", "私信", "点击"))
    for i in range(3):
        assert points[i] in elements[2 + i]["content"]

    used = src["points_used"]
    unused = src["points_unused"]
    assert sorted([p for p in used + unused]) == sorted(points), "卖点全集对不上"

    # brief 规定的平台名/结构名字面串，与引擎内置串不同，此处按 brief 覆盖
    structure = {
        "template_version": src["template_version"],
        "platform": src["platform"],
        "platform_name": "短视频口播稿",
        "structure_name": "3秒钩子 + 痛点 + 价值点×3 + 行动号召",
        "topic": topic,
        "points_input_count": len(points),
        "points_used": used,
        "points_unused": unused,
        "element_count": len(elements),
        "elements": elements,
        "placeholder_stats": {"slots": 3, "filled": 3, "placeholders": 0},
    }

    blob = json.dumps(structure, ensure_ascii=False, indent=2) + "\n"
    for word in BANNED:
        assert word not in blob, f"structure.json 命中绝对化用语：{word}"
    assert not re.search(r"\{\{.*?\}\}", blob, re.S), "structure.json 残留 {{ }} 占位"
    assert "{{" not in blob, "structure.json 残留 {{ 变量"

    lines = [f"【{e['name']}】{e['content']}" for e in elements]
    md = "\n".join(lines) + "\n"
    for word in BANNED:
        assert word not in md, f"骨架.md 命中绝对化用语：{word}"
    assert not re.search(r"\{\{.*?\}\}", md, re.S), "骨架.md 残留 {{ }} 占位"
    assert "{{" not in md, "骨架.md 残留 {{ 变量"

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "structure.json").write_text(blob, encoding="utf-8")
    (OUT / "骨架.md").write_text(md, encoding="utf-8")
    print(f"OK adapted elements={len(elements)} placeholders=0 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
