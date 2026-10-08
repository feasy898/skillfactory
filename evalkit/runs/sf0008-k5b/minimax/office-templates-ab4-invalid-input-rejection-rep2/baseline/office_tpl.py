#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""office_tpl.py — 办公文书模板生成入口。

用法：
    python3 office_tpl.py --template 周报 --data fixtures/周报/case1.json \
                         --out out --case case1

产物：<out>/<模板名>/<case>/文书.docx 与 <out>/<模板名>/<case>/fields.json

退出码：
    0  生成成功
    2  非法输入被拒绝（模板名非法 / 数据文件不存在 / JSON 解析失败 / 顶层非对象）

行为约定：
    * 必填字段缺失不算非法输入，缺失字段以 ____ 占位并记入 fields.json 台账；
    * 非法输入必须在写出任何目录/文件之前被拒绝（零产物残留）。
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

EXIT_OK = 0
EXIT_INVALID_INPUT = 2

PLACEHOLDER = "____"

TEMPLATE_NAMES = ["周报", "请示函", "会议通知", "工作总结"]

# 各模板必填字段（缺失走占位，不算非法输入）
REQUIRED = {
    "周报": ["部门", "填报人", "周期", "本周工作内容", "下周工作计划", "问题与需协调事项", "报送日期"],
    "请示函": ["主送机关", "请示事项", "请示理由", "拟制文单位", "联系人", "联系电话", "成文日期", "附注"],
    "会议通知": ["会议名称", "会议时间", "会议地点", "主持人", "参会人员", "会议议题", "参会方式",
                 "请假方式", "联系人", "联系电话", "报送日期"],
    "工作总结": ["总结主体", "总结周期", "主要成绩", "存在问题", "下步打算", "成文日期"],
}


class InvalidInput(Exception):
    """非法输入。捕获后打印中文错误并以退出码 2 拒绝。"""


# ---------------------------------------------------------------- 字段取值

def field(data, name):
    """取字段值。返回 (展示值, 状态)：状态 ∈ {filled, missing, unknown}。"""
    if name not in data:
        return PLACEHOLDER, "missing"
    v = data[name]
    if v is None or v == "" or v == [] or v == {}:
        return PLACEHOLDER, "missing"
    if isinstance(v, (list, tuple)):
        return [("" if x is None else str(x)) for x in v], "filled"
    return str(v), "filled"


def items(v, empty=PLACEHOLDER):
    """把列表/标量渲染成条目行列表；列表按 1．2．3． 顺序编号。"""
    if isinstance(v, list):
        return ["%d．%s" % (i, x) for i, x in enumerate(v, 1)] or [empty]
    return ["1．%s" % v]


# ---------------------------------------------------------------- 文档骨架

def new_document():
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(16)
    st.element.rPr.rFonts.set(
        __import__("docx").oxml.ns.qn("w:eastAsia"), "仿宋_GB2312")
    return d


def add_title(doc, text):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.size = Pt(22)
    r.font.bold = True
    r.font.name = "Times New Roman"
    r._r.get_or_add_rPr().get_or_add_rFonts().set(
        __import__("docx").oxml.ns.qn("w:eastAsia"), "方正小标宋简体")
    return p


def add_heading(doc, text):
    from docx.shared import Pt
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(16)
    r.font.bold = True
    r._r.get_or_add_rPr().get_or_add_rFonts().set(
        __import__("docx").oxml.ns.qn("w:eastAsia"), "黑体")
    return p


def add_body(doc, text):
    """正文段：首行缩进 2 字符（w:firstLineChars=200）。"""
    from docx.shared import Pt
    from docx.oxml.ns import qn
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = Pt(28)
    p._p.get_or_add_pPr().append(
        _ind_el(qn("w:firstLineChars"), "200"))
    r = p.add_run(text)
    r.font.size = Pt(16)
    r.font.name = "Times New Roman"
    r._r.get_or_add_rPr().get_or_add_rFonts().set(
        qn("w:eastAsia"), "仿宋_GB2312")
    return p


def _ind_el(tag, val):
    from docx.oxml import OxmlElement
    el = OxmlElement("w:ind")
    el.set(tag, val)
    return el


def add_sign(doc, lines):
    """落款：右对齐，逐行。"""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    from docx.oxml.ns import qn
    out = []
    for text in lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run(text)
        r.font.size = Pt(16)
        r.font.name = "Times New Roman"
        r._r.get_or_add_rPr().get_or_add_rFonts().set(
            qn("w:eastAsia"), "仿宋_GB2312")
        out.append(p)
    return out


# ---------------------------------------------------------------- 模板渲染

def render_周报(doc, data):
    部门, _ = field(data, "部门")
    周期, _ = field(data, "周期")
    add_title(doc, "%s工作周报" % 部门)
    add_body(doc, "填报周期：%s。本周我部门围绕既定目标推进各项工作，"
                  "现将本周工作情况报告如下。" % 周期)
    add_heading(doc, "一、本周工作完成情况")
    w, _ = field(data, "本周工作内容")
    for line in items(w):
        add_body(doc, line)
    add_heading(doc, "二、下周工作计划")
    n, _ = field(data, "下周工作计划")
    for line in items(n):
        add_body(doc, line)
    add_heading(doc, "三、问题与需协调事项")
    i, _ = field(data, "问题与需协调事项")
    for line in items(i):
        add_body(doc, line)
    add_sign(doc, [field(data, "填报人")[0],
                   field(data, "部门")[0],
                   field(data, "报送日期")[0]])


def render_请示函(doc, data):
    主送, _ = field(data, "主送机关")
    add_title(doc, "请 示")
    add_sign(doc, ["%s：" % 主送])
    add_body(doc, "兹就有关事项请示如下，请予审示。")
    add_heading(doc, "一、请示事项")
    for line in items(field(data, "请示事项")[0]):
        add_body(doc, line)
    add_heading(doc, "二、请示理由")
    for line in items(field(data, "请示理由")[0]):
        add_body(doc, line)
    add_heading(doc, "三、拟制文单位")
    for line in items(field(data, "拟制文单位")[0]):
        add_body(doc, line)
    add_sign(doc, ["拟制文单位：%s" % ("、".join(field(data, "拟制文单位")[0])
                                   if isinstance(field(data, "拟制文单位")[0], list)
                                   else field(data, "拟制文单位")[0]),
                   "联系人：%s" % field(data, "联系人")[0],
                   "联系电话：%s" % field(data, "联系电话")[0],
                   field(data, "成文日期")[0]])
    if isinstance(field(data, "附注")[0], str):
        add_body(doc, "附注：%s" % field(data, "附注")[0])


def render_会议通知(doc, data):
    名称, _ = field(data, "会议名称")
    add_title(doc, "关于%s的通知" % 名称 if 名称 != PLACEHOLDER else "会议通知")
    add_body(doc, "各有关单位：现将会议有关事项通知如下，请遵照执行。")
    add_heading(doc, "一、会议名称")
    add_body(doc, "%s" % 名称)
    add_heading(doc, "二、会议时间")
    add_body(doc, "%s" % field(data, "会议时间")[0])
    add_heading(doc, "三、会议地点")
    add_body(doc, "%s" % field(data, "会议地点")[0])
    add_heading(doc, "四、主持人")
    add_body(doc, "%s" % field(data, "主持人")[0])
    add_heading(doc, "五、参会人员")
    for line in items(field(data, "参会人员")[0]):
        add_body(doc, line)
    add_heading(doc, "六、会议议题")
    for line in items(field(data, "会议议题")[0]):
        add_body(doc, line)
    add_heading(doc, "七、参会方式与请假方式")
    add_body(doc, "参会方式：%s。请假方式：%s。" % (
        field(data, "参会方式")[0], field(data, "请假方式")[0]))
    add_sign(doc, ["联系人：%s" % field(data, "联系人")[0],
                   "联系电话：%s" % field(data, "联系电话")[0],
                   field(data, "报送日期")[0]])


def render_工作总结(doc, data):
    主体, _ = field(data, "总结主体")
    周期, _ = field(data, "总结周期")
    add_title(doc, "%s%s工作总结" % (
        PLACEHOLDER if 主体 == PLACEHOLDER else "",
        周期 if 周期 != PLACEHOLDER else PLACEHOLDER))
    add_body(doc, "%s自 %s 以来，认真落实各项工作任务，"
                  "现将有关情况总结如下。" % (主体, 周期))
    add_heading(doc, "一、主要成绩")
    for line in items(field(data, "主要成绩")[0]):
        add_body(doc, line)
    add_heading(doc, "二、存在问题")
    for line in items(field(data, "存在问题")[0]):
        add_body(doc, line)
    add_heading(doc, "三、下步打算")
    for line in items(field(data, "下步打算")[0]):
        add_body(doc, line)
    add_sign(doc, [主体, field(data, "成文日期")[0]])


RENDER = {
    "周报": render_周报,
    "请示函": render_请示函,
    "会议通知": render_会议通知,
    "工作总结": render_工作总结,
}


# ---------------------------------------------------------------- 校验

def validate(template, data_path):
    """全部校验先于任何落盘动作。返回 (数据, 解析说明)。"""
    if template not in RENDER:
        raise InvalidInput(
            "模板名「%s」非法。可用模板：%s。"
            % (template, "、".join(TEMPLATE_NAMES)))
    if not os.path.isfile(data_path):
        raise InvalidInput("数据文件不存在：%s" % data_path)
    try:
        with open(data_path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        raise InvalidInput("数据文件无法读取：%s（%s）" % (data_path, exc))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInput(
            "数据文件不是合法 JSON：%s（%s 第 %d 行第 %d 列：%s）"
            % (data_path, data_path, exc.lineno, exc.colno, exc.msg))
    if not isinstance(data, dict):
        raise InvalidInput(
            "数据文件顶层必须是 JSON 对象，实际为%s：%s"
            % ("数组" if isinstance(data, list) else type(data).__name__, data_path))
    return data


def build_ledger(template, case, data_path, data):
    fields, filled, missing, unknown = [], [], [], []
    for name in REQUIRED[template]:
        v, st = field(data, name)
        if st == "filled":
            filled.append(name)
        else:
            missing.append(name)
        fields.append({"name": name, "status": st,
                       "value": None if st == "missing" else v})
    for name in data:
        if name not in REQUIRED[template]:
            unknown.append(name)
            fields.append({"name": name, "status": "unknown", "value": data[name]})
    return {"template": template, "case": case, "source": data_path,
            "required": REQUIRED[template],
            "fields": fields, "filled_fields": filled,
            "missing_fields": missing, "unknown_fields": unknown,
            "filled_count": len(filled), "missing_count": len(missing),
            "unknown_count": len(unknown)}


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="office_tpl.py", description="办公文书模板生成入口")
    ap.add_argument("--template", required=True, help="模板名：%s" % "、".join(TEMPLATE_NAMES))
    ap.add_argument("--data", required=True, help="数据 JSON 文件路径")
    ap.add_argument("--out", default="out", help="产物根目录（默认 out）")
    ap.add_argument("--case", default=None, help="单元名（默认取数据文件名）")
    args = ap.parse_args(argv)

    case = args.case or os.path.splitext(os.path.basename(args.data))[0]

    # —— 阶段一：校验（此段之前不触碰文件系统写入）——
    try:
        data = validate(args.template, args.data)
    except InvalidInput as exc:
        sys.stderr.write("错误：%s\n" % exc)
        sys.stderr.write("提示：请检查 --template 与 --data 参数；"
                         "必填字段缺失不属非法输入，将以 %s 占位。\n" % PLACEHOLDER)
        return EXIT_INVALID_INPUT

    # —— 阶段二：生成（先写临时目录，成功后整体落位）——
    unit_dir = os.path.join(args.out, args.template, case)
    parent = os.path.dirname(unit_dir)
    tmp_dir = None
    try:
        os.makedirs(parent, exist_ok=True)
        tmp_dir = tempfile.mkdtemp(prefix=".tmp-", dir=parent)
        doc = new_document()
        RENDER[args.template](doc, data)
        doc.save(os.path.join(tmp_dir, "文书.docx"))
        ledger = build_ledger(args.template, case, args.data, data)
        with open(os.path.join(tmp_dir, "fields.json"), "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
        if os.path.isdir(unit_dir):
            shutil.rmtree(unit_dir)
        os.replace(tmp_dir, unit_dir)
        tmp_dir = None
    except Exception as exc:  # 生成失败也不留半成品
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.stderr.write("错误：生成失败：%s\n" % exc)
        return EXIT_INVALID_INPUT

    sys.stdout.write("已生成：%s（已填 %d，缺失 %d，模板外 %d）\n" % (
        unit_dir, ledger["filled_count"], ledger["missing_count"],
        ledger["unknown_count"]))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
