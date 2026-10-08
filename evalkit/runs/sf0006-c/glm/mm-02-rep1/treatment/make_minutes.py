#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 brief.md 生成 out/纪要.docx 与 out/summary.json。

输入 fixtures/transcript.txt：无时间戳、存在同名说话人（同一姓名多次发言，
稿内无区分标记）。条目内容一律逐字取自转写稿行，禁止改写/摘要/编造。
"""
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

BASE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(BASE, "fixtures", "transcript.txt")
OUTDIR = os.path.join(BASE, "out")

TITLE = "望舒客服工作台项目会议纪要"

# 条目按转写稿行号钉死（1-based），内容从原稿逐字取出，杜绝手抄走样。
DECISION_LINES = [2, 3, 4]
TODO_LINES = [  # (行号, 期限)；转写稿未提到时限的填「未明确」
    (5, "6月30日前"),
    (6, "7月中旬"),
    (7, "未明确"),
    (10, "未明确"),
]
RISK_LINES = [8, 9]


def parse_transcript(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = re.match(r"^([^：:]+?)\s*[：:]\s*(.+?)\s*$", line)
            if not m:
                raise ValueError("无法解析的发言行: %r" % line)
            rows.append((m.group(1), m.group(2)))
    return rows


def set_cn_font(run, size=None, bold=None):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def add_para(doc, text, size=None, bold=None, center=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_cn_font(run, size=size, bold=bold)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def entry_text(index, category, person, content, needs_flag):
    body = content[:-1] if content.endswith("。") else content
    if needs_flag:
        body += "（归属待核）"
    return "%d. 【%s · %s】%s" % (index, category, person, body)


def main():
    rows = parse_transcript(TRANSCRIPT)
    turn_count = {}
    for name, _ in rows:
        turn_count[name] = turn_count.get(name, 0) + 1

    def line(n):
        return rows[n - 1]

    # 同名归属：同一姓名对应多次发言且稿内无区分标记，无法唯一归属 → 追加后缀
    def needs_flag(person):
        return turn_count.get(person, 0) > 1

    decisions = [line(n) for n in DECISION_LINES]
    todos = [(line(n), ddl) for n, ddl in TODO_LINES]
    risks = [line(n) for n in RISK_LINES]

    doc = Document()
    add_para(doc, TITLE, size=18, bold=True, center=True)

    add_para(doc, "一、决议事项", size=14, bold=True)
    for i, (person, content) in enumerate(decisions, 1):
        add_para(doc, entry_text(i, "决议事项", person, content, needs_flag(person)))

    add_para(doc, "二、待办事项", size=14, bold=True)
    table = doc.add_table(rows=1 + len(todos), cols=3)
    table.style = "Table Grid"
    for j, head in enumerate(["事项", "负责人", "期限"]):
        cell = table.rows[0].cells[j]
        cell.text = ""
        set_cn_font(cell.paragraphs[0].add_run(head), bold=True)
    for i, ((person, content), ddl) in enumerate(todos, 1):
        body = content[:-1] if content.endswith("。") else content
        for j, value in enumerate([body, person, ddl]):
            cell = table.rows[i].cells[j]
            cell.text = ""
            set_cn_font(cell.paragraphs[0].add_run(value))

    add_para(doc, "三、风险与关注", size=14, bold=True)
    for i, (person, content) in enumerate(risks, 1):
        add_para(doc, entry_text(i, "风险与关注", person, content, needs_flag(person)))

    os.makedirs(OUTDIR, exist_ok=True)
    doc.save(os.path.join(OUTDIR, "纪要.docx"))

    summary = {
        "决议事项": len(decisions),
        "待办事项": len(todos),
        "风险与关注": len(risks),
        "合计": len(decisions) + len(todos) + len(risks),
    }
    with open(os.path.join(OUTDIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("生成完毕:", OUTDIR)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
