#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板生成入口（SF-0008 office 臂）。

命令行契约：
    gen_doc.py --template <周报|请示函|会议通知|工作总结>
                --data <数据 json 路径>
                --outdir <输出目录>

每次调用在 <outdir>/<模板名>/<数据文件名主干>/ 下生成两个产物：
文书.docx 与 fields.json。

行为约定（ab4 核心）：
  * 输入非法（模板名非法 / 数据文件不存在 / JSON 解析失败 / 顶层非对象）
    一律以退出码 2 拒绝，stderr 输出中文错误信息，且**零产物残留**——
    不创建输出目录、不写半成品。校验全部前置，产物在内存中构建完成后才落盘。
  * 必填字段缺失**不算非法输入**：正常退出（0），必填以 ____ 占位、
    选填留空或省略，并在 fields.json 中如实记账。
"""

import argparse
import io
import json
import os
import sys

EXIT_OK = 0
EXIT_INVALID_INPUT = 2

TEMPLATES = ["周报", "请示函", "会议通知", "工作总结"]

PLACEHOLDER = "____"

# 字段定义：顺序即渲染顺序；required=True 为必填。
FIELD_SPEC = {
    "周报": [
        {"name": "部门", "required": True, "kind": "scalar"},
        {"name": "填报人", "required": False, "kind": "scalar"},
        {"name": "周期", "required": True, "kind": "scalar"},
        {"name": "本周工作内容", "required": True, "kind": "list"},
        {"name": "下周工作计划", "required": False, "kind": "list"},
        {"name": "问题与需协调事项", "required": False, "kind": "list"},
        {"name": "报送日期", "required": False, "kind": "scalar"},
    ],
    "请示函": [
        {"name": "主送机关", "required": True, "kind": "scalar"},
        {"name": "请示事项", "required": True, "kind": "scalar"},
        {"name": "政策依据", "required": False, "kind": "scalar"},
        {"name": "拟办意见", "required": False, "kind": "scalar"},
        {"name": "经费需求", "required": False, "kind": "scalar"},
        {"name": "联系电话", "required": False, "kind": "scalar"},
        {"name": "申请人", "required": False, "kind": "scalar"},
        {"name": "成文日期", "required": False, "kind": "scalar"},
    ],
    "会议通知": [
        {"name": "主送单位", "required": False, "kind": "scalar"},
        {"name": "会议名称", "required": True, "kind": "scalar"},
        {"name": "会议时间", "required": False, "kind": "scalar"},
        {"name": "会议地点", "required": True, "kind": "scalar"},
        {"name": "会议议题", "required": False, "kind": "list"},
        {"name": "参会人员", "required": False, "kind": "list"},
        {"name": "主持人", "required": False, "kind": "scalar"},
        {"name": "会议要求", "required": False, "kind": "list"},
        {"name": "联系人", "required": False, "kind": "scalar"},
        {"name": "联系电话", "required": False, "kind": "scalar"},
        {"name": "成文日期", "required": False, "kind": "scalar"},
    ],
    "工作总结": [
        {"name": "总结主体", "required": True, "kind": "scalar"},
        {"name": "统计周期", "required": False, "kind": "scalar"},
        {"name": "主要成绩", "required": True, "kind": "list"},
        {"name": "存在问题", "required": False, "kind": "list"},
        {"name": "下步计划", "required": False, "kind": "list"},
        {"name": "部门负责人", "required": False, "kind": "scalar"},
        {"name": "成文日期", "required": False, "kind": "scalar"},
    ],
}

CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


# ---------------------------------------------------------------- 输入校验
def fail(msg):
    """统一非法输入出口：中文错误写 stderr，退出码 2，零产物。"""
    sys.stderr.write("错误：%s\n" % msg)
    return EXIT_INVALID_INPUT


def load_data(path):
    """读入并校验数据文件。返回 (data, None) 或 (None, 错误信息)。"""
    if not os.path.exists(path):
        return None, "数据文件不存在：%s" % path
    if os.path.isdir(path):
        return None, "数据路径是目录而非文件：%s" % path
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        return None, "数据文件无法读取：%s（%s）" % (path, exc.strerror or exc)
    except UnicodeDecodeError as exc:
        return None, "数据文件不是 UTF-8 文本，无法解析：%s（%s）" % (path, exc.reason)
    if not raw.strip():
        return None, "数据文件为空文件，JSON 解析失败：%s" % path
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, "数据文件不是合法 JSON，解析失败：%s（%s）" % (path, exc)
    if not isinstance(data, dict):
        return None, ("数据文件顶层必须是 JSON 对象，实际为 %s：%s"
                      % (_json_type_cn(data), path))
    return data, None


def _json_type_cn(value):
    if isinstance(value, list):
        return "数组"
    if isinstance(value, str):
        return "字符串"
    if isinstance(value, bool):
        return "布尔值"
    if isinstance(value, (int, float)):
        return "数字"
    if value is None:
        return "null"
    return "其他类型"


# ---------------------------------------------------------------- 字段取值
def _scalar_items(value):
    """标量字段 → 条目列表；空串/None 视为缺失。"""
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
            elif v is not None and not isinstance(v, (dict, list)):
                out.append(str(v).strip())
        return out
    if isinstance(value, dict):
        return []
    if isinstance(value, bool):
        return ["是" if value else "否"]
    return [str(value).strip()]


def resolve_fields(template, data):
    """按模板字段表逐字段判定状态与渲染内容，如实记账。"""
    spec = FIELD_SPEC[template]
    known = {f["name"] for f in spec}
    fields = []
    for f in spec:
        name = f["name"]
        present = name in data
        if f["kind"] == "list":
            items = _scalar_items(data.get(name))
        else:
            items = _scalar_items(data.get(name))
        if items:
            status, value, render = "filled", data.get(name), "verbatim"
        elif present:
            # 键在但值为空串/空列表/空对象：属缺失事实，不是非法输入
            status, value, render = "missing", None, "placeholder" if f["required"] else "omit"
        else:
            status, value, render = "missing", None, "placeholder" if f["required"] else "omit"
        fields.append({
            "name": name,
            "required": f["required"],
            "status": status,
            "value": value,
            "items": items,
            "render": render,
        })
    unknown_keys = [k for k in data if k not in known]
    filled = [f["name"] for f in fields if f["status"] == "filled"]
    missing = [f["name"] for f in fields if f["status"] == "missing"]
    missing_required = [f["name"] for f in fields
                        if f["status"] == "missing" and f["required"]]
    missing_optional = [f["name"] for f in fields
                        if f["status"] == "missing" and not f["required"]]
    return fields, {
        "filled_fields": filled,
        "missing_fields": missing,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "unknown_keys": unknown_keys,
        "summary": {"filled": len(filled), "missing": len(missing),
                    "total": len(fields)},
    }


# ---------------------------------------------------------------- 版式工具
def _set_run_font(run, east, size_pt, bold=False):
    from docx.oxml.ns import qn
    run.font.size = None
    run.font.name = east
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:eastAsia"), east)
    sz = rPr.get_or_add_sz()
    sz.set(qn("w:val"), str(int(size_pt * 2)))
    szcs = rPr.find(qn("w:szCs"))
    if szcs is None:
        szcs = rPr.makeelement(qn("w:szCs"), {})
        sz.append(szcs)
    szcs.set(qn("w:val"), str(int(size_pt * 2)))
    if bold:
        run.bold = True


def _set_indent_chars(paragraph, first_line_chars=200):
    """按字符数设置首行缩进（GB/T 9704 正文缩进 2 字符）。"""
    from docx.oxml.ns import qn
    pPr = paragraph._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = pPr.makeelement(qn("w:ind"), {})
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), str(first_line_chars))
    ind.set(qn("w:firstLine"), "640")


def _setup_page(doc):
    from docx.enum.section import WD_SECTION
    from docx.shared import Cm
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(3.7)
        section.bottom_margin = Cm(3.5)
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.6)
    return WD_SECTION


def _new_para(doc, text, *, align=None, east="仿宋_GB2312", size=16.0,
              bold=False, indent_chars=200, line_pt=28.0, space_after=0.0):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = Pt(line_pt)
    if align is not None:
        p.alignment = align
    if indent_chars:
        _set_indent_chars(p, indent_chars)
    if text:
        run = p.add_run(text)
        _set_run_font(run, east, size, bold)
    return p


def _numbered(doc, items, *, size=16.0, line_pt=28.0):
    """公文条列体：1．条目（使用全角点号 U+FF0E）。"""
    from docx.shared import Pt
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = Pt(line_pt)
        _set_indent_chars(p, 200)
        _set_indent_chars_hanging(p, 200)
        run = p.add_run("%d．%s" % (i, item))
        _set_run_font(run, "仿宋_GB2312", size)


def _set_indent_chars_hanging(paragraph, chars=200):
    from docx.oxml.ns import qn
    pPr = paragraph._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = pPr.makeelement(qn("w:ind"), {})
        pPr.append(ind)
    ind.set(qn("w:leftChars"), str(chars))
    ind.set(qn("w:hangingChars"), str(chars))
    ind.set(qn("w:left"), "640")
    ind.set(qn("w:hanging"), "640")


def _placeholder_or(value_items, required):
    """必填缺失 → ____ 占位；选填缺失 → 省略（返回 None）。"""
    if value_items:
        return value_items
    if required:
        return [PLACEHOLDER]
    return []


# ---------------------------------------------------------------- 四类模板渲染
def _title_of(template, fmap):
    if template == "周报":
        return "%s工作周报" % (fmap["部门"][0] if fmap["部门"] else PLACEHOLDER)
    if template == "工作总结":
        return "%s工作总结" % (fmap["总结主体"][0] if fmap["总结主体"] else PLACEHOLDER)
    if template == "请示函":
        return "请　示　函"
    return "会　议　通　知"


def _render_doc(template, fields, ledger):
    """在内存中构建 docx，返回 (docx_bytes, title)。"""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    fmap = {f["name"]: _placeholder_or(f["items"], f["required"]) for f in fields}
    doc = Document()
    _setup_page(doc)

    normal = doc.styles["Normal"]
    normal.font.size = Pt(16)
    normal.font.name = "仿宋_GB2312"

    # 标题：小标宋二号，居中
    title = _title_of(template, fmap)
    _new_para(doc, title, align=WD_ALIGN_PARAGRAPH.CENTER,
              east="方正小标宋简体", size=22.0, line_pt=34.0, space_after=18.0,
              indent_chars=0)

    if template == "周报":
        _new_para(doc, "公司领导：", indent_chars=0)
        period = fmap["周期"][0] if fmap["周期"] else PLACEHOLDER
        dept = fmap["部门"][0] if fmap["部门"] else PLACEHOLDER
        _new_para(doc, "%s，%s现将本周工作开展情况报告如下：" % (period, dept))
        sec = 0
        for label, key in (("本周工作内容", "本周工作内容"),
                           ("下周工作计划", "下周工作计划"),
                           ("问题与需协调事项", "问题与需协调事项")):
            sec += 1
            _new_para(doc, "%s、%s：" % (CN_NUM[sec - 1], label))
            items = fmap[key]
            if items:
                _numbered(doc, items)
            else:
                _new_para(doc, PLACEHOLDER)
        _new_para(doc, "特此报告。")
        _new_para(doc, (fmap["填报人"][0] if fmap["填报人"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0, space_after=0.0)
        _new_para(doc, (fmap["报送日期"][0] if fmap["报送日期"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0)

    elif template == "工作总结":
        _new_para(doc, "公司领导：", indent_chars=0)
        subj = fmap["总结主体"][0] if fmap["总结主体"] else PLACEHOLDER
        period = fmap["统计周期"][0] if fmap["统计周期"] else ""
        lead = "%s%s工作总结如下：" % (subj, ("%s" % period) if period else "")
        _new_para(doc, lead)
        sec = 0
        for label, key in (("主要成绩", "主要成绩"),
                           ("存在问题", "存在问题"),
                           ("下步计划", "下步计划")):
            sec += 1
            _new_para(doc, "%s、%s：" % (CN_NUM[sec - 1], label))
            if fmap[key]:
                _numbered(doc, fmap[key])
            else:
                _new_para(doc, PLACEHOLDER)
        _new_para(doc, "特此总结。")
        _new_para(doc, (fmap["部门负责人"][0] if fmap["部门负责人"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0, space_after=0.0)
        _new_para(doc, (fmap["成文日期"][0] if fmap["成文日期"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0)

    elif template == "请示函":
        _new_para(doc, (fmap["主送机关"][0] if fmap["主送机关"] else PLACEHOLDER) + "：",
                  indent_chars=0)
        matter = fmap["请示事项"][0] if fmap["请示事项"] else PLACEHOLDER
        _new_para(doc, "为%s事宜，特请示如下：" % matter)
        if fmap["政策依据"]:
            _new_para(doc, "一、依据：%s。" % "；".join(fmap["政策依据"]))
        if fmap["拟办意见"]:
            _new_para(doc, "二、拟办意见：%s。" % "；".join(fmap["拟办意见"]))
        if fmap["经费需求"]:
            _new_para(doc, "三、经费需求：%s。" % "；".join(fmap["经费需求"]))
        if fmap["联系电话"]:
            _new_para(doc, "四、联系电话：%s。" % "；".join(fmap["联系电话"]))
        _new_para(doc, "妥否，请批示。")
        _new_para(doc, (fmap["申请人"][0] if fmap["申请人"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0, space_after=0.0)
        _new_para(doc, (fmap["成文日期"][0] if fmap["成文日期"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0)

    else:  # 会议通知
        _new_para(doc, (fmap["主送单位"][0] if fmap["主送单位"] else "各部门、直属单位") + "：",
                  indent_chars=0)
        name = fmap["会议名称"][0] if fmap["会议名称"] else PLACEHOLDER
        _new_para(doc, "现将%s有关事项通知如下：" % name)
        items = []
        if fmap["会议时间"]:
            items.append("一、会议时间：%s。" % "；".join(fmap["会议时间"]))
        items.append("%s、会议地点：%s。"
                     % (CN_NUM[len(items)], "；".join(fmap["会议地点"] or [PLACEHOLDER])))
        if fmap["会议议题"]:
            items.append("%s、会议议题：%s。" % (CN_NUM[len(items)], "；".join(fmap["会议议题"])))
        if fmap["参会人员"]:
            items.append("%s、参会人员：%s。" % (CN_NUM[len(items)], "；".join(fmap["参会人员"])))
        if fmap["主持人"]:
            items.append("%s、主持人：%s。" % (CN_NUM[len(items)], "；".join(fmap["主持人"])))
        if fmap["会议要求"]:
            items.append("%s、会议要求：%s。" % (CN_NUM[len(items)], "；".join(fmap["会议要求"])))
        if fmap["联系人"] or fmap["联系电话"]:
            contact = "、".join(x for x in (fmap["联系人"] + fmap["联系电话"]) if x)
            items.append("%s、联系人及联系方式：%s。" % (CN_NUM[len(items)], contact))
        for it in items:
            _new_para(doc, it)
        _new_para(doc, "请各单位按期参加。")
        _new_para(doc, (fmap["成文日期"][0] if fmap["成文日期"] else PLACEHOLDER),
                  align=WD_ALIGN_PARAGRAPH.RIGHT, indent_chars=0)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), title


# ---------------------------------------------------------------- 落盘
def write_products(outdir, template, case, docx_bytes, fields_json_text):
    """两产物在内存就绪后才落盘；写 fields.json 失败则回滚 docx，保证零半成品。"""
    unit = os.path.join(outdir, template, case)
    docx_path = os.path.join(unit, "文书.docx")
    fj_path = os.path.join(unit, "fields.json")
    os.makedirs(unit, exist_ok=True)
    with open(docx_path, "wb") as f:
        f.write(docx_bytes)
    try:
        with open(fj_path, "w", encoding="utf-8") as f:
            f.write(fields_json_text)
    except OSError:
        try:
            os.remove(docx_path)
        except OSError:
            pass
        raise
    return docx_path, fj_path


# ---------------------------------------------------------------- main
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gen_doc.py", description="公文模板生成入口（周报/请示函/会议通知/工作总结）")
    parser.add_argument("--template", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args(argv)

    # —— 前置校验（全部通过前不碰文件系统输出面，保证零产物残留）——
    if args.template not in TEMPLATES:
        return fail("模板名非法：%r。可选模板为：%s。"
                    % (args.template, "、".join(TEMPLATES)))
    data, err = load_data(args.data)
    if err is not None:
        return fail(err)

    case = os.path.splitext(os.path.basename(args.data))[0]
    fields, ledger = resolve_fields(args.template, data)
    docx_bytes, title = _render_doc(args.template, fields, ledger)

    payload = {
        "template": args.template,
        "case": case,
        "source_data": os.path.basename(args.data),
        "title": title,
        "fields": [{"name": f["name"], "required": f["required"],
                    "status": f["status"], "value": f["value"],
                    "render": f["render"]} for f in fields],
        "filled_fields": ledger["filled_fields"],
        "missing_fields": ledger["missing_fields"],
        "missing_required": ledger["missing_required"],
        "missing_optional": ledger["missing_optional"],
        "unknown_keys": ledger["unknown_keys"],
        "summary": ledger["summary"],
    }
    fj_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    try:
        docx_path, fj_path = write_products(
            args.outdir, args.template, case, docx_bytes, fj_text)
    except OSError as exc:
        return fail("产物写出失败：%s" % exc)

    sys.stdout.write("已生成：%s\n" % docx_path)
    sys.stdout.write("已生成：%s\n" % fj_path)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
