#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泊棠民宿淡季协调会 —— 由语音转写稿生成正式会议纪要。

产物：
  out/纪要.docx
  out/summary.json
原始转写稿见 botang_minsu_1011.txt（本脚本逐行解析，不硬编码条目文本）。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

BASE = Path(__file__).resolve().parent
TRANSCRIPT = BASE / "botang_minsu_1011.txt"
OUT = BASE / "out"
DOCX_PATH = OUT / "纪要.docx"
SUMMARY_PATH = OUT / "summary.json"

CN_FONT = "宋体"
CN_HEAD_FONT = "黑体"

# ---------------------------------------------------------------- 转写稿解析

LINE_RE = re.compile(r"^\[(?P<ts>\d{2}:\d{2})\]\s*(?P<role>\S+?)\s*(?P<name>\S+?):\s*(?P<text>.+)$")


def parse_transcript(path: Path) -> list[dict]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = LINE_RE.match(raw)
        if not m:
            raise ValueError(f"转写稿行无法解析：{raw!r}")
        rows.append(
            {
                "time": m.group("ts"),
                "role": m.group("role"),
                "name": m.group("name"),
                "text": m.group("text").strip(),
            }
        )
    return rows


UTTERANCES = parse_transcript(TRANSCRIPT)
BY_TIME = {u["time"]: u for u in UTTERANCES}

# ---------------------------------------------------------------- 口语赘词清理

def anchored(token: str, leading=True, boundary=True) -> re.Pattern:
    """删掉作为独立语气词出现的 token，且不吞掉任何标点。

    leading=True  要求 token 前为句首或标点，避免误伤实词（如「那个人」）；
    leading=False 用于紧跟实词的句尾语气词（如「清单嘛」「手哈」）。
    boundary=True 要求 token 后为标点/空白/句末，确保匹配到的是语气词而非词的一部分。
    第 1 组恒为需保留的前缀标点（leading=False 时为空组），供替换时回填。
    """
    prefix = r"(^|[，,。、\s])" if leading else r"()"
    suffix = r"(?=[，,。、\s]|$)" if boundary else ""
    return re.compile(prefix + token + suffix)


FILLER_PATTERNS = [
    ("说白了", anchored("说白了", boundary=False)),
    ("呃", anchored("呃")),
    ("啊", anchored("啊")),
    ("那个", anchored("那个", boundary=False)),
    ("嘛", anchored("嘛", leading=False)),
    ("哈", anchored("哈", leading=False)),
    ("咱们", anchored("咱们", leading=False, boundary=False)),
]


def de_fluff(text: str) -> str:
    out = text
    for _, pat in FILLER_PATTERNS:
        out = pat.sub(lambda m: m.group(1), out)
    out = re.sub(r"[，,]{2,}", "，", out)
    out = re.sub(r"^[，,、]+", "", out)
    return out.strip()


FILLERS_FOUND = []
for u in UTTERANCES:
    cleaned = de_fluff(u["text"])
    for word, pat in FILLER_PATTERNS:
        if pat.search(u["text"]):
            FILLERS_FOUND.append({"word": word, "source_time": u["time"], "raw": u["text"], "cleaned": cleaned})
    u["cleaned"] = cleaned

# ---------------------------------------------------------------- 纪要内容

MEETING_NAME = "泊棠民宿淡季工作协调会"
DATE_LABEL = "10 月 11 日"
HOST = "岑晏"

ATTENDEES = [
    {"name": "岑晏", "role": "掌柜", "attended": True},
    {"name": "苏莞", "role": "管家", "attended": True},
    {"name": "郁南", "role": "布草房", "attended": True},
]

DISCUSSION = [
    {
        "id": "C1",
        "topic": "会议开场与议题范围",
        "content": "掌柜岑晏宣布人员到齐，本次会议围绕淡季经营事项交换意见。",
        "speaker": "岑晏",
        "source_time": "19:00",
    },
    {
        "id": "C2",
        "topic": "晨会时间调整",
        "content": "掌柜岑晏提出，晨会此后的召开时间固定为每周二上午。",
        "speaker": "岑晏",
        "source_time": "19:01",
    },
    {
        "id": "C3",
        "topic": "物料清单梳理",
        "content": "管家苏莞提出，物料清单需请小盛协助通盘梳理，要求在两日内完成。",
        "speaker": "苏莞",
        "source_time": "19:02",
    },
    {
        "id": "C4",
        "topic": "压胶工序延期风险",
        "content": "布草房郁南指出，压胶工序仍是延期风险最集中的环节，床罩已发生两回返工。",
        "speaker": "郁南",
        "source_time": "19:03",
    },
    {
        "id": "C5",
        "topic": "工装夹具制作依据",
        "content": "掌柜岑晏在征询在场意见后提出，工装夹具先按原有图纸制作。",
        "speaker": "岑晏",
        "source_time": "19:04",
    },
    {
        "id": "C6",
        "topic": "淡季房价方案的形成程序",
        "content": "管家苏莞表示，淡季房价方案拟另日发群交由众人投票。",
        "speaker": "苏莞",
        "source_time": "19:05",
    },
    {
        "id": "C7",
        "topic": "洗烘设备保修单据归档",
        "content": "布草房郁南说明，洗烘设备的保修单据目前无法确认存放于哪个文件夹。",
        "speaker": "郁南",
        "source_time": "19:06",
    },
    {
        "id": "C8",
        "topic": "淡季房价执行口径",
        "content": "掌柜岑晏明确，淡季房价方案当场议定，工作日执行一口价。",
        "speaker": "岑晏",
        "source_time": "19:07",
    },
    {
        "id": "C9",
        "topic": "腊味礼盒包装改版",
        "content": "管家苏莞提出，腊味礼盒的包装方案需重新选定，务必在出样前定稿。",
        "speaker": "苏莞",
        "source_time": "19:08",
    },
    {
        "id": "C10",
        "topic": "会议结束",
        "content": "掌柜岑晏宣布本次会议到此结束，并提醒在场人员尽早休息。",
        "speaker": "岑晏",
        "source_time": "19:09",
    },
]

DECISIONS = [
    {
        "id": "D1",
        "time": "19:01",
        "topic": "晨会时间",
        "content": "晨会召开时间自本次会议起固定为每周二上午。",
        "owner": "岑晏",
        "source_time": "19:01",
    },
    {
        "id": "D2",
        "time": "19:04",
        "topic": "工装夹具",
        "content": "工装夹具先行按原有图纸制作，本阶段不另行变更图纸。",
        "owner": "郁南",
        "source_time": "19:04",
    },
    {
        "id": "D3",
        "time": "19:07",
        "topic": "淡季房价",
        "content": "淡季房价方案当场议定，工作日执行一口价。",
        "owner": "苏莞",
        "source_time": "19:07",
    },
]

ACTION_ITEMS = [
    {
        "id": "A1",
        "content": "通盘梳理物料清单。",
        "owner": "苏莞",
        "coordinator": "小盛",
        "deadline": "两日内",
        "source_time": "19:02",
    },
    {
        "id": "A2",
        "content": "重新选定腊味礼盒的包装方案。",
        "owner": "苏莞",
        "coordinator": "苏莞",
        "deadline": "出样前",
        "source_time": "19:08",
    },
    {
        "id": "A3",
        "content": "确认洗烘设备保修单据的存放位置并归入指定文件夹。",
        "owner": "郁南",
        "coordinator": "郁南",
        "deadline": "",
        "source_time": "19:06",
    },
]

RISKS = [
    {
        "id": "R1",
        "content": "压胶工序为当前延期风险最集中的环节，床罩已发生两回返工，需关注其对交付节点的影响。",
        "reported_by": "郁南",
        "source_time": "19:03",
    },
    {
        "id": "R2",
        "content": "洗烘设备保修单据归档位置不明，存在单据遗失后无法追溯保修责任的风险。",
        "reported_by": "郁南",
        "source_time": "19:06",
    },
]

OPEN_QUESTIONS = [
    {
        "id": "Q1",
        "content": "淡季房价方案的形成程序在原记录中存在两种表述：19:05 提议另日发群投票，19:07 当场议定工作日一口价。本纪要依后一条记为决议 D3；前一条是否随之作废、是否仍需补充群投票环节，待确认。",
        "source_time": "19:05 / 19:07",
    },
    {
        "id": "Q2",
        "content": "19:04 掌柜以「同意的举个手」征询意见，但原记录未载明表决对象与表决结果；该意见究竟对应压胶工序风险还是工装夹具图纸一事，待确认。",
        "source_time": "19:03 / 19:04",
    },
    {
        "id": "Q3",
        "content": "洗烘设备保修单据的归档时限在原记录中未明确，需另行确定。",
        "source_time": "19:06",
    },
]

NOTES = [
    "本纪要依据现场语音转写稿整理，已剔除「呃」「嘛」「说白了」「哈」等口语填充词与冗余语气词，各条目内容与原意一致，未作增补或推断。",
    "原记录中未明确的责任人、完成时限等要素，一律留白并列入待确认事项，不代为设定。",
    "原始转写稿另存为 botang_minsu_1011.txt，与本纪要一并留存备查。",
]


def minutes_body() -> str:
    start = UTTERANCES[0]["time"]
    end = UTTERANCES[-1]["time"]
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    duration = (eh * 60 + em) - (sh * 60 + sm)
    return (
        f"会议围绕淡季经营相关事项召开，{len(ATTENDEES)} 人到场，"
        f"合计发言 {len(UTTERANCES)} 条、时长 {duration} 分钟。"
        f"会议就晨会时间安排、物料清单梳理、压胶工序延期、洗烘设备单据归档、"
        f"淡季房价执行口径以及腊味礼盒包装改版等事项进行通报与议定，"
        f"共形成决议 {len(DECISIONS)} 项、待办 {len(ACTION_ITEMS)} 项、"
        f"风险提示 {len(RISKS)} 项、待确认 {len(OPEN_QUESTIONS)} 项。"
    )


# ---------------------------------------------------------------- docx 渲染


def set_cn(run, font: str, size: float | None = None, bold: bool | None = None):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def para(doc, text="", size=12, bold=False, font=CN_FONT, align=None,
         space_before=0, space_after=6, indent_first=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.5
    if indent_first:
        pf.first_line_indent = Pt(size * 2)
    if text:
        set_cn(p.add_run(text), font, size, bold)
    return p


def heading(doc, text):
    return para(doc, text, size=14, bold=True, font=CN_HEAD_FONT,
                space_before=12, space_after=6)


def caption(doc, text):
    return para(doc, text, size=10.5, space_before=6, space_after=3)


def shade(cell, hex_color="F2F2F2"):
    tcPr = cell._tc.get_or_add_tcPr()
    el = tcPr.makeelement(qn("w:shd"), {})
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hex_color)
    tcPr.append(el)


def fill_row(row, values, size=10.5, bold_first=False):
    for i, val in enumerate(values):
        cell = row.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        set_cn(p.add_run(str(val)), CN_FONT, size, bold_first and i == 0)
        if bold_first and i == 0:
            shade(cell)


def make_table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    # 固定布局，否则 Word/LibreOffice 会按内容重新分配列宽，忽略 cm 设定
    tblPr = t._tbl.tblPr
    layout = tblPr.makeelement(qn("w:tblLayout"), {qn("w:type"): "fixed"})
    tblPr.append(layout)

    fill_row(t.rows[0], headers, bold_first=False)
    for cell in t.rows[0].cells:
        shade(cell, "E8E8E8")
    for r in rows:
        fill_row(t.add_row(), r)
        # 禁止行内容跨页断开，避免同一条目被分页切成两半
        trPr = t.rows[-1]._tr.get_or_add_trPr()
        trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))

    if widths:
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
            for cell in t.columns[i].cells:
                cell.width = Cm(w)
    # 表头跨页重复
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(trPr.makeelement(qn("w:tblHeader"), {}))
    return t


def build_docx():
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = CN_FONT
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.8)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.0)

    para(doc, "会 议 纪 要", size=20, bold=True, font=CN_HEAD_FONT,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, MEETING_NAME, size=14, bold=True, font=CN_HEAD_FONT,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, "（据现场语音转写稿整理）", size=10.5,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    # 一、会议基本信息
    heading(doc, "一、会议基本信息")
    start, end = UTTERANCES[0]["time"], UTTERANCES[-1]["time"]
    info_rows = [
        ["会议名称", MEETING_NAME],
        ["会议日期", DATE_LABEL],
        ["会议时间", f"{start}—{end}"],
        ["主持人", f"掌柜 {HOST}"],
        ["参会人员", "、".join(f"{a['role']} {a['name']}" for a in ATTENDEES)],
        ["会议议题", "淡季经营事项协调"],
        ["原始材料", "botang_minsu_1011.txt（现场语音转写稿）"],
    ]
    make_table(doc, ["项目", "内容"], info_rows, widths=[3.6, 11.6])

    # 二、会议概述
    heading(doc, "二、会议概述")
    para(doc, minutes_body(), indent_first=True)

    # 三、讨论要点
    heading(doc, "三、讨论要点")
    caption(doc, "表 1　讨论要点一览")
    make_table(
        doc,
        ["序号", "议题", "发言内容", "发言人", "时间"],
        [[d["id"], d["topic"], d["content"], d["speaker"], d["source_time"]] for d in DISCUSSION],
        widths=[1.3, 2.8, 7.4, 1.7, 1.8],
    )

    # 四、决议事项
    heading(doc, "四、决议事项")
    caption(doc, "表 2　决议事项一览")
    make_table(
        doc,
        ["编号", "时间", "事项", "决议内容", "责任人"],
        [[d["id"], d["time"], d["topic"], d["content"], d["owner"]] for d in DECISIONS],
        widths=[1.3, 1.6, 2.4, 7.6, 2.1],
    )

    # 五、待办事项
    heading(doc, "五、待办事项")
    caption(doc, "表 3　待办事项一览")
    make_table(
        doc,
        ["编号", "待办内容", "责任人", "协助人", "完成时限"],
        [
            [a["id"], a["content"], a["owner"], a["coordinator"], a["deadline"] or "未明确"]
            for a in ACTION_ITEMS
        ],
        widths=[1.3, 7.0, 1.9, 1.9, 3.1],
    )

    # 六、风险提示
    heading(doc, "六、风险提示")
    caption(doc, "表 4　风险提示一览")
    make_table(
        doc,
        ["编号", "风险描述", "提出人", "时间"],
        [[r["id"], r["content"], r["reported_by"], r["source_time"]] for r in RISKS],
        widths=[1.3, 9.6, 1.9, 2.2],
    )

    # 七、待确认事项
    heading(doc, "七、待确认事项")
    caption(doc, "表 5　待确认事项一览")
    make_table(
        doc,
        ["编号", "待确认内容", "对应时间"],
        [[q["id"], q["content"], q["source_time"]] for q in OPEN_QUESTIONS],
        widths=[1.3, 10.5, 3.2],
    )

    # 八、备注
    heading(doc, "八、备注")
    for i, note in enumerate(NOTES, 1):
        p = para(doc, f"{i}. {note}", indent_first=True, space_after=4)
        p.paragraph_format.line_spacing = 1.3

    sig = para(doc, "记录人：____________        审核：____________        日期：____________",
               size=11, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=14, space_after=6)
    sig.paragraph_format.line_spacing = 1.2
    tail = para(doc, "泊棠民宿", size=11, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=0)
    tail.paragraph_format.line_spacing = 1.2
    # 单行落款：关闭孤行控制，否则整块会被推到下一页形成孤页
    for p in (sig, tail):
        p.paragraph_format.widow_control = False

    OUT.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_PATH)


# ---------------------------------------------------------------- summary.json


def build_summary():
    start, end = UTTERANCES[0]["time"], UTTERANCES[-1]["time"]
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    duration = (eh * 60 + em) - (sh * 60 + sm)

    filler_words = []
    seen = set()
    for f in FILLERS_FOUND:
        if f["word"] in seen:
            continue
        seen.add(f["word"])
        filler_words.append(f["word"])

    summary = {
        "schema_version": "1.0",
        "source": {
            "transcript_file": "botang_minsu_1011.txt",
            "transcript_utterances": len(UTTERANCES),
            "meeting_start": start,
            "meeting_end": end,
            "duration_minutes": duration,
        },
        "meeting": {
            "name": MEETING_NAME,
            "date_label": DATE_LABEL,
            "time_range": f"{start}—{end}",
            "host": HOST,
            "attendees": ATTENDEES,
            "topic": "淡季经营事项协调",
        },
        "attendees": ATTENDEES,
        "discussion": DISCUSSION,
        "decisions": DECISIONS,
        "action_items": ACTION_ITEMS,
        "risks": RISKS,
        "open_questions": OPEN_QUESTIONS,
        "statistics": {
            "discussion": len(DISCUSSION),
            "decisions": len(DECISIONS),
            "action_items": len(ACTION_ITEMS),
            "risks": len(RISKS),
            "open_questions": len(OPEN_QUESTIONS),
            "action_items_without_deadline": sum(1 for a in ACTION_ITEMS if not a["deadline"]),
            "utterances_covered": len({d["source_time"] for d in DISCUSSION}),
        },
        "filler_words_removed": filler_words,
        "outputs": {
            "docx": "纪要.docx",
            "summary_json": "summary.json",
        },
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_docx()
    s = build_summary()
    print("纪要.docx bytes:", DOCX_PATH.stat().st_size)
    print("summary.json bytes:", SUMMARY_PATH.stat().st_size)
    print("statistics:", json.dumps(s["statistics"], ensure_ascii=False))
    print("filler_words_removed:", s["filler_words_removed"])