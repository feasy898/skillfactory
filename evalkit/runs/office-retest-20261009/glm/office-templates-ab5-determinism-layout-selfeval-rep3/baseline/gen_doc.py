#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会议文书生成器（确定性实现，零外部依赖引导）。

命令行契约:
    python3 gen_doc.py --template 会议通知 --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成恰两个产物:
    文书.docx    按指定模板渲染的公文（A4、公文页边距、三号仿宋正文）
    fields.json  字段清单

确定性保证（同输入 → 逐字节同输出）:
  * 不读系统时钟、不用随机源、无网络访问；文档全部内容由输入数据与
    固定版式常量决定；docProps 时间沿用 python-docx 模板内的固定值，
    不做任何改写。
  * docx 保存后对 ZIP 容器做一次规范化重写：条目顺序保持原序、
    date_time 统一为 1980-01-01 00:00:00、create_system/external_attr
    固定、压缩级别固定 9 —— 消除 zipfile.writestr 默认写入当前时间
    导致的逐字节漂移。
  * fields.json 仅含模板名、命令行所给数据源相对路径、两个产物文件名
    （不含绝对路径）与字段回显；固定键序、ensure_ascii=False、
    indent=2、结尾恰一个换行。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile


def _ensure_docx_module() -> None:
    """优先用系统 python-docx；缺失时回退到本目录 .venv 的 site-packages。"""
    try:
        import docx  # noqa: F401
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        site = os.path.join(here, ".venv", "lib",
                            "python%d.%d" % sys.version_info[:2],
                            "site-packages")
        if not os.path.isdir(site):
            raise
        sys.path.insert(0, site)
        import docx  # noqa: F401


_ensure_docx_module()

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

# ---------------------------------------------------------------- 版式常量
FONT_ASCII = "Times New Roman"
FONT_TITLE_EAST = "黑体"
FONT_BODY_EAST = "仿宋"
FONT_LABEL_EAST = "黑体"
SIZE_TITLE_PT = 22          # 二号
SIZE_BODY_PT = 16           # 三号
LINE_TITLE = Pt(36)         # 标题固定行距
LINE_BODY = Pt(28)          # 正文固定行距（公文惯例 28 磅）
INDENT_TWO_CHARS = Pt(32)   # 三号字两字符首行缩进
SPACE_AFTER_TITLE = Pt(24)

DOC_NAME = "文书.docx"
FIELDS_NAME = "fields.json"

# ZIP 规范化参数（消除 writestr 默认当前时间戳）
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
ZIP_COMPRESS_LEVEL = 9
ZIP_CREATE_SYSTEM = 3                       # unix
ZIP_EXTERNAL_ATTR = 0o100644 << 16          # 常规文件 0644


# ---------------------------------------------------------------- 通用工具
def _style_run(run, east: str, size_pt: float, bold: bool = False) -> None:
    run.font.name = FONT_ASCII
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rfonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), east)


def _para(doc, parts, *, align, line=LINE_BODY, first=None, left=None,
          before=Pt(0), after=Pt(0), keep_next=False):
    """新建段落；parts 为 [(文本, 东亚字体, 字号, 加粗), ...] 的混排描述。

    段前/段后默认显式 0（不继承 Normal 样式的 8pt 段后距），保证版式
    完全由本文件常量决定；keep_next 用于「标签不与首条目分页」等约束。
    """
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = before
    pf.space_after = after
    pf.keep_with_next = keep_next
    if first is not None:
        pf.first_line_indent = first
    if left is not None:
        pf.left_indent = left
    for text, east, size_pt, bold in parts:
        _style_run(p.add_run(text), east, size_pt, bold)
    return p


def normalize_docx_zip(path: str) -> None:
    """就地重写 docx 的 ZIP 容器，使逐字节输出可复现。"""
    with zipfile.ZipFile(path, "r") as zin:
        payload = [(info.filename, zin.read(info.filename))
                   for info in zin.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=ZIP_COMPRESS_LEVEL) as zout:
        for name, blob in payload:
            info = zipfile.ZipInfo(filename=name, date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = ZIP_CREATE_SYSTEM
            info.external_attr = ZIP_EXTERNAL_ATTR
            zout.writestr(info, blob)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


# ---------------------------------------------------------------- 会议通知模板
def build_meeting_notice(data: dict):
    """按「会议通知」模板用输入数据构建文档，返回 (Document, 派生信息)。"""
    get = lambda k: str(data.get(k, "") or "")
    name = get("会议名称")
    title = "关于召开%s的通知" % name if name else "会议通知"

    doc = Document()

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)   # A4 纵向
    sec.top_margin, sec.bottom_margin = Mm(37), Mm(35)   # 公文页边距
    sec.left_margin, sec.right_margin = Mm(28), Mm(26)

    cp = doc.core_properties
    cp.title = title
    cp.subject = "会议通知"
    cp.author = get("召开单位")
    cp.last_modified_by = get("召开单位")

    # 标题
    _para(doc, [(title, FONT_TITLE_EAST, SIZE_TITLE_PT, False)],
          align=WD_ALIGN_PARAGRAPH.CENTER, line=LINE_TITLE,
          after=SPACE_AFTER_TITLE)

    # 主送对象（顶格）
    _para(doc, [("%s：" % get("主送对象"), FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.LEFT)

    # 导语
    intro = ("为研究部署%s相关工作，经研究决定，于%s在%s召开%s，"
             "现将有关事项通知如下："
             % (get("会议议题"), get("会议时间"), get("会议地点"), name))
    _para(doc, [(intro, FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS)

    # 事项条目（标签黑体、内容仿宋）
    items = [
        ("一、会议时间：", get("会议时间")),
        ("二、会议地点：", get("会议地点")),
        ("三、参会人员：", get("参会人员")),
        ("四、会议议题：", get("会议议题")),
    ]
    for label, value in items:
        _para(doc, [(label, FONT_LABEL_EAST, SIZE_BODY_PT, False),
                    (value, FONT_BODY_EAST, SIZE_BODY_PT, False)],
              align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS)

    requirements = _as_list(data.get("会议要求"))
    _para(doc, [("五、会议要求：", FONT_LABEL_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS,
          keep_next=bool(requirements))
    for idx, req in enumerate(requirements, start=1):
        _para(doc, [("%d. %s" % (idx, req), FONT_BODY_EAST, SIZE_BODY_PT, False)],
              align=WD_ALIGN_PARAGRAPH.JUSTIFY, left=INDENT_TWO_CHARS)

    contact = "%s，联系电话：%s" % (get("联系人"), get("联系电话"))
    _para(doc, [("六、联系方式：", FONT_LABEL_EAST, SIZE_BODY_PT, False),
                (contact, FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS)

    # 结尾与落款
    closing = "请%s提前安排好工作，准时参加会议。" % get("主送对象")
    _para(doc, [(closing, FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS)
    _para(doc, [("特此通知。", FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=INDENT_TWO_CHARS)
    _para(doc, [(get("召开单位"), FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.RIGHT, keep_next=True)
    _para(doc, [(get("发文日期"), FONT_BODY_EAST, SIZE_BODY_PT, False)],
          align=WD_ALIGN_PARAGRAPH.RIGHT)

    derived = {
        "标题": title,
        "段落数": len(doc.paragraphs),
        "会议要求条目数": len(requirements),
    }
    return doc, derived


TEMPLATES = {
    "会议通知": build_meeting_notice,
}


# ---------------------------------------------------------------- 主流程
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="会议文书生成器（确定性实现：同输入产物逐字节一致）")
    ap.add_argument("--template", required=True, help="模板名，如 会议通知")
    ap.add_argument("--data", required=True, help="数据 json 文件路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args(argv)

    renderer = TEMPLATES.get(args.template)
    if renderer is None:
        ap.error("未知模板：%s（可用：%s）" % (args.template, "、".join(TEMPLATES)))

    with open(args.data, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    os.makedirs(args.outdir, exist_ok=True)

    doc, derived = renderer(data)
    docx_path = os.path.join(args.outdir, DOC_NAME)
    doc.save(docx_path)
    normalize_docx_zip(docx_path)

    manifest = {
        "template": args.template,
        "data_source": args.data,
        "outputs": {"docx": DOC_NAME, "fields": FIELDS_NAME},
        "fields": data,
        "derived": derived,
    }
    fields_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    with open(os.path.join(args.outdir, FIELDS_NAME), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(fields_text)

    print("已生成: %s" % os.path.join(args.outdir, DOC_NAME))
    print("已生成: %s" % os.path.join(args.outdir, FIELDS_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(main())
