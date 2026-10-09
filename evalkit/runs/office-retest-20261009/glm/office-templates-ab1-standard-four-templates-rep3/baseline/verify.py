#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付自检：核对 out/<模板>/case1/ 四个单元目录与产物齐全、记账与版式达标。

检查项：
  1. 四个单元目录存在，且每个目录恰含 文书.docx 与 fields.json 两个产物；
  2. fields.json 顶层含 title / fields / summary，字段含
     名称、是否必填、状态、值、渲染方式 五要素；
  3. summary 的 filled/missing/total 与 fields 明细一致（filled+missing=total）；
  4. fields 值与 fixtures 原始数据逐字段一致（值不编造、原样记账），
     字段清单与 gen_doc.SCHEMA 一致；
  5. 文书.docx：A4 版面（210×297mm）与 GB/T 9704 版心
     （上37/下35/左28/右26mm）；标题段与 fields.json.title 一致；
     数据每个取值（列表逐条）都能在正文文本中找到。
"""

import json
import os
import sys

from docx import Document
from docx.shared import Mm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_doc import SCHEMA  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = ["周报", "请示函", "会议通知", "工作总结"]
FIELD_KEYS = {"名称", "是否必填", "状态", "值", "渲染方式"}

failures = []


def check(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        failures.append(msg)
        print(f"  FAIL  {msg}")


def docx_text(doc):
    return "\n".join(p.text for p in doc.paragraphs)


for t in TEMPLATES:
    unit = os.path.join(BASE, "out", t, "case1")
    print(f"== {t}（{os.path.relpath(unit, BASE)}）==")

    # 1. 目录与产物齐全
    check(os.path.isdir(unit), f"{t}: 单元目录存在")
    entries = sorted(os.listdir(unit)) if os.path.isdir(unit) else []
    check(set(entries) == {"文书.docx", "fields.json"} and len(entries) == 2,
          f"{t}: 目录恰含 文书.docx 与 fields.json（实际: {entries}）")

    # 2. fields.json 结构
    with open(os.path.join(unit, "fields.json"), encoding="utf-8") as fh:
        ledger = json.load(fh)
    check(set(ledger) >= {"title", "fields", "summary"},
          f"{t}: fields.json 顶层含 title/fields/summary")
    check(all(FIELD_KEYS <= set(fld) for fld in ledger["fields"]),
          f"{t}: 每个字段含 名称/是否必填/状态/值/渲染方式 五要素")

    # 3. summary 计数一致
    s = ledger["summary"]
    fields = ledger["fields"]
    filled = sum(1 for x in fields if x["状态"] == "filled")
    missing = sum(1 for x in fields if x["状态"] == "missing")
    check(set(s) == {"filled", "missing", "total"}, f"{t}: summary 键为 filled/missing/total")
    check(s["filled"] == filled and s["missing"] == missing
          and s["total"] == len(fields) and filled + missing == s["total"],
          f"{t}: summary 计数与明细一致（{s}）")

    # 4. 与 fixtures 逐字段对账
    with open(os.path.join(BASE, "fixtures", t, "case1.json"),
              encoding="utf-8") as fh:
        fixture = json.load(fh)
    schema_names = [n for n, _ in SCHEMA[t]]
    check([x["名称"] for x in fields] == schema_names,
          f"{t}: 字段清单与口径一致且不缺不重")
    check(all(x["值"] == fixture.get(x["名称"]) for x in fields),
          f"{t}: 字段值与数据 JSON 原样一致（无编造）")
    check(fixture and all(x["状态"] == "filled" for x in fields),
          f"{t}: case1 字段全部齐全 → 全部 filled（missing=0）")

    # 5. 文书.docx 版式与内容（docx 以 twip 存储几何值，允许半个 twip 级舍入差）
    def mm_eq(actual, mm, tol=Mm(0.05)):
        return abs(actual - Mm(mm)) <= tol

    doc = Document(os.path.join(unit, "文书.docx"))
    sec = doc.sections[0]
    check(mm_eq(sec.page_width, 210) and mm_eq(sec.page_height, 297),
          f"{t}: A4 版面 210×297mm")
    check(mm_eq(sec.top_margin, 37) and mm_eq(sec.bottom_margin, 35)
          and mm_eq(sec.left_margin, 28) and mm_eq(sec.right_margin, 26),
          f"{t}: GB/T 9704 版心 上37/下35/左28/右26mm")
    text = docx_text(doc)
    first = next((p.text for p in doc.paragraphs if p.text.strip()), "")
    check(first == ledger["title"],
          f"{t}: 标题段与 fields.json.title 一致（{ledger['title']}）")
    missing_vals = []
    for name, val in fixture.items():
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            if str(v) not in text:
                missing_vals.append(f"{name}={v}")
    check(not missing_vals, f"{t}: 数据每个取值均见于文书正文（缺: {missing_vals}）")
    print()

print("=" * 60)
if failures:
    print(f"VERIFY FAIL（{len(failures)} 项）")
    sys.exit(1)
print("VERIFY PASS：四个单元目录与产物齐全，记账与版式自检全部通过")
