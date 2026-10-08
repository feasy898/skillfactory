#!/usr/bin/env python3
"""Build out/structure.json and out/骨架.md from fixtures/input.json."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "fixtures", "input.json"), encoding="utf-8") as f:
    data = json.load(f)

points = data["points"]

ELEMENTS = [
    ("标题", "3个通勤读书方法✅碎片时间也能读透一本书"),
    ("开头", "每天通勤的两小时与其刷手机，不如用固定节奏把它变成阅读时间。下面这三个方法拆开就能用，先收藏再试。"),
    ("要点1", "方法一｜按25分钟专注加5分钟休息的节奏执行，一段地铁通勤刚好走完两个循环。"),
    ("要点2", "方法二｜用四象限法给青澜会员中台相关任务排优先级，先啃当天最卡的那件。"),
    ("要点3", "方法三｜每周日晚固定30分钟复盘本周得失，把下周要读的书提前排进日程。"),
    ("标签", "#通勤读书 #读书方法 #时间管理 #碎片时间 #效率工具 #学习成长"),
]

structure = {
    "template_version": "1.0",
    "platform": "xhs",
    "platform_name": "图文笔记",
    "structure_name": "数字标题 + 开头 + 要点×3 + 标签",
    "topic": data["topic"],
    "points_input_count": len(points),
    "points_used": list(points),
    "points_unused": [],
    "element_count": len(ELEMENTS),
    "elements": [{"name": n, "content": c} for n, c in ELEMENTS],
    "placeholder_stats": {"slots": len(points), "filled": len(points), "placeholders": 0},
}

os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
with open(os.path.join(BASE, "out", "structure.json"), "w", encoding="utf-8") as f:
    json.dump(structure, f, ensure_ascii=False, indent=2)
    f.write("\n")

with open(os.path.join(BASE, "out", "骨架.md"), "w", encoding="utf-8") as f:
    for n, c in ELEMENTS:
        f.write(f"【{n}】{c}\n")

print("written")