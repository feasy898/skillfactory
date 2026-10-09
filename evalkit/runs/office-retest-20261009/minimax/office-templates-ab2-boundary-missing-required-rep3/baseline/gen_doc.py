#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公文模板渲染器（请示函 / 会议通知）。

命令行契约：
    python3 gen_doc.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>

每次调用在 --outdir 下生成且仅生成两个产物：
    文书.docx    —— 按模板版式渲染的公文
    fields.json  —— 字段记账（必填缺失 / 选填缺失 / 模板外键）

核心行为（缺数据不编造、如实记账）：
  * 必填字段缺失（键不存在，或值为空串 / 纯空白）→ 以 ____ 占位渲染，程序正常结束（退出码 0）；
  * 选填字段缺失 → 该行留空或整行省略，且**不**记入 missing_required；
  * 模板外键（数据里有、模板里没有的键）→ 记入 unknown_keys，不渲染进正文；
  * 任何情况下都不推断、不编造、不用默认值填充缺失数据。

实现说明：DOCX 采用标准库 zipfile + OOXML 直写，不依赖 python-docx，
保证在任何 Python 3 环境下都可运行。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

PLACEHOLDER = "____"          # 必填缺失占位符（四个下划线）
DOCX_NAME = "文书.docx"
FIELDS_NAME = "fields.json"

# ---------------------------------------------------------------------------
# 模板定义：字段 -> 是否必填
#   required=True  缺失时以 PLACEHOLDER 占位渲染，并记入 missing_required
#   required=False 缺失时整行省略（留空），记入 missing_optional
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "请示函": {
        "required": ["主送机关", "请示事由", "请示缘由", "请示事项", "请示单位"],
        "optional": ["联系人", "联系电话", "成文日期"],
        "order": [
            "主送机关", "请示事由", "请示缘由", "请示事项",
            "请示单位", "成文日期", "联系人", "联系电话",
        ],
    },
    "会议通知": {
        "required": ["会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "参会人员", "发文日期"],
        "optional": ["会议议题", "会议要求", "联系人", "联系电话"],
        "order": [
            "会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
            "参会人员", "会议议题", "会议要求", "发文日期", "联系人", "联系电话",
        ],
    },
}


# ---------------------------------------------------------------------------
# 数据读取与缺失判定
# ---------------------------------------------------------------------------

def _is_blank(value: Any) -> bool:
    """键不存在、或值为空串 / 纯空白 / 非标量，均视为“无有效数据”。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        # 空容器同样无内容；非空容器按原样字符串化处理，不做编造
        return len(value) == 0
    return False


def load_data(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("数据 json 顶层必须是对象")
    return data


def audit(template: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """按模板审计输入数据，产出如实记账的结果（不推断、不补全）。"""
    spec = TEMPLATES[template]
    known = set(spec["required"]) | set(spec["optional"])

    fields: Dict[str, Dict[str, Any]] = {}
    missing_required: List[str] = []
    missing_optional: List[str] = []

    for name in spec["order"]:
        required = name in spec["required"]
        present = name in data and not _is_blank(data[name])
        raw = data.get(name)
        value = "" if raw is None else (raw if isinstance(raw, str) else str(raw))
        fields[name] = {
            "required": required,
            "present_in_input": name in data,
            "filled": present,
            "value": value if present else "",
            "render_as": PLACEHOLDER if (not present and required) else ("line" if present else "omit"),
        }
        if not present:
            (missing_required if required else missing_optional).append(name)

    unknown_keys = sorted(k for k in data.keys() if k not in known)
    unknown_key_values = {k: (data[k] if isinstance(data[k], str) else str(data[k])) for k in unknown_keys}

    return {
        "template": template,
        "fields": fields,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "unknown_keys": unknown_keys,
        "unknown_key_values": unknown_key_values,
    }


# ---------------------------------------------------------------------------
# 极简 OOXML DOCX 写入器（标准库）
# ---------------------------------------------------------------------------

_FONT_BODY = "仿宋"
_FONT_TITLE = "方正小标宋简体"
_FONT_HEAD = "黑体"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _run(text: str, *, font: str = _FONT_BODY, size: int = 32, bold: bool = False) -> str:
    rpr = (
        '<w:rPr>'
        f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="{_esc(font)}" w:cs="Times New Roman"/>'
        + ("<w:b/><w:bCs/>" if bold else "")
        + f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        "</w:rPr>"
    )
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'


def _para(
    runs: str,
    *,
    align: str = "left",          # left | center | right
    first_line_chars: int = 200,  # 首行缩进（百分之一字符）；0 = 顶格
    space_after: int = 0,
    line: int = 360,
) -> str:
    if first_line_chars:
        # 同时给出 firstLineChars（Word 精确按字符缩进）与 firstLine（twips，
        # 供只读 w:firstLine 的解析器判定）：2 字符 @16pt = 640 twips
        ind = (
            f'<w:ind w:firstLineChars="{first_line_chars}" '
            f'w:firstLine="{int(first_line_chars * 320 / 100)}"/>'
        )
    else:
        ind = ""
    ppr = (
        "<w:pPr>"
        f'<w:spacing w:beforeLines="0" w:afterLines="0" w:line="{line}" w:lineRule="auto"/>'
        + (f'<w:jc w:val="{align}"/>' if align != "left" else "")
        + ind
        + "</w:pPr>"
    )
    return f"<w:p>{ppr}{runs}</w:p>"


def _body_para(text: str) -> str:
    """正文段：首行缩进 2 字符，左对齐。"""
    return _para(_run(text), align="left", first_line_chars=200)


def _salutation_para(text: str) -> str:
    """称谓段：顶格（不缩进），左对齐。"""
    return _para(_run(text), align="left", first_line_chars=0)


def _title_para(text: str) -> str:
    """标题段：居中。"""
    return _para(_run(text, font=_FONT_TITLE, size=44, bold=False), align="center", first_line_chars=0)


def _signoff_para(text: str) -> str:
    """落款段：右对齐，不缩进。"""
    return _para(_run(text), align="right", first_line_chars=0)


def _label_para(label: str, text: str) -> str:
    return _body_para(f"{label}：{text}")


def build_document_xml(paragraphs: List[str]) -> str:
    sect = (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1474" w:bottom="1440" w:left="1587" w:header="851" w:footer="992" w:gutter="0"/>'
        '<w:cols w:space="425"/>'
        "<w:docGrid w:type=\"lines\" w:linePitch=\"312\"/>"
        "</w:sectPr>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>" + "".join(paragraphs) + sect + "</w:body></w:document>"
    )


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
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults>
<w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="仿宋" w:cs="Times New Roman"/>
<w:sz w:val="32"/><w:szCs w:val="32"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr>
<w:spacing w:line="360" w:lineRule="auto"/>
</w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
<w:name w:val="Normal"/><w:qFormat/>
</w:style>
</w:styles>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title></dc:title>
<dc:creator>gen_doc.py</dc:creator>
<cp:lastModifiedBy>gen_doc.py</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>gen_doc.py</Application>
</Properties>"""


def write_docx(path: str, paragraphs: List[str]) -> None:
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "word/document.xml": build_document_xml(paragraphs),
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES,
        "docProps/core.xml": CORE,
        "docProps/app.xml": APP,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in parts.items():
            # 固定时间戳，保证同样输入产出字节一致的包
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, content.encode("utf-8"))


# ---------------------------------------------------------------------------
# 正文渲染
# ---------------------------------------------------------------------------

def _val(aud: Dict[str, Any], name: str) -> str:
    """取渲染值：缺失的必填字段返回占位符，缺失的选填字段返回空串。"""
    return aud["fields"][name]["rendered_value"]


def render_request_letter(aud: Dict[str, Any]) -> List[str]:
    """请示函版式：标题居中 / 称谓顶格 / 正文缩进 2 字符 / 落款右对齐。"""
    paras: List[str] = []

    reason = _val(aud, "请示事由")
    paras.append(_title_para(f"关于{reason}的请示"))

    # 称谓：顶格
    paras.append(_salutation_para(f"{_val(aud, '主送机关')}："))

    # 正文
    paras.append(_body_para(f"我部就{reason}一事请示如下。"))
    paras.append(_body_para(_val(aud, "请示缘由")))
    paras.append(_body_para(_val(aud, "请示事项")))

    # 落款：右对齐
    paras.append(_signoff_para(_val(aud, "请示单位")))
    if aud["fields"]["成文日期"]["filled"]:
        paras.append(_signoff_para(aud["fields"]["成文日期"]["value"]))

    # 选填联系方式：有值才出（缺则留空/省略），不记入必填
    for label, name in (("联系人", "联系人"), ("联系电话", "联系电话")):
        if aud["fields"][name]["filled"]:
            paras.append(_label_para(label, aud["fields"][name]["value"]))

    return paras


def render_meeting_notice(aud: Dict[str, Any]) -> List[str]:
    """会议通知版式：标题居中 / 称谓顶格 / 正文缩进 2 字符 / 落款右对齐。"""
    paras: List[str] = []

    name = _val(aud, "会议名称")
    paras.append(_title_para(f"关于{name}的通知"))

    # 称谓：顶格
    paras.append(_salutation_para(f"{_val(aud, '主送对象')}："))

    # 正文：开头 + 事项条列
    when = _val(aud, "会议时间")
    paras.append(
        _body_para(f"兹定于{when}召开会议，现将有关事项通知如下：")
    )
    paras.append(_label_para("会议名称", name))
    paras.append(_label_para("召开单位", _val(aud, "召开单位")))
    paras.append(_label_para("会议时间", when))
    paras.append(_label_para("会议地点", _val(aud, "会议地点")))
    paras.append(_label_para("参会人员", _val(aud, "参会人员")))

    # 选填项：有值才出
    if aud["fields"]["会议议题"]["filled"]:
        paras.append(_label_para("会议议题", aud["fields"]["会议议题"]["value"]))
    if aud["fields"]["会议要求"]["filled"]:
        paras.append(_label_para("会议要求", aud["fields"]["会议要求"]["value"]))

    # 落款：右对齐
    paras.append(_signoff_para(_val(aud, "召开单位")))
    if aud["fields"]["发文日期"]["filled"]:
        paras.append(_signoff_para(aud["fields"]["发文日期"]["value"]))

    for name_ in ("联系人", "联系电话"):
        if aud["fields"][name_]["filled"]:
            paras.append(_label_para(name_, aud["fields"][name_]["value"]))

    return paras


RENDERERS = {"请示函": render_request_letter, "会议通知": render_meeting_notice}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build_fields_report(
    template: str, aud: Dict[str, Any], data_path: str, outdir: str
) -> Dict[str, Any]:
    spec = TEMPLATES[template]
    return {
        "schema_version": "1.0",
        "template": template,
        "template_required_fields": spec["required"],
        "template_optional_fields": spec["optional"],
        "case": os.path.splitext(os.path.basename(data_path))[0],
        "data_file": os.path.relpath(os.path.abspath(data_path)),
        "outdir": os.path.relpath(os.path.abspath(outdir)),
        "placeholder": PLACEHOLDER,
        "policy": {
            "missing_required": "以 ____ 占位渲染，不推断、不编造，程序正常结束（退出码 0）",
            "missing_optional": "留空或整行省略，不渲染内容，不记入 missing_required",
            "unknown_keys": "数据中不属于本模板的键，记入 unknown_keys，不渲染进正文",
            "invented_values": "无——所有渲染值均来自输入数据或占位符",
        },
        "fields": aud["fields"],
        "missing_required": aud["missing_required"],
        "missing_optional": aud["missing_optional"],
        # 别名：便于外部记账口径直接消费
        "required_missing": aud["missing_required"],
        "optional_missing": aud["missing_optional"],
        "unknown_keys": aud["unknown_keys"],
        "unknown_key_values": aud["unknown_key_values"],
        "counts": {
            "required_total": len(spec["required"]),
            "required_filled": len(spec["required"]) - len(aud["missing_required"]),
            "required_missing": len(aud["missing_required"]),
            "optional_total": len(spec["optional"]),
            "optional_filled": len(spec["optional"]) - len(aud["missing_optional"]),
            "optional_missing": len(aud["missing_optional"]),
            "unknown_keys": len(aud["unknown_keys"]),
        },
        "artifacts": [DOCX_NAME, FIELDS_NAME],
        "exit_code": 0,
        "status": "ok",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="公文模板渲染器（请示函 / 会议通知），缺数据以 ____ 占位并如实记账。"
    )
    parser.add_argument("--template", required=True, choices=sorted(TEMPLATES.keys()))
    parser.add_argument("--data", required=True, help="数据 json 路径")
    parser.add_argument("--outdir", required=True, help="输出目录")
    args = parser.parse_args(argv)

    data = load_data(args.data)
    aud = audit(args.template, data)

    # 为渲染器补上 rendered_value：必填缺失 → 占位符；缺失的选填 → 空串
    for name, info in aud["fields"].items():
        if info["filled"]:
            info["rendered_value"] = info["value"]
        elif info["required"]:
            info["rendered_value"] = PLACEHOLDER
        else:
            info["rendered_value"] = ""

    os.makedirs(args.outdir, exist_ok=True)

    paragraphs = RENDERERS[args.template](aud)
    write_docx(os.path.join(args.outdir, DOCX_NAME), paragraphs)

    report = build_fields_report(args.template, aud, args.data, args.outdir)
    with open(os.path.join(args.outdir, FIELDS_NAME), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # 人可读摘要走 stderr，不污染 stdout 契约
    print(
        f"[{args.template}] 已生成 {DOCX_NAME} / {FIELDS_NAME} → {args.outdir}"
        f" | 必填缺失={aud['missing_required'] or '无'}"
        f" | 选填缺失={aud['missing_optional'] or '无'}"
        f" | 模板外键={aud['unknown_keys'] or '无'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())