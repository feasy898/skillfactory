#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_doc.py —— 办公文书模板生成器（缺字段边界处理）

命令行契约：
    python3 gen_doc.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>

每次调用在 --outdir 下生成两个产物：
    文书.docx    按模板版式渲染的 Word 文书
    fields.json  字段记账（present / missing_required / missing_optional / unknown_keys）

核心行为约定：
  1. 缺数据不编造：必填缺失一律以 ``____`` 占位渲染，程序正常结束，退出码 0。
  2. 选填缺失：留空或整段省略，绝不渲染成必填占位，也不计入 missing_required。
  3. 模板外键（unknown_keys）只记账、不渲染。
  4. 版式不因缺数据而破坏：称谓顶格（无缩进、左对齐），落款右对齐。

实现只依赖标准库：.docx 由 OOXML（zip + WordprocessingML）直接打包，
不依赖 python-docx，保证在任何环境下均可复现。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import zipfile

PLACEHOLDER = "____"          # 必填缺失占位符
DOCX_NAME = "文书.docx"
FIELDS_NAME = "fields.json"

# ---------------------------------------------------------------------------
# 一、模板字段定义
#
# required=True  -> 缺失时以 ____ 占位渲染，并记入 missing_required
# required=False -> 缺失时留空/省略，记入 missing_optional
# 声明顺序即记账顺序，保证输出稳定可比。
# ---------------------------------------------------------------------------

TEMPLATES = {
    "请示函": {
        "title": "请示函",
        "fields": [
            {"name": "主送机关", "required": True, "role": "称谓", "layout": "顶格"},
            {"name": "请示事由", "required": True, "role": "正文"},
            {"name": "请示缘由", "required": True, "role": "正文"},
            {"name": "请示事项", "required": True, "role": "正文"},
            {"name": "请示单位", "required": True, "role": "落款", "layout": "右对齐"},
            {"name": "联系人", "required": False, "role": "落款", "layout": "右对齐"},
            {"name": "联系电话", "required": False, "role": "落款", "layout": "右对齐"},
            {"name": "成文日期", "required": False, "role": "落款", "layout": "右对齐"},
        ],
    },
    "会议通知": {
        "title": "会议通知",
        "fields": [
            {"name": "会议名称", "required": True, "role": "标题", "layout": "居中"},
            {"name": "主送对象", "required": True, "role": "称谓", "layout": "顶格"},
            {"name": "召开单位", "required": True, "role": "正文"},
            {"name": "会议时间", "required": True, "role": "正文"},
            {"name": "会议地点", "required": True, "role": "正文"},
            {"name": "参会人员", "required": True, "role": "正文"},
            {"name": "会议议题", "required": False, "role": "正文"},
            {"name": "会议要求", "required": False, "role": "正文"},
            {"name": "联系人", "required": False, "role": "落款", "layout": "右对齐"},
            {"name": "联系电话", "required": False, "role": "落款", "layout": "右对齐"},
            {"name": "发文日期", "required": False, "role": "落款", "layout": "右对齐"},
        ],
    },
}

# 缺失原因（用于 fields.json 如实记账）
REASON_ABSENT = "absent_key"        # 输入中根本没有该键
REASON_EMPTY = "empty_string"       # 键在但值为空字符串
REASON_NULL = "json_null"           # 键在但值为 null
REASON_BLANK = "whitespace_only"    # 键在但只有空白字符

REASON_TEXT = {
    REASON_ABSENT: "输入数据中无此键",
    REASON_EMPTY: "输入数据中该键为空字符串",
    REASON_NULL: "输入数据中该键为 null",
    REASON_BLANK: "输入数据中该键仅有空白字符",
}


# ---------------------------------------------------------------------------
# 二、字段分类：把输入事实原样分成 present / missing_required / missing_optional
# ---------------------------------------------------------------------------

def _classify_value(value):
    """返回 (ok, 归一化文本, 缺失原因)。ok=False 表示按「缺失」处理。"""
    if value is None:
        return False, "", REASON_NULL
    if isinstance(value, bool):
        return True, ("是" if value else "否"), ""
    if isinstance(value, (int, float)):
        return True, str(value), ""
    if isinstance(value, str):
        if value == "":
            return False, "", REASON_EMPTY
        if value.strip() == "":
            return False, "", REASON_BLANK
        return True, value.strip(), ""
    # 列表/字典等结构化值按 JSON 文本呈现，不做任何臆测加工
    return True, json.dumps(value, ensure_ascii=False, sort_keys=True), ""


def classify(data, tpl):
    """按模板逐字段分类；返回 (field_records, missing_required, missing_optional)。"""
    records = []
    missing_required = []
    missing_optional = []

    for spec in tpl["fields"]:
        name = spec["name"]
        required = spec["required"]
        rec = {
            "name": name,
            "required": required,
            "role": spec.get("role", "正文"),
            "layout": spec.get("layout", "正文缩进"),
            "present_in_input": name in data,
        }
        if name in data:
            ok, text, reason = _classify_value(data[name])
            if ok:
                rec["state"] = "present"
                rec["value"] = text
                rec["rendered"] = text
                rec["missing_reason"] = ""
            else:
                rec["value"] = None
                rec["rendered"] = PLACEHOLDER if required else ""
                rec["missing_reason"] = reason
                rec["state"] = "missing_required" if required else "missing_optional"
                (missing_required if required else missing_optional).append(name)
        else:
            rec["value"] = None
            rec["rendered"] = PLACEHOLDER if required else ""
            rec["missing_reason"] = REASON_ABSENT
            rec["state"] = "missing_required" if required else "missing_optional"
            (missing_required if required else missing_optional).append(name)
        records.append(rec)

    return records, missing_required, missing_optional


def find_unknown_keys(data, tpl):
    known = {f["name"] for f in tpl["fields"]}
    return [k for k in data.keys() if k not in known]


# ---------------------------------------------------------------------------
# 三、OOXML 打包（.docx = zip）
# ---------------------------------------------------------------------------

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
# 固定时间戳，保证同样输入产出逐字节一致的 docx
FIXED_DT = (2026, 10, 9, 0, 0, 0)


def esc(text):
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def run_xml(text, size=32, bold=False, east_asia="宋体", ascii_font="Times New Roman"):
    if text == "":
        return ""
    rpr = ['<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>'
           % (ascii_font, ascii_font, east_asia, ascii_font)]
    if bold:
        rpr.append("<w:b/><w:bCs/>")
    rpr.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size))
    return ('<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>'
            % ("".join(rpr), esc(text)))


def para_xml(text="", align="both", first_line_chars=200, size=32, bold=False,
             east_asia="宋体", ascii_font="Times New Roman", line=560,
             before=0, after=0):
    """一段。first_line_chars=0 且 align=left => 称谓顶格；align=right => 落款右对齐。"""
    # w:pPr 子元素必须按 CT_PPr schema 顺序：
    # kinsoku -> overflowPunct -> spacing -> ind -> jc
    # kinsoku/overflowPunct 开启中文避头尾，避免标点出现在行首。
    ppr = ["<w:kinsoku/><w:overflowPunct/>",
           '<w:spacing w:before="%d" w:after="%d" w:line="%d" w:lineRule="exact"/>'
           % (before, after, line)]
    if first_line_chars > 0:
        # 只用 w:firstLine（缇，twips）。实测 firstLineChars 与 firstLine 并存时
        # LibreOffice 会误判该段为右对齐，故此处不写 firstLineChars。
        # first_line_chars 单位为字符的百分之一（200 = 2 字），字号 sz 单位为半点
        # （sz/2 = 磅），1 磅 = 20 缇 => 缇 = chars/100 × (sz/2) × 20
        ppr.append('<w:ind w:left="0" w:right="0" w:firstLine="%d"/>'
                   % (first_line_chars * size // 10))
    ppr.append('<w:jc w:val="%s"/>' % ("both" if align == "both" else align))
    body = run_xml(text, size=size, bold=bold, east_asia=east_asia, ascii_font=ascii_font)
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % ("".join(ppr), body)


# 版式常量
SZ_TITLE = 44    # 二号
SZ_BODY = 32     # 三号
SZ_LABEL = 32
FONT_TITLE = "宋体"


_SENT_END = "。！？；.!?;"


def _ensure_period(s):
    """确保句末有句号，避免拼接时出现「。」+「，」这类重复标点。"""
    s = (s or "").strip()
    if not s:
        return ""
    return s if s[-1] in _SENT_END else s + "。"


def render_paragraphs(template_name, val):
    """按模板组装段落序列。val: {字段名: 渲染文本（缺失必填为 ____，缺失选填为 ''）}"""
    paras = []

    if template_name == "请示函":
        # 称谓：顶格（左对齐、无缩进），即便缺失也保持顶格结构
        paras.append(para_xml(val["主送机关"] + "：", align="left", first_line_chars=0))
        # 正文：首行缩进 2 字符
        paras.append(para_xml(_ensure_period(val["请示事由"])
                              + _ensure_period(val["请示缘由"]) + "现请示如下："))
        paras.append(para_xml(val["请示事项"]))
        paras.append(para_xml("妥否，请批示。"))
        # 落款：右对齐
        paras.append(para_xml(val["请示单位"], align="right", first_line_chars=0))
        contact = _contact_line(val)
        if contact:
            paras.append(para_xml(contact, align="right", first_line_chars=0))
        if val["成文日期"]:                       # 选填缺失 -> 整段省略
            paras.append(para_xml(val["成文日期"], align="right", first_line_chars=0))
        return paras

    if template_name == "会议通知":
        # 标题：居中
        paras.append(para_xml(val["会议名称"], align="center", first_line_chars=0,
                              size=SZ_TITLE, bold=True, east_asia=FONT_TITLE,
                              line=640, after=200))
        # 称谓：顶格
        paras.append(para_xml(val["主送对象"] + "：", align="left", first_line_chars=0))
        # 正文（会议名称/会议地点 缺失时以 ____ 占位，占位后不再接标点，
        #      避免占位符折行导致标点出现在行首）
        paras.append(para_xml(
            "%s定于%s召开%s。参加人员：%s。会议地点：%s"
            % (val["召开单位"], val["会议时间"], val["会议名称"], val["参会人员"], val["会议地点"])))
        if val["会议议题"]:                       # 选填缺失 -> 整段省略
            paras.append(para_xml("会议议题：" + val["会议议题"]))
        if val["会议要求"]:                       # 选填缺失 -> 整段省略
            paras.append(para_xml("会议要求：" + val["会议要求"]))
        # 落款：右对齐
        paras.append(para_xml(val["召开单位"], align="right", first_line_chars=0))
        contact = _contact_line(val)
        if contact:
            paras.append(para_xml(contact, align="right", first_line_chars=0))
        if val["发文日期"]:                       # 选填缺失 -> 整段省略
            paras.append(para_xml(val["发文日期"], align="right", first_line_chars=0))
        return paras

    raise ValueError("未知模板：%s" % template_name)


def _contact_line(val):
    """联系人 / 联系电话 拼成一行；两者皆缺则返回空串（整段省略）。"""
    parts = []
    if val.get("联系人"):
        parts.append("联系人：" + val["联系人"])
    if val.get("联系电话"):
        parts.append("联系电话：" + val["联系电话"])
    return "  ".join(parts)


SECT_PR = (
    "<w:sectPr>"
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="2098" w:right="1474" w:bottom="1984" w:left="1588" '
    'w:header="851" w:footer="992" w:gutter="0"/>'
    '<w:cols w:space="425"/>'
    '<w:docGrid w:type="none" w:linePitch="312"/>'
    "</w:sectPr>"
)


def build_docx(paragraphs, template_name):
    document = (XML_DECL
                + '<w:document xmlns:w="%s"><w:body>%s%s</w:body></w:document>'
                % (NS_W, "".join(paragraphs), SECT_PR))

    styles = (XML_DECL
              + '<w:styles xmlns:w="%s">'
                '<w:docDefaults><w:rPrDefault><w:rPr>'
                '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
                'w:eastAsia="宋体" w:cs="Times New Roman"/>'
                '<w:sz w:val="%d"/><w:szCs w:val="%d"/>'
                '</w:rPr></w:rPrDefault>'
                '<w:pPrDefault><w:pPr>'
                '<w:spacing w:line="560" w:lineRule="exact"/>'
                '</w:pPr></w:pPrDefault></w:docDefaults>'
                '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
                '<w:name w:val="Normal"/><w:qFormat/></w:style>'
                '</w:styles>' % (NS_W, SZ_BODY, SZ_BODY))

    content_types = (XML_DECL
                     + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                       '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                       '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                       '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                       '</Types>')

    root_rels = (XML_DECL
                 + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                   '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
                   '</Relationships>')

    doc_rels = (XML_DECL
                + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                  '</Relationships>')

    now = "%sZ" % _dt.datetime(2026, 10, 9, 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
    core = (XML_DECL
            + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
              'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
              '<dc:title>%s</dc:title><dc:creator>gen_doc.py</dc:creator>'
              '<cp:lastModifiedBy>gen_doc.py</cp:lastModifiedBy>'
              '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
              '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
              '</cp:coreProperties>' % (esc(template_name), now, now))

    app = (XML_DECL
           + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
             'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
             '<Application>gen_doc.py</Application></Properties>')

    parts = [
        ("[Content_Types].xml", content_types),
        ("_rels/.rels", root_rels),
        ("docProps/core.xml", core),
        ("docProps/app.xml", app),
        ("word/_rels/document.xml.rels", doc_rels),
        ("word/document.xml", document),
        ("word/styles.xml", styles),
    ]
    return parts


def write_docx(path, parts):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts:
            info = zipfile.ZipInfo(name, date_time=FIXED_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, data.encode("utf-8"))


# ---------------------------------------------------------------------------
# 四、主流程
# ---------------------------------------------------------------------------

def generate(template_name, data_path, outdir):
    if template_name not in TEMPLATES:
        raise SystemExit("错误：未知模板 %r，可选：%s"
                         % (template_name, "、".join(TEMPLATES.keys())))
    if not os.path.isfile(data_path):
        raise SystemExit("错误：数据文件不存在：%s" % data_path)

    with open(data_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit("错误：数据文件顶层必须是 JSON 对象：%s" % data_path)

    tpl = TEMPLATES[template_name]
    records, missing_required, missing_optional = classify(data, tpl)
    unknown_keys = find_unknown_keys(data, tpl)

    val = {r["name"]: r["rendered"] for r in records}
    paragraphs = render_paragraphs(template_name, val)

    os.makedirs(outdir, exist_ok=True)
    docx_path = os.path.join(outdir, DOCX_NAME)
    fields_path = os.path.join(outdir, FIELDS_NAME)

    write_docx(docx_path, build_docx(paragraphs, template_name))

    fields = {
        "template": template_name,
        "template_title": tpl["title"],
        "data_path": os.path.relpath(data_path, start=os.getcwd()),
        "generator": "gen_doc.py",
        "placeholder": PLACEHOLDER,
        "artifacts": [DOCX_NAME, FIELDS_NAME],
        "fields": records,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "unknown_keys": unknown_keys,
        "unknown_key_values": {k: data[k] for k in unknown_keys},
        "missing_reason_detail": {
            r["name"]: r["missing_reason"]
            for r in records if r["missing_reason"]
        },
        "missing_reason_text": {
            r["name"]: REASON_TEXT[r["missing_reason"]]
            for r in records if r["missing_reason"]
        },
        "counts": {
            "schema_fields": len(records),
            "input_keys": len(data),
            "present": sum(1 for r in records if r["state"] == "present"),
            "missing_required": len(missing_required),
            "missing_optional": len(missing_optional),
            "unknown_keys": len(unknown_keys),
        },
        "exit_code": 0,
    }
    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(fields, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    return fields


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gen_doc.py",
        description="按模板渲染文书并如实记账缺失字段（缺数据不编造）")
    ap.add_argument("--template", required=True, choices=sorted(TEMPLATES.keys()),
                    help="模板名：请示函 / 会议通知")
    ap.add_argument("--data", required=True, help="数据 JSON 路径")
    ap.add_argument("--outdir", required=True, help="输出目录（生成 文书.docx 与 fields.json）")
    args = ap.parse_args(argv)

    fields = generate(args.template, args.data, args.outdir)
    c = fields["counts"]
    print("[gen_doc] 模板=%s outdir=%s" % (fields["template"], args.outdir))
    print("[gen_doc] 字段 %d：命中 %d / 必填缺失 %d / 选填缺失 %d / 模板外键 %d"
          % (c["schema_fields"], c["present"], c["missing_required"],
             c["missing_optional"], c["unknown_keys"]))
    if fields["missing_required"]:
        print("[gen_doc] 必填缺失（以 %s 占位）：%s"
              % (PLACEHOLDER, "、".join(fields["missing_required"])))
    if fields["missing_optional"]:
        print("[gen_doc] 选填缺失（留空/省略，未误记为必填）：%s"
              % "、".join(fields["missing_optional"]))
    if fields["unknown_keys"]:
        print("[gen_doc] 模板外键（仅记账、不渲染）：%s"
              % "、".join(fields["unknown_keys"]))
    print("[gen_doc] 产物：%s、%s" % (DOCX_NAME, FIELDS_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(main())