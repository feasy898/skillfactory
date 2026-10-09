#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文生成器（GB/T 9704-2012 风格，A4 版面）。

命令行契约：
    python3 gen_doc.py --template <周报|请示函|会议通知|工作总结> \
                       --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两个产物：
    文书.docx   —— GB/T 9704 风格公文（A4，3号仿宋正文，2号小标宋标题）
    fields.json —— 字段记账（title / fields / summary）

缺数据不编造：必填缺失以 ____ 占位；选填缺失留空或省略；fields.json 如实记账。
"""

import argparse
import json
import os
import re
import sys
import unicodedata

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

# ---------- GB/T 9704-2012 常量 ----------
FANGSONG = "仿宋_GB2312"        # 正文：3号仿宋
XIAOBIAOSONG = "方正小标宋简体"  # 标题：2号小标宋
HEITI = "黑体"                  # 一级标题：3号黑体
SONG = "宋体"                   # 页码：4号宋体
ASCII_FONT = "Times New Roman"  # 数字/字母

SIZE_BODY = 16    # 3号
SIZE_TITLE = 22   # 2号
SIZE_PAGE = 14    # 4号
LINE_PITCH = 28.95           # 每页22行：225mm / 22 ≈ 28.95pt
LINE_PITCH_TWENTIETHS = 579  # 28.95pt 的 1/20 pt 值（docGrid linePitch）
MARGIN_TOP, MARGIN_BOTTOM, MARGIN_LEFT, MARGIN_RIGHT = 37, 35, 28, 26  # mm
BODY_WIDTH_PT = 442.2        # 版心宽 156mm（210-28-26）
DATE_RIGHT_BLANK = 64        # 成文日期右空四字：4 × 16pt

CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def cn_no(i):
    """1 -> 一，12 -> 十二"""
    if i <= 10:
        return CN_NUM[i - 1]
    if i < 20:
        return "十" + CN_NUM[i - 11]
    return str(i)


def text_width_pt(text, size):
    """按全角=size、半角=size/2 估算串宽（用于落款居中估算）。"""
    w = 0.0
    for ch in text:
        w += size if unicodedata.east_asian_width(ch) in ("F", "W") else size / 2
    return w


# 标题回行不可拆散的文种词（词意完整）
GENRE_WORDS = {"请示函", "请示", "通知", "总结", "周报", "报告", "批复", "意见", "纪要", "函"}
# 不可居行首的字符
NO_LINE_START = set("，。；：、）】》”!?%,.;:)]}")


def wrap_title(text, size, max_w):
    """标题回行：GB/T 9704 要求词意完整、上长下短（梯形/菱形）。
    超出版心宽时在允许断点中选行宽最均衡的方案；文种词不拆、
    行首不出「的」等虚词与标点。"""
    if text_width_pt(text, size) <= max_w:
        return [text]
    units = re.findall(r"[0-9A-Za-z]+|.", text, re.S)
    n = len(units)
    best = None  # (rank 元组, i)
    for i in range(1, n):
        head, tail = units[:i], units[i:]
        if not head or not tail:
            continue
        first = tail[0]
        if first in NO_LINE_START or first in ("的", "了", "等"):
            continue
        last = head[-1]
        if last + first in GENRE_WORDS and len(last + first) in (2, 3):
            continue  # 文种词不跨行拆散
        w1 = text_width_pt("".join(head), size)
        w2 = text_width_pt("".join(tail), size)
        if w1 > max_w:
            continue
        # 断点类别：词边界（空格邻接/拉丁数字边界）优先，其次行宽均衡，再次靠后断
        boundary = (last.strip() == "" or first.strip() == ""
                    or (first[0].isascii() and first[0].isalnum()))
        penalty = size * 0.55 if first.strip() == "" else 0.0  # 行首不留空格
        rank = (1 if boundary else 0, round(min(w1, w2) - penalty, 2), round(w1, 2))
        if best is None or rank > best[0]:
            best = (rank, i)
    if best is None:  # 找不到合规断点：交由渲染器自动回行
        return [text]
    i = best[1]
    return ["".join(units[:i]), "".join(units[i:])]


# ---------- docx 底层 helpers ----------

def _run(par, text, cjk, size, ascii_font=ASCII_FONT):
    run = par.add_run(text)
    run.font.name = ascii_font
    run.font.size = Pt(size)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), cjk)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    return run


def _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=LINE_PITCH,
          first_line_chars=0, left_chars=0, right_indent_pt=0.0,
          space_before=0, space_after=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.line_spacing = Pt(line)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    ind_attrs = {}
    if first_line_chars:
        ind_attrs["firstLineChars"] = str(first_line_chars * 100)
        ind_attrs["firstLine"] = str(int(first_line_chars * SIZE_BODY * 20))
    if left_chars:
        ind_attrs["leftChars"] = str(left_chars * 100)
        ind_attrs["left"] = str(int(left_chars * SIZE_BODY * 20))
    if right_indent_pt:
        pf.right_indent = Pt(right_indent_pt)
    if ind_attrs:
        pPr = p._p.get_or_add_pPr()
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind")
            pPr.append(ind)
        for k, v in ind_attrs.items():
            ind.set(qn("w:" + k), v)
    return p


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)  # A4
    sec.top_margin, sec.bottom_margin = Mm(MARGIN_TOP), Mm(MARGIN_BOTTOM)
    sec.left_margin, sec.right_margin = Mm(MARGIN_LEFT), Mm(MARGIN_RIGHT)
    sec.footer_distance = Mm(23)
    # 版式网格：每页22行
    sectPr = sec._sectPr
    grid = sectPr.find(qn("w:docGrid"))
    if grid is None:
        grid = OxmlElement("w:docGrid")
        sectPr.append(grid)
    grid.set(qn("w:type"), "lines")
    grid.set(qn("w:linePitch"), str(LINE_PITCH_TWENTIETHS))


def add_page_number(doc):
    """页码：4号宋体「— n —」，单页码居右。"""
    footer = doc.sections[0].footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(p, "— ", SONG, SIZE_PAGE)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), " PAGE \\* MERGEFORMAT ")
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:eastAsia"), SONG)
    rf.set(qn("w:ascii"), ASCII_FONT)
    rf.set(qn("w:hAnsi"), ASCII_FONT)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(SIZE_PAGE * 2))
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), str(SIZE_PAGE * 2))
    rPr.append(rf)
    rPr.append(sz)
    rPr.append(szCs)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(rPr)
    r.append(t)
    fld.append(r)
    p._p.append(fld)
    _run(p, " —", SONG, SIZE_PAGE)


# ---------- 公文构件 ----------

def add_title(doc, text, subtitle=None):
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, line=33,
              space_after=LINE_PITCH if subtitle is None else 0)
    lines = wrap_title(text, SIZE_TITLE, BODY_WIDTH_PT)
    run = _run(p, lines[0], XIAOBIAOSONG, SIZE_TITLE, ascii_font=XIAOBIAOSONG)
    for ln in lines[1:]:
        run.add_break()
        run.add_text(ln)
    if subtitle is not None:
        ps = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER,
                   space_after=LINE_PITCH)
        _run(ps, subtitle, FANGSONG, SIZE_BODY)


def add_master(doc, text):
    """主送机关：顶格，后加全角冒号。"""
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT)
    _run(p, text + "：", FANGSONG, SIZE_BODY)


def add_body(doc, text):
    p = _para(doc, first_line_chars=2)
    _run(p, text, FANGSONG, SIZE_BODY)
    return p


def add_heading(doc, text):
    """一级标题：3号黑体，首行缩进二字。"""
    p = _para(doc, first_line_chars=2)
    _run(p, text, HEITI, SIZE_BODY, ascii_font=HEITI)
    return p


def add_label_item(doc, label, value):
    """条目行：黑体标签「一、××」＋仿宋值「：…」。"""
    p = _para(doc, first_line_chars=2)
    _run(p, label, HEITI, SIZE_BODY, ascii_font=HEITI)
    _run(p, "：" + value, FANGSONG, SIZE_BODY)
    return p


def add_list(doc, items):
    """条目列表：1. 2. 3. …（3号仿宋，首行缩进二字）。"""
    for i, it in enumerate(items, 1):
        add_body(doc, "%d. %s" % (i, it))


def add_signature_block(doc, sig_text, date_text):
    """落款：署名居中于成文日期之上；成文日期右空四字。"""
    _para(doc)  # 正文后空一行
    dw = text_width_pt(date_text, SIZE_BODY)
    sw = text_width_pt(sig_text, SIZE_BODY)
    sig_right = max(DATE_RIGHT_BLANK + (dw - sw) / 2.0, 8.0)
    p1 = _para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT,
               right_indent_pt=sig_right)
    _run(p1, sig_text, FANGSONG, SIZE_BODY)
    p2 = _para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT,
               right_indent_pt=DATE_RIGHT_BLANK)
    _run(p2, date_text, FANGSONG, SIZE_BODY)


def add_note(doc, text):
    """附注：成文日期下一行，左空二字，加圆括号。"""
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, left_chars=2)
    _run(p, "（" + text + "）", FANGSONG, SIZE_BODY)


# ---------- 字段记账 ----------

FILLED, PLACEHOLDER, OMITTED = "filled", "placeholder", "omitted"

SCHEMA = {
    "周报": {
        "required": {"部门", "填报人", "周期", "本周工作内容", "下周工作计划", "报送日期"},
        "desc": {
            "部门": "标题「{部门}工作周报」",
            "填报人": "文末落款署名（居中于报送日期之上）",
            "周期": "标题下居中副题行「（{周期}）」",
            "本周工作内容": "一级标题「本周工作内容」＋条目列表（1. 2. …）",
            "下周工作计划": "一级标题「下周工作计划」＋条目列表（1. 2. …）",
            "问题与需协调事项": "一级标题「问题与需协调事项」＋条目列表（1. 2. …）",
            "报送日期": "文末落款日期行（右空四字）",
        },
    },
    "请示函": {
        "required": {"请示事由", "主送机关", "请示缘由", "请示事项", "请示单位", "成文日期"},
        "desc": {
            "请示事由": "标题「{请示单位}关于{请示事由}的请示」",
            "主送机关": "版心首行顶格主送（后加全角冒号）",
            "请示缘由": "正文首段（首行缩进二字）",
            "请示事项": "正文段落（首行缩进二字）",
            "请示单位": "标题组成＋文末落款署名（居中于成文日期之上）",
            "联系人": "成文日期下附注行（左空二字加圆括号）",
            "联系电话": "成文日期下附注行（左空二字加圆括号）",
            "成文日期": "文末落款日期行（右空四字）",
        },
    },
    "会议通知": {
        "required": {"会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
                     "会议议题", "发文日期"},
        "desc": {
            "会议名称": "标题「{召开单位}关于召开{会议名称}的通知」＋正文导语",
            "召开单位": "标题组成＋文末落款署名（居中于发文日期之上）",
            "主送对象": "版心首行顶格主送（后加全角冒号）",
            "会议时间": "正文条目「一、会议时间：…」（序号顺排，黑体标签＋仿宋值）",
            "会议地点": "正文条目「会议地点：…」（序号顺排，黑体标签＋仿宋值）",
            "参会人员": "正文条目「参会人员：…」（序号顺排，黑体标签＋仿宋值）",
            "会议议题": "正文条目「会议议题：…」（序号顺排，黑体标签＋仿宋值）",
            "会议要求": "正文条目「会议要求」（列表值逐条 1. 2. …）",
            "联系人": "正文条目「联系人：…」（序号顺排，黑体标签＋仿宋值）",
            "联系电话": "正文条目「联系电话：…」（序号顺排，黑体标签＋仿宋值）",
            "发文日期": "文末落款日期行（右空四字）",
        },
    },
    "工作总结": {
        "required": {"总结主体", "总结时段", "工作回顾", "成文日期"},
        "desc": {
            "总结主体": "标题「{总结主体}{总结时段}工作总结」＋文末落款署名（居中于成文日期之上）",
            "总结时段": "标题组成",
            "工作回顾": "一级标题「工作回顾」＋条目列表（1. 2. …）",
            "主要成绩": "一级标题「主要成绩」＋条目列表（1. 2. …）",
            "存在问题": "一级标题「存在问题」＋条目列表（1. 2. …）",
            "下一步工作打算": "一级标题「下一步工作打算」＋条目列表（1. 2. …）",
            "成文日期": "文末落款日期行（右空四字）",
        },
    },
}

PLACEHOLDER_TEXT = "____"


def is_blank(v):
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return True
    if isinstance(v, dict) and len(v) == 0:
        return True
    return False


def resolve_fields(template, data):
    """按数据键原序解析每个字段：状态 + 原值。"""
    schema = SCHEMA[template]
    resolved = {}
    order = []
    for key, raw in data.items():
        order.append(key)
        blank = is_blank(raw)
        required = key in schema["required"]
        if not blank:
            status = FILLED
        else:
            status = PLACEHOLDER if required else OMITTED
        resolved[key] = {"status": status, "value": None if blank else raw}
    return resolved, order


def val(resolved, key):
    """取渲染值：缺失返回 ____ 占位（必填）或 None（选填，调用方应省略）。"""
    rec = resolved.get(key)
    if rec is None:
        return None  # 数据里根本没有该键：按选填省略处理
    if rec["status"] == FILLED:
        v = rec["value"]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
        return v
    if rec["status"] == PLACEHOLDER:
        return PLACEHOLDER_TEXT
    return None


def render_list_value(v):
    """列表/标量统一成条目字符串列表。"""
    if isinstance(v, list):
        return ["" if it is None else str(it) for it in v]
    if isinstance(v, dict):
        return ["%s：%s" % (k, vv) for k, vv in v.items()]
    return [str(v)]


def add_section(doc, no, heading, value):
    """一级标题＋条目列表（值缺失时按占位/省略处理，返回是否渲染）。"""
    if value is None:
        return False
    add_heading(doc, "%s、%s" % (cn_no(no), heading))
    if isinstance(value, str):
        add_body(doc, value)
    else:
        add_list(doc, render_list_value(value))
    return True


# ---------- 四类模板装配 ----------

def build_zhoubao(doc, resolved, order):
    dept = val(resolved, "部门") or PLACEHOLDER_TEXT
    period = val(resolved, "周期")
    add_title(doc, "%s工作周报" % dept,
              subtitle=("（%s）" % period) if period is not None else None)
    no = 0
    for key, heading in (("本周工作内容", "本周工作内容"),
                         ("下周工作计划", "下周工作计划"),
                         ("问题与需协调事项", "问题与需协调事项")):
        if add_section(doc, no + 1, heading, val(resolved, key)):
            no += 1
    sig = val(resolved, "填报人") or PLACEHOLDER_TEXT
    date = val(resolved, "报送日期") or PLACEHOLDER_TEXT
    add_signature_block(doc, sig, date)


def build_qingshi(doc, resolved, order):
    unit = val(resolved, "请示单位") or PLACEHOLDER_TEXT
    subject = val(resolved, "请示事由") or PLACEHOLDER_TEXT
    add_title(doc, "%s关于%s的请示" % (unit, subject))
    master = val(resolved, "主送机关")
    if master is not None:
        add_master(doc, master)
    reason = val(resolved, "请示缘由")
    if reason is not None:
        add_body(doc, reason)
    matter = val(resolved, "请示事项")
    if matter is not None:
        add_body(doc, matter)
    add_body(doc, "妥否，请批示。")
    date = val(resolved, "成文日期") or PLACEHOLDER_TEXT
    add_signature_block(doc, unit, date)
    contact = val(resolved, "联系人")
    phone = val(resolved, "联系电话")
    parts = []
    if contact is not None:
        parts.append("联系人：" + contact)
    if phone is not None:
        parts.append("联系电话：" + phone)
    if parts:
        add_note(doc, "，".join(parts))


def build_tongzhi(doc, resolved, order):
    unit = val(resolved, "召开单位") or PLACEHOLDER_TEXT
    name = val(resolved, "会议名称") or PLACEHOLDER_TEXT
    add_title(doc, "%s关于召开%s的通知" % (unit, name))
    master = val(resolved, "主送对象")
    if master is not None:
        add_master(doc, master)
    add_body(doc, "现将%s有关事项通知如下：" % name)
    no = 0

    def item(label, value, as_list=False):
        nonlocal no
        if value is None:
            return
        as_list = as_list or isinstance(value, (list, dict))
        no += 1
        cn = cn_no(no)
        if as_list:
            add_label_item(doc, "%s、%s" % (cn, label), "")
            add_list(doc, render_list_value(value))
        else:
            add_label_item(doc, "%s、%s" % (cn, label), str(value))

    item("会议时间", val(resolved, "会议时间"))
    item("会议地点", val(resolved, "会议地点"))
    item("会议议题", val(resolved, "会议议题"))
    item("参会人员", val(resolved, "参会人员"))
    req = val(resolved, "会议要求")
    if req is not None:
        if isinstance(req, str):
            item("会议要求", req)
        else:
            item("会议要求", req, as_list=True)
    item("联系人", val(resolved, "联系人"))
    item("联系电话", val(resolved, "联系电话"))
    add_body(doc, "特此通知。")
    date = val(resolved, "发文日期") or PLACEHOLDER_TEXT
    add_signature_block(doc, unit, date)


def build_zongjie(doc, resolved, order):
    subject = val(resolved, "总结主体") or PLACEHOLDER_TEXT
    period = val(resolved, "总结时段") or ""
    add_title(doc, "%s%s工作总结" % (subject, period))
    no = 0
    for key in ("工作回顾", "主要成绩", "存在问题", "下一步工作打算"):
        if add_section(doc, no + 1, key, val(resolved, key)):
            no += 1
    date = val(resolved, "成文日期") or PLACEHOLDER_TEXT
    add_signature_block(doc, subject, date)


BUILDERS = {"周报": build_zhoubao, "请示函": build_qingshi,
            "会议通知": build_tongzhi, "工作总结": build_zongjie}

TITLE_MAKERS = {
    "周报": lambda r: "%s工作周报" % (val(r, "部门") or PLACEHOLDER_TEXT),
    "请示函": lambda r: "%s关于%s的请示" % (val(r, "请示单位") or PLACEHOLDER_TEXT,
                                            val(r, "请示事由") or PLACEHOLDER_TEXT),
    "会议通知": lambda r: "%s关于召开%s的通知" % (val(r, "召开单位") or PLACEHOLDER_TEXT,
                                                   val(r, "会议名称") or PLACEHOLDER_TEXT),
    "工作总结": lambda r: "%s%s工作总结" % (val(r, "总结主体") or PLACEHOLDER_TEXT,
                                             val(r, "总结时段") or ""),
}


def generate(template, data, outdir):
    resolved, order = resolve_fields(template, data)
    schema = SCHEMA[template]

    doc = Document()
    setup_page(doc)
    add_page_number(doc)

    extras = [k for k in order if k not in schema["desc"]]
    BUILDERS[template](doc, resolved, order)
    if extras:  # 模板外字段：按「名称：值」原样附加，不丢数据、不编造
        for k in extras:
            v = val(resolved, k)
            if v is None:
                continue
            if isinstance(v, (list, dict)):
                add_heading(doc, "补充信息")
                add_list(doc, render_list_value(v))
            else:
                add_body(doc, "%s：%s" % (k, v))

    title = TITLE_MAKERS[template](resolved)
    doc.core_properties.title = title

    os.makedirs(outdir, exist_ok=True)
    doc.save(os.path.join(outdir, "文书.docx"))

    fields = []
    for key in order:
        rec = resolved[key]
        desc = schema["desc"].get(key)
        if desc is None:
            desc = "正文附加段「%s：…」（数据含模板外字段，原样列出）" % key
        fields.append({
            "名称": key,
            "是否必填": key in schema["required"],
            "状态": rec["status"],
            "值": rec["value"],
            "渲染方式": desc,
        })
    filled = sum(1 for f in fields if f["状态"] == FILLED)
    missing = sum(1 for f in fields if f["状态"] != FILLED)
    fields_doc = {
        "template": template,
        "title": title,
        "fields": fields,
        "summary": {"filled": filled, "missing": missing, "total": len(fields)},
    }
    with open(os.path.join(outdir, "fields.json"), "w", encoding="utf-8") as fh:
        json.dump(fields_doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return fields_doc


def main(argv=None):
    ap = argparse.ArgumentParser(description="GB/T 9704 公文生成器")
    ap.add_argument("--template", required=True,
                    help="模板类型：周报 | 请示函 | 会议通知 | 工作总结")
    ap.add_argument("--data", required=True, help="数据 JSON 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args(argv)

    if args.template not in SCHEMA:
        ap.error("不支持的模板 %r，可选：%s" % (args.template, "｜".join(SCHEMA)))
    try:
        with open(args.data, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("读取数据失败：%s" % exc, file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("数据 JSON 顶层必须是对象", file=sys.stderr)
        return 2

    result = generate(args.template, data, args.outdir)
    s = result["summary"]
    print("[OK] %s -> %s/文书.docx + fields.json（filled=%d missing=%d total=%d）"
          % (args.template, args.outdir, s["filled"], s["missing"], s["total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
