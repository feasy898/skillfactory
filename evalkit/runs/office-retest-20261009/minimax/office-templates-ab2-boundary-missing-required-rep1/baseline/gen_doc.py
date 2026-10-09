#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板渲染器（缺数据不编造、如实记账）。

命令行契约：
    python3 gen_doc.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>

每次调用生成 文书.docx 与 fields.json，落到 <输出目录>/<模板>/<用例名>/ 下。

记账口径：
  * 必填字段缺失（键不存在，或值为空/纯空白）→ 文书中以 ____ 占位渲染，程序照常退出（退出码 0）；
  * 选填字段缺失 → 对应行整体省略，绝不冒充必填占位；
  * 模板外键 → 只记入 unknown_keys，不落进正文；
  * fields.json 的三张名单与输入数据的缺失事实一一对应，不多不少。
"""

import argparse
import json
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

PLACEHOLDER = "____"

# --------------------------------------------------------------------------
# 模板字段口径（必填 / 选填）
# --------------------------------------------------------------------------


class Spec(object):
    def __init__(self, name, required, optional):
        self.name = name
        self.required = list(required)
        self.optional = list(optional)
        self.all = self.required + self.optional


SPECS = {
    u"请示函": Spec(
        u"请示函",
        required=[u"主送机关", u"请示事由", u"请示缘由", u"请示事项", u"请示单位"],
        optional=[u"联系人", u"联系电话", u"成文日期"],
    ),
    u"会议通知": Spec(
        u"会议通知",
        required=[u"召开单位", u"主送对象", u"会议名称", u"会议时间", u"会议地点",
                  u"参会人员"],
        optional=[u"会议议题", u"会议要求", u"联系人", u"联系电话", u"发文日期"],
    ),
}

# 版式常量（公文常规）
FONT_TITLE = u"方正小标宋简体"
FONT_BODY = u"仿宋_GB2312"
SIZE_TITLE = Pt(22)
SIZE_BODY = Pt(16)
LINE_SPACING = Pt(30)


# --------------------------------------------------------------------------
# 数据读取与记账
# --------------------------------------------------------------------------


def _blank(value):
    return value is None or not str(value).strip()


def load_data(path):
    with open(path, "r") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(u"数据文件顶层必须是 JSON 对象：%s" % path)
    return data


def audit(data, spec):
    """把输入数据按模板口径分账：present / missing_required / missing_optional / unknown_keys。"""
    present, missing_required, missing_optional = [], [], []
    for field in spec.required:
        if _blank(data.get(field)):
            missing_required.append(
                {"field": field,
                 "reason": "key_absent" if field not in data else "empty_value"})
        else:
            present.append(field)
    for field in spec.optional:
        if _blank(data.get(field)):
            missing_optional.append(
                {"field": field,
                 "reason": "key_absent" if field not in data else "empty_value"})
        else:
            present.append(field)
    known = set(spec.all)
    unknown = [k for k in data.keys() if k not in known]  # 保持输入顺序
    return present, missing_required, missing_optional, unknown


def value_of(data, field, spec):
    """取渲染值：必填缺失→占位符；选填缺失→None（由调用方决定省略）。"""
    raw = data.get(field)
    if _blank(raw):
        return PLACEHOLDER if field in spec.required else None
    return str(raw).strip()


# --------------------------------------------------------------------------
# docx 版式工具
# --------------------------------------------------------------------------


def set_font(run, ascii_name, size, bold=False):
    run.font.size = size
    run.font.bold = bold
    run.font.name = ascii_name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), ascii_name)
    rfonts.set(qn("w:hAnsi"), ascii_name)
    rfonts.set(qn("w:eastAsia"), ascii_name)


def add_para(doc, text, align=WD_ALIGN_PARAGRAPH.LEFT, indent_chars=0,
             font=FONT_BODY, size=SIZE_BODY, bold=False):
    """写一段正文。indent_chars=2 表示首行缩进两字符，0 表示顶格。"""
    para = doc.add_paragraph()
    fmt = para.paragraph_format
    fmt.alignment = align
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = LINE_SPACING
    fmt.first_line_indent = Pt(size.pt * indent_chars)
    fmt.left_indent = Pt(0)
    run = para.add_run(text)
    set_font(run, font, size, bold)
    return para


def new_document():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(3.7)
    sec.bottom_margin = Cm(3.5)
    sec.left_margin = Cm(2.8)
    sec.right_margin = Cm(2.6)
    style = doc.styles["Normal"]
    style.font.size = SIZE_BODY
    style.font.name = FONT_BODY
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), FONT_BODY)
    rfonts.set(qn("w:hAnsi"), FONT_BODY)
    rfonts.set(qn("w:eastAsia"), FONT_BODY)
    return doc


def flush_signature(doc, lines):
    """落款：右对齐逐行排布（单位在上、日期在下）。"""
    for line in lines:
        if line:
            add_para(doc, line, align=WD_ALIGN_PARAGRAPH.RIGHT)


# --------------------------------------------------------------------------
# 两个模板的排版
# --------------------------------------------------------------------------


def build_qingshi(data, spec):
    """请示函：标题 / 顶格称谓 / 首行缩进正文 / 右对齐落款。"""
    doc = new_document()
    subject = value_of(data, u"请示事由", spec)          # 必填
    salutation = value_of(data, u"主送机关", spec)       # 必填（缺失即占位）
    reason = value_of(data, u"请示缘由", spec)           # 必填
    item = value_of(data, u"请示事项", spec)             # 必填（空串即占位）
    org = value_of(data, u"请示单位", spec)              # 必填
    contact = value_of(data, u"联系人", spec)            # 选填
    phone = value_of(data, u"联系电话", spec)            # 选填
    date = value_of(data, u"成文日期", spec)             # 选填

    add_para(doc, u"关于%s的请示" % subject,
             align=WD_ALIGN_PARAGRAPH.CENTER, font=FONT_TITLE,
             size=SIZE_TITLE, bold=True)
    add_para(doc, u"%s：" % salutation, indent_chars=0)   # 称谓顶格
    add_para(doc, u"我部就%s，%s" % (subject, reason), indent_chars=2)
    add_para(doc, u"我部拟%s，妥否，请批示。" % item, indent_chars=2)
    if contact:
        add_para(doc, u"联系人：%s" % contact, indent_chars=2)
    if phone:
        add_para(doc, u"联系电话：%s" % phone, indent_chars=2)

    sign = []
    if date:
        sign.append(date)          # 成文日期在单位之上（公文惯例）
    sign.append(org)
    flush_signature(doc, sign)
    return doc


def build_huitong(data, spec):
    """会议通知：标题 / 顶格称谓 / 首行缩进正文 / 右对齐落款。"""
    doc = new_document()
    org = value_of(data, u"召开单位", spec)              # 必填
    target = value_of(data, u"主送对象", spec)           # 必填
    name = value_of(data, u"会议名称", spec)             # 必填（键缺失即占位）
    when = value_of(data, u"会议时间", spec)             # 必填
    where = value_of(data, u"会议地点", spec)            # 必填（空串即占位）
    who = value_of(data, u"参会人员", spec)              # 必填
    topic = value_of(data, u"会议议题", spec)            # 选填
    req = value_of(data, u"会议要求", spec)              # 选填
    contact = value_of(data, u"联系人", spec)            # 选填
    phone = value_of(data, u"联系电话", spec)            # 选填
    date = value_of(data, u"发文日期", spec)             # 选填

    add_para(doc, u"关于%s的通知" % name,
             align=WD_ALIGN_PARAGRAPH.CENTER, font=FONT_TITLE,
             size=SIZE_TITLE, bold=True)
    add_para(doc, u"%s：" % target, indent_chars=0)       # 称谓顶格
    add_para(doc,
             u"%s定于%s在%s召开%s。" % (org, when, where, name),
             indent_chars=2)
    if topic:
        add_para(doc, u"会议议题：%s。" % topic, indent_chars=2)
    if who:
        add_para(doc, u"参会人员：%s。" % who, indent_chars=2)
    if req:
        add_para(doc, u"会议要求：%s。" % req, indent_chars=2)
    if contact:
        add_para(doc, u"联系人：%s。" % contact, indent_chars=2)
    if phone:
        add_para(doc, u"联系电话：%s。" % phone, indent_chars=2)

    sign = []
    if date:
        sign.append(date)
    sign.append(org)
    flush_signature(doc, sign)
    return doc


BUILDERS = {
    u"请示函": build_qingshi,
    u"会议通知": build_huitong,
}


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=u"按模板渲染公文，缺失必填以 ____ 占位并如实记账")
    parser.add_argument("--template", required=True, choices=sorted(SPECS.keys()))
    parser.add_argument("--data", required=True, help=u"数据 JSON 路径")
    parser.add_argument("--outdir", required=True, help=u"输出根目录")
    args = parser.parse_args(argv)

    spec = SPECS[args.template]
    data_path = os.path.abspath(args.data)
    case = os.path.splitext(os.path.basename(data_path))[0]
    data = load_data(data_path)

    present, missing_required, missing_optional, unknown = audit(data, spec)

    case_dir = os.path.join(args.outdir, args.template, case)
    if not os.path.isdir(case_dir):
        os.makedirs(case_dir)

    doc = BUILDERS[args.template](data, spec)
    doc_path = os.path.join(case_dir, u"文书.docx")
    doc.save(doc_path)

    record = {
        u"template": spec.name,
        u"case": case,
        u"data_file": data_path,
        u"artifacts": {
            u"document": os.path.abspath(doc_path),
            u"fields": os.path.abspath(os.path.join(case_dir, u"fields.json")),
        },
        u"placeholder": PLACEHOLDER,
        u"required_fields": spec.required,
        u"optional_fields": spec.optional,
        u"present_fields": present,
        u"missing_required": [item[u"field"] for item in missing_required],
        u"missing_optional": [item[u"field"] for item in missing_optional],
        u"unknown_keys": unknown,
        u"detail": {
            u"missing_required": missing_required,
            u"missing_optional": missing_optional,
            u"unknown_keys": [
                {"key": k, u"reason": u"not_in_template_schema"} for k in unknown],
        },
        u"policy": {
            u"missing_required": u"以 ____ 占位渲染，程序正常结束（退出码 0）",
            u"missing_optional": u"对应行整行省略，不冒充必填",
            u"unknown_keys": u"仅记账，不写入文书正文",
            u"no_fabrication": u"缺失内容不推测、不编造",
        },
    }
    with open(os.path.join(case_dir, u"fields.json"), "w") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write(u"\n")

    print(u"[%s/%s] 文书=%s" % (spec.name, case, doc_path))
    print(u"  missing_required=%s" % (record[u"missing_required"] or u"（无）"))
    print(u"  missing_optional=%s" % (record[u"missing_optional"] or u"（无）"))
    print(u"  unknown_keys=%s" % (record[u"unknown_keys"] or u"（无）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
