#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板生成器（缺数据不编造、如实记账）。

命令行契约：
    python3 main.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两个产物：
    文书.docx   —— 缺失必填以 ____ 占位渲染，选填缺失留空或省略
    fields.json —— 逐字段记账（filled / missing_required / missing_optional / unknown_keys）

核心行为：
    * 缺数据不编造：缺失字段一律不臆造值，必填缺失渲染为 ____ 占位符。
    * 如实记账：fields.json 的缺失名单与输入数据的缺失事实逐字段一致，
      选填缺失绝不误记为必填缺失，模板外键记入 unknown_keys。
    * 版式不因缺数据而破坏：称谓顶格、落款右对齐恒定成立。
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

PLACEHOLDER = "____"

# ---------------------------------------------------------------- 模板定义 --
# 字段声明：(字段名, 是否必填, 所在区块)
#   salutation 称谓区（顶格） / lead 引言 / body 正文条目 / sign 落款（右对齐）
#   contact    联系方式（并入落款区，右对齐；选填缺失整行省略）

TEMPLATES = {
    "请示函": {
        "doc_title": "请  示",
        "fields": [
            ("主送机关", True, "salutation"),
            ("请示事由", True, "lead"),
            ("请示缘由", True, "body"),
            ("请示事项", True, "body"),
            ("请示单位", True, "sign"),
            ("成文日期", False, "sign"),
            ("联系人", False, "contact"),
            ("联系电话", False, "contact"),
        ],
        "salutation_tpl": "{主送机关}：",
        "lead_tpl": "为{请示事由}，现将有关事项请示如下：",
        "body_items": [
            (False, "请示缘由：{请示缘由}"),
            (False, "请示事项：{请示事项}"),
        ],
    },
    "会议通知": {
        "doc_title": "会 议 通 知",
        "fields": [
            ("主送对象", False, "salutation"),
            ("会议名称", True, "body"),
            ("会议时间", True, "body"),
            ("会议地点", True, "body"),
            ("参会人员", True, "body"),
            ("会议议题", False, "body"),
            ("会议要求", False, "body"),
            ("召开单位", True, "sign"),
            ("发文日期", False, "sign"),
            ("联系人", False, "contact"),
            ("联系电话", False, "contact"),
        ],
        "salutation_tpl": "{主送对象}：",
        "lead_tpl": "现将有关事项通知如下：",
        "body_items": [
            (False, "会议名称：{会议名称}"),
            (False, "会议时间：{会议时间}"),
            (False, "会议地点：{会议地点}"),
            (False, "参会人员：{参会人员}"),
            (True, "会议议题：{会议议题}"),
            (True, "会议要求：{会议要求}"),
        ],
    },
}

TITLE_FONT = "方正小标宋简体"
BODY_FONT = "仿宋_GB2312"
CN_NUM = "一二三四五六七八九十"


# ------------------------------------------------------------ 缺失事实判定 --
def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


class FieldBook:
    """字段记账器：区分「键缺失」与「键存在但值为空」，两者都算缺失事实。"""

    def __init__(self, template, data):
        spec = TEMPLATES[template]
        self.template = template
        self.fields = {}
        self.filled = []
        self.missing_required = []
        self.missing_optional = []
        for name, required, section in spec["fields"]:
            present = name in data
            raw = data.get(name)
            filled = present and not _is_blank(raw)
            if filled:
                status = "filled"
            elif required:
                status = "missing_required"
            else:
                status = "missing_optional"
            rendered = str(raw).strip() if filled else (PLACEHOLDER if required else "")
            self.fields[name] = {
                "required": required,
                "section": section,
                "present": present,
                "value": str(raw).strip() if filled else None,
                "status": status,
                "rendered": rendered,
            }
            getattr(self, status).append(name)
        known = {name for name, _, _ in spec["fields"]}
        self.unknown_keys = [k for k in data if k not in known]
        self.unknown_key_details = [{"key": k, "value": data[k]} for k in self.unknown_keys]

    def render(self, name):
        """文档中该字段的取值：已填写真值，必填缺失给 ____，选填缺失给空串。"""
        return self.fields[name]["rendered"]

    def fill(self, template_str):
        """按模板串渲染：{字段名} 位置替换为 render() 的结果。"""
        out = template_str
        for name in self.fields:
            out = out.replace("{" + name + "}", self.render(name))
        return out


# ---------------------------------------------------------------- 版式工具 --
def _set_font(run, name, size_pt, bold=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def _add_par(doc, text, *, align=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=None,
             font=BODY_FONT, size=16, bold=False, space_after=0):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    par.alignment = align
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = Pt(30)
    if first_line_indent is not None:
        pf.first_line_indent = Pt(first_line_indent)
    _set_font(par.add_run(text), font, size, bold)
    return par


def build_docx(template, book, out_path):
    spec = TEMPLATES[template]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(3.7), Cm(3.5)
    sec.left_margin, sec.right_margin = Cm(2.8), Cm(2.6)

    # 标题：居中二号小标宋
    _add_par(doc, spec["doc_title"], align=WD_ALIGN_PARAGRAPH.CENTER,
             font=TITLE_FONT, size=22, space_after=12)

    # 称谓：顶格（无左缩进、无首行缩进）。必填缺失时以「字段名：____」显式点出缺失字段，
    # 选填缺失则整行省略——称谓行位置稳定，版式不因缺数据塌陷。
    sal_name = next(n for n, _, sec in spec["fields"] if sec == "salutation")
    sal_status = book.fields[sal_name]["status"]
    if sal_status == "missing_required":
        salutation = f"{sal_name}：{PLACEHOLDER}"
    elif sal_status == "missing_optional":
        salutation = ""
    else:
        salutation = book.fill(spec["salutation_tpl"])
    if salutation:
        _add_par(doc, salutation, align=WD_ALIGN_PARAGRAPH.LEFT, first_line_indent=0)

    # 引言：首行缩进两字
    _add_par(doc, book.fill(spec["lead_tpl"]), first_line_indent=Pt(32))

    # 正文条目：顺序编号；选填条目缺失则整条省略（不编造、不留空占位）
    idx = 0
    for optional, item_tpl in spec["body_items"]:
        field_name = item_tpl.split("{", 1)[1].split("}", 1)[0]
        if optional and book.fields[field_name]["status"] == "missing_optional":
            continue
        idx += 1
        _add_par(doc, f"{CN_NUM[idx - 1]}、" + book.fill(item_tpl),
                 first_line_indent=Pt(32))

    # 落款（含联系方式）：右对齐；选填缺失保留空行，落款版式不塌
    for name, required, section in spec["fields"]:
        if section not in ("sign", "contact"):
            continue
        if section == "contact" and book.fields[name]["status"] == "missing_optional":
            continue
        _add_par(doc, f"{name}：{book.render(name)}", align=WD_ALIGN_PARAGRAPH.RIGHT)

    doc.save(out_path)


# ------------------------------------------------------------- fields.json --
def build_fields_json(template, book, data_path):
    payload = {
        "template": template,
        "doc_title": TEMPLATES[template]["doc_title"],
        "source_data": data_path,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "placeholder": PLACEHOLDER,
        "policy": "缺失不编造：必填缺失以 ____ 占位渲染，选填缺失留空或省略，模板外键记入 unknown_keys",
        "fields": book.fields,
        "filled": book.filled,
        "missing_required": book.missing_required,
        "missing_optional": book.missing_optional,
        "unknown_keys": book.unknown_keys,
        "unknown_key_details": book.unknown_key_details,
        "counts": {
            "total_fields": len(book.fields),
            "filled": len(book.filled),
            "missing_required": len(book.missing_required),
            "missing_optional": len(book.missing_optional),
            "unknown_keys": len(book.unknown_keys),
        },
    }
    return payload


# ------------------------------------------------------------------ 主流程 --
def main(argv=None):
    ap = argparse.ArgumentParser(description="公文模板生成器（缺数据不编造、如实记账）")
    ap.add_argument("--template", required=True, choices=sorted(TEMPLATES))
    ap.add_argument("--data", required=True, help="数据 JSON 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.data):
        print(f"[error] 数据文件不存在: {args.data}", file=sys.stderr)
        return 2
    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)

    os.makedirs(args.outdir, exist_ok=True)
    book = FieldBook(args.template, data)

    docx_path = os.path.join(args.outdir, "文书.docx")
    fields_path = os.path.join(args.outdir, "fields.json")
    build_docx(args.template, book, docx_path)
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(build_fields_json(args.template, book, args.data),
                  fh, ensure_ascii=False, indent=2)

    print(f"[ok] {args.template} -> {args.outdir}")
    print(f"     产物: 文书.docx, fields.json")
    print(f"     已填 {len(book.filled)} / 必填缺失 {len(book.missing_required)} "
          f"{book.missing_required} / 选填缺失 {len(book.missing_optional)} "
          f"{book.missing_optional} / 模板外键 {len(book.unknown_keys)} {book.unknown_keys}")
    return 0


if __name__ == "__main__":
    sys.exit(main())