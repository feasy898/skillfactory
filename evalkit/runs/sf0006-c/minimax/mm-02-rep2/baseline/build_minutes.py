# -*- coding: utf-8 -*-
"""从 fixtures/transcript.txt 生成 out/纪要.docx 与 out/summary.json。

纪律：条目内容逐字取自转写稿；不补时间戳；同名说话人只加「（归属待核）」，
不发明任何区分标记。
"""
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(BASE, "fixtures", "transcript.txt")
OUT_DIR = os.path.join(BASE, "out")

# 转写稿中出现的说话人姓名（逐字），以及其中存在同名歧义、无法唯一归属的姓名。
SPEAKERS = ["周丽娜", "徐志远", "吴雨桐", "刘晓雯", "吴志远"]
AMBIGUOUS = {"徐志远", "吴志远"}

TITLE = "云岭数据看板项目会议纪要"

DECISIONS = [
    ("周丽娜", "云岭数据看板整体进度正常，会议同意按原计划推进，里程碑保持不变"),
    ("徐志远", "会议同意云岭数据看板项目预算45万元，走专项列支，由财务部跟进执行"),
    ("吴雨桐", "云岭数据看板的验收标准按新版执行，旧版同时作废"),
]

TODOS = [
    ("完成应急预案演练脚本并同步给供应链组", "徐志远", "下周一"),
    ("把验收清单整理成本周五归档", "刘晓雯", "本周五"),
    ("牵头梳理云岭数据看板的责任分工", "吴志远", "未明确"),
    ("灰度放量方案的资料我随后发群里", "周丽娜", "未明确"),
]

RISKS = [
    ("吴志远", "供应链组侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案"),
    ("周丽娜", "灰度放量方案的数据口径尚未对齐，复盘前需要补齐基线数据"),
]


def load_transcript():
    rows = []
    with open(TRANSCRIPT, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            speaker, _, text = line.partition(":")
            rows.append((speaker.strip(), text.strip()))
    return rows


def check(rows):
    """逐字可溯源校验：内容片段必须能在转写稿中找到。"""
    problems = []
    for label, who, text, tag in (
        [("决议事项", d[0], d[1], "决策") for d in DECISIONS]
        + [("待办事项", t[1], t[0], "待办") for t in TODOS]
        + [("风险与关注", r[0], r[1], "风险") for r in RISKS]
    ):
        if who not in SPEAKERS:
            problems.append("%s: 人名 %s 未在转写稿出现" % (label, who))
        if text not in "".join(t for _, t in rows):
            problems.append("%s(%s): 内容无法逐字溯源 -> %s" % (label, tag, text))
    return problems


def item_text(index, category, who, text):
    suffix = "（归属待核）" if who in AMBIGUOUS else ""
    return "%d. 【%s · %s】%s%s" % (index, category, who, text, suffix)


def build_docx(path, rows):
    doc = Document()

    head = doc.add_paragraph()
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = head.add_run(TITLE)
    run.bold = True
    run.font.size = doc.styles["Normal"].font.size

    doc.add_paragraph("一、决议事项")
    for i, (who, text) in enumerate(DECISIONS, 1):
        doc.add_paragraph(item_text(i, "决议事项", who, text))

    doc.add_paragraph("二、待办事项")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, name in zip(table.rows[0].cells, ["事项", "负责人", "期限"]):
        cell.text = ""
        cell.paragraphs[0].add_run(name).bold = True
    for item, owner, due in TODOS:
        cells = table.add_row().cells
        cells[0].text = item
        cells[1].text = owner
        cells[2].text = due

    doc.add_paragraph("三、风险与关注")
    for i, (who, text) in enumerate(RISKS, 1):
        doc.add_paragraph(item_text(i, "风险与关注", who, text))

    doc.save(path)


def check_no_timestamps(rows):
    for speaker, text in rows:
        if re.search(r"\[\d{1,2}:\d{2}\]", text):
            raise SystemExit("转写稿意外含时间戳: %s" % text)


def main():
    rows = load_transcript()
    check_no_timestamps(rows)
    problems = check(rows)
    if problems:
        raise SystemExit("溯源校验失败:\n" + "\n".join(problems))

    os.makedirs(OUT_DIR, exist_ok=True)
    build_docx(os.path.join(OUT_DIR, "纪要.docx"), rows)

    summary = {
        "决议事项": len(DECISIONS),
        "待办事项": len(TODOS),
        "风险与关注": len(RISKS),
        "合计": len(DECISIONS) + len(TODOS) + len(RISKS),
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("ok:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
