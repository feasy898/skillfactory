#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docx 解析指纹提取（供确定性对比与独立复核使用）。

对一份 docx 提取「解析后视图」的确定性指纹：逐段落的
文本 / 对齐 / 缩进（左缩进、首行缩进）/ 字体（西文、东亚、字号、加粗、逐 run）
/ 行距（含规则、段前、段后），以及 ZIP 条目时间戳集合。
两份 docx 指纹相同 ⟺ 解析后的段落文本、对齐、缩进、字体、行距完全一致。
"""
from __future__ import annotations

import os
import sys
import zipfile


def _ensure_docx_module() -> None:
    try:
        import docx  # noqa: F401
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        site = os.path.join(here, ".venv", "lib",
                            "python%d.%d" % sys.version_info[:2],
                            "site-packages")
        if not os.path.isdir(site):
            raise
        sys.path.insert(0, site)
        import docx  # noqa: F401


def _emu(value):
    """Length（EMU 整数）→ int；None → None。"""
    return int(value) if value is not None else None


def _spacing(value):
    """行距：Length（固定值）→ EMU int；float（倍数）→ 保留 4 位；None → None。"""
    if value is None:
        return None
    if isinstance(value, int):          # Length 是 int 子类
        return int(value)
    return round(float(value), 4)


def _east_asia(run):
    rpr = run._element.rPr
    if rpr is None or rpr.rFonts is None:
        return None
    from docx.oxml.ns import qn
    return rpr.rFonts.get(qn("w:eastAsia"))


def paragraph_fingerprints(path: str) -> list:
    """返回逐段落指纹列表（纯数据，可直接 json 序列化/相等比较）。"""
    _ensure_docx_module()
    from docx import Document

    doc = Document(path)
    fps = []
    for idx, para in enumerate(doc.paragraphs):
        pf = para.paragraph_format
        fps.append({
            "i": idx,
            "text": para.text,
            "align": None if para.alignment is None else str(para.alignment),
            "left_indent": _emu(pf.left_indent),
            "first_line_indent": _emu(pf.first_line_indent),
            "line_spacing": _spacing(pf.line_spacing),
            "line_spacing_rule": (None if pf.line_spacing_rule is None
                                  else str(pf.line_spacing_rule)),
            "space_before": _emu(pf.space_before),
            "space_after": _emu(pf.space_after),
            "runs": [{
                "text": r.text,
                "ascii_font": r.font.name,
                "east_asia_font": _east_asia(r),
                "size_pt": None if r.font.size is None else r.font.size.pt,
                "bold": r.font.bold,
            } for r in para.runs],
        })
    return fps


def zip_entry_datetimes(path: str) -> list:
    """docx（ZIP 容器）全部条目的 (文件名, date_time) 列表。"""
    with zipfile.ZipFile(path) as zf:
        return [(info.filename, info.date_time) for info in zf.infolist()]


def fingerprint_diff(a: list, b: list) -> list:
    """逐项比较两份指纹，返回差异描述列表（空列表 ⟺ 完全一致）。"""
    diffs = []
    if len(a) != len(b):
        diffs.append("段落数不同: %d vs %d" % (len(a), len(b)))
    for fa, fb in zip(a, b):
        if fa == fb:
            continue
        for key in fa:
            if fa.get(key) != fb.get(key):
                diffs.append("段落 %d 字段 %s: %r vs %r"
                             % (fa["i"], key, fa.get(key), fb.get(key)))
    return diffs
