# -*- coding: utf-8 -*-
"""为星帆订单系统项目例会生成三节式会议纪要（docx + summary.json）。

所有条目内容均逐字取自 fixtures/transcript.txt，不做任何归纳或改写。
"""
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

BASE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(BASE, "fixtures", "transcript.txt")
OUT = os.path.join(BASE, "out")

TITLE = "星帆订单系统项目例会会议纪要"

# 决议事项：(类别, 相关人, 内容) —— 内容为转写稿中的逐字片段
DECISIONS = [
    ("决议事项", "赵静怡", "会议同意按原计划推进，里程碑保持不变"),
    ("决议事项", "黄雨桐", "会议同意星帆订单系统项目预算300万元，走专项列支，由市场部跟进执行"),
]

# 待办事项：(事项, 负责人, 期限) —— 事项为转写稿中的逐字片段
TODOS = [
    ("完成复盘纪要并同步给财务部", "黄雨桐", "本周五前"),
    ("把数据迁移脚本整理成7月4日归档", "徐静怡", "7月4日"),
    ("提前准备预案", "吴志远", "今年"),
    ("补齐基线数据", "赵静怡", "复盘前"),
]

# 风险与关注：(类别, 相关人, 内容)
RISKS = [
    ("风险与关注", "吴志远", "财务部侧存在履约风险，去年高峰期出现过积压"),
    ("风险与关注", "赵静怡", "灰度放量方案的数据口径尚未对齐"),
]


def load_transcript():
    with open(TRANSCRIPT, encoding="utf-8") as f:
        return f.read()


def parse(raw):
    """返回 (说话人列表, 全部发言内容列表)。"""
    speakers, bodies = [], []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\[\d{2}:\d{2}\]\s*([^:]+):\s*(.*)$", line)
        if not m:
            raise ValueError("转写稿格式异常: %r" % line)
        speakers.append(m.group(1).strip())
        bodies.append(m.group(2).strip())
    return speakers, bodies


def verify(speakers, bodies):
    """自证：人名、内容、期限必须全部能在转写稿中溯源。"""
    haystack = "\n".join(bodies)
    problems = []

    def check_text(kind, owner, content):
        if owner not in speakers:
            problems.append("%s 相关人 %r 不在转写稿说话人中" % (kind, owner))
        if content not in haystack:
            problems.append("%s 内容无法逐字溯源: %r" % (kind, content))

    for cat, owner, content in DECISIONS:
        check_text(cat, owner, content)
    for item, owner, deadline in TODOS:
        check_text("待办事项(%s)" % item, owner, item)
        if deadline != "未明确" and deadline not in haystack:
            problems.append("期限无法溯源: %r" % deadline)
    for cat, owner, content in RISKS:
        check_text(cat, owner, content)

    if problems:
        raise SystemExit("溯源自证失败:\n" + "\n".join(problems))
    return len(speakers)


def build_docx(path):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "SimSun"
    style.font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(TITLE)
    run.bold = True
    run.font.size = Pt(16)

    doc.add_paragraph("一、决议事项")
    for idx, (cat, owner, content) in enumerate(DECISIONS, 1):
        doc.add_paragraph("%d. 【%s · %s】%s" % (idx, cat, owner, content))

    doc.add_paragraph("二、待办事项")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, ["事项", "负责人", "期限"]):
        cell.text = ""
        para = cell.paragraphs[0]
        head = para.add_run(text)
        head.bold = True
    for item, owner, deadline in TODOS:
        cells = table.add_row().cells
        cells[0].text = item
        cells[1].text = owner
        cells[2].text = deadline

    doc.add_paragraph("三、风险与关注")
    for idx, (cat, owner, content) in enumerate(RISKS, 1):
        doc.add_paragraph("%d. 【%s · %s】%s" % (idx, cat, owner, content))

    doc.save(path)


def build_summary(path):
    summary = {
        "决议事项": len(DECISIONS),
        "待办事项": len(TODOS),
        "风险与关注": len(RISKS),
    }
    summary["合计"] = summary["决议事项"] + summary["待办事项"] + summary["风险与关注"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return summary


def main():
    speakers, bodies = parse(load_transcript())
    n = verify(speakers, bodies)
    os.makedirs(OUT, exist_ok=True)
    build_docx(os.path.join(OUT, "纪要.docx"))
    summary = build_summary(os.path.join(OUT, "summary.json"))
    print("说话人 %d 位：%s" % (n, "、".join(dict.fromkeys(speakers))))
    print("溯源自证通过 ->", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()