#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_doc.py —— 周报/工作总结 文书生成器（ab3-empty-and-string-lists 边界臂）。

命令行契约：
    python3 gen_doc.py --template <周报|工作总结> --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两份产物：
    文书.docx    渲染后的正式文书
    fields.json  字段级渲染语义记录

核心行为（与任务书一致）：
  * 空列表（必填）→ 按必填缺失处理：渲染占位条目「1．____」，fields.json 记占位语义；
  * 字符串型列表 → 单项化：渲染为单项条目，fields.json 中该字段值为单元素数组；
  * 选填小节缺失 → 正文整节省略（不出现该节头），fields.json 仍记 missing（required=false）；
  * 必填缺失/为空 → 以「____」占位（含标题，如「____工作周报」「____2026年9月工作总结」）；
  * 小节编号「一、二、三、」、条目编号「1．2．3．」（仅对实际渲染的小节连续编号）；
  * 落款右对齐，不因空日期/缺主体破坏。
"""

import argparse
import json
import os
import re
import sys


def _ensure_docx_runtime():
    """默认解释器缺 python-docx 时，自动切换到装有该库的解释器重跑。"""
    try:
        import docx  # noqa: F401
        return
    except ImportError:
        pass
    for cand in ("/usr/bin/python3",):
        if os.path.exists(cand):
            try:
                os.execv(cand, [cand, os.path.abspath(__file__)] + sys.argv[1:])
            except OSError:
                break
    sys.exit("python-docx 不可用：请使用装有 python-docx 的 Python 解释器运行本脚本。")


_ensure_docx_runtime()

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Pt, RGBColor, Twips  # noqa: E402

PLACEHOLDER = "____"
ITEM_DOT = "\uff0e"  # 全角句点「．」，条目编号「1．2．3．」

# 模板规格：列表小节 + 标题构成 + 落款构成。
#   required=True  的字段缺失/为空 → 以 ____ 占位；
#   required=False 的字段缺失/为空 → 整节（或落款行）省略，fields.json 仍记 missing。
SPEC = {
    "周报": {
        "title_parts": ["周期", "const:工作周报"],
        "list_sections": [
            {"field": "本周工作内容", "required": True},
            {"field": "下周工作计划", "required": True},
            {"field": "问题与需协调事项", "required": False},
        ],
        "signature": [
            {"field": "填报人", "label": "填报人", "required": True},
            {"field": "报送日期", "label": "报送日期", "required": True, "date": True},
        ],
    },
    "工作总结": {
        "title_parts": ["总结主体", "总结时段", "const:工作总结"],
        "list_sections": [
            {"field": "工作回顾", "required": True},
            {"field": "主要成绩", "required": True},
            {"field": "存在问题", "required": False},
            {"field": "下一步工作打算", "required": True},
        ],
        "signature": [
            {"field": "总结主体", "label": None, "required": True},
            {"field": "成文日期", "label": None, "required": False, "date": True},
        ],
    },
}


def cn_num(n):
    """1→一 … 连续小节编号用中文数字。"""
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + digits[n - 10]
    tens, ones = divmod(n, 10)
    return digits[tens] + "十" + (digits[ones] if ones else "")


def fmt_date(value):
    """「2026-09-28」→「2026年9月28日」；无法解析则原样返回。"""
    m = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", str(value))
    if m:
        y, mo, d = (int(g) for g in m.groups())
        return f"{y}年{mo}月{d}日"
    return str(value)


def is_absent(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def resolve_scalar(data, field, required):
    """标量字段：返回 (record, 展示文本 or None)。None 表示该渲染位置省略。"""
    raw = data.get(field)
    rec = {"required": required}
    if is_absent(raw):
        rec["status"] = "placeholder" if required else "missing"
        rec["input_type"] = "string" if isinstance(raw, str) else None
        rec["value"] = raw if raw is not None else None
        rec["rendered"] = PLACEHOLDER if required else None
        if required:
            kind = "空字符串" if isinstance(raw, str) else "缺失"
            rec["note"] = f"必填字段{kind}，以____占位"
        else:
            rec["note"] = "选填字段缺失，对应渲染位置省略"
        return rec, (PLACEHOLDER if required else None)
    rec["status"] = "present"
    rec["input_type"] = "string" if isinstance(raw, str) else type(raw).__name__
    rec["value"] = raw
    rec["rendered"] = fmt_date(raw) if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", str(raw)) else str(raw)
    return rec, rec["rendered"]


def resolve_list(data, field, required):
    """列表字段：返回 (record, 条目列表 or None)。None 表示整节省略。

    空列表（必填）→ 占位条目；字符串型列表 → 单项化（值为单元素数组）。
    """
    raw = data.get(field)
    rec = {"required": required}
    if raw is None:
        rec.update(status="missing", input_type=None, value=None)
        items = None
    elif isinstance(raw, str):
        rec.update(
            status="present",
            input_type="string",
            value=[raw],
            normalization="string_single_item_list",
            raw_input=raw,
            note="字符串型列表按单项化处理：渲染为单项条目，字段值为单元素数组",
        )
        items = [raw]
    elif isinstance(raw, list):
        rec.update(status="present", input_type="list", value=list(raw))
        items = list(raw)
    else:
        rec.update(
            status="present",
            input_type=type(raw).__name__,
            value=[str(raw)],
            normalization="scalar_single_item_list",
            raw_input=raw,
        )
        items = [str(raw)]

    if items:
        rec["rendered"] = [f"{i}{ITEM_DOT}{t}" for i, t in enumerate(items, 1)]
        return rec, items
    # 缺失或空列表
    if required:
        rec["status"] = "placeholder"
        rec["rendered"] = [f"1{ITEM_DOT}{PLACEHOLDER}"]
        kind = "空列表" if raw is not None else "缺失"
        rec["note"] = f"必填列表{kind}，按必填缺失处理：渲染占位条目「1{ITEM_DOT}{PLACEHOLDER}」"
        return rec, [PLACEHOLDER]
    rec["status"] = "missing"
    rec["rendered"] = None
    rec["note"] = "选填小节缺失/为空：正文整节省略（不出现该节头）"
    return rec, None


def build_plan(template, data):
    """把输入数据解析为渲染计划：标题、小节序列、落款行、字段记录。"""
    spec = SPEC[template]
    records = {}

    # 标题：各组成部分依次拼接，必填缺失以 ____ 占位
    title_parts = []
    for part in spec["title_parts"]:
        if part.startswith("const:"):
            title_parts.append(part[len("const:"):])
            continue
        rec, display = resolve_scalar(data, part, required=True)
        rec["render_in"] = "title"
        records[part] = rec
        title_parts.append(display)  # 必填缺失时 display 为 ____
    title = "".join(title_parts)

    # 小节：仅渲染出现的小节，连续编号「一、二、三、」
    sections = []           # 实际渲染 (heading, entries)
    sections_omitted = []   # 选填缺失整节省略
    for sec_spec in spec["list_sections"]:
        field = sec_spec["field"]
        rec, items = resolve_list(data, field, sec_spec["required"])
        records[field] = rec
        if items is None:
            sections_omitted.append(field)
        else:
            sections.append({"field": field, "heading": field, "entries": items})

    # 落款：右对齐；选填缺失行省略，必填缺失以 ____ 占位。
    # 同一字段可能既进标题又进落款（如 总结主体），只解析一次，render_in 记全部位置。
    sig_lines = []
    for sig_spec in spec["signature"]:
        field = sig_spec["field"]
        if field in records:
            rec = records[field]
            _, display = resolve_scalar(data, field, sig_spec["required"])
            rec["render_in"] = ["title", "signature"]
        else:
            rec, display = resolve_scalar(data, field, sig_spec["required"])
            records[field] = rec
            rec["render_in"] = "signature"
        if display is None:
            continue
        label = sig_spec.get("label")
        sig_lines.append(f"{label}：{display}" if label else display)

    return {
        "template": template,
        "title": title,
        "sections": sections,
        "sections_omitted": sections_omitted,
        "signature_lines": sig_lines,
        "records": records,
    }


# ---------------------------------------------------------------- docx 渲染

FONT_CN_BODY = "SimSun"
FONT_CN_HEAD = "SimHei"
FONT_ASCII = "Times New Roman"


def _set_run_font(run, east=FONT_CN_BODY, ascii_font=FONT_ASCII, size=12, bold=False):
    run.font.name = ascii_font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def render_docx(plan, path):
    doc = Document()

    # A4、正式文档页边距（上下 2.54cm，左 3.0cm，右 2.5cm）
    section = doc.sections[0]
    section.page_width = Twips(11906)
    section.page_height = Twips(16838)
    section.top_margin = Twips(1440)
    section.bottom_margin = Twips(1440)
    section.left_margin = Twips(1701)
    section.right_margin = Twips(1417)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_ASCII
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT_CN_BODY)
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.space_after = Pt(0)

    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT_ASCII
    h1.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT_CN_HEAD)
    h1.font.size = Pt(14)
    h1.font.bold = True
    h1.font.color.rgb = RGBColor(0, 0, 0)
    h1.paragraph_format.space_before = Pt(13)
    h1.paragraph_format.space_after = Pt(6)
    h1.paragraph_format.line_spacing = 1.3

    # 标题：居中、黑体二号加粗；大字号显式行距防裁切（22pt*23≈506tw → 26pt atLeast）
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_after = Pt(20)
    title_p.paragraph_format.line_spacing = Pt(26)
    _set_run_font(title_p.add_run(plan["title"]), east=FONT_CN_HEAD, size=22, bold=True)

    # 小节：「一、小节名」+ 条目「1．…」（两字符首行缩进）
    for idx, sec in enumerate(plan["sections"], 1):
        head_p = doc.add_paragraph(style="Heading 1")
        _set_run_font(head_p.add_run(f"{cn_num(idx)}、{sec['heading']}"),
                      east=FONT_CN_HEAD, size=14, bold=True)
        for num, item in enumerate(sec["entries"], 1):
            item_p = doc.add_paragraph()
            item_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            item_p.paragraph_format.first_line_indent = Pt(24)
            _set_run_font(item_p.add_run(f"{num}{ITEM_DOT}{item}"), size=12)

    # 落款：右对齐；首行留白用段前距而非空段落
    for i, line in enumerate(plan["signature_lines"]):
        sig_p = doc.add_paragraph()
        sig_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i == 0:
            sig_p.paragraph_format.space_before = Pt(24)
        _set_run_font(sig_p.add_run(line), size=12)

    props = doc.core_properties
    props.title = plan["title"]
    props.author = ""
    doc.save(path)


def write_fields_json(plan, data_path, path):
    payload = {
        "template": plan["template"],
        "data": data_path,
        "title": plan["title"],
        "sections_rendered": [
            f"{cn_num(i)}、{sec['heading']}" for i, sec in enumerate(plan["sections"], 1)
        ],
        "sections_omitted": plan["sections_omitted"],
        "fields": plan["records"],
        "signature": {
            "alignment": "right",
            "lines": plan["signature_lines"],
        },
        "artifacts": ["文书.docx", "fields.json"],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    parser = argparse.ArgumentParser(description="周报/工作总结 文书生成器")
    parser.add_argument("--template", required=True, choices=sorted(SPEC), help="模板名")
    parser.add_argument("--data", required=True, help="数据 json 路径")
    parser.add_argument("--outdir", required=True, help="输出目录")
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        sys.exit("数据 json 顶层必须是对象。")

    plan = build_plan(args.template, data)
    os.makedirs(args.outdir, exist_ok=True)
    docx_path = os.path.join(args.outdir, "文书.docx")
    fields_path = os.path.join(args.outdir, "fields.json")
    render_docx(plan, docx_path)
    write_fields_json(plan, args.data, fields_path)

    print(f"[{args.template}] 标题「{plan['title']}」")
    print(f"  渲染小节: {payload_names(plan)}")
    print(f"  省略小节: {plan['sections_omitted'] or '无'}")
    print(f"  落款(右对齐): {' / '.join(plan['signature_lines']) or '（空）'}")
    print(f"  产物: {docx_path} , {fields_path}")


def payload_names(plan):
    return [f"{cn_num(i)}、{sec['heading']}" for i, sec in enumerate(plan["sections"], 1)]


if __name__ == "__main__":
    main()
