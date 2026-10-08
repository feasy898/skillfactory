#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_out.py — 按 brief.md 的交付契约产出 out/structure.json 与 out/骨架.md。

底稿来自技能包的确定性渲染引擎 scripts/gen.py（平台 xhs），本脚本只做两件事：
  1) 投影：把引擎的 7 要素 xhs 模板映射为 brief 约定的 6 要素契约
     （标题 / 开头 / 要点1..3 / 标签），并按 brief 把字段名改为 {name, content}；
  2) 填槽：把引擎文本里的【占位:…】开放槽位补写为正文（brief 要求 placeholders=0），
     同时把换行压平，保证 骨架.md 严格「每行一段」。

无时间戳、无随机数、无网络；同输入重复运行两份产物逐字节一致。
"""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(ROOT, ".zcode", "skills", "hot-templates", "scripts", "gen.py")
INPUT = os.path.join(ROOT, "fixtures", "input.json")
OUTDIR = os.path.join(ROOT, "out")

TEMPLATE_VERSION = "1.0"
PLATFORM = "xhs"
PLATFORM_NAME = "图文笔记"
STRUCTURE_NAME = "数字标题 + 开头 + 要点×3 + 标签"

# brief 契约：引擎要素 id -> 交付要素名（顺序冻结）
NAME_MAP = [
    ("title", "标题"),
    ("hook_block", "开头"),
    ("point_block_1", "要点1"),
    ("point_block_2", "要点2"),
    ("point_block_3", "要点3"),
    ("tag_group", "标签"),
]

# 引擎 id -> 开放槽位 token（见 references/frozen-tokens.md）；值为补写后的正文
SLOT_FILL = {
    "title": "上班族",
    "hook_block": "地铁上刷手机越刷越焦虑，睡前才发现今天一页没读",
    "point_block_1": "1）坐下先定25分钟闹钟，手机反扣；2）这25分钟只读不查资料；"
                     "3）第26分钟起身走动5分钟再进下一轮，读不满25分钟也算完成。",
    "point_block_2": "1）把当天待办写在一张纸上；2）按重要/紧急画四格；"
                     "3）先做重要不紧急那一格，重要紧急的排后面，不紧急的直接划掉。",
    "point_block_3": "1）周日晚上留出30分钟；2）写下本周读完的章节和卡住的地方；"
                     "3）只挑1个下周要改的动作，其余留到下周日再看。",
    "tag_group": "#时间管理 #精力管理",
}

# 广告法第九条等绝对化用语红线（brief 判定要点）
BANNED = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级",
          "独家", "万能", "百分百", "绝对", "永久有效", "全网第一"]
PLACEHOLDER_RE = re.compile(r"【占位:([^】]*)】")
TAG_RE = re.compile(r"#[^\s#]+")
DIGIT_RE = re.compile(r"[0-9]")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿✅]")


def fail(msg):
    print("[build_out.py] 错误：%s" % msg, file=sys.stderr)
    sys.exit(2)


def flatten(text):
    """把引擎文本压成单行：换行→｜，供「每行一段」的 骨架.md 使用。"""
    return "｜".join(seg.strip() for seg in text.split("\n") if seg.strip())


def main():
    with open(INPUT, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    points_in = [str(p).strip() for p in payload["points"] if str(p).strip()]

    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, GEN, "--platform", PLATFORM,
             "--topic", payload["topic"], "--points", INPUT, "--outdir", tmp],
            capture_output=True, text=True)
        if proc.returncode != 0:
            fail("渲染引擎失败：%s" % (proc.stderr.strip() or proc.stdout.strip()))
        with open(os.path.join(tmp, "structure.json"), "r", encoding="utf-8") as f:
            base = json.load(f)

    by_id = {el["id"]: el for el in base["elements"]}
    elements = []
    for el_id, name in NAME_MAP:
        text = flatten(by_id[el_id]["text"])

        def repl(_m, el_id=el_id):
            return SLOT_FILL[el_id]

        text = PLACEHOLDER_RE.sub(repl, text)
        if PLACEHOLDER_RE.search(text):
            fail("要素「%s」仍有未填槽位" % name)
        if "{{" in text or "}}" in text:
            fail("要素「%s」残留 {{ }} 模板占位" % name)
        for word in BANNED:
            if word in text:
                fail("要素「%s」命中合规红线词「%s」" % (name, word))
        elements.append({"name": name, "content": text})

    # ---- brief 判定要点自检 ----
    title = elements[0]["content"]
    if not DIGIT_RE.search(title):
        fail("标题缺少阿拉伯数字")
    if not EMOJI_RE.search(title):
        fail("标题缺少 emoji 表情")
    tags = TAG_RE.findall(elements[5]["content"])
    if not 3 <= len(tags) <= 8:
        fail("标签数量 %d 不在 3-8 之间" % len(tags))
    for i, point in enumerate(points_in[:3]):
        if point not in elements[2 + i]["content"]:
            fail("要点%d 未逐字包含第 %d 条卖点" % (i + 1, i + 1))

    used = points_in[:3]
    unused = points_in[3:]
    structure = {
        "template_version": TEMPLATE_VERSION,
        "platform": PLATFORM,
        "platform_name": PLATFORM_NAME,
        "structure_name": STRUCTURE_NAME,
        "topic": payload["topic"],
        "points_input_count": len(payload["points"]),
        "points_used": used,
        "points_unused": unused,
        "element_count": len(elements),
        "elements": elements,
        "placeholder_stats": {"slots": 3, "filled": len(used), "placeholders": 0},
    }

    lines = ["【%s】%s" % (el["name"], el["content"]) for el in elements]
    md = "\n".join(lines) + "\n"
    for word in BANNED:
        if word in md:
            fail("骨架.md 命中合规红线词「%s」" % word)

    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "structure.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(OUTDIR, "骨架.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)

    print("OK platform=%s topic=%s elements=%d placeholders=0 -> %s"
          % (PLATFORM, payload["topic"], len(elements), OUTDIR))
    sys.exit(0)


if __name__ == "__main__":
    main()
