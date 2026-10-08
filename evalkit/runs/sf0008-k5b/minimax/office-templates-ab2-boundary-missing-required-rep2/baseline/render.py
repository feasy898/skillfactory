#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板渲染器（请示函 / 会议通知）。

用法:
    python3 render.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>

每次调用在 --outdir 下生成两个产物：
    文书.docx     渲染后的文书（必填缺失以 ____ 占位，缺数据不编造）
    fields.json   字段记账（filled / missing_required / missing_optional / unknown_keys）

核心契约：
    * 必填缺失 -> 以 ____ 占位渲染，记入 missing_required，程序正常结束（退出码 0）
    * 选填缺失 -> 该行留空或整段省略，记入 missing_optional，不得误记为必填缺失
    * 模板外键 -> 不进正文，记入 unknown_keys
    * 版式不因缺数据而破坏：称谓顶格（无首行缩进）、落款右对齐

实现只依赖标准库：DOCX 直接以 OOXML 写出，避免第三方库依赖。
"""

import argparse
import json
import os
import sys
import zipfile

PLACEHOLDER = "____"

# --------------------------------------------------------------------------
# 模板字段定义
# --------------------------------------------------------------------------

TEMPLATES = {
    "请示函": {
        "title": "请 示",
        "salutation_field": "主送机关",
        "required": ["主送机关", "请示事由", "请示缘由", "请示事项", "请示单位"],
        "optional": ["联系人", "联系电话", "成文日期"],
        "body_fields": ["请示事由", "请示缘由", "请示事项"],
        "closing": "以上请示，妥否，请批示。",
        "issuer_field": "请示单位",
        "date_field": "成文日期",
        "contact_fields": ["联系人", "联系电话"],
        "contact_pattern": "（{name}：{value}）",
        "date_pattern": "{value}",
    },
    "会议通知": {
        "title": "会议通知",
        "salutation_field": "主送对象",
        "required": [
            "会议名称",
            "召开单位",
            "主送对象",
            "会议时间",
            "会议地点",
            "参会人员",
            "发文日期",
        ],
        "optional": ["会议议题", "会议要求", "联系人", "联系电话"],
        "body_fields": ["会议名称", "召开单位", "会议时间", "会议地点", "参会人员", "会议议题", "会议要求"],
        "closing": "特此通知。",
        "issuer_field": "召开单位",
        "date_field": "发文日期",
        "contact_fields": ["联系人", "联系电话"],
        "contact_pattern": "{name}：{value}",
        "date_pattern": "{value}",
    },
}


# --------------------------------------------------------------------------
# 输入解析与记账
# --------------------------------------------------------------------------


def classify(template, data):
    """把输入按键归类为 filled / missing_required / missing_optional / unknown_keys。

    「缺失」的判定口径：键不存在、值为 None、或值为去掉首尾空白后的空字符串。
    这三种情况在正文里一律不编造内容。
    """
    spec = TEMPLATES[template]
    known = list(spec["required"]) + list(spec["optional"])

    def is_missing(key):
        if key not in data:
            return True
        value = data[key]
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    fields = []
    for name in known:
        required = name in spec["required"]
        missing = is_missing(name)
        if missing:
            state = "missing_required" if required else "missing_optional"
            value = None
            rendered = PLACEHOLDER if required else ""
        else:
            state = "filled"
            value = data[name]
            rendered = str(value)
        fields.append(
            {
                "name": name,
                "required": required,
                "state": state,
                "value": value,
                "rendered": rendered,
            }
        )

    unknown = [k for k in data.keys() if k not in known]
    unknown_detail = [
        {
            "key": k,
            "value": data[k],
            "reason": "该键不在模板字段定义内，未进入正文",
        }
        for k in unknown
    ]

    return {
        "fields": fields,
        "filled_fields": [f["name"] for f in fields if f["state"] == "filled"],
        "missing_required": [f["name"] for f in fields if f["state"] == "missing_required"],
        "missing_optional": [f["name"] for f in fields if f["state"] == "missing_optional"],
        "unknown_keys": unknown,
        "unknown_keys_detail": unknown_detail,
    }


def value_of(book, name):
    for field in book["fields"]:
        if field["name"] == name:
            return field["value"]
    return None


# --------------------------------------------------------------------------
# 版式：段落描述
# --------------------------------------------------------------------------

FONT_BODY = "宋体"
FONT_TITLE = "黑体"
SZ_TITLE = 36   # 小二
SZ_BODY = 32    # 三号


def para(text, align="left", indent=False, bold=False, font=FONT_BODY, size=SZ_BODY):
    return {
        "text": text,
        "align": align,
        "indent": indent,
        "bold": bold,
        "font": font,
        "size": size,
    }


def build_paragraphs(template, book):
    """组装版式。缺数据只影响内容行，不影响称谓顶格与落款右对齐。"""
    spec = TEMPLATES[template]
    paras = [para(spec["title"], align="center", indent=False, bold=True, font=FONT_TITLE, size=SZ_TITLE)]

    # 称谓行：顶格（无首行缩进）。缺失时以「字段名：____」如实占位。
    sal_field = spec["salutation_field"]
    sal_value = value_of(book, sal_field)
    if sal_value is None:
        salutation = "%s：%s" % (sal_field, PLACEHOLDER)
    else:
        salutation = "%s：" % sal_value
    paras.append(para(salutation, align="left", indent=False))
    paras.append(para("", align="left", indent=False))

    # 正文逐字段段：首行缩进 2 字符。
    for name in spec["body_fields"]:
        value = value_of(book, name)
        required = name in spec["required"]
        if value is None:
            # 必填缺失 -> ____ 占位；选填缺失 -> 整段省略，不留空行破坏观感。
            if required:
                paras.append(para("%s：%s" % (name, PLACEHOLDER), align="both", indent=True))
            continue
        paras.append(para("%s：%s" % (name, value), align="both", indent=True))

    # 结束语
    paras.append(para(spec["closing"], align="both", indent=True))
    paras.append(para("", align="left", indent=False))

    # 落款：右对齐（缺数据不破坏对齐）
    issuer = value_of(book, spec["issuer_field"])
    if issuer is not None:
        paras.append(para(issuer, align="right", indent=False))

    for name in spec["contact_fields"]:
        value = value_of(book, name)
        if value is None:
            continue  # 选填缺失 -> 省略该行
        paras.append(para(spec["contact_pattern"].format(name=name, value=value), align="right", indent=False))

    date_value = value_of(book, spec["date_field"])
    if date_value is not None:
        paras.append(para(spec["date_pattern"].format(value=date_value), align="right", indent=False))

    return paras


# --------------------------------------------------------------------------
# DOCX 写出（纯标准库）
# --------------------------------------------------------------------------

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def paragraph_xml(p):
    parts = ["<w:p><w:pPr>"]
    parts.append('<w:spacing w:line="480" w:lineRule="auto" w:before="0" w:after="0"/>')
    parts.append('<w:jc w:val="%s"/>' % p["align"])
    if p["indent"]:
        parts.append('<w:ind w:firstLineChars="200" w:firstLine="640"/>')
    parts.append('<w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="%s" w:hAnsi="Times New Roman"/>' % p["font"])
    if p["bold"]:
        parts.append("<w:b/><w:bCs/>")
    parts.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>' % (p["size"], p["size"]))
    parts.append("</w:pPr>")
    if p["text"] != "":
        parts.append("<w:r>")
        parts.append('<w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="%s" w:hAnsi="Times New Roman"/>' % p["font"])
        if p["bold"]:
            parts.append("<w:b/><w:bCs/>")
        parts.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>' % (p["size"], p["size"]))
        parts.append('<w:t xml:space="preserve">%s</w:t>' % esc(p["text"]))
        parts.append("</w:r>")
    parts.append("</w:p>")
    return "".join(parts)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles %s>
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:eastAsia="\u5b8b\u4f53" w:hAnsi="Times New Roman"/>
<w:sz w:val="32"/><w:szCs w:val="32"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:line="480" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
</w:styles>""" % W_NS

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>%s</dc:title><dc:creator>render.py</dc:creator><cp:lastModifiedBy>render.py</cp:lastModifiedBy>
</cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>render.py</Application>
</Properties>"""


def write_docx(path, title, paras):
    body = "".join(paragraph_xml(p) for p in paras)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document %s><w:body>%s'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1588" w:bottom="1440" w:left="1588" '
        'w:header="851" w:footer="992" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>" % (W_NS, body)
    )
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "word/document.xml": document,
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES,
        "docProps/core.xml": CORE % esc(title),
        "docProps/app.xml": APP,
    }
    order = [
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "docProps/core.xml",
        "docProps/app.xml",
    ]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in order:
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, parts[name].encode("utf-8"))


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def load_data(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError("数据文件不是合法 JSON：%s" % exc)
    if not isinstance(data, dict):
        raise ValueError("数据文件顶层必须是 JSON 对象，实际为 %s" % type(data).__name__)
    return data


def render(template, data_path, outdir):
    if template not in TEMPLATES:
        raise ValueError("未知模板：%s（可选 %s）" % (template, "/".join(TEMPLATES)))
    data = load_data(data_path)

    book = classify(template, data)
    paras = build_paragraphs(template, book)

    os.makedirs(outdir, exist_ok=True)
    docx_path = os.path.join(outdir, "\u6587\u4e66.docx")
    fields_path = os.path.join(outdir, "fields.json")

    write_docx(docx_path, TEMPLATES[template]["title"], paras)

    spec = TEMPLATES[template]
    record = {
        "template": template,
        "data_path": data_path,
        "outputs": {"docx": "\u6587\u4e66.docx", "fields": "fields.json"},
        "status": "ok",
        "exit_code": 0,
        "placeholder": PLACEHOLDER,
        "policy": {
            "missing_required": "\u4ee5 %s \u5360\u4f4d\u6e32\u67d3\uff0c\u7a0b\u5e8f\u6b63\u5e38\u7ed3\u675f" % PLACEHOLDER,
            "missing_optional": "\u8be5\u6bb5\u7701\u7565\uff0c\u4e0d\u8bb0\u4e3a\u5fc5\u586b\u7f3a\u5931",
            "unknown_keys": "\u4e0d\u8fdb\u5165\u6b63\u6587\uff0c\u8bb0\u5165 unknown_keys",
        },
        "field_definitions": {"required": list(spec["required"]), "optional": list(spec["optional"])},
        "counts": {
            "total": len(book["fields"]),
            "filled": len(book["filled_fields"]),
            "missing_required": len(book["missing_required"]),
            "missing_optional": len(book["missing_optional"]),
            "unknown_keys": len(book["unknown_keys"]),
        },
        "filled_fields": book["filled_fields"],
        "missing_required": book["missing_required"],
        "missing_optional": book["missing_optional"],
        "unknown_keys": book["unknown_keys"],
        "unknown_keys_detail": book["unknown_keys_detail"],
        "fields": book["fields"],
        "paragraphs": [
            {"text": p["text"], "align": p["align"], "first_line_indent": p["indent"]} for p in paras
        ],
    }

    with open(fields_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("模板：%s" % template)
    print("已填字段：%s" % ("、".join(book["filled_fields"]) or "（无）"))
    print("必填缺失：%s" % ("、".join(book["missing_required"]) or "（无）"))
    print("选填缺失：%s" % ("、".join(book["missing_optional"]) or "（无）"))
    print("模板外键：%s" % ("、".join(book["unknown_keys"]) or "（无）"))
    print("产物：%s、%s" % (docx_path, fields_path))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="公文模板渲染器（请示函 / 会议通知）")
    parser.add_argument("--template", required=True, help="模板名：请示函 | 会议通知")
    parser.add_argument("--data", required=True, help="数据 JSON 路径")
    parser.add_argument("--outdir", required=True, help="输出目录（写入 文书.docx 与 fields.json）")
    args = parser.parse_args(argv)
    try:
        return render(args.template, args.data, args.outdir)
    except (OSError, ValueError) as exc:
        sys.stderr.write("错误：%s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())