#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拾贝书店第42周周报生成器。

从 shibei_week42.json 读取填报数据，产��：
  out/fields.json          字段台账（交付核对的唯一依据）
  out/文书.docx              周报正文
  out/delivery-report.json 交付核对报告（四个键，字段台账派生）
"""

import json
import os
import re

import docx
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "shibei_week42.json")
OUT = os.path.join(BASE, "out")

# ---------------------------------------------------------------- 模板字段定义
# required=True 的字段缺失即视为不完整；optional=True 缺失不阻断交付。
SCHEMA = [
    ("部门", "text", True),
    ("填报人", "text", True),
    ("周期", "text", True),
    ("本周工作内容", "list", True),
    ("下周工作计划", "text", True),
    ("问题与需协调事项", "list", True),
    ("报送日期", "text", True),
    ("温馨提示", "text", False),
]

SECTION_NO = {
    "本周工作内容": "一、本周工作内容",
    "下周工作计划": "二、下周工作计划",
    "问题与需协调事项": "三、问题与需协调事项",
    "温馨提示": "四、温馨提示",
}

HEAD_FONT = "黑体"
BODY_FONT = "宋体"


def is_blank(value):
    """空值判定：None、空串、纯空白串。"""
    return value is None or (isinstance(value, str) and value.strip() == "")


def normalize(kind, value):
    """按字段类型归一化。返回 (归一化值, 丢弃条目数, 是否有值)。"""
    if kind == "list":
        items = value if isinstance(value, list) else ([] if is_blank(value) else [value])
        kept = [str(it).strip() for it in items if not is_blank(it)]
        return kept, len(items) - len(kept), len(kept) > 0
    text = "" if is_blank(value) else str(value).strip()
    return text, 0, text != ""


def short_period(period):
    """周期常带括号补充日期（如「2026年10月第2周（10月5日-10月9日）」），
    标题里取括号前的主干，避免标题出现套叠括号。"""
    main = re.split(r"[（(]", period, maxsplit=1)[0].strip()
    return main or period


def build_ledger(raw):
    """构建字段台账。missing_required_names / missing_optional / unknown_keys 全部由此派生。"""
    fields = []
    for name, kind, required in SCHEMA:
        present = name in raw
        raw_value = raw.get(name)
        value, dropped, has_value = normalize(kind, raw_value)
        missing = present and not has_value  # 键存在但内容为空 -> 视为缺失
        fields.append({
            "name": name,
            "type": kind,
            "required": required,
            "present": present,
            "missing": missing,
            "dropped_blank_items": dropped,
            "raw": raw_value,
            "value": value,
        })

    return {
        "title": "{dept}周报（{period}）".format(
            dept=next((f["value"] for f in fields if f["name"] == "部门"), ""),
            period=short_period(next((f["value"] for f in fields if f["name"] == "周期"), "")),
        ),
        "source": "shibei_week42.json",
        "fields": fields,
        "missing_required_names": [f["name"] for f in fields if f["required"] and f["missing"]],
        "missing_optional": [f["name"] for f in fields if not f["required"] and f["missing"]],
        "unknown_keys": [k for k in raw if k not in {n for n, _, _ in SCHEMA}],
    }


def v(ledger, name):
    for f in ledger["fields"]:
        if f["name"] == name:
            return f["value"]
    return ""


# ------------------------------------------------------------------ 排版工具
def set_font(run, cn, size, bold=False, color=None):
    run.font.name = cn
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)


def line13(par, first_indent_chars=0):
    """1.3 倍行距；可选首行缩进（以字符为单位）。"""
    pf = par.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.3
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)
    if first_indent_chars:
        pf.first_line_indent = Pt(first_indent_chars * size_pt)


size_pt = 12


def body_par(doc, text, indent=0, size=12):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.3
    pf.space_after = Pt(6)
    if indent:
        pf.first_line_indent = Pt(indent * size)
    set_font(p.add_run(text), BODY_FONT, size)
    return p


def heading(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.3
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    pf.keep_with_next = True
    # 挂到 Heading 2 语义样式，保证目录/导航可用；样式默认蓝色在此覆盖
    p.style = doc.styles["Heading 2"]
    set_font(p.add_run(text), HEAD_FONT, 14, bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))
    return p


def build_docx(ledger, path):
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(size_pt)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.17)

    # 标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(12)
    title.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    title.paragraph_format.line_spacing = 1.3
    set_font(title.add_run(ledger["title"]), HEAD_FONT, 18, bold=True,
             color=RGBColor(0x1A, 0x1A, 0x1A))

    # 报送信息表
    meta = [("周期", v(ledger, "周期")),
            ("填报人", v(ledger, "填报人")),
            ("报送日期", v(ledger, "报送日期"))]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for label, value in meta:
        row = table.add_row()
        for cell in row.cells:
            cell.paragraphs[0].paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            cell.paragraphs[0].paragraph_format.line_spacing = 1.3
            cell.paragraphs[0].paragraph_format.space_after = Pt(2)
        row.cells[0].width = Cm(3.2)
        row.cells[1].width = Cm(11.0)
        set_font(row.cells[0].paragraphs[0].add_run(label), HEAD_FONT, 11, bold=True)
        set_font(row.cells[1].paragraphs[0].add_run(value), BODY_FONT, 11)
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(docx.oxml.parse_xml(
            '<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))

    doc.add_paragraph()

    # 正文各栏目
    for name in ("本周工作内容", "下周工作计划", "问题与需协调事项", "温馨提示"):
        value = v(ledger, name)
        if isinstance(value, list):
            heading(doc, SECTION_NO[name])
            if not value:
                body_par(doc, "（无）", indent=2)
            for idx, item in enumerate(value, 1):
                p = body_par(doc, "{}. {}".format(idx, item))
                p.paragraph_format.left_indent = Cm(0.74)
        else:
            if not value:
                continue
            heading(doc, SECTION_NO[name])
            body_par(doc, value, indent=2)

    doc.save(path)


def main():
    with open(SRC, encoding="utf-8") as fh:
        raw = json.load(fh)

    ledger = build_ledger(raw)
    os.makedirs(OUT, exist_ok=True)

    fields_path = os.path.join(OUT, "fields.json")
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)

    docx_path = os.path.join(OUT, "文书.docx")
    build_docx(ledger, docx_path)

    report = {
        "missing_required_names": ledger["missing_required_names"],
        "missing_optional": ledger["missing_optional"],
        "unknown_keys": ledger["unknown_keys"],
        "title": ledger["title"],
    }
    with open(os.path.join(OUT, "delivery-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    for f in ledger["fields"]:
        if f["dropped_blank_items"]:
            print("剔除空白条目 {} 项：{}".format(f["dropped_blank_items"], f["name"]))
    print("标题：", ledger["title"])
    print("产物：", fields_path, docx_path, os.path.join(OUT, "delivery-report.json"))


if __name__ == "__main__":
    main()