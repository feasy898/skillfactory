# -*- coding: utf-8 -*-
"""生成泊棠民宿淡季协调会正式会议纪要（纪要.docx + summary.json）。

输入：botang_minsu_1011.txt（语音转写稿）
输出：out/纪要.docx、out/summary.json
"""
import json
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
TRANSCRIPT = os.path.join(BASE, "botang_minsu_1011.txt")
DOCX_PATH = os.path.join(OUT, "纪要.docx")
JSON_PATH = os.path.join(OUT, "summary.json")

BODY_FONT = "宋体"
HEAD_FONT = "黑体"

MEETING = {
    "name": "泊棠民宿淡季工作协调会",
    "date_label": "10 月 11 日",
    "time_range": "19:00—19:09",
    "host": "掌柜 岑晏",
    "attendees": [
        {"name": "岑晏", "role": "掌柜", "attended": True},
        {"name": "苏莞", "role": "管家", "attended": True},
        {"name": "郁南", "role": "布草房", "attended": True},
        {"name": "小盛", "role": "未列明（受托事项承接人）", "attended": False},
    ],
    "topic": "淡季经营与布草、物料、房价、包装等事项的协调与定夺",
}

DECISIONS = [
    {
        "id": "D1",
        "time": "19:01 / 19:04",
        "topic": "晨会安排",
        "content": "自本次会议起，晨会固定为每周二上午召开，时间不再临时调整。",
        "owner": "岑晏",
        "source_time": "19:01",
    },
    {
        "id": "D2",
        "time": "19:04",
        "topic": "工装夹具",
        "content": "工装夹具先行按原有图纸组织加工，本阶段不作图面变更。",
        "owner": "岑晏",
        "source_time": "19:04",
    },
    {
        "id": "D3",
        "time": "19:07",
        "topic": "淡季房价",
        "content": "淡季房价方案当场议定，工作日执行一口价，不设分档议价。",
        "owner": "岑晏",
        "source_time": "19:07",
    },
]

ACTIONS = [
    {
        "id": "A1",
        "content": "梳理并核对物料清单，形成可用清单。",
        "owner": "小盛",
        "coordinator": "苏莞",
        "deadline": "会议后两日内",
        "source_time": "19:02",
    },
    {
        "id": "A2",
        "content": "定位洗烘设备保修单据归入的文件夹并归档。",
        "owner": "苏莞 / 郁南",
        "coordinator": "苏莞",
        "deadline": "未明确，需另行确认",
        "source_time": "19:06",
    },
    {
        "id": "A3",
        "content": "重新选定腊味礼盒包装方案。",
        "owner": "苏莞",
        "coordinator": "苏莞",
        "deadline": "包装出样前",
        "source_time": "19:08",
    },
]

RISKS = [
    {
        "id": "R1",
        "content": "压胶工序为当前延期风险最高的环节，床罩已发生两轮返工，须优先跟进。",
        "reported_by": "郁南",
        "source_time": "19:03",
    }
]

OPEN_ISSUES = [
    {
        "id": "Q1",
        "content": (
            "淡季房价方案的确定程序存在两种表述：19:05 提议「改天发群投票」，"
            "19:07 当场议定「工作日一口价」。本次纪要按后一条记录为决议事项 D3，"
            "前一条是否作废、是否仍需补充群投票，请于确认后回填。"
        ),
        "source_time": "19:05 / 19:07",
    },
    {
        "id": "Q2",
        "content": "洗烘设备保修单据的归档时限在原记录中未明确，需由苏莞补充确定。",
        "source_time": "19:06",
    },
]

DISCUSSION = [
    {
        "id": "P1",
        "topic": "会议开场",
        "content": "掌柜岑晏说明本次会议就淡季期间的经营事项进行沟通，与会人员到齐，会议开始。",
        "speaker": "岑晏",
        "source_time": "19:00",
    },
    {
        "id": "P2",
        "topic": "晨会安排",
        "content": "岑晏宣布晨会改为每周二上午召开，并在会上就工装夹具的图面使用征求在场意见后形成结论。",
        "speaker": "岑晏",
        "source_time": "19:01 / 19:04",
    },
    {
        "id": "P3",
        "topic": "物料与布草",
        "content": (
            "苏莞提出物料清单需请小盛协助梳理，要求两日内完成；"
            "郁南说明压胶工序仍是延期风险最集中的环节，床罩已返工两次；"
            "另就洗烘设备保修单据的存放位置提出疑问。"
        ),
        "speaker": "苏莞、郁南",
        "source_time": "19:02 / 19:03 / 19:06",
    },
    {
        "id": "P4",
        "topic": "房价与包装",
        "content": (
            "苏莞提出淡季房价方案拟在群内发起投票，随后改由岑晏在会上直接议定，"
            "确定工作日执行一口价；腊味礼盒包装方案需重新选定，限期至出样前。"
        ),
        "speaker": "苏莞、岑晏",
        "source_time": "19:05 / 19:07 / 19:08",
    },
    {
        "id": "P5",
        "topic": "会议结束",
        "content": "各项议题讨论完毕，岑晏宣布散会，并提醒在场人员注意休息。",
        "speaker": "岑晏",
        "source_time": "19:09",
    },
]


# --------------------------------------------------------------------------- #
# docx 渲染
# --------------------------------------------------------------------------- #
def _set_cn_font(run, font, size, bold=False, color=None):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")


def _para(doc, text, size=12, bold=False, font=BODY_FONT, align=None,
          space_before=0, space_after=6, indent_chars=0, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.5
    if indent_chars:
        pf.first_line_indent = Pt(size * indent_chars)
    if align is not None:
        p.alignment = align
    _set_cn_font(p.add_run(text), font, size, bold=bold, color=color)
    return p


def _heading(doc, text):
    return _para(doc, text, size=13, bold=True, font=HEAD_FONT,
                 space_before=12, space_after=6, color=RGBColor(0x1F, 0x30, 0x54))


def _set_fixed_layout(table, widths):
    """固定列宽：关闭 autofit 并写入 tblLayout=fixed + tblGrid。"""
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 567)))  # cm -> twips
    for row in table.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = Cm(w)


def _table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        _set_cn_font(p.add_run(h), HEAD_FONT, 10.5, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.25
            _set_cn_font(p.add_run(str(val)), BODY_FONT, 10.5)
    if widths:
        _set_fixed_layout(t, widths)
    _no_split(t)
    _repeat_header(t)
    return t


def _no_split(table):
    """禁止单行跨页断开。"""
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))


def _repeat_header(table):
    """表头行跨页重复。"""
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def build_docx():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.4)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    _para(doc, "会议纪要", size=18, bold=True, font=HEAD_FONT,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _para(doc, MEETING["name"], size=13, bold=True, font=HEAD_FONT,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _para(doc, "（据语音转写稿整理）", size=9, font=BODY_FONT,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10,
          color=RGBColor(0x66, 0x66, 0x66))

    _table(
        doc,
        ["项目", "内容"],
        [
            ["会议时间", "{} {}".format(MEETING["date_label"], MEETING["time_range"])],
            ["主持人", MEETING["host"]],
            ["参会人员", "岑晏（掌柜）、苏莞（管家）、郁南（布草房）"],
            ["会议议题", MEETING["topic"]],
            ["材料来源", "botang_minsu_1011.txt（现场语音转写稿，共 10 条发言记录）"],
        ],
        widths=[3.2, 12.2],
    )

    _heading(doc, "一、会议概述")
    _para(
        doc,
        "会议围绕淡季经营相关事项召开，掌柜、管家与布草房三方到会，"
        "合计发言 10 条、时长 9 分钟。会议就晨会安排、物料清单梳理、"
        "压胶工序延期、洗烘设备单据归档、淡季房价执行口径以及腊味礼盒包装"
        "六项具体事项形成意见，其中 3 项议定为决议事项，3 项派为待办事项，"
        "1 项列为风险提示，另有 2 项口径待确认事项留待补充。",
        indent_chars=2,
    )

    _heading(doc, "二、讨论要点")
    _table(
        doc,
        ["序号", "议题", "讨论内容", "发言人", "时间"],
        [[d["id"], d["topic"], d["content"], d["speaker"], d["source_time"]]
         for d in DISCUSSION],
        widths=[1.3, 2.4, 7.6, 2.2, 2.0],
    )

    _heading(doc, "三、决议事项")
    _table(
        doc,
        ["编号", "事项", "决议内容", "责任人", "时间"],
        [[d["id"], d["topic"], d["content"], d["owner"], d["time"]]
         for d in DECISIONS],
        widths=[1.3, 2.4, 7.6, 2.2, 2.0],
    )

    _heading(doc, "四、待办事项")
    _table(
        doc,
        ["编号", "待办内容", "责任人", "协办/提出", "完成时限", "时间"],
        [[a["id"], a["content"], a["owner"], a["coordinator"], a["deadline"], a["source_time"]]
         for a in ACTIONS],
        widths=[1.3, 6.0, 2.0, 2.0, 2.6, 1.6],
    )

    _heading(doc, "五、风险提示")
    _table(
        doc,
        ["编号", "风险描述", "提出人", "时间"],
        [[r["id"], r["content"], r["reported_by"], r["source_time"]] for r in RISKS],
        widths=[1.3, 9.0, 2.6, 2.6],
    )

    _heading(doc, "六、待确认事项")
    for q in OPEN_ISSUES:
        _para(doc, "· " + q["content"], size=11, space_after=4)

    _heading(doc, "七、备注")
    _para(
        doc,
        "1. 本纪要依现场语音转写稿整理，已剔除「呃」「嘛」「说白了」等口语填充词，"
        "条目内容与原意一致，未作增补或推断。\n"
        "2. 原始转写稿另存为 botang_minsu_1011.txt，与本纪要配套归档。\n"
        "3. 第六节两项待确认事项，经办人确认后由记录人回填，回填不影响本纪要其余内容。",
        size=10.5,
    )

    _para(doc, "", space_after=8)
    _para(doc, "记录人：___________        审核：___________", size=10.5)
    _para(doc, "泊棠民宿", size=10.5, align=WD_ALIGN_PARAGRAPH.RIGHT)

    doc.save(DOCX_PATH)


def build_summary():
    data = {
        "schema_version": "1.0",
        "source": {
            "transcript_file": "botang_minsu_1011.txt",
            "transcript_utterances": 10,
            "meeting_start": "19:00",
            "meeting_end": "19:09",
            "duration_minutes": 9,
        },
        "meeting": MEETING,
        "attendees": MEETING["attendees"],
        "discussion": DISCUSSION,
        "decisions": DECISIONS,
        "action_items": ACTIONS,
        "risks": RISKS,
        "open_questions": OPEN_ISSUES,
        "statistics": {
            "decisions": len(DECISIONS),
            "action_items": len(ACTIONS),
            "risks": len(RISKS),
            "open_questions": len(OPEN_ISSUES),
            "action_items_without_deadline": sum(
                1 for a in ACTIONS if a["deadline"] == "未明确，需另行确认"
            ),
        },
        "filler_words_removed": ["呃", "嘛", "说白了", "哈", "啊", "那个", "行"],
        "outputs": {
            "docx": "out/纪要.docx",
            "summary_json": "out/summary.json",
        },
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    build_docx()
    build_summary()
    print("docx ->", DOCX_PATH)
    print("json ->", JSON_PATH)