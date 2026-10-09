#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段台账构建器：读取原始周报 JSON，做字段级清洗，产出
out/fields.json（字段台账）与 out/delivery-report.json（交付核对报告）。

台账是唯一的真相源：delivery-report.json 的四个键全部由台账推导，不另行判断。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "shibei_week42.json")
OUT = os.path.join(BASE, "out")

# 周报模板字段定义：顺序即文书中的呈现顺序
SCHEMA = [
    {"name": "部门", "required": True, "type": "string", "label": "部门"},
    {"name": "填报人", "required": True, "type": "string", "label": "填报人"},
    {"name": "周期", "required": True, "type": "string", "label": "报送周期"},
    {"name": "本周工作内容", "required": True, "type": "list", "label": "本周工作内容"},
    {"name": "下周工作计划", "required": True, "type": "string", "label": "下周工作计划"},
    {"name": "问题与需协调事项", "required": False, "type": "list", "label": "问题与需协调事项"},
    {"name": "报送日期", "required": True, "type": "string", "label": "报送日期"},
    {"name": "温馨提示", "required": False, "type": "string", "label": "温馨提示"},
]

PLACEHOLDER = {"string": "【请填写】", "list": "【请填写】"}


def clean_string(raw):
    """去首尾空白；若清洗后为空则视为未填。"""
    value = str(raw).strip()
    return value, [] if value == str(raw) else ["trim"]


def clean_list(raw):
    """逐项去首尾空白，剔除清洗后为空的项。"""
    items, dropped = [], []
    for i, entry in enumerate(raw if isinstance(raw, list) else [raw]):
        text = str(entry).strip()
        if text:
            items.append(text)
        else:
            dropped.append(i)
    actions = ["trim"] if any(str(e) != str(e).strip() for e in raw) else []
    if dropped:
        actions.append("drop_blank_items")
    return items, actions, dropped


def build_ledger():
    with open(SRC, encoding="utf-8") as fh:
        raw = json.load(fh)

    known = {f["name"] for f in SCHEMA}
    fields = []
    for spec in SCHEMA:
        name, ftype = spec["name"], spec["type"]
        entry = {
            "name": name,
            "label": spec["label"],
            "required": spec["required"],
            "type": ftype,
            "present": name in raw,
            "raw": raw.get(name),
            "value": None,
            "cleaning": [],
            "item_count": None,
        }
        if name not in raw:
            entry["missing"] = True
            fields.append(entry)
            continue
        entry["missing"] = False
        src = raw[name]
        if ftype == "list":
            items, actions, dropped = clean_list(src)
            entry["value"] = items
            entry["item_count"] = len(items)
            entry["cleaning"] = actions
            entry["dropped_blank_items"] = dropped
            # 声明为必填但清洗后无有效内容 —— 视为缺失
            if not items and spec["required"]:
                entry["missing"] = True
        else:
            value, actions = clean_string(src)
            entry["value"] = value
            if not value and spec["required"]:
                entry["missing"] = True
            entry["cleaning"] = actions
        fields.append(entry)

    unknown_keys = [k for k in raw if k not in known]

    ledger = {
        "schema_version": "1.0",
        "source": os.path.relpath(SRC, BASE),
        "document_title": "拾贝书店 2026年10月第2周 工作周报",
        "fields": fields,
        "summary": {
            "total_fields": len(SCHEMA),
            "required_fields": sum(1 for f in SCHEMA if f["required"]),
            "optional_fields": sum(1 for f in SCHEMA if not f["required"]),
            "present_fields": sum(1 for f in fields if f["present"]),
            "missing_required_names": [f["name"] for f in fields
                                       if f["required"] and f["missing"]],
            "missing_optional": [f["name"] for f in fields
                                 if not f["required"] and f["missing"]],
            "unknown_keys": unknown_keys,
            "cleaned_field_names": [f["name"] for f in fields if f["cleaning"]],
        },
    }
    return ledger


def main():
    ledger = build_ledger()
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, "fields.json"), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # 交付核对报告：严格四个键，全部取自台账
    s = ledger["summary"]
    report = {
        "missing_required_names": s["missing_required_names"],
        "missing_optional": s["missing_optional"],
        "unknown_keys": s["unknown_keys"],
        "title": ledger["document_title"],
    }
    with open(os.path.join(OUT, "delivery-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(json.dumps(report, ensure_ascii=False))
    print("cleaned:", s["cleaned_field_names"])


if __name__ == "__main__":
    main()