#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性公文生成器（会议通知，GB/T 9704-2012 风格，A4 版面）。

命令行契约：
    python3 gen_doc.py --template 会议通知 --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两个产物（且仅此两个）：
    文书.docx   —— GB/T 9704 风格会议通知（A4；2号方正小标宋标题、3号仿宋正文）
    fields.json —— 字段记账（template / title / fields / summary），不含任何路径键

缺数据不编造：必填缺失以 ____ 占位；选填缺失省略不渲染；fields.json 如实记账。

确定性设计（同一输入 ⇒ 任意多遍产物逐字节一致）：
    1) 生成路径零不可复现源：不取系统时钟、无随机数、无机器标识；
       core properties 只写入由数据派生的 title，不写时钟类属性；
    2) fields.json 固定序列化参数（ensure_ascii=False + indent=2 + 末尾换行），
       内容全部由输入数据与模板规则派生，含字典序即代码构造序（3.7+ 保序）；
    3) 文书.docx 保存后对 zip 容器做归一化重写：全部条目时间戳固定为常量
       1980-01-01 00:00:00、external_attr 固定 0644、压缩统一 ZIP_DEFLATED、
       条目顺序沿用源包（python-docx 对同一构建过程序列化顺序固定），
       从而消除 zip 条目头里的「保存时刻」这一唯一的逐字节不稳定源。
"""

import argparse
import json
import os
import re
import sys
import unicodedata
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

# ---------- GB/T 9704-2012 常量 ----------
FANGSONG = "仿宋_GB2312"        # 正文：3号仿宋
XIAOBIAOSONG = "方正小标宋简体"  # 标题：2号小标宋
HEITI = "黑体"                  # 条目标签：3号黑体
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

TEMPLATE = "会议通知"

# 字段规则：required=必填（缺失占位 ____）；desc=渲染方式记账描述
REQUIRED = {"会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
            "会议议题", "发文日期"}
DESC = {
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
}

PLACEHOLDER_TEXT = "____"

# 标题回行不可拆散的文种词（词意完整）
GENRE_WORDS = {"通知", "请示", "总结", "周报", "报告", "批复", "意见", "纪要", "函"}
# 不可居行首的字符
NO_LINE_START = set("，。；：、）】》”!?%,.;:)]}")


def cn_no(i):
    """1 -> 一，12 -> 十二。"""
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


def wrap_title(text, size, max_w):
    """标题回行：词意完整、上长下短（梯形/菱形）；超出版心宽时在允许断点中
    选行宽最均衡的方案；文种词不拆、行首不出虚词与标点。输入相同 ⇒ 输出相同。"""
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

def add_title(doc, text):
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, line=33,
              space_after=LINE_PITCH)
    lines = wrap_title(text, SIZE_TITLE, BODY_WIDTH_PT)
    run = _run(p, lines[0], XIAOBIAOSONG, SIZE_TITLE, ascii_font=XIAOBIAOSONG)
    for ln in lines[1:]:
        run.add_break()
        run.add_text(ln)


def add_master(doc, text):
    """主送机关：顶格，后加全角冒号。"""
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT)
    _run(p, text + "：", FANGSONG, SIZE_BODY)


def add_body(doc, text):
    p = _para(doc, first_line_chars=2)
    _run(p, text, FANGSONG, SIZE_BODY)
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


# ---------- 字段记账 ----------

FILLED, PLACEHOLDER, OMITTED = "filled", "placeholder", "omitted"


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


def resolve_fields(data):
    """按数据键原序解析每个字段：状态 + 原值。"""
    resolved = {}
    order = []
    for key, raw in data.items():
        order.append(key)
        blank = is_blank(raw)
        if not blank:
            status = FILLED
        else:
            status = PLACEHOLDER if key in REQUIRED else OMITTED
        resolved[key] = {"status": status, "value": None if blank else raw}
    return resolved, order


def val(resolved, key):
    """取渲染值：缺失返回 ____ 占位（必填）或 None（选填，调用方省略）。"""
    rec = resolved.get(key)
    if rec is None:
        return None  # 数据里没有该键：按选填省略处理
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


# ---------- 会议通知装配 ----------

def make_title(resolved):
    unit = val(resolved, "召开单位") or PLACEHOLDER_TEXT
    name = val(resolved, "会议名称") or PLACEHOLDER_TEXT
    return "%s关于召开%s的通知" % (unit, name)


def build_tongzhi(doc, resolved):
    unit = val(resolved, "召开单位") or PLACEHOLDER_TEXT
    name = val(resolved, "会议名称") or PLACEHOLDER_TEXT
    add_title(doc, make_title(resolved))
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
    item("参会人员", val(resolved, "参会人员"))
    item("会议议题", val(resolved, "会议议题"))
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


# ---------- 确定性收尾 ----------

# zip 容器归一化常量：全部条目统一的时间戳（远离当前时间的固定值）与权限
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
ZIP_ATTR = 0o644 << 16


def normalize_docx_zip(path):
    """归一化重写 docx 的 zip 容器。

    python-docx 落盘时 zip 条目头会带「保存时刻」，这是同输入两遍产物
    唯一可能的逐字节差异源；这里按源包条目顺序重写全部条目，时间戳、
    权限、压缩方式全部固定，重写后文件内容只由 XML 净荷决定。
    """
    with zipfile.ZipFile(path, "r") as src:
        entries = [(info.filename, src.read(info.filename))
                   for info in src.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, blob in entries:
            zi = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = ZIP_ATTR
            dst.writestr(zi, blob)


def generate(data, outdir):
    resolved, order = resolve_fields(data)

    doc = Document()
    setup_page(doc)
    add_page_number(doc)
    build_tongzhi(doc, resolved)

    title = make_title(resolved)
    doc.core_properties.title = title

    os.makedirs(outdir, exist_ok=True)
    docx_path = os.path.join(outdir, "文书.docx")
    doc.save(docx_path)
    normalize_docx_zip(docx_path)

    fields = []
    for key in order:
        rec = resolved[key]
        desc = DESC.get(key)
        if desc is None:
            desc = "正文附加段「%s：…」（数据含模板外字段，原样列出）" % key
        fields.append({
            "名称": key,
            "是否必填": key in REQUIRED,
            "状态": rec["status"],
            "值": rec["value"],
            "渲染方式": desc,
        })
    filled = sum(1 for f in fields if f["状态"] == FILLED)
    missing = sum(1 for f in fields if f["状态"] != FILLED)
    fields_doc = {
        "template": TEMPLATE,
        "title": title,
        "fields": fields,
        "summary": {"filled": filled, "missing": missing, "total": len(fields)},
    }
    with open(os.path.join(outdir, "fields.json"), "w", encoding="utf-8") as fh:
        json.dump(fields_doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return fields_doc


def main(argv=None):
    ap = argparse.ArgumentParser(description="确定性会议通知生成器（GB/T 9704 风格）")
    ap.add_argument("--template", required=True, help="模板类型：会议通知")
    ap.add_argument("--data", required=True, help="数据 JSON 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args(argv)

    if args.template != TEMPLATE:
        ap.error("不支持的模板 %r，本生成器仅支持：%s" % (args.template, TEMPLATE))
    try:
        with open(args.data, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("读取数据失败：%s" % exc, file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("数据 JSON 顶层必须是对象", file=sys.stderr)
        return 2

    result = generate(data, args.outdir)
    s = result["summary"]
    print("[OK] %s -> %s/文书.docx + fields.json（filled=%d missing=%d total=%d）"
          % (TEMPLATE, args.outdir, s["filled"], s["missing"], s["total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
