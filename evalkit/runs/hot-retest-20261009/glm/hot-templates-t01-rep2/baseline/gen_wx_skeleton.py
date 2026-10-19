#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_wx_skeleton.py — 公众号文章（wx）爆款内容骨架生成器（本工作面自研实现，纯标准库、确定性）。

模板规格取自仓库内公开冻结文档（逐字冻结，不由本脚本发明）：
  - dist/hot-templates-skill/references/wx.md（5 要素/开放槽位/填充语义）
  - dist/hot-templates-skill/references/frozen-tokens.md（占位 token 常量表）

结构名：引子 + 三段论 + 金句收尾（5 要素，id 顺序冻结，模板版本 1.0）：
  lead_in → thesis_what → thesis_why → thesis_how → golden_ending

冻结要点（wx）：
  - topic 在 lead_in/thesis_what/thesis_why/golden_ending 四要素各记一次 filled_from_input="topic"；
    thesis_how 三抓手行记 point#1..3 → 满 3 卖点 total_filled_from_input=7。
  - 【占位:…】开放槽位禁止填充；总 open 恒 10（lead_in 1 + what 2 + why 3 + how 3 + ending 1）。
  - 卖点恰好 3 槽：非空 strip 入槽，缺失落【占位:价值点N】，第 4 条起保序记 points_unused。

用法：
  python3 gen_wx_skeleton.py --topic <主题> --points <内联 JSON 串或 utf-8 JSON 文件路径> --outdir <目录>

产物：<outdir>/骨架.md 与 <outdir>/structure.json（UTF-8、LF；structure.json 为
ensure_ascii=False、indent=2、文件尾一个换行；同输入重跑逐字节一致）。成功 exit 0，
参数错 exit 2（不建目录、零产物）。
"""

import argparse
import json
import os
import re
import sys

TEMPLATE_VERSION = "1.0"
PLATFORM = "wx"
PLATFORM_NAME = "公众号文章"
STRUCTURE_NAME = "引子 + 三段论 + 金句收尾"

PLACEHOLDER_RE = re.compile(r"【占位:([^】]*)】")


def fail(msg):
    print("[gen_wx_skeleton] 错误：%s" % msg, file=sys.stderr)
    sys.exit(2)


def load_points(spec):
    """--points 接受：utf-8(-sig) JSON 文件路径（纯列表或含 points 键的对象）或内联 JSON 串。"""
    if os.path.isfile(spec):
        try:
            with open(spec, "r", encoding="utf-8-sig") as f:
                raw = f.read()
        except OSError as e:
            fail("卖点文件无法读取：%s（%s）" % (spec, e))
    else:
        raw = spec
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        fail("--points 不是合法 JSON（既非可读文件，也非内联 JSON）：%r" % spec[:80])
    if isinstance(data, dict):
        if "points" not in data:
            fail("--points 指向的 JSON 对象缺少 points 键：%r" % (list(data.keys()),))
        data = data["points"]
    if not isinstance(data, list):
        fail("--points 解析结果不是列表（got %s）" % type(data).__name__)
    for i, item in enumerate(data, 1):
        if not isinstance(item, str):
            fail("--points 第 %d 项不是字符串（got %s）" % (i, type(item).__name__))
    return [p.strip() for p in data]


def normalize_points(points):
    """规整为恰好 3 槽：不足记缺失，超出保序记 unused。"""
    used, filled = [], []
    for i in range(3):
        if i < len(points) and points[i]:
            used.append(points[i])
            filled.append(True)
        else:
            used.append(None)
            filled.append(False)
    return used, filled, points[3:]


def point_slot(idx, val):
    return val if val else "【占位:价值点%d】" % idx


def build_elements(topic, pts, filled):
    how_lines = ["落到操作层面，给你三个抓手："]
    for i, (pv, ok) in enumerate(zip(pts, filled), 1):
        how_lines.append("%d. %s——【占位:展开：具体做法+一个例子】" % (i, point_slot(i, pv)))
    return [{
        "id": "lead_in", "name": "引子", "order": 1,
        "text": "【占位:用一个具体场景/对话/新闻切入，150字左右】——这背后，其实是同一个问题：%s。" % topic,
        "filled_from_input": ["topic"],
        "meta": {"beat": "场景化开场，把读者拉进问题现场"},
    }, {
        "id": "thesis_what", "name": "三段论·一（是什么）", "order": 2,
        "text": "一、是什么\n%s的本质，不是【占位:常见误解】，而是【占位:一句话给出你的定义】。" % topic,
        "filled_from_input": ["topic"],
        "meta": {"beat": "先破后立，给出定义"},
    }, {
        "id": "thesis_why", "name": "三段论·二（为什么）", "order": 3,
        "text": "二、为什么\n大多数人在%s上反复失败，根源有三：【占位:根因1】；【占位:根因2】；【占位:根因3】。" % topic,
        "filled_from_input": ["topic"],
        "meta": {"beat": "归因，三条根因对齐后文三个抓手"},
    }, {
        "id": "thesis_how", "name": "三段论·三（怎么办）", "order": 4,
        "text": "三、怎么办\n" + "\n".join(how_lines),
        "filled_from_input": ["point#%d" % (i + 1) for i in range(3) if filled[i]],
        "meta": {"beat": "三个抓手一一对应三条根因，可执行"},
    }, {
        "id": "golden_ending", "name": "金句收尾", "order": 5,
        "text": "「%s这件事，【占位:金句主体——句式建议：真正的…不是靠…，而是靠…】」\n共勉。" % topic,
        "filled_from_input": ["topic"],
        "meta": {"beat": "一句话收束，可直接被读者摘抄转发"},
    }]


def count_placeholders(text):
    toks = PLACEHOLDER_RE.findall(text)
    return len(toks), list(dict.fromkeys(toks))


def build_stats(elements):
    by_element, total_open, filled_slots = {}, 0, []
    unique_tokens = []
    for el in elements:
        n, toks = count_placeholders(el["text"])
        by_element[el["id"]] = n
        total_open += n
        filled_slots.extend(el["filled_from_input"])
        for t in toks:
            if t not in unique_tokens:
                unique_tokens.append(t)
    return {
        "total_open": total_open,
        "total_filled_from_input": len(filled_slots),
        "by_element": by_element,
        "open_tokens_unique": unique_tokens,
        "filled_slots": filled_slots,
    }


def render_markdown(topic, points_in, used, filled, unused, elements):
    lines = [
        "# %s · 爆款骨架" % PLATFORM_NAME,
        "",
        "- 主题：%s" % topic,
        "- 平台/模板：`%s` @ v%s（%s）" % (PLATFORM, TEMPLATE_VERSION, STRUCTURE_NAME),
        "- 卖点输入：%d 条 → 规整为 3 条（缺失补占位 %d 条，超出截断 %d 条）"
        % (len(points_in), sum(1 for f in filled if not f), len(unused)),
        "",
        "---",
        "",
    ]
    for el in elements:
        lines.append("## %d. %s" % (el["order"], el["name"]))
        lines.append("")
        lines.append(el["text"])
        lines.append("")
        lines.append("> 写法要点：%s" % el["meta"]["beat"])
        lines.append("")
    lines += ["---", "", "## 占位符统计", ""]
    stats = build_stats(elements)
    lines.append("- 未填占位符（待人工/AI 补写）：**%d 处**" % stats["total_open"])
    lines.append("- 已从输入填充：%d 处（%s）" % (stats["total_filled_from_input"],
                                                 "、".join(stats["filled_slots"]) or "无"))
    for el in elements:
        lines.append("  - %d. %s：%d 处" % (el["order"], el["name"],
                                            stats["by_element"][el["id"]]))
    lines.append("")
    lines.append("> 说明：所有 `【占位:…】` 为开放槽位，由使用者补写；"
                 "`structure.json` 为机器可读的结构要素清单与占位符统计，与本文同源同构。")
    lines.append("")
    return "\n".join(lines)


def build_structure_json(topic, points_in, used, unused, elements):
    els_out = []
    for el in elements:
        n, toks = count_placeholders(el["text"])
        els_out.append({
            "id": el["id"],
            "name": el["name"],
            "order": el["order"],
            "required": True,
            "text": el["text"],
            "placeholder_count": n,
            "open_placeholders": toks,
            "filled_from_input": el["filled_from_input"],
            "meta": el["meta"],
        })
    return {
        "template_version": TEMPLATE_VERSION,
        "platform": PLATFORM,
        "platform_name": PLATFORM_NAME,
        "structure_name": STRUCTURE_NAME,
        "topic": topic,
        "points_input_count": len(points_in),
        "points_used": [u if u else None for u in used],
        "points_unused": unused,
        "element_count": len(els_out),
        "elements": els_out,
        "placeholder_stats": build_stats(elements),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="公众号文章（wx）爆款内容骨架生成器")
    ap.add_argument("--topic", required=True, help="主题（strip 后不得为空）")
    ap.add_argument("--points", required=True, help="卖点 JSON：文件路径或内联串")
    ap.add_argument("--outdir", required=True, help="输出目录（不存在则递归创建）")
    args = ap.parse_args()

    topic = args.topic.strip()
    if not topic:
        fail("--topic 不能为空")
    points_in = load_points(args.points)
    used, filled, unused = normalize_points(points_in)

    elements = build_elements(topic, used, filled)
    md = render_markdown(topic, points_in, used, filled, unused, elements)
    sj = build_structure_json(topic, points_in, used, unused, elements)

    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "骨架.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    with open(os.path.join(args.outdir, "structure.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(sj, f, ensure_ascii=False, indent=2)
        f.write("\n")

    stats = sj["placeholder_stats"]
    print("OK platform=%s topic=%s elements=%d open_placeholders=%d filled_from_input=%d -> %s"
          % (PLATFORM, topic, sj["element_count"], stats["total_open"],
             stats["total_filled_from_input"], args.outdir))
    sys.exit(0)


if __name__ == "__main__":
    main()
