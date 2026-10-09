#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""青蘅茶社会议通知生成器（GB/T 9704—2012 公文风格，A4 版面）。

用法：
    python3 gen_doc.py --data qingheng_teahui.json --outdir out

在 outdir 下生成两个产物：
    文书.docx   —— 正式会议通知（A4；上37/下35/左28/右26mm 版心；
                   2号小标宋标题、3号仿宋正文、黑体条目标签、固定28磅行距）
    fields.json —— 字段记账（template / title / fields / summary）

缺数据不编造：必填缺失以 ____ 占位；选填缺失省略条目；fields.json 如实记账。
"""

import argparse
import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

# ---------- GB/T 9704—2012 常量 ----------
F_XBS = "华文小标宋"      # 标题：2号小标宋（缺字体环境回退宋体加粗）
F_FS = "仿宋"             # 正文：3号仿宋
F_HEI = "黑体"            # 一级条目标签：3号黑体
F_ASCII = "Times New Roman"  # 西文/数字

SZ_TITLE = Pt(22)   # 2号
SZ_BODY = Pt(16)    # 3号
SZ_PAGE = Pt(14)    # 4号（页码）
LINE_BODY = Pt(28)  # 固定28磅行距
INDENT2 = Pt(32)    # 首行缩进两字（3号字）

REQUIRED = {"会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "会议议题", "发文日期"}


def clean(v):
    """去除首尾空白（含全角空格）；None 安全。"""
    if v is None:
        return None
    return str(v).strip(" \u3000\t\r\n")


def set_run(run, east, size=SZ_BODY, bold=False, ascii_font=F_ASCII):
    run.font.name = ascii_font
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), east)
    return run


def para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_indent=None, before=0, after=0,
         line=LINE_BODY, rule=WD_LINE_SPACING.EXACTLY, right_indent=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    p.alignment = align
    if first_indent is not None:
        pf.first_line_indent = first_indent
    if right_indent is not None:
        pf.right_indent = right_indent
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.line_spacing_rule = rule
    return p


def add_page_number_footer(section):
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run("— ")
    set_run(r1, F_FS, size=SZ_PAGE)
    r2 = fp.add_run()
    set_run(r2, F_FS, size=SZ_PAGE)
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    r2._element.append(fld)
    r3 = fp.add_run()
    set_run(r3, F_FS, size=SZ_PAGE)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    r3._element.append(instr)
    r4 = fp.add_run()
    set_run(r4, F_FS, size=SZ_PAGE)
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r4._element.append(fld2)
    r5 = fp.add_run(" —")
    set_run(r5, F_FS, size=SZ_PAGE)


def build_docx(data, outdir):
    doc = Document()

    # 版面：A4，GB/T 9704—2012 页边距（上37/下35/左28/右26 mm）
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Pt(595.3), Pt(841.9)  # 210×297mm
    sec.top_margin, sec.bottom_margin = Pt(104.9), Pt(99.2)  # 37/35mm
    sec.left_margin, sec.right_margin = Pt(79.4), Pt(73.7)   # 28/26mm
    add_page_number_footer(sec)

    # 默认样式兜底
    normal = doc.styles["Normal"]
    normal.font.name = F_ASCII
    normal.font.size = SZ_BODY
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), F_FS)

    g = {k: clean(data.get(k)) for k in (
        "会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
        "参会人员", "会议议题", "联系人", "联系电话", "发文日期")}
    reqs = data.get("会议要求") or []

    title = "{单位}关于召开{会议}的通知".format(
        单位=g["召开单位"] or "____", 会议=g["会议名称"] or "____")

    # 标题（2号小标宋，居中）
    p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=14,
             line=Pt(33), rule=WD_LINE_SPACING.AT_LEAST)
    set_run(p.add_run(title), F_XBS, size=SZ_TITLE, bold=True, ascii_font=F_XBS)

    # 主送对象（顶格，全角冒号）
    p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT)
    set_run(p.add_run((g["主送对象"] or "____") + "："), F_FS)

    # 导语（事实全部来自数据，不添加额外情节）
    lead = "兹定于{时间}在{地点}召开{会议}，现将有关事项通知如下：".format(
        时间=g["会议时间"] or "____", 地点=g["会议地点"] or "____",
        会议=g["会议名称"] or "____")
    p = para(doc, first_indent=INDENT2)
    set_run(p.add_run(lead), F_FS)

    # 正文条目（黑体标签＋仿宋值），序号按实际条目顺排
    seq = "一二三四五六七八九十"
    counter = [0]

    def item(label, value):
        counter[0] += 1
        no = seq[counter[0] - 1] if counter[0] <= 10 else str(counter[0])
        p = para(doc, first_indent=INDENT2)
        set_run(p.add_run("{}、{}：".format(no, label)), F_HEI, bold=True)
        set_run(p.add_run(value), F_FS)

    item("会议时间", g["会议时间"] or "____")
    item("会议地点", g["会议地点"] or "____")
    if g["参会人员"]:
        item("参会人员", g["参会人员"])
    if g["会议议题"]:
        item("会议议题", g["会议议题"])

    if reqs:
        counter[0] += 1
        no = seq[counter[0] - 1] if counter[0] <= 10 else str(counter[0])
        p = para(doc, first_indent=INDENT2)
        set_run(p.add_run("{}、会议要求：".format(no)), F_HEI, bold=True)
        for i, r in enumerate(reqs):
            end = "。" if i == len(reqs) - 1 else "；"
            mark = "（" + (seq[i] if i < 10 else str(i + 1)) + "）"
            p = para(doc, first_indent=INDENT2)
            set_run(p.add_run(mark + r + end), F_FS)

    if g["联系人"]:
        item("联系人", g["联系人"])
    if g["联系电话"]:
        item("联系电话", g["联系电话"])

    # 结语
    p = para(doc, first_indent=INDENT2)
    set_run(p.add_run("特此通知。"), F_FS)

    # 落款：署名居中于成文日期之上，日期右空四字；署名与日期同页绑定
    unit = g["召开单位"] or "____"
    date = g["发文日期"] or "____"
    p = para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT, before=28, right_indent=Pt(84))
    p.paragraph_format.keep_with_next = True
    set_run(p.add_run(unit), F_FS)
    p = para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT, right_indent=Pt(64))
    set_run(p.add_run(date), F_FS)

    doc.core_properties.title = title
    path = os.path.join(outdir, "文书.docx")
    doc.save(path)
    return path, title


def build_fields(data, title):
    g = {k: clean(data.get(k)) for k in (
        "会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
        "参会人员", "会议议题", "联系人", "联系电话", "发文日期")}
    reqs = [clean(r) for r in (data.get("会议要求") or []) if clean(r)]

    def rec(name, value, render):
        filled = value is not None and value != "" and value != []
        return {
            "名称": name,
            "是否必填": name in REQUIRED,
            "状态": "filled" if filled else ("missing_placeholder" if name in REQUIRED else "omitted"),
            "值": value if filled else ("____" if name in REQUIRED else None),
            "渲染方式": render if filled else (
                "必填缺失：以____占位（标题/主送/导语/条目/落款相应位置）" if name in REQUIRED
                else "选填缺失：未渲染相应条目"),
        }

    fields = [
        rec("会议名称", g["会议名称"],
            "标题「{召开单位}关于召开{会议名称}的通知」＋正文导语「召开……」点名"),
        rec("召开单位", g["召开单位"],
            "标题组成部分＋文末落款署名（居中于发文日期之上）"),
        rec("主送对象", g["主送对象"],
            "版心首行顶格主送（后加全角冒号）"),
        rec("会议时间", g["会议时间"],
            "正文条目「一、会议时间：…」＋导语点名（黑体标签＋仿宋值）"),
        rec("会议地点", g["会议地点"],
            "正文条目「二、会议地点：…」＋导语点名（黑体标签＋仿宋值）"),
        rec("参会人员", g["参会人员"],
            "正文条目「三、参会人员：…」（黑体标签＋仿宋值）"),
        rec("会议议题", g["会议议题"],
            "正文条目「四、会议议题：…」（黑体标签＋仿宋值）；"
            "源数据首尾各含一个半角空格，已按公文排版规范剔除后渲染，值记剔除后文本"),
        rec("会议要求", reqs,
            "正文条目「五、会议要求：」下（一）—（六）逐条列出（仿宋；"
            "条目原文末尾无标点，公文列表按规范依次补「；」，末条补「。」）"),
        rec("联系人", g["联系人"],
            "正文条目「六、联系人：…」（黑体标签＋仿宋值）"),
        rec("联系电话", g["联系电话"],
            "正文条目「七、联系电话：…」（黑体标签＋仿宋值，数字以 Times New Roman 呈现）"),
        rec("发文日期", g["发文日期"],
            "文末落款日期行（右空四字；依 GB/T 9704—2012 采用阿拉伯数字成文日期，与源数据一致）"),
    ]
    filled = sum(1 for f in fields if f["状态"] == "filled")
    return {
        "template": "会议通知",
        "title": title,
        "fields": fields,
        "summary": {"filled": filled, "missing": len(fields) - filled, "total": len(fields)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="qingheng_teahui.json")
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(args.outdir, exist_ok=True)

    path, title = build_docx(data, args.outdir)
    fields = build_fields(data, title)
    fpath = os.path.join(args.outdir, "fields.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("OK 文书:", path)
    print("OK 记账:", fpath, fields["summary"])


if __name__ == "__main__":
    main()
