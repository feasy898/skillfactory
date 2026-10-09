#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文生成流程：读取结构化数据 → 归一化 → 渲染 文书.docx + fields.json。

设计要点（针对空数据/空白数据的鲁棒性）：
  * 字段缺失（key 不存在）与字段空白（值为空串/纯空白/空列表）分开记录，
    两者在正文中都渲染为占位符 ［未填写］，但 fields.json 如实区分状态。
  * 不做任何编造填充，缺失内容一律以占位符呈现，并在 fields.json 的
    "说明" 中写明未填写字段清单。
  * 任何异常都不向上冒泡中断生成：单个字段出错时降级为占位符并记入
    "错误" 列表，两份文书都保证落盘。
"""

import json
import os
import sys
import traceback
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

# ---------------------------------------------------------------- 常量

PLACEHOLDER = "［未填写］"

FONT_TITLE = "方正小标宋简体"
FONT_BODY = "仿宋_GB2312"
FONT_SECTION = "黑体"
SIZE_TITLE = Pt(22)      # 二号
SIZE_BODY = Pt(16)       # 三号
LINE_SPACING = Pt(29)    # 公文正文行距
INDENT_2CHAR = Pt(32)    # 三号字两字符首行缩进

STATUS_FILLED = "已填写"
STATUS_BLANK = "空白"    # 键存在但值为空串/纯空白/空列表
STATUS_MISSING = "缺失"  # 键不存在


# ---------------------------------------------------------------- 归一化

def _is_blank_text(value):
    """空串、None、纯空白（含全角空格 U+3000）都算空白。"""
    if value is None:
        return True
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    if isinstance(value, str):
        return value.strip() == ""
    return False


def normalize(raw, source_key):
    """把一个原始取值归一化。

    返回 (状态, 规范值)。规范值：text -> str 或 None；list -> list[str] 或 None。
    """
    if source_key is not None and source_key not in raw:
        return STATUS_MISSING, None

    value = raw.get(source_key)

    if isinstance(value, list):
        items = [str(v).strip() for v in value if not _is_blank_text(v)]
        if not items:
            return STATUS_BLANK, []
        return STATUS_FILLED, items

    if _is_blank_text(value):
        return STATUS_BLANK, None

    if isinstance(value, (dict, list)):
        return STATUS_FILLED, value

    return STATUS_FILLED, str(value).strip()


def display(status, value):
    """正文里显示的文本：已填写的用真值，其余一律占位符。"""
    if status != STATUS_FILLED:
        return PLACEHOLDER
    if isinstance(value, list):
        return PLACEHOLDER
    return value


def items_of(status, value):
    """列表字段用于逐条渲染；未填写时给出一个占位符条目，保持结构完整。"""
    if status == STATUS_FILLED and isinstance(value, list) and value:
        return list(value)
    return [PLACEHOLDER]


# ---------------------------------------------------------------- Word 排版

def style_run(run, font_name, size, bold=False):
    run.font.name = font_name
    run.font.size = size
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)


def new_document():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT_BODY
    normal.font.size = SIZE_BODY
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)

    for section in doc.sections:
        section.top_margin = Mm(37)
        section.bottom_margin = Mm(35)
        section.left_margin = Mm(28)
        section.right_margin = Mm(26)
    return doc


def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(24)
    p.paragraph_format.line_spacing = LINE_SPACING
    style_run(p.add_run(text), FONT_TITLE, SIZE_TITLE)
    return p


def add_body(doc, text, indent=True, font=FONT_BODY, size=SIZE_BODY):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = LINE_SPACING
    pf.space_after = Pt(0)
    if indent:
        pf.first_line_indent = INDENT_2CHAR
    style_run(p.add_run(text), font, size)
    return p


def add_section_heading(doc, text):
    """一、二、…… 小标题：黑体三号，首行缩进两字符。"""
    return add_body(doc, text, indent=True, font=FONT_SECTION)


def add_addressee(doc, text):
    """主送机关：顶格，末尾加冒号。"""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = LINE_SPACING
    p.paragraph_format.space_after = Pt(0)
    style_run(p.add_run(text + "："), FONT_BODY, SIZE_BODY)
    return p


def add_signature(doc, unit, date):
    """落款：右对齐（署名与日期各占一行，右空两字符）。"""
    for i, text in enumerate((unit, date)):
        if text is None:
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = LINE_SPACING
        p.paragraph_format.space_after = Pt(0)
        # 落款与正文之间空一行，符合公文惯例
        if i == 0:
            p.paragraph_format.space_before = LINE_SPACING
        p.paragraph_format.right_indent = Pt(SIZE_BODY.pt * 2)
        style_run(p.add_run(text), FONT_BODY, SIZE_BODY)


def add_empty_marker(doc):
    """正文下方加一条灰底提示，说明本件是空数据生成的骨架稿。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(36)
    style_run(p.add_run("（本件由空数据生成，正文 ［未填写］ 处待补充）"),
              FONT_BODY, Pt(10.5))
    return p


# ---------------------------------------------------------------- 模板

def collect_fields(raw, schema):
    """按模板 schema 抽取字段，产出 fields.json 用的字段清单。"""
    records = []
    for spec in schema:
        source_key = spec.get("source_key", spec["key"])
        try:
            status, value = normalize(raw, source_key)
        except Exception as exc:  # 单字段异常不中断，降级为缺失并记录
            status, value = STATUS_MISSING, None
            spec = dict(spec)
            spec["_error"] = "%s: %s" % (type(exc).__name__, exc)
        records.append({
            "字段": spec["key"],
            "来源键": source_key,
            "类型": spec.get("type", "text"),
            "状态": status,
            "原文": raw.get(source_key, None),
            "规范值": value,
            "正文取值": display(status, value),
            "占位符": status != STATUS_FILLED,
        })
    return records


def summarize(records):
    stats = {
        "字段总数": len(records),
        STATUS_FILLED: sum(1 for r in records if r["状态"] == STATUS_FILLED),
        STATUS_BLANK: sum(1 for r in records if r["状态"] == STATUS_BLANK),
        STATUS_MISSING: sum(1 for r in records if r["状态"] == STATUS_MISSING),
    }
    stats["占位符渲染数"] = stats[STATUS_BLANK] + stats[STATUS_MISSING]
    return stats


def build_fields_json(doc_type, source_path, source_key_name, raw, records,
                      out_dir, errors):
    unfilled = [r["字段"] for r in records if r["状态"] != STATUS_FILLED]
    return {
        "文书类型": doc_type,
        "数据来源": os.path.relpath(source_path, os.path.dirname(os.path.dirname(out_dir))),
        "源文件名": os.path.basename(source_path),
        "输出目录": os.path.relpath(out_dir, os.path.dirname(os.path.dirname(out_dir))),
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "源数据": raw,
        "字段清单": records,
        "统计": summarize(records),
        "未填写字段": unfilled,
        "处理说明": (
            "本次输入数据存在未填写项。生成流程对缺失键与空白值一律不做编造，"
            "正文相应位置渲染为占位符 ［未填写］，并在本清单中逐项记录状态；"
            "文档结构与段落层级完整保留，可直接在占位符处补写。"
        ),
        "错误": errors,
    }


# ---------------------------------------------------------------- 两个模板

def gen_qingshi(raw, source_path, out_dir, errors):
    doc_type = "请示函"
    doc = new_document()

    schema = [
        {"key": "标题", "source_key": "标题"},
        {"key": "主送机关", "source_key": "主送机关"},
        {"key": "请示事由", "source_key": "请示事由"},
        {"key": "请示事项", "source_key": "请示事项", "type": "list"},
        {"key": "落款单位", "source_key": "落款单位"},
        {"key": "成文日期", "source_key": "成文日期"},
    ]
    records = collect_fields(raw, schema)
    by_key = {r["字段"]: r for r in records}

    add_title(doc, by_key["标题"]["正文取值"])

    add_addressee(doc, by_key["主送机关"]["正文取值"])

    add_body(doc, "现就有关事项请示如下：")

    r = by_key["请示事由"]
    add_section_heading(doc, "一、请示事由")
    add_body(doc, r["正文取值"])

    r = by_key["请示事项"]
    add_section_heading(doc, "二、请示事项")
    for i, item in enumerate(items_of(r["状态"], r["规范值"]), 1):
        add_body(doc, "（%s）%s" % ("一二三四五六七八九十"[i - 1], item))

    add_body(doc, "妥否，请批示。")

    unit = by_key["落款单位"]["正文取值"]
    date = by_key["成文日期"]["正文取值"]
    add_signature(doc, unit, date)

    if summarize(records)["占位符渲染数"]:
        add_empty_marker(doc)

    os.makedirs(out_dir, exist_ok=True)
    docx_path = os.path.join(out_dir, "文书.docx")
    doc.save(docx_path)
    return docx_path, build_fields_json(doc_type, source_path, "qingshi_empty",
                                        raw, records, out_dir, errors)


def gen_zongjie(raw, source_path, out_dir, errors):
    doc_type = "工作总结"
    doc = new_document()

    schema = [
        {"key": "标题", "source_key": "标题"},
        {"key": "总结主体", "source_key": "总结主体"},
        {"key": "总结时段", "source_key": "总结时段"},
        {"key": "工作回顾", "source_key": "工作回顾", "type": "list"},
        {"key": "主要成绩", "source_key": "主要成绩", "type": "list"},
        {"key": "存在问题", "source_key": "存在问题"},
        {"key": "下一步工作打算", "source_key": "下一步工作打算", "type": "list"},
        {"key": "落款单位", "source_key": "落款单位"},
        {"key": "成文日期", "source_key": "成文日期"},
    ]
    records = collect_fields(raw, schema)
    by_key = {r["字段"]: r for r in records}

    # 标题缺省时用「总结主体+总结时段」拼装，任一为空白则退回占位符片段。
    subject = by_key["总结主体"]["正文取值"]
    period = by_key["总结时段"]["正文取值"]
    title = by_key["标题"]["正文取值"]
    if by_key["标题"]["状态"] != STATUS_FILLED:
        if subject != PLACEHOLDER and period != PLACEHOLDER:
            title = "%s%s工作总结" % (subject, period)
        else:
            title = PLACEHOLDER
    add_title(doc, title)

    lead = " ".join(x for x in (subject, period) if x != PLACEHOLDER)
    add_body(doc, lead if lead else PLACEHOLDER)

    for heading, key in (("一、工作回顾", "工作回顾"),
                         ("二、主要成绩", "主要成绩")):
        r = by_key[key]
        add_section_heading(doc, heading)
        for i, item in enumerate(items_of(r["状态"], r["规范值"]), 1):
            add_body(doc, "（%s）%s" % ("一二三四五六七八九十"[i - 1], item))

    r = by_key["存在问题"]
    add_section_heading(doc, "三、存在问题")
    add_body(doc, r["正文取值"])

    r = by_key["下一步工作打算"]
    add_section_heading(doc, "四、下一步工作打算")
    for i, item in enumerate(items_of(r["状态"], r["规范值"]), 1):
        add_body(doc, "（%s）%s" % ("一二三四五六七八九十"[i - 1], item))

    unit = by_key["落款单位"]["正文取值"]
    date = by_key["成文日期"]["正文取值"]
    add_signature(doc, unit, date)

    if summarize(records)["占位符渲染数"]:
        add_empty_marker(doc)

    os.makedirs(out_dir, exist_ok=True)
    docx_path = os.path.join(out_dir, "文书.docx")
    doc.save(docx_path)
    return docx_path, build_fields_json(doc_type, source_path, "zongjie_blank",
                                        raw, records, out_dir, errors)


JOBS = [
    ("fixtures/qingshi_empty.json", "out/请示函-empty", gen_qingshi),
    ("fixtures/zongjie_blank.json", "out/工作总结-blank", gen_zongjie),
]


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    run_log = []
    exit_code = 0

    for rel_src, rel_out, builder in JOBS:
        entry = {"源文件": rel_src, "输出目录": rel_out}
        errors = []
        try:
            with open(rel_src, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                errors.append("顶层不是对象，按空对象处理")
                raw = {}
        except Exception as exc:
            errors.append("读取源数据失败：%s: %s" % (type(exc).__name__, exc))
            traceback.print_exc()
            raw = {}

        try:
            docx_path, fields = builder(raw, os.path.abspath(rel_src),
                                        os.path.abspath(rel_out), errors)
            fields_path = os.path.join(os.path.abspath(rel_out), "fields.json")
            with open(fields_path, "w", encoding="utf-8") as fh:
                json.dump(fields, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            entry.update({
                "文书": docx_path,
                "字段清单": fields_path,
                "统计": fields["统计"],
                "状态": "ok",
            })
        except Exception as exc:
            traceback.print_exc()
            entry.update({
                "状态": "failed",
                "错误": "%s: %s" % (type(exc).__name__, exc),
            })
            exit_code = 1
        run_log.append(entry)

    with open("run_log.json", "w", encoding="utf-8") as fh:
        json.dump({"生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "任务": run_log}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for entry in run_log:
        print("[%s] %s -> %s  %s" % (entry["状态"], entry["源文件"],
                                    entry["输出目录"], entry.get("统计", "")))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
