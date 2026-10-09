#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板生成入口。

用法:
    python3 gen_doc.py --template 周报 --data fixtures/周报/case1.json

产物: out/<模板名>/<数据文件名主干>/文书.docx 与 fields.json

行为约定:
    * 非法输入(模板名非法 / 数据文件不存在 / JSON 解析失败 / 顶层非对象)一律以退出码 2
      拒绝, 向 stderr 输出中文错误信息, 且不留下任何产物(不建输出目录、不写半成品)。
    * 必填字段缺失不算非法输入: 以「待定」占位继续生成。
    * 一切校验在创建输出目录之前完成, 文档先在内存中构建, 校验通过后才落盘。
"""

import argparse
import io
import json
import os
import sys

EXIT_INVALID_INPUT = 2

# 支持的模板集合(闭集)。--template 的取值不在此集合内即为非法输入。
TEMPLATES = ("周报", "请示函", "工作总结", "会议通知")

# 各模板的必填字段与展示形态: name -> (标题, 渲染方式, 版式标签)
#   render: "text"  单段文本; "list" 多条要点; "kv"   键值对行
PLACEHOLDER = "待定"

TEMPLATE_FIELDS = {
    "周报": {
        "文档标题": "周报",
        "fields": [
            ("部门", "text", "基本信息"),
            ("填报人", "text", "基本信息"),
            ("周期", "text", "基本信息"),
            ("本周工作内容", "list", "本周工作内容"),
            ("下周工作计划", "list", "下周工作计划"),
            ("问题与需协调事项", "list", "问题与需协调事项"),
            ("报送日期", "text", "落款"),
        ],
    },
    "请示函": {
        "文档标题": "请示函",
        "fields": [
            ("发文机关", "text", "抬头"),
            ("主送机关", "text", "抬头"),
            ("标题事由", "text", "事由"),
            ("请示事项", "list", "请示事项"),
            ("依据", "text", "说明"),
            ("联系人", "text", "落款"),
            ("联系电话", "text", "落款"),
            ("发文日期", "text", "落款"),
        ],
    },
    "工作总结": {
        "文档标题": "工作总结",
        "fields": [
            ("单位名称", "text", "抬头"),
            ("总结年度", "text", "抬头"),
            ("总体情况", "list", "总体情况"),
            ("主要做法与成效", "list", "主要做法与成效"),
            ("存在的问题", "list", "存在的问题"),
            ("下一步计划", "list", "下一步计划"),
            ("落款单位", "text", "落款"),
            ("落款日期", "text", "落款"),
        ],
    },
    "会议通知": {
        "文档标题": "会议通知",
        "fields": [
            ("发文单位", "text", "抬头"),
            ("会议名称", "text", "抬头"),
            ("会议时间", "text", "会议安排"),
            ("会议地点", "text", "会议安排"),
            ("参会人员", "list", "参会人员"),
            ("会议议程", "list", "会议议程"),
            ("联系人", "text", "联系方式"),
            ("联系电话", "text", "联系方式"),
        ],
    },
}


def fail(message):
    """拒绝: 中文错误信息写 stderr, 退出码 2。"""
    sys.stderr.write("错误：{}。已拒绝本次生成，未产生任何输出文件。\n".format(message))
    sys.stderr.flush()
    sys.exit(EXIT_INVALID_INPUT)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="gen_doc.py", description="公文模板生成入口", add_help=True
    )
    parser.add_argument("--template", required=True, help="模板名（取值范围：{}）".format("、".join(TEMPLATES)))
    parser.add_argument("--data", required=True, help="数据 JSON 文件路径")
    return parser.parse_args(argv)


def load_data(path):
    """校验并读取数据文件。任何不合法的输入都在此阶段终止。"""
    if not os.path.exists(path):
        fail("数据文件不存在：{}".format(path))
    if os.path.isdir(path):
        fail("数据路径不是文件而是一个目录：{}".format(path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        fail("数据文件无法读取：{}（{}）".format(path, exc))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("数据文件不是合法 JSON：{}（第 {} 行第 {} 列：{}）".format(
            path, exc.lineno, exc.colno, exc.msg))
    if not isinstance(data, dict):
        fail("数据文件 JSON 顶层必须是对象，实际为{}：{}".format(
            {"list": "数组", "str": "字符串", "int": "数字", "float": "数字",
             "bool": "布尔值", "None": "null"}.get(type(data).__name__,
                                                  type(data).__name__), path))
    return data


def normalize(value):
    """把字段值统一成渲染用的一行行文本。缺失或空值以「待定」占位。"""
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return items if items else [PLACEHOLDER]
    text = str(value).strip()
    return [text if text else PLACEHOLDER]


def resolve_fields(template, data):
    """按模板字段表取出值; 缺失的必填字段填「待定」而非报错。"""
    spec = TEMPLATE_FIELDS[template]
    resolved, missing = {}, []
    for name, render, section in spec["fields"]:
        if name in data and data[name] not in (None, "", [], {}):
            resolved[name] = normalize(data[name])
        else:
            resolved[name] = [PLACEHOLDER]
            missing.append(name)
    return resolved, missing


def build_docx_bytes(template, resolved):
    """在内存中构建 docx; 校验通过后才会落盘, 因此失败路径零残留。"""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Pt

    spec = TEMPLATE_FIELDS[template]
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(spec["文档标题"])
    run.bold = True
    run.font.size = Pt(20)
    run.font.name = "方正小标宋简体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "方正小标宋简体")

    last_section = None
    for name, render, section in spec["fields"]:
        if section != last_section:
            head = doc.add_paragraph()
            hrun = head.add_run(section)
            hrun.bold = True
            hrun.font.size = Pt(14)
            hrun.font.name = "黑体"
            hrun._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
            last_section = section

        lines = resolved[name]
        if render == "list":
            for line in lines:
                doc.add_paragraph("　　" + line)
        else:
            text = lines[0]
            p = doc.add_paragraph()
            if section == "落款":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.add_run("{}：{}".format(name, text))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # 校验 1: 模板名必须属于受支持集合。此处失败时输出目录尚未被触碰。
    if args.template not in TEMPLATES:
        fail("模板名非法：{}（可用模板：{}）".format(args.template, "、".join(TEMPLATES)))

    # 校验 2/3/4: 数据文件存在、JSON 可解析、顶层为对象。任一不满足即拒绝。
    data = load_data(args.data)

    resolved, missing = resolve_fields(args.template, data)
    docx_bytes = build_docx_bytes(args.template, resolved)

    case_name = os.path.splitext(os.path.basename(args.data))[0]
    out_dir = os.path.join("out", args.template, case_name)
    os.makedirs(out_dir, exist_ok=True)

    docx_path = os.path.join(out_dir, "文书.docx")
    fields_path = os.path.join(out_dir, "fields.json")

    with open(docx_path, "wb") as fh:
        fh.write(docx_bytes)
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump({
            "模板": args.template,
            "数据文件": args.data,
            "字段": {name: resolved[name] for name, *_ in TEMPLATE_FIELDS[args.template]["fields"]},
            "缺失字段": missing,
            "产物": ["文书.docx", "fields.json"],
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    sys.stdout.write("已生成：{}\n".format(docx_path))
    if missing:
        sys.stdout.write("提示：{} 个必填字段缺失，已以「{}」占位。\n".format(len(missing), PLACEHOLDER))
    return 0


if __name__ == "__main__":
    sys.exit(main())