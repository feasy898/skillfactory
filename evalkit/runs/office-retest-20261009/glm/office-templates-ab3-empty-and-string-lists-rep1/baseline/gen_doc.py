#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""office 模板文书生成器（周报 / 工作总结）—— ab3-empty-and-string-lists baseline 臂。

命令行契约：
    python3 gen_doc.py --template <周报|工作总结> --data <数据json路径> --outdir <输出目录>

每次调用在 outdir 下生成两份产物：文书.docx 与 fields.json。

边界行为（任务书口径）：
- 空列表按必填缺失处理：渲染占位条目（如「1．____」），fields.json 记占位语义；
- 字符串型列表按单项化处理：渲染为单项条目，fields.json 中该字段值为单元素数组；
- 选填小节缺失：整节省略（正文不出现该节头），fields.json 仍记 missing（required=false）；
- 必填缺失以 ____ 占位（如标题「____工作周报」「____2026年9月工作总结」）；
- 小节编号「一、二、三、」、条目编号「1．2．3．」（U+FF0E 全角句点）；
- 落款右对齐，不因空日期 / 缺主体破坏（必填缺主体→____ 行仍右对齐；选填空日期→行省略）。

实现：零依赖（仅 Python 标准库），直接产出 OOXML zip 包，输出确定性（无时间戳、固定 zip 时间）。
"""

import argparse
import json
import os
import sys
import zipfile
from xml.sax.saxutils import escape

PLACEHOLDER = "____"          # 必填缺失占位符（4 个下划线，与任务书一致）
SECTION_SEP = "\u3001"        # 、小节编号分隔
ENTRY_SEP = "\uff0e"          # ．条目编号分隔（全角句点）

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# ---------------------------------------------------------------- 模板注册表

TEMPLATES = {
    "周报": {
        "title_parts": [
            {"field": "周期", "required": True},
            {"literal": "工作周报"},
        ],
        "sections": [
            {"field": "本周工作内容", "required": True},
            {"field": "下周工作计划", "required": True},
            {"field": "问题与需协调事项", "required": False},
        ],
        "signature_lines": [
            {"field": "填报人", "required": True, "format": "填报人：{value}"},
            {"field": "报送日期", "required": True, "format": "报送日期：{value}"},
        ],
    },
    "工作总结": {
        "title_parts": [
            {"field": "总结主体", "required": True},
            {"field": "总结时段", "required": True},
            {"literal": "工作总结"},
        ],
        "sections": [
            {"field": "工作回顾", "required": True},
            {"field": "主要成绩", "required": True},
            {"field": "存在问题", "required": False},
            {"field": "下一步工作打算", "required": True},
        ],
        "signature_lines": [
            {"field": "总结主体", "required": True, "format": "{value}"},
            {"field": "成文日期", "required": False, "format": "{value}"},
        ],
    },
}

# ---------------------------------------------------------------- 工具函数

CN_DIGITS = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    """1→一、2→二……（支持到 99，足够小节编号使用）。"""
    if n < 1 or n > 99:
        raise ValueError(f"小节序号超出范围: {n}")
    if n < 10:
        return CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + CN_DIGITS[n - 10]
    tens, ones = divmod(n, 10)
    return CN_DIGITS[tens] + "十" + (CN_DIGITS[ones] if ones else "")


def is_blank(v) -> bool:
    """字符串为空或纯空白视为空。"""
    return isinstance(v, str) and v.strip() == ""


def normalize_list(raw):
    """列表字段归一化：字符串→单元素数组（单项化）；列表→字符串元素列表；
    其他标量→单元素数组。返回 (items, normalized_from)；归一化后为空表即视为空列表。"""
    if isinstance(raw, list):
        return [x if isinstance(x, str) else str(x) for x in raw], None
    if isinstance(raw, str):
        return ([raw] if raw.strip() else []), "string"
    if raw is None:
        return [], None
    return [str(raw)], "scalar"


def missing_kind_of(raw, expected_type: str) -> str:
    if raw is None:
        return "absent"
    if expected_type == "list":
        if isinstance(raw, str):
            return "empty_string" if is_blank(raw) else "absent"
        return "empty_list"
    return "empty_string" if is_blank(raw) else "absent"


# ---------------------------------------------------------------- 字段求值

def evaluate_fields(template_name: str, data: dict) -> dict:
    """按模板 schema 逐字段求值，产出 fields.json 的 fields 记录（含状态与占位语义）。

    status 取值：
      filled               —— 有值，正常渲染；
      missing_placeholder  —— 必填缺失/为空（或选填键存在但为空表），以 ____ 占位渲染；
      missing_omitted      —— 选填缺失，整节 / 整行省略，仅 fields.json 记 missing。
    """
    schema = TEMPLATES[template_name]
    usages = {}

    for part in schema["title_parts"]:
        if "field" in part:
            usages.setdefault(part["field"], []).append("title")
    for sec in schema["sections"]:
        usages.setdefault(sec["field"], []).append("section")
    for line in schema["signature_lines"]:
        usages.setdefault(line["field"], []).append("signature")

    records = {}
    for field, uses in usages.items():
        required = None
        for part in schema["title_parts"]:
            if part.get("field") == field:
                required = part["required"]
        for sec in schema["sections"]:
            if sec["field"] == field:
                required = sec["required"]
        for line in schema["signature_lines"]:
            if line["field"] == field:
                required = line["required"]
        assert required is not None, f"schema 不一致: {field}"

        raw = data.get(field)
        rec = {
            "required": required,
            "expected_type": "list" if "section" in uses else "string",
            "usage": uses,
            "raw_value": raw,
        }

        if required and raw is None:
            rec.update({
                "value": None,
                "status": "required_missing_placeholder",  # 见下方统一改写
                "missing_kind": "absent",
                "placeholder": PLACEHOLDER,
                "note": "必填缺失，以____占位",
            })
            records[field] = rec
            continue

        if not required and raw is None:
            rec.update({
                "value": None,
                "status": "missing_omitted",
                "missing_kind": "absent",
                "note": "选填缺失：整节/整行省略，正文不出现，fields.json 记 missing（required=false）",
            })
            records[field] = rec
            continue

        # 键存在：归一化后判定
        if "section" in uses:
            items, normalized_from = normalize_list(raw)
            if items:
                rec.update({
                    "value": items,
                    "status": "filled",
                })
                if normalized_from == "string":
                    rec["normalized_from"] = "string"
                    rec["normalization"] = "字符串型列表单项化：渲染为单项条目，字段值为单元素数组"
            else:
                kind = missing_kind_of(raw, "list")
                rec.update({
                    "value": [],
                    "status": "missing_placeholder",
                    "missing_kind": kind,
                    "placeholder_entry": f"1{ENTRY_SEP}{PLACEHOLDER}",
                    "note": ("空列表按必填缺失处理：渲染占位条目 1．____，记占位语义"
                             if required else "选填键存在但为空表：同样按占位条目渲染，记占位语义"),
                })
        else:
            # 字符串字段（标题部件 / 落款行）
            if isinstance(raw, list):
                value = "；".join(str(x) for x in raw)
                rec.update({"value": value, "status": "filled",
                            "normalized_from": "list"})
            elif is_blank(raw):
                if required:
                    rec.update({
                        "value": raw if isinstance(raw, str) else "",
                        "status": "missing_placeholder",
                        "missing_kind": "empty_string",
                        "placeholder": PLACEHOLDER,
                        "note": "必填字符串为空，以____占位",
                    })
                else:
                    rec.update({
                        "value": raw if isinstance(raw, str) else "",
                        "status": "missing_omitted",
                        "missing_kind": "empty_string",
                        "note": "选填字符串为空：整节/整行省略，fields.json 记 missing（required=false）",
                    })
            else:
                rec.update({"value": str(raw), "status": "filled"})
        records[field] = rec

    # 统一状态命名（必填缺失的占位一律 missing_placeholder；上方 required_missing_placeholder 仅占位防漏）
    for rec in records.values():
        if rec["status"] == "required_missing_placeholder":
            rec["status"] = "missing_placeholder"

    return records


# ---------------------------------------------------------------- 版面模型

def compose_document(template_name: str, data: dict):
    """把数据 + schema 组装为版面模型：标题、已渲染小节（重编号）、落款行。"""
    schema = TEMPLATES[template_name]
    records = evaluate_fields(template_name, data)

    # 标题
    title = ""
    for part in schema["title_parts"]:
        if "literal" in part:
            title += part["literal"]
            continue
        rec = records[part["field"]]
        if rec["status"] == "filled":
            title += rec["value"]
        elif rec["status"] == "missing_placeholder":
            title += PLACEHOLDER
        # 选填缺失的标题部件：跳过
        rec.setdefault("rendered", {})["title_part"] = (
            rec["value"] if rec["status"] == "filled" else PLACEHOLDER)
        rec["rendered"]["title"] = None  # 占位，稍后统一回填

    for rec in records.values():
        if "rendered" in rec and rec["rendered"].get("title") is None:
            rec["rendered"]["title"] = title

    # 小节（只渲染「有值」或「必填缺失占位」的小节；选填缺失整节省略），编号在已渲染小节上重排
    rendered_sections = []
    section_no = 0
    for sec in schema["sections"]:
        rec = records[sec["field"]]
        if rec["status"] == "missing_omitted":
            rec.setdefault("rendered", {})["section_omitted"] = True
            continue
        section_no += 1
        heading = f"{cn_num(section_no)}{SECTION_SEP}{sec['field']}"
        rec.setdefault("rendered", {})
        if rec["status"] == "missing_placeholder":
            entries = [rec["placeholder_entry"]]
            rec["rendered"].update({"heading": heading, "entries": entries})
            rendered_sections.append({
                "order": section_no, "heading": heading, "field": sec["field"],
                "entries": entries, "placeholder_entry": True,
            })
        else:
            entries = [f"{i}{ENTRY_SEP}{item}" for i, item in enumerate(rec["value"], 1)]
            rec["rendered"].update({"heading": heading, "entries": entries})
            rendered_sections.append({
                "order": section_no, "heading": heading, "field": sec["field"],
                "entries": entries, "placeholder_entry": False,
            })

    # 落款：必填缺失→____ 行（仍右对齐）；选填缺失→整行省略
    signature_lines = []
    omitted = []
    for line in schema["signature_lines"]:
        rec = records[line["field"]]
        if rec["status"] == "filled":
            text = line["format"].format(value=rec["value"])
            signature_lines.append(text)
            rec.setdefault("rendered", {})["signature_line"] = text
        elif rec["status"] == "missing_placeholder":
            text = line["format"].format(value=PLACEHOLDER)
            signature_lines.append(text)
            rec.setdefault("rendered", {})["signature_line"] = text
        else:
            omitted.append({"field": line["field"], "required": rec["required"],
                            "reason": "选填缺失，落款行省略（不影响其余落款行右对齐）"})
            rec.setdefault("rendered", {})["signature_line_omitted"] = True

    return {
        "title": title,
        "sections": rendered_sections,
        "signature": {"alignment": "right", "lines": signature_lines,
                      "omitted_fields": omitted},
        "records": records,
    }


# ---------------------------------------------------------------- OOXML 产出

def w_run(text: str, east_asia: str, sz_half_pt: int, bold: bool = False,
          ascii_font: str = "Times New Roman") -> str:
    rpr = (f'<w:rFonts w:ascii="{ascii_font}" w:eastAsia="{east_asia}"'
           f' w:hAnsi="{ascii_font}" w:cs="{ascii_font}"/>')
    if bold:
        rpr += "<w:b/><w:bCs/>"
    rpr += f'<w:sz w:val="{sz_half_pt}"/><w:szCs w:val="{sz_half_pt}"/>'
    return (f'<w:r><w:rPr>{rpr}</w:rPr>'
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')


def w_para(runs: str, jc: str = None, before: int = 0, after: int = 0,
           line: int = 560, first_line: int = None, pstyle: str = None,
           keep_next: bool = False) -> str:
    ppr = ""
    if pstyle:
        ppr += f'<w:pStyle w:val="{pstyle}"/>'
    if keep_next:
        ppr += "<w:keepNext/>"
    ppr += (f'<w:spacing w:before="{before}" w:after="{after}"'
            f' w:line="{line}" w:lineRule="atLeast"/>')
    if first_line:
        ppr += f'<w:ind w:firstLine="{first_line}"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def build_paragraphs(layout: dict) -> list:
    """公文体版面：二号宋体加粗居中标题；黑体三号小节头（一、二、三、）；
    仿宋三号条目（1．2．3．），固定行距 28 磅（atLeast 防裁切）；落款右对齐仿宋。"""
    paras = []
    # 标题（二号 22pt = sz 44）
    paras.append(w_para(w_run(layout["title"], "宋体", 44, bold=True),
                        jc="center", after=560))
    # 小节头 + 条目（三号 16pt = sz 32；首行缩进 2 字符 = 640 twips）
    for sec in layout["sections"]:
        paras.append(w_para(w_run(sec["heading"], "黑体", 32, bold=True),
                            pstyle="Heading1", keep_next=True,
                            first_line=640, before=120))
        for entry in sec["entries"]:
            paras.append(w_para(w_run(entry, "仿宋", 32),
                                jc="both", first_line=640))
    # 落款（右对齐；与正文之间空一行）
    for i, line in enumerate(layout["signature"]["lines"]):
        paras.append(w_para(w_run(line, "仿宋", 32),
                            jc="right", before=560 if i == 0 else 0))
    return paras


STYLES_XML = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="仿宋" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:color w:val="000000"/><w:kern w:val="2"/><w:sz w:val="32"/><w:szCs w:val="32"/><w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:widowControl/><w:spacing w:line="560" w:lineRule="atLeast"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0" w:line="560" w:lineRule="atLeast"/><w:ind w:firstLine="640"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="黑体" w:hAnsi="Times New Roman"/><w:b/><w:color w:val="000000"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style></w:styles>'''


def build_footer_xml() -> str:
    """页脚：居中「— X —」四号仿宋页码（PAGE 域）。"""
    rpr = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="仿宋"'
           ' w:hAnsi="Times New Roman"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="{W_NS}"><w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="atLeast"/><w:jc w:val="center"/></w:pPr><w:r>{rpr}<w:t xml:space="preserve">— </w:t></w:r><w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rpr}<w:instrText xml:space="preserve"> PAGE \\* MERGEFORMAT </w:instrText></w:r><w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rpr}<w:t>1</w:t></w:r><w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r><w:r>{rpr}<w:t xml:space="preserve"> —</w:t></w:r></w:p></w:ftr>'''


def build_document_xml(paras: list) -> str:
    sectpr = (f'<w:sectPr><w:footerReference w:type="default" r:id="rId2"/>'
              f'<w:pgSz w:w="11906" w:h="16838"/>'
              f'<w:pgMar w:top="1440" w:right="1417" w:bottom="1440" w:left="1701"'
              f' w:header="851" w:footer="992" w:gutter="0"/>'
              f'<w:cols w:space="425"/></w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}"><w:body>'
            + "".join(paras) + sectpr + "</w:body></w:document>")


def build_docx_bytes(title: str, paras: list) -> bytes:
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                     '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                     '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
                '</Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
            ' xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:title>{escape(title)}</dc:title>'
            '<dc:creator>office 模板生成器</dc:creator>'
            '<cp:lastModifiedBy>office 模板生成器</cp:lastModifiedBy>'
            '</cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>OfficeDocGen</Application></Properties>')

    parts = {
        "[Content_Types].xml": content_types,
        "_rels/.rels": rels,
        "docProps/core.xml": core,
        "docProps/app.xml": app,
        "word/document.xml": build_document_xml(paras),
        "word/styles.xml": STYLES_XML,
        "word/_rels/document.xml.rels": doc_rels,
        "word/footer1.xml": build_footer_xml(),
    }
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ["[Content_Types].xml", "_rels/.rels", "docProps/core.xml",
                     "docProps/app.xml", "word/document.xml", "word/styles.xml",
                     "word/_rels/document.xml.rels", "word/footer1.xml"]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, parts[name].encode("utf-8"))
    return buf.getvalue()


# ---------------------------------------------------------------- 主流程

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="周报/工作总结 模板文书生成器：--template <周报|工作总结> "
                    "--data <数据json路径> --outdir <输出目录>；生成 文书.docx 与 fields.json")
    parser.add_argument("--template", required=True, help="模板名：周报 或 工作总结")
    parser.add_argument("--data", required=True, help="数据 json 路径")
    parser.add_argument("--outdir", required=True, help="输出目录")
    args = parser.parse_args(argv)

    if args.template not in TEMPLATES:
        print(f"[gen_doc] 错误：未知模板 {args.template!r}（可选：{'、'.join(TEMPLATES)}）",
              file=sys.stderr)
        return 3

    try:
        with open(args.data, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[gen_doc] 错误：数据文件读取失败 {args.data}: {exc}", file=sys.stderr)
        return 4
    if not isinstance(data, dict):
        print("[gen_doc] 错误：数据 json 顶层必须是对象", file=sys.stderr)
        return 4

    layout = compose_document(args.template, data)
    schema = TEMPLATES[args.template]
    known = set()
    for part in schema["title_parts"]:
        if "field" in part:
            known.add(part["field"])
    for sec in schema["sections"]:
        known.add(sec["field"])
    for line in schema["signature_lines"]:
        known.add(line["field"])
    extra = [k for k in data if k not in known]

    # fields.json（无时间戳，保证确定性）
    fields_json = {
        "template": args.template,
        "data_source": args.data,
        "artifacts": {"document": "文书.docx", "fields": "fields.json"},
        "title": layout["title"],
        "numbering": {"sections": "一、二、三、…", "entries": "1．2．3．…"},
        "fields": layout["records"],
        "extra_input_fields": extra,
        "rendered_sections": layout["sections"],
        "signature": layout["signature"],
    }

    os.makedirs(args.outdir, exist_ok=True)
    docx_path = os.path.join(args.outdir, "文书.docx")
    fields_path = os.path.join(args.outdir, "fields.json")

    paras = build_paragraphs(layout)
    with open(docx_path, "wb") as fh:
        fh.write(build_docx_bytes(layout["title"], paras))
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(fields_json, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    sec_summary = "；".join(
        f"{s['heading']}" + ("（占位）" if s["placeholder_entry"] else "")
        for s in layout["sections"])
    print(f"[gen_doc] template={args.template} data={args.data} outdir={args.outdir}")
    print(f"[gen_doc] 标题：{layout['title']}")
    print(f"[gen_doc] 小节：{sec_summary or '（无）'}")
    if layout["signature"]["omitted_fields"]:
        omits = "、".join(f"{o['field']}(选填缺失省略)"
                          for o in layout["signature"]["omitted_fields"])
        print(f"[gen_doc] 落款省略：{omits}")
    print(f"[gen_doc] 落款（右对齐）：{' ／ '.join(layout['signature']['lines']) or '（无）'}")
    print(f"[gen_doc] 产物：{docx_path}（{len(paras)} 段）、{fields_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
