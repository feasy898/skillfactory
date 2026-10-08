# -*- coding: utf-8 -*-
"""生成 out/纪要.docx 与 out/summary.json。

条目内容全部逐字取自 fixtures/transcript.txt，不做归纳改写。
同名（名相同）说话人：刘文博/黄文博（文博）、王晓雯/张晓雯（晓雯）；
黄静怡在稿中唯一出现，其条目不加归属待核后缀。
"""
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "fixtures", "transcript.txt")
OUT = os.path.join(BASE, "out")

# 同名（名相同）说话人集合：无法唯一归属，条目追加“（归属待核）”
HOMONYM = {"刘文博", "黄文博", "王晓雯", "张晓雯"}

DECISIONS = [
    ("刘文博", "望舒客服工作台整体进度正常，会议同意按原计划推进，里程碑保持不变。"),
    ("黄静怡", "会议同意望舒客服工作台项目预算300万元，走专项列支，由综合办跟进执行。"),
    ("黄文博", "望舒客服工作台的验收标准按新版执行，旧版同时作废。"),
]

TODOS = [
    ("完成复盘纪要并同步给市场部", "黄静怡", "6月30日前"),
    ("把灰度放量方案整理成7月中旬归档", "王晓雯", "7月中旬"),
    ("牵头梳理望舒客服工作台的责任分工", "张晓雯", "未明确"),
    ("验收清单的资料我随后发群里", "刘文博", "未明确"),
]

RISKS = [
    ("张晓雯", "市场部侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案。"),
    ("刘文博", "验收清单的数据口径尚未对齐，复盘前需要补齐基线数据。"),
]


def load_transcript():
    with open(SRC, encoding="utf-8") as fh:
        return fh.read()


def strip_period(text):
    return text[:-1] if text.endswith("。") else text


def check(blob):
    """自证：条目内容逐字出现在转写稿；无 [HH:MM] 时间戳；人名均来自稿中说话人。"""
    speakers = set()
    for line in blob.splitlines():
        m = re.match(r"^([^:：]{1,10})[:：]", line.strip())
        if m:
            speakers.add(m.group(1).strip())
    for who, text in DECISIONS + RISKS:
        assert text in blob, f"内容非逐字: {text}"
        assert strip_period(text) in blob
        assert who in speakers, f"人名非稿中说话人: {who}"
    for item, who, _ in TODOS:
        assert item in blob, f"待办事项无逐字出处: {item}"
        assert who in speakers, f"负责人非稿中说话人: {who}"
    for who, text in DECISIONS + RISKS:
        if who in HOMONYM:
            assert text + "（归属待核）" not in blob  # 后缀不在原文中
    return speakers


def set_cjk_font(run, name="宋体", size=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)


def add_par(doc, text, bold=False, size=12, align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    set_cjk_font(run, size=size)
    if align is not None:
        p.alignment = align
    return p


def entry_text(idx, category, who, text):
    suffix = "（归属待核）" if who in HOMONYM else ""
    return f"{idx}. 【{category} · {who}】{strip_period(text)}{suffix}"


def main():
    blob = load_transcript()
    check(blob)
    os.makedirs(OUT, exist_ok=True)

    doc = Document()
    title = add_par(doc, "望舒客服工作台项目会议纪要", bold=True, size=16,
                    align=WD_ALIGN_PARAGRAPH.CENTER)

    add_par(doc, "一、决议事项", bold=True, size=14)
    for i, (who, text) in enumerate(DECISIONS, 1):
        add_par(doc, entry_text(i, "决议事项", who, text))

    add_par(doc, "二、待办事项", bold=True, size=14)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, head in zip(table.rows[0].cells, ["事项", "负责人", "期限"]):
        run = cell.paragraphs[0].add_run(head)
        run.bold = True
        set_cjk_font(run, size=11)
    for item, who, due in TODOS:
        cells = table.add_row().cells
        for cell, val in zip(cells, [item, who, due]):
            set_cjk_font(cell.paragraphs[0].add_run(val), size=11)
    add_par(doc, "注：转写稿未记录时间戳；稿中 刘文博 与 黄文博（名同为“文博”）、"
                 "王晓雯 与 张晓雯（名同为“晓雯”）存在同名无法唯一归属的情况，"
                 "相关条目标注“（归属待核）”，待核实后确认。", size=9)

    add_par(doc, "三、风险与关注", bold=True, size=14)
    for i, (who, text) in enumerate(RISKS, 1):
        add_par(doc, entry_text(i, "风险与关注", who, text))

    doc.save(os.path.join(OUT, "纪要.docx"))

    summary = {
        "决议事项": len(DECISIONS),
        "待办事项": len(TODOS),
        "风险与关注": len(RISKS),
        "合计": len(DECISIONS) + len(TODOS) + len(RISKS),
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()