# -*- coding: utf-8 -*-
"""
从 fixtures/transcript.txt 生成 out/纪要.docx 与 out/summary.json。

纪律（与 brief.md 一致）：
- 转写稿是唯一事实来源；条目内容逐字取自原稿；
- 原稿无时间戳，因此不出现任何 [HH:MM] 形式时间；
- 不为同名说话人虚构区分标记；无法唯一归属的条目追加（归属待核）。
"""
import json
import os
import re
import sys
from collections import Counter

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

BASE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(BASE, "fixtures", "transcript.txt")
OUTDIR = os.path.join(BASE, "out")

LINE_RE = re.compile(r"^\s*([^：:]+?)\s*[：:]\s*(.+?)\s*$")

# 说话人标签出现次数 > 1 → 该姓名在稿内无法唯一归属到某一位与会者
with open(TRANSCRIPT, encoding="utf-8-sig") as fh:
    RAW = fh.read()
TRANSCRIPT_TEXT = RAW.replace("\r\n", "\n")
LINES = [ln for ln in TRANSCRIPT_TEXT.split("\n") if ln.strip()]

parsed = []
for ln in LINES:
    m = LINE_RE.match(ln)
    if not m:
        continue
    parsed.append((m.group(1), m.group(2)))
SPEAKER_COUNT = Counter(spk for spk, _ in parsed)


def ambiguous(speaker):
    return SPEAKER_COUNT[speaker] > 1


# ---------------------------------------------------------------- 结构化条目
# (相关人, 内容原文——逐字取自该条发言，不改写、不摘要)
DECISIONS = [
    ("周丽娜", "云岭数据看板整体进度正常，会议同意按原计划推进，里程碑保持不变"),
    ("徐志远", "会议同意云岭数据看板项目预算45万元，走专项列支，由财务部跟进执行"),
    ("吴雨桐", "云岭数据看板的验收标准按新版执行，旧版同时作废"),
]

TODOS = [
    # (事项原文, 负责人, 期限)
    ("徐志远在下周一前完成应急预案演练脚本并同步给供应链组", "徐志远", "下周一"),
    ("刘晓雯负责把验收清单整理成本周五归档", "刘晓雯", "本周五"),
    ("吴志远牵头梳理云岭数据看板的责任分工", "吴志远", "未明确"),
    ("我这边补充一点，灰度放量方案的资料我随后发群里", "周丽娜", "未明确"),
]

RISKS = [
    ("吴志远", "供应链组侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案"),
    ("周丽娜", "灰度放量方案的数据口径尚未对齐，复盘前需要补齐基线数据"),
]

SUFFIX = "（归属待核）"


# ---------------------------------------------------------------- 自校验
def selftest():
    errs = []
    for spk, content in DECISIONS + RISKS:
        if content not in TRANSCRIPT_TEXT:
            errs.append("内容无法逐字溯源: " + content)
    for item, owner, due in TODOS:
        if item not in TRANSCRIPT_TEXT:
            errs.append("待办事项无法逐字溯源: " + item)
        if owner not in SPEAKER_COUNT:
            errs.append("负责人非原稿说话人: " + owner)
        if due != "未明确" and due not in item:
            errs.append("期限非该条原文用语: %s / %s" % (due, item))
    if re.search(r"\[\d{1,2}:\d{2}\]", TRANSCRIPT_TEXT):
        errs.append("原稿竟含时间戳")
    return errs


# ---------------------------------------------------------------- 生成
def set_font(run, name="宋体", size=None, bold=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def add_para(doc, text, size=11, bold=False, align=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_font(run, size=size, bold=bold)
    return p


def item_text(idx, category, speaker, content):
    text = "%d. 【%s · %s】%s" % (idx, category, speaker, content)
    if ambiguous(speaker):
        text += SUFFIX
    return text


def main():
    errs = selftest()
    if errs:
        for e in errs:
            print("SELFCHECK FAIL:", e, file=sys.stderr)
        sys.exit(2)

    os.makedirs(OUTDIR, exist_ok=True)
    doc = Document()

    add_para(doc, "云岭数据看板项目及灰度放量方案专题会议纪要", size=18, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)

    add_para(doc, "一、决议事项", size=14, bold=True)
    for i, (spk, content) in enumerate(DECISIONS, 1):
        add_para(doc, item_text(i, "决议事项", spk, content))

    add_para(doc, "二、待办事项", size=14, bold=True)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, head in zip(table.rows[0].cells, ("事项", "负责人", "期限")):
        run = cell.paragraphs[0].add_run(head)
        set_font(run, size=11, bold=True)
    for item, owner, due in TODOS:
        cells = table.add_row().cells
        for cell, val in zip(cells, (item, owner, due)):
            run = cell.paragraphs[0].add_run(val)
            set_font(run, size=11)

    add_para(doc, "三、风险与关注", size=14, bold=True)
    for i, (spk, content) in enumerate(RISKS, 1):
        add_para(doc, item_text(i, "风险与关注", spk, content))

    dup = sorted(spk for spk, c in SPEAKER_COUNT.items() if c > 1)
    note = ("说明：转写稿无时间戳，且说话人标签「%s」各出现于多条发言、稿内无区分标记，"
            "无法唯一归属到某一位与会者，故相关条目追加「%s」；「%s」在稿内仅出现一次，"
            "可唯一归属，不加该后缀。条目内容均逐字取自转写稿，未作归纳改写。"
            % ("」「".join(dup), SUFFIX,
               "」「".join(spk for spk in SPEAKER_COUNT if SPEAKER_COUNT[spk] == 1)))
    add_para(doc, note, size=9)

    docx_path = os.path.join(OUTDIR, "纪要.docx")
    doc.save(docx_path)

    summary = {
        "决议事项": len(DECISIONS),
        "待办事项": len(TODOS),
        "风险与关注": len(RISKS),
        "合计": len(DECISIONS) + len(TODOS) + len(RISKS),
    }
    with open(os.path.join(OUTDIR, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()