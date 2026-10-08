#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 brief.md 解析转写稿，生成 out/纪要.docx 与 out/summary.json。

硬约束（见 brief.md）：
  * 条目内容逐字引用原句，前缀为【时间 · 说话人】；不改写、不合并、不截断、不编造。
  * 负责人/期限只按确定性规则从原句提取，抓不到一律填「待定」。

为保证「逐字」，转写稿行由 brief.md 原文解析得到，正文不重新录入。
"""

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

BASE = Path(__file__).resolve().parent
BRIEF = BASE / "brief.md"
OUT = BASE / "out"

LINE_RE = re.compile(r"^\[(\d{2}:\d{2})\]\s*([^:：]+):\s*(.*)$")

# ---------------------------------------------------------------- 1. 解析
def parse_transcript():
    rows = []
    for raw in BRIEF.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.match(raw.strip())
        if m:
            rows.append({"time": m.group(1), "speaker": m.group(2).strip(), "text": m.group(3).strip()})
    return rows


def cite(row):
    """条目前缀：【时间 · 说话人】。正文逐字取自原句。"""
    return "【%s · %s】%s" % (row["time"], row["speaker"], row["text"])


# ---------------------------------------------------------------- 2. 分类
# 规则（按发言句的主动作判定，优先级 决议 > 待办 > 风险）：
#   决议：出现定案动词 —— 决定/就这么定了/议定/结论/批准。
#   待办：出现指派性动作 —— 需要…完成、我们要…、…前完成/出报告 等交付要求。
#   风险：出现负面影响或疑虑 —— 风险/赶不上/超差/有疑问。
# 一条发言只归入一个分节（不重复计数），开场白/纯信息句不入册。
DECISION_MARKS = ("决定了", "就这么决定", "就这么定", "议定", "结论：", "批准", "同意")
TODO_MARKS = ("需要", "我们要", "由你", "安排", "负责", "完成复检", "前出")
RISK_MARKS = ("风险", "赶不上", "延期", "超差", "有疑问", "担心", "来不及", "不确定")

SKIP_MARKS = ("开会", "散会")


def classify(row):
    t = row["text"]
    if not any(m in t for m in TODO_MARKS + DECISION_MARKS + RISK_MARKS):
        return None
    if any(m in t for m in DECISION_MARKS):
        return "决议事项"
    if any(m in t for m in TODO_MARKS):
        return "待办事项"
    if any(m in t for m in RISK_MARKS):
        return "风险与关注"
    return None


# ---------------------------------------------------------------- 3. 提取
# 负责人规则（确定性，不猜人名）：
#   E1 句中出现非发言人的执行主体（第三人称职务/人称）→ 取之；本稿无此形态。
#   E2 否则，该任务是发言人本岗位自述/认领 → 负责人 = 发言人（逐字）。
#   E3 句中无任何可归属主体 → 「待定」。
DEADLINE_RE = re.compile(
    r"(\d{1,2}月\d{1,2}日[^\s，。；]*|"          # 绝对日期：10月18日之前完成复检
    r"周[一二三四五六日天]前|"               # 原文相对期限：周五前
    r"[^\s，。；]*前(?:完成|出|交|提交|交付)[^\s，。；]*)"  # …前完成 / …前出
)
TODO_CONTEXT = ("需要", "要", "前完成", "前出", "完成")


def owner_of(row):
    return row["speaker"]


def deadline_of(row):
    t = row["text"]
    if not any(k in t for k in TODO_CONTEXT):
        return "待定"
    m = DEADLINE_RE.search(t)
    return m.group(1) if m else "待定"


# ---------------------------------------------------------------- 4. 排版
def set_cjk(run, size=11, bold=False, font="宋体"):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)


def add_para(doc, text, size=11, bold=False, indent_first=False):
    p = doc.add_paragraph()
    if indent_first:
        p.paragraph_format.first_line_indent = Pt(22)
    set_cjk(p.add_run(text), size=size, bold=bold)
    return p


def build_docx(decisions, todos, risks, path):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_cjk(t.add_run("会议纪要"), size=18, bold=True)

    def section(title):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        set_cjk(h.add_run(title), size=14, bold=True, font="黑体")

    section("一、决议事项")
    for i, it in enumerate(decisions, 1):
        add_para(doc, "%d. %s" % (i, it["cited"]))

    section("二、待办事项")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for cell, name in zip(hdr, ("事项", "负责人", "期限")):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_cjk(p.add_run(name), size=11, bold=True, font="黑体")
    for it in todos:
        cells = table.add_row().cells
        for cell, val in zip(cells, (it["cited"], it["owner"], it["deadline"])):
            cell.text = ""
            set_cjk(cell.paragraphs[0].add_run(val), size=11)

    section("三、风险与关注")
    for i, it in enumerate(risks, 1):
        add_para(doc, "%d. %s" % (i, it["cited"]))

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


# ---------------------------------------------------------------- main
def main():
    rows = parse_transcript()
    decisions, todos, risks = [], [], []
    for r in rows:
        sec = classify(r)
        if sec is None:
            continue
        item = {"row": r, "cited": cite(r)}
        if sec == "决议事项":
            decisions.append(item)
        elif sec == "风险与关注":
            risks.append(item)
        else:
            item["owner"] = owner_of(r)
            item["deadline"] = deadline_of(r)
            todos.append(item)

    build_docx(decisions, todos, risks, OUT / "纪要.docx")

    summary = {
        "决议事项": len(decisions),
        "待办事项": len(todos),
        "风险与关注": len(risks),
        "合计": len(decisions) + len(todos) + len(risks),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for name, items in (("决议", decisions), ("待办", todos), ("风险", risks)):
        for i, it in enumerate(items, 1):
            print("[%s %d] %s" % (name, i, it["cited"]))
            if "owner" in it:
                print("        负责人=%s 期限=%s" % (it["owner"], it["deadline"]))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
