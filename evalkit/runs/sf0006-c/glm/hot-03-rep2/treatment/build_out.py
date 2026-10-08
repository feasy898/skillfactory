#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_out.py — 按 brief.md 的交付契约生成 out/structure.json 与 out/骨架.md。

为何不直接搬 hot-templates 技能 scripts/gen.py 的产物：
其 wx 冻结模板（结构名“引子 + 三段论 + 金句收尾”、要素 9 键、卖点同居 thesis_how、
全文 10+ 处开放占位符）与 brief.md 规定的契约（结构名“引入 + 论点×3 + 总结”、
要素名 引入/论点1..3/总结、每要素 {name,content} 两键、卖点分槽各居一处、
全篇占位恰 1 处、placeholder_stats 三键）不一致，引擎直出物无法通过 brief 的判定。
brief.md 明示“判定即按此执行”，为本次任务的权威契约，故以 brief 契约为准；
【占位:价值点N】token 与 points_used/points_unused 记账语义沿用该技能冻结规约。

确定性：无时间戳、无随机数、无网络；同输入重跑产物逐字节一致（UTF-8 / LF）。
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "out")
INPUT_PATH = os.path.join(ROOT, "fixtures", "input.json")
SJ_PATH = os.path.join(OUT_DIR, "structure.json")
MD_PATH = os.path.join(OUT_DIR, "骨架.md")

TOP_KEYS = [
    "template_version", "platform", "platform_name", "structure_name", "topic",
    "points_input_count", "points_used", "points_unused", "element_count",
    "elements", "placeholder_stats",
]
ELEMENT_NAMES = ["引入", "论点1", "论点2", "论点3", "总结"]
SLOTS = 3  # 论点槽位数（论点1..3）
POINT3_TOKEN = "【占位:价值点3】"
PLACEHOLDER_RE = re.compile(r"【占位:([^】]*)】")
# 合规红线：广告法第九条绝对化用语（逐字扫描两个产物全文）
FORBIDDEN = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级", "独家",
             "万能", "百分百", "绝对", "永久有效", "全网第一"]


def build():
    with open(INPUT_PATH, "r", encoding="utf-8-sig") as f:
        inp = json.load(f)
    if inp.get("platform") != "wx":
        sys.exit("[build_out] 输入 platform 不是 wx，本脚本只实现 brief 的 wx 契约")
    topic = inp["topic"].strip()
    pts = [p.strip() for p in inp["points"]]
    # brief：本任务恰 2 条卖点，全部入槽（论点1/论点2），论点3 落占位
    if len(pts) != 2 or not all(pts):
        sys.exit("[build_out] 输入卖点应为非空 2 条，实得 %r" % (pts,))
    p1, p2 = pts

    contents = {
        "引入": ("家常快手菜这件事，难的不是菜谱，而是每天愿意开火的那点余力——"
                 "把备菜安排进日程、给琐事排好次序，晚饭就能又快又稳地端上桌。"),
        "论点1": (p1 + "：回家先开一个25分钟计时，这一段只做洗切备菜，时间一到立刻开火；"
                  "把这样的专注块固定写进每日计划，快手菜的快才有着落。"),
        "论点2": (p2 + "：把当天工单按重要与紧急分成四格，先清重要且紧急的那格，再按序推进其余；"
                  "同一套排序也可以搬进备菜清单，先做什么后做什么一目了然。"),
        "论点3": ("第3条卖点尚未提供，此论点留位待补：" + POINT3_TOKEN +
                  "——待补充后按前两条的写法展开，此处不代拟新卖点。"),
        "总结": ("家常快手菜的骨架到此搭好：一条论点管安排，一条管排序，第3条留位待补；"
                 "先把已有两条跑顺，整套流程就能日复一日转下去。"),
    }

    filled = 2  # 论点1/论点2 已由卖点填充
    doc = {
        "template_version": "1.0",
        "platform": "wx",
        "platform_name": "公众号文章",
        "structure_name": "引入 + 论点×3 + 总结",
        "topic": topic,
        "points_input_count": len(inp["points"]),
        "points_used": pts,          # 2 条全部在用
        "points_unused": [],         # 无超出/弃用
        "element_count": len(ELEMENT_NAMES),
        "elements": [{"name": n, "content": contents[n]} for n in ELEMENT_NAMES],
        "placeholder_stats": {"slots": SLOTS, "filled": filled,
                              "placeholders": SLOTS - filled},
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(SJ_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join("【%s】%s" % (el["name"], el["content"])
                          for el in doc["elements"]))
        f.write("\n")
    return doc


def verify(doc):
    with open(SJ_PATH, "r", encoding="utf-8") as f:
        sj_text = f.read()
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()
    sj = json.loads(sj_text)
    md_body = md_text.split("\n")
    if md_body and md_body[-1] == "":
        md_body.pop()  # 去掉末尾换行产生的空段
    els = sj["elements"]
    by_name = {e["name"]: e["content"] for e in els}
    stats = sj["placeholder_stats"]

    checks = []
    def check(name, ok, detail=""):
        checks.append((ok, name + (("——" + detail) if (detail and not ok) else "")))

    check("顶层键名与顺序恰为 11 键", list(sj.keys()) == TOP_KEYS, repr(list(sj.keys())))
    check("固定字段取值（platform/platform_name/structure_name/template_version）",
          sj["platform"] == "wx" and sj["platform_name"] == "公众号文章"
          and sj["structure_name"] == "引入 + 论点×3 + 总结" and sj["template_version"] == "1.0")
    with open(INPUT_PATH, "r", encoding="utf-8-sig") as f:
        inp = json.load(f)
    pts_in = [p.strip() for p in inp["points"]]
    check("topic 与 points_input_count 与输入一致",
          sj["topic"] == inp["topic"].strip() and sj["points_input_count"] == len(inp["points"]))
    check("points_used + points_unused 恰等于输入卖点全集",
          sj["points_used"] + sj["points_unused"] == pts_in
          and sj["points_unused"] == [])
    check("要素 name 序列逐字一致且 element_count=5",
          [e["name"] for e in els] == ELEMENT_NAMES and sj["element_count"] == 5)
    check("每要素恰含 name/content 两键",
          all(list(e.keys()) == ["name", "content"] for e in els))
    check("引入/总结 内容各 ≥ 8 字符",
          len(by_name["引入"]) >= 8 and len(by_name["总结"]) >= 8,
          "引入=%d 总结=%d" % (len(by_name["引入"]), len(by_name["总结"])))
    check("论点1 逐字含第 1 条卖点", pts_in[0] in by_name["论点1"])
    check("论点2 逐字含第 2 条卖点", pts_in[1] in by_name["论点2"])
    check("论点3 含逐字占位 token 且未编造/未留空",
          POINT3_TOKEN in by_name["论点3"] and len(by_name["论点3"]) > len(POINT3_TOKEN))
    check("占位仅出现在论点3（其余要素 0 处）",
          sum(1 for e in els if e["name"] != "论点3" and PLACEHOLDER_RE.search(e["content"])) == 0)
    check("placeholder_stats 三键且取值 {slots:3, filled:2, placeholders:1}",
          list(stats.keys()) == ["slots", "filled", "placeholders"]
          and stats == {"slots": 3, "filled": 2, "placeholders": 1})
    md_ph = len(PLACEHOLDER_RE.findall(md_text))
    check("占位记账三处一致（stats/骨架.md 计数/实际未填槽数）",
          md_ph == stats["placeholders"] == SLOTS - stats["filled"], "md=%d" % md_ph)
    bad_sj = [w for w in FORBIDDEN if w in sj_text]
    bad_md = [w for w in FORBIDDEN if w in md_text]
    check("两文件无绝对化用语", not bad_sj and not bad_md,
          "json=%r md=%r" % (bad_sj, bad_md))
    check("两文件无 {{ }} 模板占位残留",
          "{{" not in sj_text and "{{" not in md_text and "}}" not in md_text)
    check("骨架.md 每行一段、恰 5 行、行首【要素名】与 structure.json 一致",
          len(md_body) == 5 and all(
              md_body[i].startswith("【%s】" % n) and md_body[i] == "【%s】%s" % (n, by_name[n])
              for i, n in enumerate(ELEMENT_NAMES)), "行数=%d" % len(md_body))

    for ok, name in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    failed = [n for ok, n in checks if not ok]
    if failed:
        sys.exit("[build_out] %d 项判定未通过" % len(failed))
    print("全部 %d 项判定要点通过 -> %s" % (len(checks), OUT_DIR))


if __name__ == "__main__":
    verify(build())
