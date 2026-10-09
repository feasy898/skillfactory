#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 GB/T 9704 党政机关公文格式，从 lanshan_miji.json 起草请示函。

产出：out/文书.docx、out/fields.json
"""
import json
import pathlib

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

BASE = pathlib.Path(__file__).resolve().parent
OUT = BASE / "out"
OUT.mkdir(exist_ok=True)

# 本机可用的中文宋体族：Noto Serif CJK SC（衬线，≈仿宋/宋观感）
FONT = "Noto Serif CJK SC"
# 三号 = 16pt，二号 = 22pt，小二 = 18pt，四号 = 14pt
SIZE_3 = Pt(16)
SIZE_2 = Pt(22)
SIZE_XIAO2 = Pt(18)
LINE = Pt(28.8)  # 公文标准行距（每页 22 行）
CHAR = SIZE_3    # 一个「字」宽，用于按字符数缩进
RED = "FF0000"


def set_font(run, size=SIZE_3, bold=False, color=None, font=FONT):
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    if color:
        run.font.color.rgb = __import__("docx").shared.RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), font)


def para(doc, text="", *, size=SIZE_3, bold=False, color=None,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent_chars=0, right_chars=0,
         before=0, after=0, line=LINE, keep_next=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if indent_chars:
        pf.first_line_indent = Pt(indent_chars * size.pt)
    if right_chars:
        pf.right_indent = Pt(right_chars * size.pt)
    pf.keep_with_next = keep_next
    if text:
        set_font(p.add_run(text), size=size, bold=bold, color=color)
    return p


def red_rule(doc):
    """武文线：版头下方的红色分隔线。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(24)
    pPr = p._element.get_or_add_pPr()
    bdr = pPr.makeelement(qn("w:pBdr"), {})
    bottom = pPr.makeelement(qn("w:bottom"), {})
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")      # 1.5pt
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), RED)
    bdr.append(bottom)
    pPr.append(bdr)
    return p


def page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("— "), size=Pt(14))
    r = p.add_run()
    set_font(r, size=Pt(14))
    fld = r._element.makeelement(qn("w:fldSimple"), {})
    fld.set(qn("w:instr"), "PAGE")
    r._element.addnext(fld)
    set_font(p.add_run(" —"), size=Pt(14))


def main():
    data = json.loads((BASE / "lanshan_miji.json").read_text(encoding="utf-8"))

    doc = Document()
    # 文档默认字体
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = SIZE_3
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(37), Mm(35)
    sec.left_margin, sec.right_margin = Mm(28), Mm(26)
    sec.footer_distance = Mm(20)
    page_number_footer(sec)

    # —— 版头：发文机关标志（红色）——
    para(doc, data["请示单位"] + "文件", size=SIZE_XIAO2, bold=True, color=RED,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    red_rule(doc)

    # —— 标题：关于……的请示 ——
    title = "关于" + data["请示事由"]
    para(doc, title, size=SIZE_2, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
         after=24)

    # —— 主送机关（顶格）——
    para(doc, data["主送机关"] + "：", align=WD_ALIGN_PARAGRAPH.LEFT,
         after=Pt(2).pt)

    # —— 正文：缘由 / 事项 / 结语 ——
    para(doc, data["请示缘由"], indent_chars=2)
    para(doc, data["请示事项"], indent_chars=2)
    para(doc, "妥否，请批示。", indent_chars=2)

    # —— 联系方式（正文之下空一行，左空二字）——
    para(doc, "（联系人：%s　　联系电话：%s）" % (data["联系人"], data["联系电话"]),
         indent_chars=2, before=12, after=18)

    # —— 发文机关署名与成文日期：日期右空四字，署名较日期右移二字（GB/T 9704）——
    para(doc, data["请示单位"], align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=2)
    para(doc, data["成文日期"], align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=4)

    doc.save(OUT / "文书.docx")

    (OUT / "fields.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", OUT / "文书.docx", "and", OUT / "fields.json")


if __name__ == "__main__":
    main()