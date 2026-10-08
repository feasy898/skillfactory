#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""office_gen.py —— 周报/工作总结 模板文书生成器（SF-0008 ab3-empty-and-string-lists）

命令行契约：
    python3 office_gen.py --template <周报|工作总结> --data <数据json路径> --outdir <输出目录>

每次调用在 <outdir>/<模板>/<数据文件stem>/ 单元目录下生成恰两份产物：
    文书.docx   渲染后的正式文书
    fields.json 字段级渲染语义记录

核心语义（对应任务书）：
  1. 空列表按必填缺失处理：渲染占位条目「1．____」，fields.json 记占位语义
     （placeholder / placeholder_items / section.placeholder）；
  2. 字符串型列表按单项化处理：渲染为单项条目「1．<str>」，fields.json 该字段
     value 为单元素数组，并记 input_was_string=true；
  3. 选填小节缺失：整节省略（正文不出现该节头），fields.json 仍记
     status=missing、required=false、section_omitted=true；
  4. 必填缺失（含空字符串标量）以「____」占位，标题如「____工作周报」
     「____2026年9月工作总结」；
  5. 小节编号「一、二、三、」，条目编号「1．2．3．」（全角句点 U+FF0E）；
  6. 落款恒右对齐渲染：落款行值缺则以「____」占位，不因空日期/缺主体破坏。

实现：纯 Python 标准库（zipfile 手写 OOXML），无第三方依赖。
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

PLACEHOLDER = "____"

CN_NUMS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
           "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# ---------------------------------------------------------------------------
# 模板规格：字段按模板规范顺序排列；roles 决定渲染位置
#   title_part: 标题组成部分（按序拼接于文书名词前）
#   sign:       落款行（labeled=「字段名：值」，plain=裸值）
#   section:    渲染为编号小节（一、二、三、…），条目编号 1．2．3．
# ---------------------------------------------------------------------------
TEMPLATES = {
    "周报": {
        "doc_noun": "工作周报",
        "fields": [
            {"name": "周期",             "kind": "scalar", "required": True,  "title_part": 0},
            {"name": "填报人",           "kind": "scalar", "required": True,  "sign": "labeled"},
            {"name": "本周工作内容",     "kind": "list",   "required": True,  "section": True},
            {"name": "下周工作计划",     "kind": "list",   "required": True,  "section": True},
            {"name": "问题与需协调事项", "kind": "list",   "required": False, "section": True},
            {"name": "报送日期",         "kind": "scalar", "required": True,  "sign": "labeled"},
        ],
    },
    "工作总结": {
        "doc_noun": "工作总结",
        "fields": [
            {"name": "总结主体",     "kind": "scalar", "required": True,  "title_part": 0, "sign": "plain"},
            {"name": "总结时段",     "kind": "scalar", "required": True,  "title_part": 1},
            {"name": "工作回顾",     "kind": "list",   "required": True,  "section": True},
            {"name": "主要成绩",     "kind": "list",   "required": True,  "section": True},
            {"name": "存在问题",     "kind": "list",   "required": False, "section": True},
            {"name": "下一步工作打算", "kind": "list",  "required": True,  "section": True},
            {"name": "成文日期",     "kind": "scalar", "required": False, "sign": "plain"},
        ],
    },
}


def cn_num(i):
    """1 基序号 → 中文小节号。"""
    return CN_NUMS[i - 1] if 1 <= i <= len(CN_NUMS) else str(i)


# ---------------------------------------------------------------------------
# 字段求值
# ---------------------------------------------------------------------------
def eval_field(spec, raw):
    """按模板规格求值单个字段。

    返回 dict：status filled/missing、value（filled 为规范化值，missing 恒 null）、
    raw_input 原样输入（键缺席为 null）、list 字段附 items 与 input_was_string。
    """
    name, kind, required = spec["name"], spec["kind"], spec["required"]
    out = {"name": name, "kind": kind, "required": required,
           "status": "missing", "value": None, "raw_input": raw}

    if kind == "list":
        if raw is None:
            pass  # 键缺席：missing（必填→占位条目；选填→整节省略）
        elif isinstance(raw, str):
            out["status"] = "filled"
            out["value"] = [raw]          # 单项化：字符串型列表 → 单元素数组
            out["items"] = [raw]
            out["input_was_string"] = True
        elif isinstance(raw, list):
            if len(raw) == 0:
                pass  # 空列表按缺失处理
            else:
                out["status"] = "filled"
                out["value"] = list(raw)
                out["items"] = [str(x) for x in raw]
        else:
            raise ValueError(f"字段 {name} 期望字符串或字符串数组，实际 {type(raw).__name__}")
    else:  # scalar
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            pass  # 键缺席或空字符串：missing（如「周期」为空字符串）
        else:
            out["status"] = "filled"
            out["value"] = raw
    return out


def display(ev):
    """字段的显示文本：filled 为值，missing 为「____」占位。"""
    return ev["value"] if ev["status"] == "filled" else PLACEHOLDER


# ---------------------------------------------------------------------------
# 渲染规划（正文小节 / 标题 / 落款）
# ---------------------------------------------------------------------------
def build_plan(template, evs):
    """由求值结果生成标题、编号小节与右对齐落款。"""
    spec_fields = template["fields"]

    # 标题：title_part 字段按序显示拼接 + 文书名词；缺失以 ____ 占位
    parts = sorted(((f.get("title_part"), f["name"]) for f in spec_fields if "title_part" in f))
    title = "".join(display(evs[n]) for _, n in parts) + template["doc_noun"]

    # 小节：选填缺失整节省略（不出现节头）；必填缺失渲染单条占位条目
    sections, omitted = [], []
    sec_no = 0
    for f in spec_fields:
        if not f.get("section"):
            continue
        ev = evs[f["name"]]
        if ev["status"] == "filled":
            sec_no += 1
            items = [f"{i}．{t}" for i, t in enumerate(ev["items"], start=1)]
            sections.append({"index": sec_no, "number": cn_num(sec_no),
                             "header": f"{cn_num(sec_no)}、{f['name']}",
                             "field": f["name"], "items": items, "placeholder": False})
        elif f["required"]:
            sec_no += 1
            items = [f"1．{PLACEHOLDER}"]
            sections.append({"index": sec_no, "number": cn_num(sec_no),
                             "header": f"{cn_num(sec_no)}、{f['name']}",
                             "field": f["name"], "items": items, "placeholder": True})
        else:
            omitted.append(f["name"])

    # 落款：恒渲染（值缺以 ____ 占位），右对齐
    sig_lines = []
    for f in spec_fields:
        if "sign" not in f:
            continue
        text = display(evs[f["name"]]) if f["sign"] == "plain" \
            else f"{f['name']}：{display(evs[f['name']])}"
        sig_lines.append({"field": f["name"], "text": text})

    return {"title": title, "sections": sections, "omitted_sections": omitted,
            "signature": {"alignment": "right", "lines": sig_lines}}


def build_fields_json(template_name, template, evs, plan, data_path, unit):
    """组装 fields.json：字段数组 + 渲染了的小节 + 落款。"""
    fields = []
    for f in template["fields"]:
        ev = evs[f["name"]]
        entry = {"name": ev["name"], "kind": ev["kind"], "required": ev["required"],
                 "status": ev["status"], "value": ev["value"], "raw_input": ev["raw_input"]}
        if ev.get("input_was_string"):
            entry["input_was_string"] = True
        if ev["status"] == "missing":
            if ev["kind"] == "list":
                if ev["required"]:
                    entry["placeholder"] = PLACEHOLDER
                    sec = next(s for s in plan["sections"] if s["field"] == ev["name"])
                    entry["placeholder_items"] = sec["items"]  # 占位条目，如「1．____」
                else:
                    entry["section_omitted"] = True  # 选填缺失整节省略，不渲染任何占位
            else:
                entry["placeholder"] = PLACEHOLDER  # 标题/落款位以 ____ 占位渲染
        fields.append(entry)

    return {
        "template": template_name,
        "data_source": data_path,
        "unit": unit,
        "title": plan["title"],
        "fields": fields,
        "sections": [
            {"number": s["number"], "header": s["header"], "items": s["items"],
             "placeholder": s["placeholder"]} for s in plan["sections"]
        ],
        "omitted_sections": plan["omitted_sections"],
        "signature": plan["signature"],
    }


# ---------------------------------------------------------------------------
# OOXML（纯标准库手写 DOCX）
# ---------------------------------------------------------------------------
def _rpr(bold=False, sz=24):
    rpr = ('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
           'w:eastAsia="宋体" w:cs="Times New Roman"/>')
    if bold:
        rpr += "<w:b/><w:bCs/>"
    rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    return rpr


def _para(text, *, bold=False, sz=24, jc=None, before=None, after=None,
          line=312, first_line=None, keep_next=False):
    """生成 <w:p>；pPr 子元素按 OOXML schema 顺序输出。"""
    ppr = ""
    if keep_next:
        ppr += "<w:keepNext/>"
    spacing = ""
    if before is not None:
        spacing += f' w:before="{before}"'
    if after is not None:
        spacing += f' w:after="{after}"'
    if line is not None:
        spacing += f' w:line="{line}" w:lineRule="auto"'
    if spacing:
        ppr += f"<w:spacing{spacing}/>"
    if first_line is not None:
        ppr += f'<w:ind w:firstLine="{first_line}"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    if ppr:
        ppr = f"<w:pPr>{ppr}</w:pPr>"
    run = f"<w:r><w:rPr>{_rpr(bold, sz)}</w:rPr>" \
          f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    return f"<w:p>{ppr}{run}</w:p>"


def build_docx_xml(plan):
    """标题（居中加粗二号）→ 编号小节 → 右对齐落款。"""
    ps = [_para(plan["title"], bold=True, sz=44, jc="center", after=360, line=312)]
    for s in plan["sections"]:
        ps.append(_para(s["header"], bold=True, sz=24, before=240, after=80,
                        line=312, keep_next=True))
        for item in s["items"]:
            ps.append(_para(item, sz=24, after=40, line=312, first_line=480))
    for i, line in enumerate(plan["signature"]["lines"]):
        ps.append(_para(line["text"], sz=24, jc="right",
                        before=480 if i == 0 else 60, after=40, line=312))
    sect = ('<w:sectPr>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1440" w:right="1797" w:bottom="1440" w:left="1797" '
            'w:header="851" w:footer="992" w:gutter="0"/>'
            '<w:cols w:space="425"/>'
            '<w:docGrid w:type="lines" w:linePitch="312"/>'
            '</w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f"<w:document {W_NS}><w:body>{''.join(ps)}{sect}</w:body></w:document>")


STYLES_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f"<w:styles {W_NS}>"
              "<w:docDefaults><w:rPrDefault><w:rPr>"
              '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
              'w:eastAsia="宋体" w:cs="Times New Roman"/>'
              '<w:sz w:val="24"/><w:szCs w:val="24"/>'
              '<w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/>'
              "</w:rPr></w:rPrDefault>"
              '<w:pPrDefault><w:pPr><w:spacing w:line="312" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
              "</w:docDefaults>"
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
              "<w:name w:val=\"Normal\"/><w:qFormat/></w:style>"
              "</w:styles>")

CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                 '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                 '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                 "</Types>")

ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
             '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
             "</Relationships>")

DOC_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>")


def core_xml(title):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{escape(title)}</dc:title>"
            "<dc:creator>office_gen.py</dc:creator>"
            "<cp:lastModifiedBy>office_gen.py</cp:lastModifiedBy>"
            '<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-08T00:00:00Z</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-08T00:00:00Z</dcterms:modified>'
            "</cp:coreProperties>")


APP_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           "<Application>office_gen.py</Application></Properties>")


def write_docx(path, plan):
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "docProps/core.xml": core_xml(plan["title"]),
        "docProps/app.xml": APP_XML,
        "word/document.xml": build_docx_xml(plan),
        "word/styles.xml": STYLES_XML,
        "word/_rels/document.xml.rels": DOC_RELS,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="周报/工作总结 模板文书生成器")
    ap.add_argument("--template", required=True, choices=sorted(TEMPLATES),
                    help="模板名：周报 或 工作总结")
    ap.add_argument("--data", required=True, help="数据 json 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args(argv)

    data_path = Path(args.data)
    if not data_path.is_file():
        print(f"错误：数据文件不存在：{data_path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"错误：数据文件不是合法 JSON：{e}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("错误：数据文件顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    template = TEMPLATES[args.template]
    known = {f["name"] for f in template["fields"]}
    unmapped = {k: v for k, v in data.items() if k not in known}

    evs = {}
    for f in template["fields"]:
        evs[f["name"]] = eval_field(f, data.get(f["name"]))
    plan = build_plan(template, evs)

    unit = data_path.stem
    unit_dir = Path(args.outdir) / args.template / unit
    unit_dir.mkdir(parents=True, exist_ok=True)

    write_docx(unit_dir / "文书.docx", plan)

    doc = build_fields_json(args.template, template, evs, plan,
                            str(data_path), unit)
    if unmapped:
        doc["unmapped_input"] = unmapped  # 模板外字段原样登记，不参与渲染
    with open(unit_dir / "fields.json", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"模板={args.template} 单元={unit} → {unit_dir}/文书.docx + fields.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
