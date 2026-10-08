#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SF-0008 office 臂（ab1-standard-four-templates）公文生成器。

命令行契约：
    gen_office.py --template <周报|请示函|会议通知|工作总结> --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两个产物：
    文书.docx   GB/T 9704 公文风格（A4 版面：上37/下35/左28/右26 mm，
                标题二号宋体居中，正文三号仿宋、固定行距、首行缩进两字，
                一级小标题黑体，落款右对齐，页码「— n —」）
    fields.json 顶层 title / fields（每字段：名称、是否必填、状态、值、渲染方式）
                / summary（filled/missing/total）

缺数据不编造：必填缺失以 ____ 占位，选填缺失留空或省略，fields.json 如实记账。
"""

import argparse
import json
import os
import sys

from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BLANK = "____"

# 各模板字段（名称, 是否必填），顺序与冻结输入键序一致
TEMPLATES = {
    "周报": [
        ("部门", True),
        ("填报人", True),
        ("周期", True),
        ("本周工作内容", True),
        ("下周工作计划", True),
        ("问题与需协调事项", True),
        ("报送日期", True),
    ],
    "请示函": [
        ("请示事由", True),
        ("主送机关", True),
        ("请示缘由", True),
        ("请示事项", True),
        ("请示单位", True),
        ("联系人", False),
        ("联系电话", False),
        ("成文日期", True),
    ],
    "会议通知": [
        ("会议名称", True),
        ("召开单位", True),
        ("主送对象", True),
        ("会议时间", True),
        ("会议地点", True),
        ("参会人员", True),
        ("会议议题", True),
        ("会议要求", False),
        ("联系人", False),
        ("联系电话", False),
        ("发文日期", True),
    ],
    "工作总结": [
        ("总结主体", True),
        ("总结时段", True),
        ("工作回顾", True),
        ("主要成绩", False),
        ("存在问题", False),
        ("下一步工作打算", True),
        ("成文日期", True),
    ],
}

CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]

# ---------------- docx 排版底层 ----------------

FS_BODY = 16    # 三号
FS_TITLE = 22   # 二号
LINE_BODY = 28.8  # 固定行距（版心 225mm / 22 行）


def style_run(run, east, size, bold=False, ascii_font="Times New Roman"):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)


def para(doc, text, *, east="仿宋", size=FS_BODY, bold=False, align=None,
         indent_chars=0, line=LINE_BODY, before=0.0, after=0.0, right_pt=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)   # 先建 w:spacing，再补固定行距属性
    pf.space_after = Pt(after)
    pPr = p._p.get_or_add_pPr()
    sp = pPr.find(qn("w:spacing"))
    if sp is None:
        sp = OxmlElement("w:spacing")
        pPr.append(sp)
    sp.set(qn("w:line"), str(int(round(line * 20))))
    sp.set(qn("w:lineRule"), "exact")
    if right_pt:
        pf.right_indent = Pt(right_pt)   # 建 w:ind（schema 次序在 spacing 后）
    if indent_chars:
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind")
            pPr.append(ind)
        ind.set(qn("w:firstLineChars"), str(int(indent_chars * 100)))
        ind.set(qn("w:firstLine"), str(int(size * 20 * indent_chars)))
    if align is not None:   # 最后设对齐，python-docx 按 schema 次序插入 w:jc
        pf.alignment = align
    if text:
        style_run(p.add_run(text), east, size, bold)
    return p


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)   # A4
    sec.top_margin, sec.bottom_margin = Mm(37), Mm(35)   # GB/T 9704 版心 225mm
    sec.left_margin, sec.right_margin = Mm(28), Mm(26)   # 版心宽 156mm
    # 页码：4号宋体「— n —」，右空一字（单面首页按奇数页居右）
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.right_indent = Pt(14)
    style_run(p.add_run("— "), "宋体", 14)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), r" PAGE \* MERGEFORMAT ")
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:eastAsia"), "宋体")
    rf.set(qn("w:ascii"), "Times New Roman")
    rf.set(qn("w:hAnsi"), "Times New Roman")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "28")
    rPr.append(rf)
    rPr.append(sz)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)
    style_run(p.add_run(" —"), "宋体", 14)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(FS_BODY)
    normal._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "仿宋")


# ---------------- 数据访问 ----------------

class View:
    """按模板规格读取数据；缺失即 missing，绝不编造。"""

    def __init__(self, data, spec, renders):
        self.data = data
        self.renders = renders
        self.spec = spec

    def get(self, name):
        v = self.data.get(name)
        if v is None or v == "" or v == []:
            return None
        return v

    def scalar(self, name):
        return self.get(name)

    def items(self, name):
        v = self.get(name)
        return list(v) if isinstance(v, list) else None

    def rec(self, name, s):
        self.renders[name] = s


def numbered_items(seq):
    return ["{}. {}".format(i, s) for i, s in enumerate(seq, 1)]


# ---------------- 段落块模型 ----------------
# (kind, text)：title/sub/flush/body/noline(通知条目)/heading/item/sign/date/
#               dateline(右对齐无右空)/contact/space

B = lambda kind, text="": (kind, text)


def compose(template, view):
    """返回 (title, blocks)。同时把每个字段的渲染方式记入 view.renders。"""
    g = view
    if template == "周报":
        dept = g.scalar("部门") or BLANK
        title = "{}工作周报".format(dept)
        g.rec("部门", "标题「{}」前缀呈现".format(title) if g.scalar("部门")
              else "标题以「____」占位（必填缺失）")
        blocks = [B("title", title)]
        period = g.scalar("周期")
        sub = "（{}）".format(period) if period else "（{}）".format(BLANK)
        blocks.append(B("sub", sub))
        g.rec("周期", "标题下居中副行「{}」".format(sub) if period
              else "标题下副行以「（____）」占位（必填缺失）")
        filler = g.scalar("填报人")
        blocks.append(B("body", "填报人：{}".format(filler or BLANK)))
        g.rec("填报人", "正文段「填报人：{}」".format(filler) if filler
              else "正文段「填报人：____」占位（必填缺失）")
        sec_no = 0
        for name in ("本周工作内容", "下周工作计划", "问题与需协调事项"):
            sec_no += 1
            blocks.append(B("heading", "{}、{}".format(CN_NUM[sec_no - 1], name)))
            items = g.items(name)
            if items:
                for it in numbered_items(items):
                    blocks.append(B("item", it))
                g.rec(name, "黑体段「{}、{}」引领，逐条编号列出（{} 条）"
                      .format(CN_NUM[sec_no - 1], name, len(items)))
            else:
                blocks.append(B("item", BLANK))
                g.rec(name, "黑体段「{}、{}」下以「____」占位（必填缺失）"
                      .format(CN_NUM[sec_no - 1], name))
        d = g.scalar("报送日期")
        blocks.append(B("dateline", "报送日期：{}".format(d or BLANK)))
        g.rec("报送日期", "文末右对齐段「报送日期：{}」".format(d) if d
              else "文末右对齐「报送日期：____」占位（必填缺失）")
        return title, blocks

    if template == "请示函":
        subj = g.scalar("请示事由")
        title = "关于{}的请示".format(subj if subj else BLANK)
        g.rec("请示事由", "标题「{}」呈现".format(title) if subj
              else "标题以「关于____的请示」占位（必填缺失）")
        blocks = [B("title", title)]
        msto = g.scalar("主送机关")
        blocks.append(B("flush", "{}：".format(msto if msto else BLANK)))
        g.rec("主送机关", "称谓行顶格「{}：」".format(msto) if msto
              else "称谓行顶格「____：」占位（必填缺失）")
        reason = g.scalar("请示缘由")
        blocks.append(B("body", reason or BLANK))
        g.rec("请示缘由", "正文首段原文呈现（首行缩进两字）" if reason
              else "正文首段以「____」占位（必填缺失）")
        matter = g.scalar("请示事项")
        blocks.append(B("body", "请示事项：{}".format(matter or BLANK)))
        g.rec("请示事项", "正文段「请示事项：{}」".format(matter) if matter
              else "正文段「请示事项：____」占位（必填缺失）")
        blocks.append(B("body", "妥否，请批示。"))
        unit = g.scalar("请示单位")
        blocks.append(B("sign", unit or BLANK))
        g.rec("请示单位", "落款右对齐「{}」".format(unit) if unit
              else "落款以「____」占位（必填缺失）")
        date = g.scalar("成文日期")
        blocks.append(B("date", date or BLANK))
        g.rec("成文日期", "落款右对齐「{}」（右空四字）".format(date) if date
              else "落款日期以「____」占位（必填缺失）")
        contact_line(g, blocks)
        return title, blocks

    if template == "会议通知":
        name_ = g.scalar("会议名称")
        title = "关于召开{}的通知".format(name_ if name_ else BLANK)
        g.rec("会议名称", "标题「{}」呈现".format(title) if name_
              else "标题以「关于召开____的通知」占位（必填缺失）")
        blocks = [B("title", title)]
        msto = g.scalar("主送对象")
        blocks.append(B("flush", "{}：".format(msto if msto else BLANK)))
        g.rec("主送对象", "称谓行顶格「{}：」".format(msto) if msto
              else "称谓行顶格「____：」占位（必填缺失）")
        blocks.append(B("body", "现将会议有关事项通知如下："))
        sec_no = 0
        for fname in ("会议时间", "会议地点", "参会人员", "会议议题"):
            sec_no += 1
            v = g.scalar(fname)
            blocks.append(B("noline", "{}、{}：{}".format(
                CN_NUM[sec_no - 1], fname, v if v else BLANK)))
            g.rec(fname, "正文条目「{}、{}：{}」".format(
                CN_NUM[sec_no - 1], fname, v) if v
                else "正文条目「{}、{}：____」占位（必填缺失）".format(CN_NUM[sec_no - 1], fname))
        req = g.items("会议要求")
        if req:
            sec_no += 1
            blocks.append(B("noline", "{}、会议要求".format(CN_NUM[sec_no - 1])))
            for it in numbered_items(req):
                blocks.append(B("item", it))
            g.rec("会议要求", "正文条目「{}、会议要求」引领，逐条编号列出（{} 条）"
                  .format(CN_NUM[sec_no - 1], len(req)))
        else:
            g.rec("会议要求", "选填缺失，未呈现（省略）")
        blocks.append(B("body", "特此通知。"))
        unit = g.scalar("召开单位")
        blocks.append(B("sign", unit or BLANK))
        g.rec("召开单位", "落款右对齐「{}」".format(unit) if unit
              else "落款以「____」占位（必填缺失）")
        date = g.scalar("发文日期")
        blocks.append(B("date", date or BLANK))
        g.rec("发文日期", "落款右对齐「{}」（右空四字）".format(date) if date
              else "落款日期以「____」占位（必填缺失）")
        contact_line(g, blocks)
        return title, blocks

    if template == "工作总结":
        org = g.scalar("总结主体")
        span = g.scalar("总结时段")
        title = "{}{}工作总结".format(org or BLANK, span or BLANK)
        g.rec("总结主体", "标题「{}」前缀呈现；落款右对齐「{}」".format(title, org)
              if org else "标题以「____」占位；落款「____」占位（必填缺失）")
        g.rec("总结时段", "标题「{}」中呈现".format(title) if span
              else "标题时段位以「____」占位（必填缺失）")
        blocks = [B("title", title)]
        sec_no = 0
        for fname, required in (("工作回顾", True), ("主要成绩", False),
                                ("存在问题", False), ("下一步工作打算", True)):
            items = g.items(fname)
            if not items:
                if required:
                    sec_no += 1
                    blocks.append(B("heading", "{}、{}".format(CN_NUM[sec_no - 1], fname)))
                    blocks.append(B("item", BLANK))
                    g.rec(fname, "黑体段「{}、{}」下以「____」占位（必填缺失）"
                          .format(CN_NUM[sec_no - 1], fname))
                else:
                    g.rec(fname, "选填缺失，未呈现（省略）")
                continue
            sec_no += 1
            blocks.append(B("heading", "{}、{}".format(CN_NUM[sec_no - 1], fname)))
            for it in numbered_items(items):
                blocks.append(B("item", it))
            g.rec(fname, "黑体段「{}、{}」引领，逐条编号列出（{} 条）"
                  .format(CN_NUM[sec_no - 1], fname, len(items)))
        unit = g.scalar("总结主体")
        blocks.append(B("sign", unit or BLANK))
        date = g.scalar("成文日期")
        blocks.append(B("date", date or BLANK))
        g.rec("成文日期", "落款右对齐「{}」（右空四字）".format(date) if date
              else "落款日期以「____」占位（必填缺失）")
        return title, blocks

    raise ValueError("unknown template: {}".format(template))


def contact_line(g, blocks):
    """文末联系行（选填：仅呈现已填项；两者皆缺则整行省略）。"""
    parts, names = [], []
    v = g.scalar("联系人")
    if v:
        parts.append("联系人：{}".format(v))
        names.append(("联系人", "联系人：{}".format(v)))
    v = g.scalar("联系电话")
    if v:
        parts.append("联系电话：{}".format(v))
        names.append(("联系电话", "联系电话：{}".format(v)))
    line = "（{}）".format("；".join(parts))
    for fname, frag in names:
        g.rec(fname, "文末联系行「{}」".format(line))
    for fname in ("联系人", "联系电话"):
        if fname not in g.renders:
            g.rec(fname, "选填缺失，未呈现（省略）")
    if parts:
        blocks.append(B("contact", line))


# ---------------- blocks -> docx ----------------

def emit(doc, title, blocks):
    unit = ""
    for kind, text in blocks:
        if kind in ("sign",):
            unit = text
    for kind, text in blocks:
        if kind == "title":
            para(doc, text, east="宋体", size=FS_TITLE, align=WD_ALIGN_PARAGRAPH.CENTER,
                 line=35.0, before=6.0, after=10.0)
        elif kind == "sub":
            para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, after=6.0)
        elif kind == "flush":
            para(doc, text)  # 称谓顶格
        elif kind == "body":
            para(doc, text, indent_chars=2)
        elif kind == "noline":
            para(doc, text, indent_chars=2)
        elif kind == "heading":
            para(doc, text, east="黑体", indent_chars=2)
        elif kind == "item":
            para(doc, text, indent_chars=2)
        elif kind == "sign":
            para(doc, text, align=WD_ALIGN_PARAGRAPH.RIGHT, right_pt=64.0, before=28.0)
        elif kind == "date":
            para(doc, text, align=WD_ALIGN_PARAGRAPH.RIGHT, right_pt=64.0)
        elif kind == "dateline":
            para(doc, text, align=WD_ALIGN_PARAGRAPH.RIGHT, before=28.0)
        elif kind == "contact":
            para(doc, text, indent_chars=2, before=14.0)
        elif kind == "space":
            para(doc, "")
    doc.core_properties.title = title
    doc.core_properties.author = unit or "公文生成"


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser(description="办公模板公文生成（GB/T 9704 风格）")
    ap.add_argument("--template", required=True,
                    choices=["周报", "请示函", "会议通知", "工作总结"])
    ap.add_argument("--data", required=True, help="数据 json 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    spec = list(TEMPLATES[args.template])
    known = {n for n, _ in spec}
    for k in data.keys():          # 计划外字段：如实并入（按选填正文附加呈现）
        if k not in known:
            spec.append((k, False))

    renders = {}
    view = View(data, spec, renders)
    title, blocks = compose(args.template, view)
    # 计划外字段（冻结输入中模板规格之外的键）：正文附加呈现，置于落款之前
    known = [n for n, _ in TEMPLATES[args.template]]
    extras = [n for n, _ in spec if n not in known]
    if extras:
        extra_blocks = []
        for n in extras:
            v = view.get(n)
            if isinstance(v, list):
                extra_blocks.append(B("heading", "附：{}".format(n)))
                for it in numbered_items(v):
                    extra_blocks.append(B("item", it))
                renders[n] = "黑体段「附：{}」引领，逐条编号列出（{} 条）".format(n, len(v))
            elif v is not None:
                extra_blocks.append(B("body", "{}：{}".format(n, v)))
                renders[n] = "正文段「{}：{}」".format(n, v)
            else:
                renders[n] = "计划外选填缺失，未呈现（省略）"
        idx = next((i for i, b in enumerate(blocks) if b[0] in ("sign", "dateline")), len(blocks))
        blocks = blocks[:idx] + extra_blocks + blocks[idx:]
    fields = []
    for name, required in spec:
        v = view.get(name)
        filled = v is not None
        fields.append({
            "name": name,
            "required": bool(required),
            "status": "filled" if filled else "missing",
            "value": v if filled else None,
            "render": renders.get(name, "选填缺失，未呈现（省略）"),
        })
    n_fill = sum(1 for f_ in fields if f_["status"] == "filled")
    summary = {"filled": n_fill, "missing": len(fields) - n_fill, "total": len(fields)}

    os.makedirs(args.outdir, exist_ok=True)
    doc = Document()
    setup_page(doc)
    emit(doc, title, blocks)
    docx_path = os.path.join(args.outdir, "文书.docx")
    doc.save(docx_path)

    fields_doc = {
        "title": title,
        "template": args.template,
        "data_source": args.data,
        "fields": fields,
        "summary": summary,
    }
    json_path = os.path.join(args.outdir, "fields.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(fields_doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("[{}] {} -> {}".format(args.template, args.data, args.outdir))
    print("  文书.docx | fields.json  filled={}/{} missing={}".format(
        n_fill, len(fields), len(fields) - n_fill))


if __name__ == "__main__":
    main()
