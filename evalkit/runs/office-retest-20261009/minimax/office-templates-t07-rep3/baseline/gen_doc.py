#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
由季度工作总结数据生成一期周报（office-templates t07 / 模板错配场景）。

原则：字段能对上号的直接放；对不上的字段不编造数据，改为标注口径与待补状态。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
SRC = os.path.join(BASE, "yuguang_q3.json")

# ---------------------------------------------------------------- 数据装载
with open(SRC, encoding="utf-8") as f:
    D = json.load(f)

SUBJECT = D["总结主体"]
SRC_PERIOD = D["总结时段"]
DATE_TEXT = D["成文日期"]

# 由成文日期推导的报告周期（推导值，需业务确认）
WEEK_FROM = "2026年10月5日"
WEEK_TO = "2026年10月11日"
WEEK = f"{WEEK_FROM}—{WEEK_TO}"
WEEK_BRIEF = f"{WEEK_FROM}（周一）至{WEEK_TO}（周日）"

GAP_NOTE = (
    f"本期源数据为{SRC_PERIOD}汇总口径，统计区间为 2026年7月1日至9月30日；"
    f"而周报目标周期为{WEEK_BRIEF}，成文日期{DATE_TEXT}距季度结束已逾 9 天，"
    "两区间无任何重叠。因此源数据中的杯测场次、客诉单量、闭环率等指标"
    "均属季度累计值，无法折算或拆分成本周发生额。本报告据此处理："
    "可确证的内容一律保留原始季度口径并显式标注；本周发生额一栏不作推测填写。"
)

# ---------------------------------------------------------------- fields.json
FIELDS = {
    "schema": "office-templates/t07/fields.json@1",
    "生成日期": DATE_TEXT,
    "源数据": {
        "文件": "yuguang_q3.json",
        "类型": "季度工作总结",
        "主体": SUBJECT,
        "时段": SRC_PERIOD,
        "统计区间": "2026-07-01 至 2026-09-30（92 天）",
    },
    "目标模板": {
        "类型": "周报",
        "周期": WEEK,
        "周期来源": "推导值——由成文日期 2026年10月9日（周五）所在自然周推得，未在源数据中出现，待业务确认",
    },
    "口径冲突": {
        "级别": "阻断级",
        "说明": GAP_NOTE,
        "重叠天数": 0,
        "可否折算": "否——季度累计值无法拆分为单周发生额，按均摊分摊亦无统计依据，不予采纳",
    },
    "字段": [
        {
            "字段": "报告标题",
            "值": f"{SUBJECT}周报（{WEEK}）",
            "来源字段": "总结主体 + 总结时段（周期经推导替换）",
            "状态": "推导-待确认",
            "说明": "主体为直接对应；周区间为推导值，须经填报人确认后定稿。",
        },
        {
            "字段": "填报部门",
            "值": SUBJECT,
            "来源字段": "总结主体",
            "状态": "直接对应",
            "说明": "原样映射，无歧义。",
        },
        {
            "字段": "报告周期",
            "值": WEEK,
            "来源字段": "成文日期（推导自然周）",
            "状态": "推导-待确认",
            "说明": "源数据仅有季度区间，无周区间。若实际周报周期非此区间，须整体替换。",
        },
        {
            "字段": "成文日期",
            "值": DATE_TEXT,
            "来源字段": "成文日期",
            "状态": "直接对应",
            "说明": "原样映射。",
        },
        {
            "字段": "本周工作完成情况（本周发生额）",
            "值": None,
            "来源字段": None,
            "状态": "无数据源-待补",
            "说明": "源数据“完成季度杯测 36 场”“处理客诉工单 58 单”为季度累计，不等于本周发生额。按 92 天均摊会得出无统计依据的数值，故留空待业务据实填报。",
            "不可用值示例": "不得填入 36 场 / 58 单（季度累计）、亦不得按 36÷13 周均摊",
        },
        {
            "字段": "季度工作回溯（可确证）",
            "值": D["工作回顾"],
            "来源字段": "工作回顾",
            "状态": "直接对应-口径降级回溯",
            "说明": "内容真实可核，但作用域为季度。在周报中作为“季度数据回溯”小节呈现，已在正文中显式标注季度口径。",
        },
        {
            "字段": "主要成绩",
            "值": D["主要成绩"],
            "来源字段": "主要成绩",
            "状态": "直接对应-口径降级回溯",
            "说明": "“客诉 48 小时闭环率提升至 92%”为季度末状态值，非本周改善幅度，作为季度成果回溯列示。",
        },
        {
            "字段": "存在问题",
            "值": D["存在问题"],
            "来源字段": "存在问题",
            "状态": "直接对应-口径降级回溯",
            "说明": "“偏远门店物流损耗偏高”为跨季度持续状态问题，在周报“本周关注事项”中延续列示，不表述为本周新增问题。",
        },
        {
            "字段": "下一步工作打算",
            "值": D["下一步工作打算"],
            "来源字段": "下一步工作打算",
            "状态": "直接对应-口径降级回溯",
            "说明": "季度计划项，语义上可承接为后续跟进事项，但“引入”的时间点与本周推进状态未知，已标注。",
        },
        {
            "字段": "填报人 / 联系人",
            "值": None,
            "来源字段": None,
            "状态": "无数据源-待补",
            "说明": "源数据未提供，须由业务补充。",
        },
        {
            "字段": "本周新增问题",
            "值": None,
            "来源字段": None,
            "状态": "无数据源-待补",
            "说明": "源数据仅含季度层面的问题清单，无本周新增问题记录。",
        },
    ],
    "未采用的折算方案": [
        {
            "方案": "季度累计按 13 周均摊（36→约 2.8 场/周，58→约 4.5 单/周）",
            "否决理由": "杯测与客诉受理并非均匀发生，均摊值无业务含义；写入正式周报即为失实数据。",
        },
        {
            "方案": "将 36 场 / 58 单直接标注为“本周完成”",
            "否决理由": "直接改变数据作用域，构成虚假陈述。",
        },
        {
            "方案": "留空占位符铺满全表",
            "否决理由": "文档不可用；本报告改以“已确证内容 + 显式待补清单”组织，兼顾可读性与真实性。",
        },
    ],
}

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "fields.json"), "w", encoding="utf-8") as f:
    json.dump(FIELDS, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- docx 排版
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

FONT_HEI = "黑体"
FONT_FANG = "仿宋_GB2312"
FONT_SONG = "宋体"


def style_run(run, cn=FONT_FANG, size=16, bold=False, color=None):
    run.font.name = cn
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)


def para(doc, text="", cn=FONT_FANG, size=16, bold=False, align=None,
         indent_chars=0, space_after=6, line_pt=28.8, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        p.alignment = align
    pf.space_after = Pt(space_after)
    pf.line_spacing = Pt(line_pt)
    if indent_chars:
        pf.first_line_indent = Pt(size * indent_chars)
    if text:
        style_run(p.add_run(text), cn, size, bold, color)
    return p


def shade(cell_or_par, hexcolor):
    el = cell_or_par._element
    pr = el.get_or_add_tcPr() if el.tag.endswith("}tc") else el.get_or_add_pPr()
    sh = pr.makeelement(qn("w:shd"), {})
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), hexcolor)
    pr.append(sh)


doc = Document()
sec = doc.sections[0]
sec.top_margin = Cm(3.0)
sec.bottom_margin = Cm(3.0)
sec.left_margin = Cm(2.8)
sec.right_margin = Cm(2.8)

st = doc.styles["Normal"]
st.font.name = FONT_FANG
st.font.size = Pt(16)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_FANG)

# ---- 标题
para(doc, f"{SUBJECT}周报", cn=FONT_HEI, size=22, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4, line_pt=34)
para(doc, f"（{WEEK}）", cn=FONT_HEI, size=16,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14, line_pt=26)

# ---- 报告要素表
meta = doc.add_table(rows=4, cols=2)
meta.style = "Table Grid"
meta.alignment = WD_TABLE_ALIGNMENT.CENTER
meta_rows = [
    ("填报部门", SUBJECT),
    ("报告周期", WEEK + "（推导值，待确认）"),
    ("成文日期", DATE_TEXT),
    ("数据来源", "yuguang_q3.json（季度工作总结口径）"),
]
for i, (k, v) in enumerate(meta_rows):
    for j, txt in enumerate((k, v)):
        c = meta.cell(i, j)
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j == 0 else WD_ALIGN_PARAGRAPH.LEFT
        style_run(p.add_run(txt), FONT_SONG, 12, bold=(j == 0))
        if j == 0:
            shade(c, "F2F2F2")
for row in meta.rows:
    row.cells[0].width = Cm(3.0)
    row.cells[1].width = Cm(11.0)

para(doc, space_after=8, line_pt=10)

# ---- 数据口径提示
warn = para(doc, line_pt=26, space_after=4)
style_run(warn.add_run("【数据口径提示】"), FONT_HEI, 14, bold=True,
          color=RGBColor(0xB0, 0x00, 0x00))
shade(warn, "FFF3CD")
wp = doc.add_paragraph()
wp.paragraph_format.line_spacing = Pt(24)
wp.paragraph_format.space_after = Pt(10)
wp.paragraph_format.first_line_indent = Pt(24)
style_run(wp.add_run(GAP_NOTE), FONT_FANG, 12)
shade(wp, "FFF9E6")

# ---- 一、本周工作完成情况
para(doc, "一、本周工作完成情况", cn=FONT_HEI, size=16, bold=True, space_after=6)
para(doc, "本周（" + WEEK + "）实际发生的杯测场次、客诉工单受理量、闭环率变动等发生额数据，"
          "源数据中无对应记录，留待品控组据实补报后填入。",
     indent_chars=2, space_after=4)
para(doc, "待补字段：① 本周完成杯测场次；② 本周处理客诉工单数；③ 本周客诉 48 小时闭环率；"
          "④ 本周新增问题（如无，请填“无”）。",
     indent_chars=2, space_after=10)

# ---- 二、季度数据回溯
para(doc, "二、季度数据回溯（2026年第三季度口径，非本周发生额）", cn=FONT_HEI, size=16,
     bold=True, space_after=6)
for item in D["工作回顾"]:
    para(doc, f"{D['工作回顾'].index(item) + 1}. {item}。", indent_chars=2, space_after=4)
for item in D["主要成绩"]:
    para(doc, f"3. {item}。", indent_chars=2, space_after=4)
para(doc, "注：上述各项为第三季度累计值，仅作口径回溯参考，不得作为本周工作量的填报依据。",
     indent_chars=2, size=12, space_after=10)

# ---- 三、存在问题
para(doc, "三、本周关注事项", cn=FONT_HEI, size=16, bold=True, space_after=6)
for item in D["存在问题"]:
    para(doc, f"{D['存在问题'].index(item) + 1}. {item}（第三季度已识别的持续性问题，本周延续跟进）。",
         indent_chars=2, space_after=4)
para(doc, "本周是否新增问题，源数据未记录，待补充。", indent_chars=2, space_after=10)

# ---- 四、下周工作计划
para(doc, "四、下周工作计划", cn=FONT_HEI, size=16, bold=True, space_after=6)
for item in D["下一步工作打算"]:
    para(doc, f"{D['下一步工作打算'].index(item) + 1}. {item}——"
              f"该项为第三季度既定计划，其在本周的实际推进进度源数据未记录，待补充。",
         indent_chars=2, space_after=10)

# ---- 五、字段对照与待补清单
para(doc, "五、字段对照与待补清单", cn=FONT_HEI, size=16, bold=True, space_after=6)

tbl = doc.add_table(rows=1, cols=4)
tbl.style = "Table Grid"
hdr = ["周报字段", "取值", "状态", "来源 / 说明"]
for j, h in enumerate(hdr):
    c = tbl.rows[0].cells[j]
    c.text = ""
    p = c.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(p.add_run(h), FONT_SONG, 11, bold=True)
    shade(c, "E8E8E8")

BRIEF = {
    "报告标题": f"{SUBJECT}周报（{WEEK}）",
    "填报部门": SUBJECT,
    "报告周期": f"{WEEK}，推导值待确认",
    "成文日期": DATE_TEXT,
    "本周工作完成情况（本周发生额）": "（待补）",
    "季度数据回溯（可确证）": "；".join(D["工作回顾"] + D["主要成绩"]),
    "存在问题 / 本周关注事项": "；".join(D["存在问题"]),
    "下一步工作打算": "；".join(D["下一步工作打算"]),
    "填报人 / 联系人": "（待补）",
}

for fl in FIELDS["字段"]:
    key = fl["字段"]
    if key == "报告标题":
        disp = "报告标题"
    elif key == "本周工作完成情况（本周发生额）":
        disp = key
    elif key == "季度工作回溯（可确证）":
        disp = "季度数据回溯（可确证）"
    elif key == "存在问题":
        disp = "存在问题 / 本周关注事项"
    elif key == "下一步工作打算":
        disp = "下一步工作打算"
    else:
        disp = key
    r = tbl.add_row().cells
    for j, txt in enumerate((disp, BRIEF.get(disp, ""), fl["状态"], fl["说明"])):
        r[j].text = ""
        p = r[j].paragraphs[0]
        p.paragraph_format.line_spacing = Pt(14)
        style_run(p.add_run(txt), FONT_SONG, 9,
                  bold=(j == 2),
                  color=(RGBColor(0xB0, 0x00, 0x00) if (j == 2 and "待补" in txt) else None))

widths = [Cm(3.2), Cm(4.6), Cm(2.6), Cm(5.4)]
for row in tbl.rows:
    for c, w in zip(row.cells, widths):
        c.width = w

# 表头跨页重复，且单元格内容不跨页拆分
trPr = tbl.rows[0]._tr.get_or_add_trPr()
trPr.append(trPr.makeelement(qn("w:tblHeader"), {}))
for row in tbl.rows:
    pr = row._tr.get_or_add_trPr()
    pr.append(pr.makeelement(qn("w:cantSplit"), {}))

para(doc, space_after=6, line_pt=10)
para(doc, "填报人签字：＿＿＿＿＿＿　　复核：＿＿＿＿＿＿　　日期：＿＿＿＿＿＿",
     cn=FONT_SONG, size=12, space_after=0)

doc.save(os.path.join(OUT, "文书.docx"))
print("OK ->", os.path.join(OUT, "文书.docx"), "|", os.path.join(OUT, "fields.json"))