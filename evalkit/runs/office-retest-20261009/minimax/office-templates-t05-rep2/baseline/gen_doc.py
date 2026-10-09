#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成请示函（公文格式，GB/T 9704-2012 版式口径）

输入：lanshan_miji.json（源数据）
输出：out/文书.docx      —— 请示函正文
      out/fields.json   —— 字段抽取登记表（字段 → 文书落点）

版式要点：
  页面    A4，上边距 37mm / 下 35mm / 左 28mm / 右 26mm（公文标准页边距）
  行距    固定值 28.8 磅（每面 22 行、每行 28 字）
  标题    方正小标宋简体 小2号（18pt），居中，单行不拆词，标题下空一行
  主送    仿宋_GB2312 3 号，居左顶格，行末冒号
  正文    仿宋_GB2312 3 号，首行缩进 2 字
  落款    发文机关署名、成文日期均右空四字
  附注    居左空二字，编排在成文日期下一行
  页码    4 号半角宋体阿拉伯数字，单页码居右空一字
"""

import json
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "lanshan_miji.json")
OUTDIR = os.path.join(BASE, "out")
DOCX = os.path.join(OUTDIR, "文书.docx")
FIELDS = os.path.join(OUTDIR, "fields.json")

# ---------------------------------------------------------------- 字体 / 字号
FS_TITLE = "方正小标宋简体"          # 公文标题用小标宋
FS_BODY = "仿宋_GB2312"              # 正文主字体
FS_NOTE = "楷体_GB2312"              # 附注用楷体
FS_PAGE = "宋体"                     # 页码

SZ_TITLE = Pt(18)                    # 小 2 号：20 字标题在版心内排单行
SZ_BODY = Pt(16)                     # 3 号
SZ_PAGE = Pt(14)                     # 4 号


# ---------------------------------------------------------------- 低层工具函数
def _set_run_font(run, name, size, bold=False):
    """设置中西文字体（w:eastAsia 必须显式指定，否则中文回退默认字体）。"""
    run.font.name = name
    run.font.size = size
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), name)


def _fix_line_spacing(par, exact_pt=28.8):
    """固定行距（公文要求每行 28 字、每面 22 行，版心高度换算约 28.8 磅）。"""
    pf = par.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(exact_pt)


# CT_PPr 的子元素必须按 OOXML schema 规定的顺序排列，顺序错了 Word 会判文件损坏。
PPR_SEQ = [
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
    "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
]


def _pPr_insert(par, tag):
    """按 schema 顺序把 tag 插入段落的 w:pPr，返回该元素（已存在则复用）。"""
    pPr = par._element.get_or_add_pPr()
    existing = pPr.find(qn(tag))
    if existing is not None:
        return existing
    el = OxmlElement(tag)
    rank = PPR_SEQ.index(tag)
    for child in pPr:
        name = child.tag.split("}")[-1]
        cand = "w:" + name
        if cand in PPR_SEQ and PPR_SEQ.index(cand) > rank:
            child.addprevious(el)
            return el
    pPr.append(el)
    return el


def _no_auto_space(par):
    """关闭中西文、中文与数字之间的自动间距。

    Word/LibreOffice 默认会在汉字与阿拉伯数字之间撑开空隙（「2025 年」而不是
    「2025年」），公文排版要求数字与汉字紧排，需显式关掉。
    """
    for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
        _pPr_insert(par, tag).set(qn("w:val"), "0")


def _char_indent(par, first_line_chars=0, left_chars=0, right_chars=0):
    """按“字符”设置缩进，随字号自适应，等价于公文的“空 N 字”。"""
    pPr = par._element.get_or_add_pPr()
    ind = _pPr_insert(par, "w:ind")
    if first_line_chars:
        ind.set(qn("w:firstLineChars"), str(first_line_chars * 100))
        ind.set(qn("w:firstLine"), str(int(first_line_chars * SZ_BODY.pt * 20)))
    if left_chars:
        ind.set(qn("w:leftChars"), str(left_chars * 100))
        ind.set(qn("w:left"), str(int(left_chars * SZ_BODY.pt * 20)))
    if right_chars:
        ind.set(qn("w:rightChars"), str(right_chars * 100))
        ind.set(qn("w:right"), str(int(right_chars * SZ_BODY.pt * 20)))


def _enable_odd_even_headers(doc):
    """奇偶页页眉页脚分设的开关必须写在 settings.xml，不能放进 sectPr。"""
    settings = doc.settings.element
    if settings.find(qn("w:evenAndOddHeaders")) is None:
        settings.append(OxmlElement("w:evenAndOddHeaders"))


def _fill_page_number(par, align):
    """在页脚段落里写入「— n —」形式的 PAGE 域。

    注意：w:fldChar 必须包在 w:r 内部，直接挂在 w:p 下会让 Word 判定文件损坏。
    """
    par.text = ""
    par.alignment = align
    if align == WD_ALIGN_PARAGRAPH.RIGHT:      # 单页码居右空一字
        _char_indent(par, right_chars=1)
    else:                                       # 双页码居左空一字
        _char_indent(par, left_chars=1)

    def _emit_fld_char(kind):
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
            rf.set(qn(attr), FS_PAGE)
        rPr.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "28")   # 4 号 = 14pt = 28 半磅
        rPr.append(sz)
        r.append(rPr)
        fld = OxmlElement("w:fldChar")
        fld.set(qn("w:fldCharType"), kind)
        r.append(fld)
        par._p.append(r)

    def _emit_instr():
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
            rf.set(qn(attr), FS_PAGE)
        rPr.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "28")
        rPr.append(sz)
        r.append(rPr)
        t = OxmlElement("w:instrText")
        t.set(qn("xml:space"), "preserve")
        t.text = " PAGE "
        r.append(t)
        par._p.append(r)

    def _emit_text(txt):
        run = par.add_run(txt)
        _set_run_font(run, FS_PAGE, SZ_PAGE)

    _emit_text("— ")
    _emit_fld_char("begin")
    _emit_instr()
    _emit_fld_char("separate")
    _emit_text("1")          # 域的缓存结果，Word 打开后自动重算
    _emit_fld_char("end")
    _emit_text(" —")


def _page_number_footer(section, doc):
    """页码：4 号半角宋体，格式「— n —」，单页码居右、双页码居左（外侧对齐）。"""
    _enable_odd_even_headers(doc)

    odd = section.footer
    odd.is_linked_to_previous = False
    _fill_page_number(odd.paragraphs[0] if odd.paragraphs else odd.add_paragraph(),
                      WD_ALIGN_PARAGRAPH.RIGHT)

    even = section.even_page_footer
    even.is_linked_to_previous = False
    _fill_page_number(even.paragraphs[0] if even.paragraphs else even.add_paragraph(),
                      WD_ALIGN_PARAGRAPH.LEFT)


def _set_doc_grid(section):
    """文档网格：每行 28 字、每面 22 行（公文标准版心）。
    python-docx 默认模板自带一个 docGrid，必须替换而非追加，否则出现重复元素。"""
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:docGrid")):
        sectPr.remove(old)
    grid = OxmlElement("w:docGrid")
    grid.set(qn("w:type"), "lines")       # 与段落固定行距配套，保证每面 22 行
    # 版心高 297-37-35=225mm ≈ 637.8pt；每面 22 行 → 28.99pt/行
    # w:linePitch 单位为 1/20 磅，故取 580（≈28.99pt）
    grid.set(qn("w:linePitch"), "580")
    sectPr.append(grid)


# ---------------------------------------------------------------- 文书正文
def build(data):
    doc = Document()

    # 页面设置
    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Mm(37)
    sec.bottom_margin = Mm(35)
    sec.left_margin = Mm(28)
    sec.right_margin = Mm(26)
    sec.footer_distance = Mm(20)
    _set_doc_grid(sec)
    _page_number_footer(sec, doc)

    # 默认样式（正文兜底字体）
    style = doc.styles["Normal"]
    style.font.name = FS_BODY
    style.font.size = SZ_BODY
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FS_BODY)

    # ---- 1. 标题：发文机关 + 关于 + 事由，去掉原「请示」二字后缀后重新成文
    #         「购置档案密集架的请示」→ 事由「购置档案密集架」+ 文种「请示」
    subject = data["请示事由"]
    if subject.endswith("的请示"):
        subject = subject[: -len("的请示")]
    title = "关于{}的请示".format(subject)

    used = []   # (用途, 段落序号, 角色, 文本)

    def add(text, *, align=None, font=FS_BODY, size=SZ_BODY, bold=False,
            first_line_chars=0, left_chars=0, right_chars=0, role="",
            field=None, source="verbatim"):
        par = doc.add_paragraph()
        par.alignment = align
        _no_auto_space(par)
        _fix_line_spacing(par)
        if first_line_chars or left_chars or right_chars:
            _char_indent(par, first_line_chars, left_chars, right_chars)
        else:
            _char_indent(par, first_line_chars)
        run = par.add_run(text)
        _set_run_font(run, font, size, bold)
        idx = len(doc.paragraphs) - 1
        if role:
            used.append({
                "role": role,
                "paragraph_index": idx,
                "text": text,
            })
        return par, idx

    # 标题（居中，小标宋）。GB/T 9704 规定标题一般用 2 号，字数偏多时用小 2 号；
    # 本标题 20 字，2 号在 156mm 版心内会回行并把「请示」拆散，故用小 2 号排单行。
    p_title, i_title = add(
        "澜山物业综合管理部{}".format(title),
        align=WD_ALIGN_PARAGRAPH.CENTER,
        font=FS_TITLE, size=SZ_TITLE,
        role="title", field="请示事由",
    )
    used[-1]["text"] = "澜山物业综合管理部" + title
    used[-1]["note"] = (
        "由「请示单位」+「请示事由」拼装：去掉事由末尾的「的请示」，"
        "改写为公文标题惯用的「关于……的请示」句式"
    )

    # 标题下空一行
    add("")

    # 主送机关（上行文，顶格，行末冒号）
    p_zhu, i_zhu = add(
        data["主送机关"] + "：",
        align=WD_ALIGN_PARAGRAPH.LEFT,
        role="addressee", field="主送机关",
    )
    used[-1]["note"] = "上行文，主送机关居左顶格，行末加冒号"

    # 正文：缘由
    p_yuan, i_yuan = add(
        data["请示缘由"],
        first_line_chars=2,
        role="body_reason", field="请示缘由",
    )

    # 正文：事项
    p_shi, i_shi = add(
        data["请示事项"],
        first_line_chars=2,
        role="body_action", field="请示事项",
    )

    # 正文：结语（请示专用结束语）
    p_jie, i_jie = add(
        "妥否，请批示。",
        first_line_chars=2,
        role="closing",
    )
    used[-1]["note"] = "请示文种结语，正文中已含完整事项，故不再另起「以上请示」"

    # 空一行
    add("")

    # 发文机关署名：右空四字
    p_sign, i_sign = add(
        data["请示单位"],
        align=WD_ALIGN_PARAGRAPH.RIGHT,
        right_chars=4,
        role="signature", field="请示单位",
    )

    # 成文日期：右空四字，比署名再右空一字（标准写法为日期略低于署名右端对齐）
    p_date, i_date = add(
        data["成文日期"],
        align=WD_ALIGN_PARAGRAPH.RIGHT,
        right_chars=4,
        role="date", field="成文日期",
    )
    # 日期右空一字略多于署名，符合「成文日期右空四字、署名右空四字」的成对写法
    used[-1]["note"] = "中文数字日期，右空四字，与发文机关署名成对出现"

    # 附注：联系人 / 联系电话，居左空二字，排在成文日期下一行
    p_note, i_note = add(
        "（联系人：{}　联系电话：{}）".format(data["联系人"], data["联系电话"]),
        align=WD_ALIGN_PARAGRAPH.LEFT,
        font=FS_NOTE, size=SZ_BODY,
        left_chars=2,
        role="contact_note",
    )
    used[-1]["note"] = "两个字段合并为一条附注，加圆括号，居左空二字"

    return doc, used, title, {
        "title": i_title,
        "addressee": i_zhu,
        "body_reason": i_yuan,
        "body_action": i_shi,
        "closing": i_jie,
        "signature": i_sign,
        "date": i_date,
        "contact_note": i_note,
    }


# ---------------------------------------------------------------- 字段登记表
def build_fields(data, title, used, idx_map):
    def loc(role):
        for u in used:
            if u["role"] == role:
                return {"paragraph_index": u["paragraph_index"], "paragraph_text": u["text"]}
        return None

    fields = [
        {
            "key": "请示事由",
            "label": "请示事由",
            "value": data["请示事由"],
            "docx_usage": title,
            "transformed": True,
            "transform_rule": "去掉末尾「的请示」，改写为「关于{事由}的请示」，并冠以发文机关全称",
            "placement": loc("title"),
            "section": "标题",
        },
        {
            "key": "主送机关",
            "label": "主送机关",
            "value": data["主送机关"],
            "docx_usage": data["主送机关"] + "：",
            "transformed": False,
            "transform_rule": "仅补行末冒号",
            "placement": loc("addressee"),
            "section": "主送机关",
        },
        {
            "key": "请示缘由",
            "label": "请示缘由",
            "value": data["请示缘由"],
            "docx_usage": data["请示缘由"],
            "transformed": False,
            "transform_rule": None,
            "placement": loc("body_reason"),
            "section": "正文·缘由",
        },
        {
            "key": "请示事项",
            "label": "请示事项",
            "value": data["请示事项"],
            "docx_usage": data["请示事项"],
            "transformed": False,
            "transform_rule": None,
            "placement": loc("body_action"),
            "section": "正文·事项",
        },
        {
            "key": "请示单位",
            "label": "请示单位（发文机关署名）",
            "value": data["请示单位"],
            "docx_usage": data["请示单位"],
            "transformed": False,
            "transform_rule": None,
            "placement": loc("signature"),
            "section": "落款·发文机关署名",
            "also_used_in": "标题（与请示事由拼装为完整标题）",
        },
        {
            "key": "联系人",
            "label": "联系人",
            "value": data["联系人"],
            "docx_usage": "联系人：{}".format(data["联系人"]),
            "transformed": False,
            "transform_rule": None,
            "placement": loc("contact_note"),
            "section": "附注",
        },
        {
            "key": "联系电话",
            "label": "联系电话",
            "value": data["联系电话"],
            "docx_usage": "联系电话：{}".format(data["联系电话"]),
            "transformed": False,
            "transform_rule": None,
            "placement": loc("contact_note"),
            "section": "附注",
        },
        {
            "key": "成文日期",
            "label": "成文日期",
            "value": data["成文日期"],
            "docx_usage": data["成文日期"],
            "transformed": False,
            "transform_rule": None,
            "placement": loc("date"),
            "section": "落款·成文日期",
        },
    ]

    return {
        "schema": "office-document-fields/1.0",
        "source": "lanshan_miji.json",
        "artifact": "out/文书.docx",
        "document": {
            "文种": "请示",
            "标题": "澜山物业综合管理部" + title,
            "主送机关": data["主送机关"],
            "发文机关": data["请示单位"],
            "成文日期": data["成文日期"],
            "联系人": data["联系人"],
            "联系电话": data["联系电话"],
        },
        "layout": {
            "纸张": "A4（210mm × 297mm）",
            "页边距": {"上": "37mm", "下": "35mm", "左": "28mm", "右": "26mm"},
            "版心": "每行 28 字，每面 22 行",
            "行距": "固定值 28.8 磅",
            "标题": "方正小标宋简体 小 2 号（18pt），居中，标题下空一行",
            "标题字号说明": "GB/T 9704 规定标题一般用 2 号；本标题含发文机关全称共 20 字，2 号在 156mm 版心内会回行并把「请示」拆成两行，故按「字数偏多用小 2 号」的例外降一号处理",
            "主送机关": "仿宋_GB2312 3 号，居左顶格，行末冒号",
            "正文": "仿宋_GB2312 3 号，首行缩进 2 字",
            "落款": "发文机关署名与成文日期均右空四字",
            "附注": "楷体_GB2312 3 号，居左空二字，加圆括号，编排在成文日期下一行",
            "页码": "4 号半角宋体阿拉伯数字，格式「— n —」，单页码居右、双页码居左",
            "中西文间距": "已关闭 autoSpaceDE / autoSpaceDN，数字与汉字紧排",
        },
        "field_count": len(fields),
        "fields": fields,
        "paragraph_map": idx_map,
    }


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(OUTDIR, exist_ok=True)
    doc, used, title, idx_map = build(data)
    doc.save(DOCX)

    payload = build_fields(data, title, used, idx_map)
    with open(FIELDS, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("wrote:", DOCX)
    print("wrote:", FIELDS)


if __name__ == "__main__":
    main()