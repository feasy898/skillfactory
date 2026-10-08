# -*- coding: utf-8 -*-
"""从 fixtures/transcript.txt 生成 out/纪要.docx 与 out/summary.json。

纪律：转写稿是唯一事实来源；不补时间戳；不虚构说话人区分；条目内容逐字取自转写稿。
"""
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "fixtures", "transcript.txt")
OUT = os.path.join(BASE, "out")

# ---------------------------------------------------------------- 解析转写稿
raw = open(SRC, encoding="utf-8").read()
LINES = []
for ln in raw.splitlines():
    m = re.match(r"^([^:]+):\s*(.*)$", ln.strip())
    if m:
        LINES.append({"speaker": m.group(1), "text": m.group(2).strip()})
TRANSCRIPT = "\n".join(l["text"] for l in LINES)

SPEAKERS = sorted({l["speaker"] for l in LINES})

# 同名（同名/同字）说话人：同一姓名可能对应不止一位与会者，稿内无区分标记。
# 同姓：黄静怡/黄文博；同名字：刘文博/黄文博（文博）、王晓雯/张晓雯（晓雯）。
AMBIGUOUS = {"刘文博", "黄文博", "王晓雯", "张晓雯"}


def verify(snippet: str, label: str) -> str:
    """断言 snippet 在转写稿正文中逐字出现，否则直接失败（防止归纳/改写）。"""
    core = snippet.replace("（归属待核）", "")
    if core and core not in TRANSCRIPT:
        raise SystemExit("非逐字：%s -> %r" % (label, core))
    if re.search(r"\[\d{1,2}:\d{2}\]", raw):
        raise SystemExit("转写稿意外出现时间戳")
    return core


# ------------------------------------------------------------------ 纪要内容
TITLE = "望舒客服工作台项目专题会议纪要"

# 决议事项：(序号, 相关人, 转写稿原句)
DECISIONS = [
    ("刘文博", "望舒客服工作台整体进度正常，会议同意按原计划推进，里程碑保持不变"),
    ("黄静怡", "会议同意望舒客服工作台项目预算300万元，走专项列支，由综合办跟进执行"),
    ("黄文博", "望舒客服工作台的验收标准按新版执行，旧版同时作废"),
]

# 待办事项：(事项原句片段, 负责人, 期限)
TODOS = [
    ("在6月30日前完成复盘纪要并同步给市场部", "黄静怡", "6月30日前"),
    ("负责把灰度放量方案整理成7月中旬归档", "王晓雯", "7月中旬"),
    ("牵头梳理望舒客服工作台的责任分工", "张晓雯", "未明确"),
    ("验收清单的资料我随后发群里", "刘文博", "未明确"),
]

# 风险与关注：(序号, 相关人, 转写稿原句)
RISKS = [
    ("张晓雯", "市场部侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案"),
    ("刘文博", "验收清单的数据口径尚未对齐，复盘前需要补齐基线数据"),
]

for person, text in DECISIONS + RISKS:
    if person not in SPEAKERS:
        raise SystemExit("未知说话人：%s" % person)
    verify(text, "条目")
for text, person, _ in TODOS:
    if person not in SPEAKERS:
        raise SystemExit("未知负责人：%s" % person)
    verify(text, "待办事项")


def render(person: str, text: str) -> str:
    """同名且无法唯一归属时追加「（归属待核）」；可唯一归属的不加。"""
    suffix = "（归属待核）" if person in AMBIGUOUS else ""
    return "%s（归属待核）" % text if suffix else text


# ---------------------------------------------------------------- 生成 docx
doc = Document()
style = doc.styles["Normal"]
style.font.name = "SimSun"
style.font.size = Pt(11)

heading = doc.add_paragraph()
heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = heading.add_run(TITLE)
run.bold = True
run.font.size = Pt(16)

for section_title in ("一、决议事项", "二、待办事项", "三、风险与关注"):
    p = doc.add_paragraph()
    p.add_run(section_title).bold = True

    if section_title == "一、决议事项":
        for i, (person, text) in enumerate(DECISIONS, 1):
            doc.add_paragraph("%d. 【决议事项 · %s】%s" % (i, person, render(person, text)))
    elif section_title == "二、待办事项":
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, ("事项", "负责人", "期限")):
            cell.text = ""
            cell.paragraphs[0].add_run(label).bold = True
        for text, person, deadline in TODOS:
            cells = table.add_row().cells
            cells[0].text = text
            cells[1].text = person
            cells[2].text = deadline
    else:
        for i, (person, text) in enumerate(RISKS, 1):
            doc.add_paragraph("%d. 【风险与关注 · %s】%s" % (i, person, render(person, text)))

os.makedirs(OUT, exist_ok=True)
doc.save(os.path.join(OUT, "纪要.docx"))

summary = {
    "决议事项": len(DECISIONS),
    "待办事项": len(TODOS),
    "风险与关注": len(RISKS),
    "合计": len(DECISIONS) + len(TODOS) + len(RISKS),
}
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False))
