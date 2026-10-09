#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文书生成流程（baseline 臂自建实现）。

命令行契约：
    python3 gen_doc.py --template <请示函|工作总结> --data <数据json路径> --outdir <输出目录>

每次调用在 <outdir> 下生成两个产物：
    文书.docx     —— 按公文版式排版的成文
    fields.json   —— 字段台账（逐字段状态 + 缺失/占位语义）

设计要点（空数据容错）：
  * 任何输入都不抛错中断：类型不符、空对象、空列表、纯空白字符串均照实渲染。
  * 必填字段缺失 → 正文以 ____ 占位；列表型必填缺失 → 渲染一条「1．____」占位条目。
  * 选填小节缺失 → 整节省略（正文不出现该节头），台账仍记 missing（required=false）。
  * 列表中的空白项按缺失处理并计入 dropped_items，不进入正文。
  * 台账字段：title / missing_required_names / missing_optional / unknown_keys /
    fields / omitted_sections / summary。
"""

import argparse
import json
import os
import sys
import unicodedata

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
except ImportError as exc:  # pragma: no cover - 环境缺失时给出可执行的提示
    sys.stderr.write("需要 python-docx：pip install python-docx\n(%s)\n" % exc)
    raise

PH = "____"                # 标量占位符
PH_ITEM = "1．____"        # 列表型占位条目（1．为全角句点）
CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


# ---------------------------------------------------------------- 字段规范化

def norm(v):
    """把任意标量规整成去空白字符串；None 表示空白/缺失。

    同时吃掉半角空格、制表、换行和全角空格 U+3000（输入里成片出现的「　」）。
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, (int, float)):
        return str(v)
    if not isinstance(v, str):
        return None
    s = v.replace("　", " ").replace("\t", " ").replace("\n", " ").replace("\r", " ")
    s = " ".join(s.split())
    return s or None


def as_list(v):
    """列表字段取值：字符串型列表单项化；标量包装成单元素列表；空白项剔除。"""
    dropped = 0
    if v is None:
        return [], 0
    if isinstance(v, (list, tuple)):
        out = []
        for item in v:
            s = norm(item)
            if s is None:
                dropped += 1
            else:
                out.append(s)
        return out, dropped
    s = norm(v)
    if s is None:
        return [], 1
    return [s], 0


# ---------------------------------------------------------------- 字段台账

class Ledger(object):
    """字段台账：记录每个声明字段的取值、状态与渲染方式。"""

    def __init__(self, template, template_id, source_file, declared):
        self.template = template
        self.template_id = template_id
        self.source_file = source_file
        self.declared = declared          # [(name, required, kind, note)]
        self.entries = []                 # 逐字段台账（顺序 = 声明顺序）
        self.by_name = {}
        self.data_errors = []
        self.unknown_keys = []

    def add(self, name, required, kind, note):
        e = {
            "name": name,
            "required": bool(required),
            "kind": kind,
            "present": False,
            "value": None,
            "state": None,                # rendered / missing_required / missing_optional
            "rendered_as": None,
            "dropped_items": 0,
            "coerced_from": None,
            "note": note,
        }
        self.entries.append(e)
        self.by_name[name] = e
        return e

    # --- 取值并写入台账 -------------------------------------------------
    def take_list(self, name, data):
        e = self.by_name[name]
        raw = data.get(name, None)
        if isinstance(raw, (list, tuple)):
            items, dropped = as_list(raw)
            e["coerced_from"] = None
        elif raw is None and name in data:
            items, dropped = [], 1       # 显式给 null
        else:
            items, dropped = as_list(raw)
            e["coerced_from"] = "scalar" if items else None
        e["dropped_items"] = dropped
        if items:
            e.update(present=True, value=items, state="rendered")
        else:
            e["present"] = False
            e["value"] = []
            e["state"] = "missing_required" if e["required"] else "missing_optional"
            e["rendered_as"] = PH_ITEM if e["required"] else "(整节省略)"
        return items

    def take_str(self, name, data, placeholder=PH):
        e = self.by_name[name]
        raw = data.get(name, None)
        if isinstance(raw, (list, tuple)):
            items, dropped = as_list(raw)
            e["coerced_from"] = "list"
            e["dropped_items"] = dropped
            s = items[0] if items else None
        else:
            s = norm(raw)
        if s:
            e.update(present=True, value=s, state="rendered")
            return s
        e["present"] = False
        e["value"] = None
        e["state"] = "missing_required" if e["required"] else "missing_optional"
        e["rendered_as"] = placeholder
        return None

    # --- 汇总 -----------------------------------------------------------
    def missing_required_names(self):
        return [e["name"] for e in self.entries
                if e["required"] and e["state"] == "missing_required"]

    def missing_optional(self):
        return [e["name"] for e in self.entries
                if (not e["required"]) and e["state"] == "missing_optional"]

    def rendered_names(self):
        return [e["name"] for e in self.entries if e["state"] == "rendered"]

    def to_dict(self, title, out_docx, omitted_sections):
        req = [e for e in self.entries if e["required"]]
        opt = [e for e in self.entries if not e["required"]]
        return {
            "template": self.template,
            "template_id": self.template_id,
            "source_file": self.source_file,
            "output_file": out_docx,
            "title": title,
            "fields": self.entries,
            "rendered_names": self.rendered_names(),
            "missing_required_names": self.missing_required_names(),
            "missing_optional": self.missing_optional(),
            "unknown_keys": list(self.unknown_keys),
            "unknown_names": list(self.unknown_keys),
            "omitted_sections": omitted_sections,
            "data_errors": self.data_errors,
            "placeholder_policy": {
                "scalar": PH,
                "list_item": PH_ITEM,
                "note": "必填缺失以 ____ 占位；列表型必填缺失渲染一条「1．____」占位条目；"
                        "选填小节缺失整节省略，台账仍记 missing（required=false）。",
            },
            "summary": {
                "required_total": len(req),
                "required_missing": len(self.missing_required_names()),
                "optional_total": len(opt),
                "optional_missing": len(self.missing_optional()),
                "unknown_keys": len(self.unknown_keys),
                "fields_rendered": len(self.rendered_names()),
            },
        }


# ---------------------------------------------------------------- 版式工具

def _set_run(run, name, size_pt, bold=False):
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def new_doc():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "仿宋_GB2312"
    st.font.size = Pt(16)                       # 三号
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "仿宋_GB2312")
    pf = st.paragraph_format
    pf.line_spacing = Pt(28)                    # 公文行距
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    sec = doc.sections[0]
    sec.top_margin = Cm(3.7)
    sec.bottom_margin = Cm(3.5)
    sec.left_margin = Cm(2.8)
    sec.right_margin = Cm(2.6)
    return doc


def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(24)
    _set_run(p.add_run(text), "方正小标宋简体", 22, bold=False)
    return p


def add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(32)      # 首行缩进 2 字符
    _set_run(p.add_run(text), "黑体", 16)
    return p


def add_body(doc, text, indent=True):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(32)
    _set_run(p.add_run(text), "仿宋_GB2312", 16)
    return p


def add_signature(doc, unit, date):
    """落款：署名与成文日期右对齐，空值不破坏版式（用占位符补齐）。"""
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p1.paragraph_format.right_indent = Cm(1.1)
    p1.paragraph_format.space_before = Pt(24)
    _set_run(p1.add_run(unit), "仿宋_GB2312", 16)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.paragraph_format.right_indent = Cm(2.2)
    _set_run(p2.add_run(date), "仿宋_GB2312", 16)


def format_date(raw):
    """成文日期：原样用；空白则给 ____年__月__日 形态的占位。"""
    s = norm(raw)
    return s if s else "____年__月__日"


# ---------------------------------------------------------------- 模板：请示函

TPL_QINGSHI_DECL = [
    ("发文机关", True, "str", "落款署名（发文单位）"),
    ("主送机关", True, "str", "正文首行受文单位，顶格"),
    ("请示事由", True, "str", "用于标题「关于……的请示」与起首语"),
    ("请示事项", True, "list", "请示正文条目，一、二、三、"),
    ("成文日期", False, "str", "落款日期，右对齐；选填"),
]


def build_qingshi(data, ledger):
    org = ledger.take_str("发文机关", data)
    addr = ledger.take_str("主送机关", data)
    topic = ledger.take_str("请示事由", data)
    items = ledger.take_list("请示事项", data)
    date_raw = data.get("成文日期", None)
    date = format_date(date_raw)
    e = ledger.by_name["成文日期"]
    if norm(date_raw):
        e.update(present=True, value=norm(date_raw), state="rendered")
    else:
        e.update(present=False, value=None, state="missing_optional",
                 rendered_as="____年__月__日")

    doc = new_doc()
    title = "关于%s的请示" % (topic or PH)
    add_title(doc, title)

    add_body(doc, "%s：" % (addr or PH), indent=False)
    add_body(doc, "现就%s有关事项请示如下：" % (topic or PH))

    seq = 1
    for it in items:
        add_body(doc, "%s、%s" % (CN_NUM[seq - 1], it))
        seq += 1
    if not items:
        add_body(doc, "%s、%s" % (CN_NUM[0], PH))     # 占位条目

    add_body(doc, "妥否，请批示。")

    add_signature(doc, org or PH, date)
    return doc, title, []


# ---------------------------------------------------------------- 模板：工作总结

TPL_ZONGJIE_DECL = [
    ("总结主体", True, "str", "标题中的单位/部门，并作落款署名"),
    ("总结时段", True, "str", "标题中的时段，如 2026年9月"),
    ("工作回顾", True, "list", "第一节，回顾条目"),
    ("主要成绩", True, "list", "第二节，成绩条目"),
    ("存在问题", False, "list", "第三节，选填；缺失整节省略"),
    ("下一步工作打算", True, "list", "第四节，打算条目"),
    ("成文日期", False, "str", "落款日期，右对齐；选填"),
]


def build_zongjie(data, ledger):
    subject = ledger.take_str("总结主体", data)
    period = ledger.take_str("总结时段", data)
    items_fuxing = ledger.take_list("工作回顾", data)
    items_chengji = ledger.take_list("主要成绩", data)
    items_wenti = ledger.take_list("存在问题", data)
    items_jihua = ledger.take_list("下一步工作打算", data)
    date_raw = data.get("成文日期", None)
    date = format_date(date_raw)
    e = ledger.by_name["成文日期"]
    if norm(date_raw):
        e.update(present=True, value=norm(date_raw), state="rendered")
    else:
        e.update(present=False, value=None, state="missing_optional",
                 rendered_as="____年__月__日")

    doc = new_doc()
    title = "%s（%s）工作总结" % (subject or PH, period or (PH + "年__月"))
    add_title(doc, title)

    omitted = []
    sections = [
        ("工作回顾", items_fuxing),
        ("主要成绩", items_chengji),
        ("存在问题", items_wenti),
        ("下一步工作打算", items_jihua),
    ]
    idx = 0
    for name, items in sections:
        entry = ledger.by_name[name]
        if not items:
            # 选填节缺失 → 整节省略；必填节缺失 → 保留节头并渲染占位条目
            if entry["required"]:
                add_heading(doc, "%s、%s" % (CN_NUM[idx], name))
                add_body(doc, PH_ITEM)
                idx += 1
            else:
                omitted.append({"section": name, "field": name,
                                "reason": "选填字段缺失，整节省略（正文不出现该节头）"})
            continue
        add_heading(doc, "%s、%s" % (CN_NUM[idx], name))
        idx += 1
        for i, it in enumerate(items, 1):
            add_body(doc, "%d．%s" % (i, it))

    add_signature(doc, subject or PH, date)
    return doc, title, omitted


# ---------------------------------------------------------------- 入口

def load_data(path):
    """读数据文件；任何解析失败都不中断，退化为空对象并在台账留痕。"""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if not raw.strip():
        return {}, ["输入文件为空，按空对象处理"]
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return {}, ["JSON 解析失败（%s），按空对象处理" % exc]
    if isinstance(data, dict):
        return data, []
    if data is None:
        return {}, ["输入为 null，按空对象处理"]
    return {"__scalar_input__": data}, \
           ["输入顶层非对象（%s），已按空对象处理" % type(data).__name__]


def generate(template, data_path, outdir):
    if template == "请示函":
        tpl_id, decl, builder = "qingshi", TPL_QINGSHI_DECL, build_qingshi
    elif template == "工作总结":
        tpl_id, decl, builder = "zongjie", TPL_ZONGJIE_DECL, build_zongjie
    else:
        raise SystemExit("未知模板：%s（可选：请示函、工作总结）" % template)

    data, errors = load_data(data_path)
    ledger = Ledger(template, tpl_id, os.path.basename(data_path), decl)
    ledger.data_errors.extend(errors)
    for name, _req, _kind, _note in decl:
        ledger.add(name, _req, _kind, _note)

    declared_names = set(n for n, _r, _k, _x in decl)
    extra = [k for k in data.keys() if k not in declared_names and not k.startswith("__")]
    ledger.unknown_keys = extra

    doc, title, omitted = builder(data, ledger)

    os.makedirs(outdir, exist_ok=True)
    docx_path = os.path.join(outdir, "文书.docx")
    fields_path = os.path.join(outdir, "fields.json")
    doc.save(docx_path)

    payload = ledger.to_dict(title, "文书.docx", omitted)
    payload["input_keys"] = sorted(data.keys())
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("[%s] -> %s" % (template, outdir))
    print("  title               : %s" % title)
    print("  missing_required    : %s" % (", ".join(payload["missing_required_names"]) or "(无)"))
    print("  missing_optional    : %s" % (", ".join(payload["missing_optional"]) or "(无)"))
    print("  unknown_keys        : %s" % (", ".join(payload["unknown_keys"]) or "(无)"))
    print("  omitted_sections    : %s" % (", ".join(s["section"] for s in omitted) or "(无)"))
    return payload


def main():
    ap = argparse.ArgumentParser(description="文书生成流程")
    ap.add_argument("--template", required=True, choices=["请示函", "工作总结"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    generate(args.template, args.data, args.outdir)


if __name__ == "__main__":
    main()
