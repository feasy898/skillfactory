#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 out/ 两个单元目录做独立验收（期望值按 brief.md 手写，不复用生成器逻辑）。"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

try:
    from docx import Document
except ImportError:
    sys.path.append(str(Path.home() / ".local" / "lib" / "python3.12" / "site-packages"))
    from docx import Document

from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = Path(__file__).resolve().parent
failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def doc_paras(docx_path):
    doc = Document(docx_path)
    return [(p.text, p.alignment) for p in doc.paragraphs]


def verify_unit(unit, expect):
    print(f"\n== {unit} ==")
    unit_dir = BASE / "out" / unit / "case2"
    listing = sorted(p.name for p in unit_dir.iterdir())
    check(listing == sorted(["文书.docx", "fields.json"]), f"目录恰含两产物: {listing}")

    docx_path = unit_dir / "文书.docx"
    with zipfile.ZipFile(docx_path) as zf:
        check(zf.testzip() is None, "docx zip 完整性")

    paras = doc_paras(docx_path)
    texts = [t for t, _ in paras]
    full_text = "\n".join(texts)
    for needed in expect["must_contain"]:
        check(needed in texts, f"正文段存在: 「{needed}」")
    for banned in expect["must_not_contain"]:
        check(banned not in full_text, f"正文不出现: 「{banned}」")

    sig = [(t, a) for t, a in paras if t in expect["signature_lines"]]
    check(len(sig) == len(expect["signature_lines"]), "落款行数完整")
    for t, a in sig:
        check(a == WD_ALIGN_PARAGRAPH.RIGHT, f"落款右对齐: 「{t}」")

    fields = json.loads((unit_dir / "fields.json").read_text(encoding="utf-8"))
    check(fields["template"] == unit, "fields.json template 正确")
    check(fields["filled_fields"] == expect["filled_fields"], f"filled_fields = {fields['filled_fields']}")
    check(fields["missing_fields"] == expect["missing_fields"], f"missing_fields = {fields['missing_fields']}")

    by_name = {f["name"]: f for f in fields["fields"]}
    check(sorted(by_name) == sorted(expect["fields"]), "fields 字段集合与模板一致")
    for name, sub in expect["field_expect"].items():
        f = by_name.get(name, {})
        for key, val in sub.items():
            check(f.get(key) == val, f"fields[{name}].{key} == {val!r} (实际 {f.get(key)!r})")


verify_unit(
    "周报",
    {
        "must_contain": [
            "____工作周报",
            "周期：____",
            "一、本周工作内容",
            "1．____",
            "二、下周工作计划",
            "1．整理缺陷清单并分派责任人",
            "填报人：赵倩",
            "报送日期：2026-09-28",
        ],
        "must_not_contain": ["问题与需协调事项", "三、"],
        "signature_lines": ["填报人：赵倩", "报送日期：2026-09-28"],
        "filled_fields": ["填报人", "下周工作计划", "报送日期"],
        "missing_fields": ["周期", "本周工作内容", "问题与需协调事项"],
        "fields": ["填报人", "周期", "本周工作内容", "下周工作计划", "问题与需协调事项", "报送日期"],
        "field_expect": {
            "填报人": {"filled": True, "value": "赵倩", "required": True},
            "周期": {"filled": False, "missing": True, "value": None, "required": True, "placeholder_text": "____"},
            "本周工作内容": {"filled": False, "missing": True, "value": None, "required": True,
                          "placeholder": True, "placeholder_entries": ["1．____"]},
            "下周工作计划": {"filled": True, "value": ["整理缺陷清单并分派责任人"], "required": True},
            "问题与需协调事项": {"filled": False, "missing": True, "value": None, "required": False,
                            "section_omitted": True},
            "报送日期": {"filled": True, "value": "2026-09-28", "required": True},
        },
    },
)

verify_unit(
    "工作总结",
    {
        "must_contain": [
            "____2026年9月工作总结",
            "总结时段：2026年9月",
            "一、工作回顾",
            "1．完成评测平台月度巡检",
            "二、主要成绩",
            "1．____",
            "三、下一步工作打算",
            "1．制定四季度评测排期",
            "____",
        ],
        "must_not_contain": ["存在问题", "四、", "总结主体：", "成文日期："],
        "signature_lines": ["____", "____"],
        "filled_fields": ["总结时段", "工作回顾", "下一步工作打算"],
        "missing_fields": ["总结主体", "主要成绩", "存在问题", "成文日期"],
        "fields": ["总结主体", "总结时段", "工作回顾", "主要成绩", "下一步工作打算", "存在问题", "成文日期"],
        "field_expect": {
            "总结主体": {"filled": False, "missing": True, "value": None, "required": True, "placeholder_text": "____"},
            "总结时段": {"filled": True, "value": "2026年9月", "required": True},
            "工作回顾": {"filled": True, "value": ["完成评测平台月度巡检"], "required": True,
                      "normalization": "single_item_list"},
            "主要成绩": {"filled": False, "missing": True, "value": None, "required": True,
                      "placeholder": True, "placeholder_entries": ["1．____"]},
            "下一步工作打算": {"filled": True, "value": ["制定四季度评测排期"], "required": True},
            "存在问题": {"filled": False, "missing": True, "value": None, "required": False,
                      "section_omitted": True},
            "成文日期": {"filled": False, "missing": True, "value": None, "required": False},
        },
    },
)

# 与原始输入数据回对（值逐字一致 / 缺值回 null）
for unit, raw_path in (("周报", "fixtures/周报/case2.json"), ("工作总结", "fixtures/工作总结/case2.json")):
    raw = json.loads((BASE / raw_path).read_text(encoding="utf-8"))
    fields = json.loads((BASE / "out" / unit / "case2" / "fields.json").read_text(encoding="utf-8"))
    print(f"\n== {unit} 输入回对 ==")
    for f in fields["fields"]:
        name = f["name"]
        if f["filled"]:
            raw_val = raw.get(name)
            # 字符串型列表按 brief 单项化：fields.json 值为单元素数组
            expected = [raw_val] if f["kind"] == "list" and isinstance(raw_val, str) else raw_val
            check(f["value"] == expected, f"{name}: 已填值与输入逐字一致")
        else:
            check(f["value"] is None, f"{name}: 缺失记 null")

print(f"\n{'全部通过 ✅' if not failures else f'存在 {len(failures)} 处失败 ❌'}")
sys.exit(1 if failures else 0)
