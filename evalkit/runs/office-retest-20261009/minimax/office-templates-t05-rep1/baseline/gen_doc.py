#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成请示函 文书.docx + 字段映射 fields.json

版式依据 GB/T 9704-2012《党政机关公文格式》：
  版头（发文机关标志 / 发文字号 / 红色分隔线）→ 主体（标题 / 主送机关 / 正文 /
  发文机关署名 / 成文日期 / 印章位）→ 版记（抄送 / 印发机关 / 印发日期）。
页面 A4，天头 37mm、订口 28mm，版心 156mm × 225mm，正文三号仿宋、固定行距 29 磅。
"""
import json
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Mm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "lanshan_miji.json")
OUT_DIR = os.path.join(HERE, "out")
DOCX_PATH = os.path.join(OUT_DIR, "文书.docx")
FIELDS_PATH = os.path.join(OUT_DIR, "fields.json")

# ---------------------------------------------------------------- 字号 / 字体
CH2 = 22.0   # 二号
CH3 = 16.0   # 三号
CH4 = 14.0   # 四号
XIAOCHU = 42.0  # 初号（小初）

FS = "仿宋_GB2312"
HT = "黑体"
XBS = "方正小标宋简体"
ST = "宋体"

LINE = Pt(29)          # 固定行距，保证每面 22 行
IND2 = Pt(CH3 * 2)     # 首行缩进 2 字
RED = RGBColor(0xFF, 0x00, 0x00)

# 版记分隔线用黑色
BLACK = "000000"
REDHEX = "FF0000"


def set_run(run, font, size, bold=False, color=None):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), font)
    return run


def para(container, text="", font=FS, size=CH3, bold=False, align=None,
         first_indent=None, right_indent=None, line=LINE, space_before=0,
         space_after=0, color=None):
    p = container.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        p.alignment = align
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if first_indent is not None:
        pf.first_line_indent = first_indent
    if right_indent is not None:
        pf.right_indent = right_indent
    if text:
        set_run(p.add_run(text), font, size, bold=bold, color=color)
    return p


def para_border(p, edge="bottom", sz=12, color=BLACK, space=1):
    """给段落加边框（sz 单位 1/8 磅）。"""
    pPr = p._p.get_or_add_pPr()
    pbdr = pPr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        # w:pBdr 必须排在 w:spacing 之前
        pPr.append(pbdr)
    el = OxmlElement("w:" + edge)
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pbdr.append(el)


def bottom_line(container, sz, color, space=1):
    p = container.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(1)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    para_border(p, "bottom", sz=sz, color=color, space=space)
    return p


# ---------------------------------------------------------------- 生成文档
def build(data):
    doc = Document()

    # 默认样式（Normal）
    normal = doc.styles["Normal"]
    normal.font.name = FS
    normal.font.size = Pt(CH3)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FS)

    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Mm(37)
    sec.bottom_margin = Mm(35)
    sec.left_margin = Mm(28)
    sec.right_margin = Mm(26)
    sec.footer_distance = Mm(20)

    # ---- 页码：「— 1 —」 四号宋体，奇数页居右 / 偶数页居左（此处单页居中偏右）
    footer_p = sec.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    footer_p.paragraph_format.line_spacing = Pt(20)
    set_run(footer_p.add_run("— "), ST, CH4)
    set_run(footer_p.add_run("1"), ST, CH4)
    set_run(footer_p.add_run(" —"), ST, CH4)

    org = "澜山物业管理有限公司"
    unit = data["请示单位"]

    # ---- 版头：发文机关标志（红色小标宋）
    para(doc, org, font=XBS, size=XIAOCHU, color=RED,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=Pt(54), space_after=2)
    # ---- 发文字号（数据未提供，按机关代字 + 年份 + 流水号规范拟制）
    wenhao = "澜山物业综函〔2026〕12号"
    para(doc, wenhao, font=FS, size=CH3,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=Pt(29), space_after=0)
    # ---- 红色分隔线
    bottom_line(doc, sz=18, color=REDHEX, space=0)

    # ---- 标题
    title = "关于" + data["请示事由"].replace("的请示", "") + "的请示"
    para(doc, title, font=XBS, size=CH2, align=WD_ALIGN_PARAGRAPH.CENTER,
         line=Pt(36), space_before=20, space_after=20)

    # ---- 主送机关（顶格，回行用全角冒号后的空格表示）
    para(doc, data["主送机关"] + "：", font=FS, size=CH3,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=LINE)

    # ---- 正文
    # 请示缘由、请示事项两句原文照录（含句末句号），补充句另起，不改原句
    para(doc,
         data["请示缘由"] +
         "档案存储空间已无法满足现有归档与保管要求，"
         "为保障业委会档案资料安全、完整存放，现就有关事项请示如下。",
         first_indent=IND2, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    # 一级标题「一、」用黑体，正文用仿宋
    p = para(doc, "", first_indent=IND2, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    set_run(p.add_run("一、"), HT, CH3)
    set_run(p.add_run(data["请示事项"] +
                      "所购密集架到位后，由综合管理部档案室统一验收、"
                      "登记造册并纳入固定资产台账管理。"),
            FS, CH3)
    para(doc, "妥否，请批示。", first_indent=IND2,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    # ---- 发文机关署名（右空二字）
    para(doc, unit, font=XBS, size=CH3, align=WD_ALIGN_PARAGRAPH.RIGHT,
         right_indent=Pt(CH3 * 2), space_before=LINE.pt)
    # ---- 成文日期（右空四字）
    para(doc, data["成文日期"], font=FS, size=CH3,
         align=WD_ALIGN_PARAGRAPH.RIGHT, right_indent=Pt(CH3 * 4))
    # ---- 印章位 + 联系方式
    para(doc, "（此处加盖" + unit + "公章）", font=FS, size=CH4,
         align=WD_ALIGN_PARAGRAPH.RIGHT, right_indent=Pt(CH3 * 2))
    para(doc, "联系人：" + data["联系人"] + "　　联系电话：" + data["联系电话"],
         font=FS, size=CH4, align=WD_ALIGN_PARAGRAPH.RIGHT,
         right_indent=Pt(CH3 * 2))

    # ---- 版记（位于最后一面底部；本件为单页公文，随正文排于同页）
    # 抄送行兼作版记顶线与其内部分隔线，印发行兼作版记底线
    p = para(doc, "抄送：综合管理部档案室。", font=ST, size=CH4, line=Pt(18), space_before=10)
    para_border(p, "top", sz=12, color=BLACK, space=1)
    para_border(p, "bottom", sz=6, color=BLACK, space=1)
    p = para(doc, "印发机关：" + unit + "　　印发日期：" + data["成文日期"],
             font=ST, size=CH4, line=Pt(18), space_before=10)
    para_border(p, "bottom", sz=12, color=BLACK, space=1)

    return doc, title, wenhao


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    title, wenhao = None, None
    doc, title, wenhao = build(data)
    doc.save(DOCX_PATH)
    doc = Document(DOCX_PATH)  # reopen to confirm readable
    print("written:", DOCX_PATH, "paragraphs:", len(doc.paragraphs))

    fields = {
        "文档": "文书.docx",
        "文种": "请示（函）",
        "来源数据": "lanshan_miji.json",
        "版式依据": "GB/T 9704-2012《党政机关公文格式》",
        "标题": title,
        "发文字号": wenhao,
        "字段映射": [
            {
                "源字段": "请示事由",
                "源值": data["请示事由"],
                "出现位置": "标题",
                "文中表述": title,
                "处理": "去掉尾缀「的请示」后以「关于……的请示」公文标题格式重组"
            },
            {
                "源字段": "主送机关",
                "源值": data["主送机关"],
                "出现位置": "正文首行（顶格）",
                "文中表述": data["主送机关"] + "：",
                "处理": "原文照录，行末加全角冒号"
            },
            {
                "源字段": "请示缘由",
                "源值": data["请示缘由"],
                "出现位置": "正文第一自然段",
                "文中表述": data["请示缘由"] +
                           "档案存储空间已无法满足现有归档与保管要求，"
                           "为保障业委会档案资料安全、完整存放，现就有关事项请示如下。",
                "处理": "整句原文照录（含句末句号），补充的请示目的句另起，不改原句"
            },
            {
                "源字段": "请示事项",
                "源值": data["请示事项"],
                "出现位置": "正文第二自然段（黑体一级标题「一、」）",
                "文中表述": "一、" + data["请示事项"] +
                           "所购密集架到位后，由综合管理部档案室统一验收、"
                           "登记造册并纳入固定资产台账管理。",
                "处理": "整句原文照录（含句末句号），前置黑体一级标题「一、」，"
                        "后接落实措施句"
            },
            {
                "源字段": "请示单位",
                "源值": data["请示单位"],
                "出现位置": "正文下方发文机关署名 / 印章位 / 版记印发机关",
                "文中表述": data["请示单位"],
                "处理": "原文照录，右空二字署名"
            },
            {
                "源字段": "联系人",
                "源值": data["联系人"],
                "出现位置": "印章位下方联系方式行（右空二字）",
                "文中表述": "联系人：" + data["联系人"],
                "处理": "原文照录"
            },
            {
                "源字段": "联系电话",
                "源值": data["联系电话"],
                "出现位置": "印章位下方联系方式行（右空二字）",
                "文中表述": "联系电话：" + data["联系电话"],
                "处理": "原文照录"
            },
            {
                "源字段": "成文日期",
                "源值": data["成文日期"],
                "出现位置": "成文日期（右空四字） / 版记印发日期",
                "文中表述": data["成文日期"],
                "处理": "原文照录"
            }
        ],
        "非源数据补足项": [
            {
                "项": "发文字号",
                "值": wenhao,
                "说明": "来源数据未提供发文字号，按「机关代字+文种+〔年份〕+流水号」"
                        "规范拟制，请发文前核定"
            },
            {
                "项": "抄送机关",
                "值": "综合管理部档案室",
                "说明": "来源数据未提供，按请示事项的承办单位拟抄"
            }
        ],
        "未落文字段": []
    }
    with open(FIELDS_PATH, "w", encoding="utf-8") as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)
    print("written:", FIELDS_PATH)


if __name__ == "__main__":
    main()
