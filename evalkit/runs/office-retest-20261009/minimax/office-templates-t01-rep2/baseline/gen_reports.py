#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 shibei_week42.json 生成字段台账 out/fields.json 与核对报告 out/delivery-report.json。

字段台账口径（周报模板）：
  必填 REQUIRED = 部门 / 填报人 / 周期 / 本周工作内容 / 下周工作计划 / 报送日期
  选填 OPTIONAL = 问题与需协调事项 / 温馨提示（备注位）
  模板不认识的输入键 -> unknown_keys
归一化口径：
  字符串去首尾空白；列表逐项去首尾空白并剔除归一化后为空的元素。
核对报告只输出四个键：missing_required_names / missing_optional / unknown_keys / title。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "shibei_week42.json")
OUT = os.path.join(BASE, "out")

REQUIRED = ["部门", "填报人", "周期", "本周工作内容", "下周工作计划", "报送日期"]
OPTIONAL = ["问题与需协调事项", "温馨提示"]
KNOWN = REQUIRED + OPTIONAL


def norm_scalar(v):
    return v.strip() if isinstance(v, str) else v


def norm_list(v):
    arr = v if isinstance(v, list) else [v]
    return [x for x in (norm_scalar(i) for i in arr) if isinstance(x, str) and x != ""]


with open(SRC, encoding="utf-8") as f:
    raw = json.load(f)

values, dropped, notes = {}, [], {}
for k in KNOWN:
    if k not in raw:
        continue
    v = raw[k]
    if isinstance(v, list):
        values[k] = norm_list(v)
        for i, item in enumerate(v):
            if norm_scalar(item) == "":
                dropped.append({"field": k, "index": i, "raw_value": item})
        if v and not values[k]:
            notes[k] = "全部列表项归一化后为空，已按缺失处理"
    else:
        values[k] = norm_scalar(v)
        if isinstance(v, str) and v != v.strip():
            notes[k] = "已去除首尾空白"

unknown_keys = [k for k in raw if k not in KNOWN]


def missing_of(names):
    out = []
    for n in names:
        if n not in raw:
            out.append(n)
            continue
        v = values.get(n)
        if v is None:
            out.append(n)
        elif isinstance(v, list):
            if not v:
                out.append(n)
        elif not str(v).strip():
            out.append(n)
    return out


missing_required_names = missing_of(REQUIRED)
missing_optional = missing_of(OPTIONAL)

# title 取文书首页主标题（周期另作副标题，并已在台账中单列为独立字段）
dept = values.get("部门") or "【部门名称】"
title = dept + "周报"

fields = {}
for name in REQUIRED:
    fields[name] = {
        "requirement": "required",
        "status": "missing" if name in missing_required_names else "filled",
        "type": "list" if isinstance(values.get(name), list) else "scalar",
        "value": values.get(name),
    }
for name in OPTIONAL:
    fields[name] = {
        "requirement": "optional",
        "status": "missing" if name in missing_optional else "filled",
        "type": "list" if isinstance(values.get(name), list) else "scalar",
        "value": values.get(name),
    }
for k in unknown_keys:
    fields[k] = {
        "requirement": "unrecognized",
        "status": "unused",
        "type": "list" if isinstance(raw.get(k), list) else "scalar",
        "value": raw.get(k),
    }
for k, v in notes.items():
    if k in fields:
        fields[k]["normalization"] = v

ledger = {
    "title": title,
    "template": "周报",
    "source_file": os.path.basename(SRC),
    "document": os.path.join("out", "文书.docx"),
    "required_fields": REQUIRED,
    "optional_fields": OPTIONAL,
    "fields": fields,
    "normalization": {
        "scalar": "字符串去除首尾空白",
        "list": "逐项去除首尾空白，并剔除归一化后为空的元素",
        "dropped_empty_items": dropped,
        "trimmed_values": [
            {"field": k, "raw_value": raw[k], "normalized_value": values[k]}
            for k in KNOWN
            if isinstance(raw.get(k), str) and raw[k] != raw[k].strip()
        ],
    },
}

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "fields.json"), "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)
    f.write("\n")

report = {
    "missing_required_names": missing_required_names,
    "missing_optional": missing_optional,
    "unknown_keys": unknown_keys,
    "title": title,
}
with open(os.path.join(OUT, "delivery-report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("title:", title)
print("missing_required_names:", missing_required_names)
print("missing_optional:", missing_optional)
print("unknown_keys:", unknown_keys)
print("dropped:", json.dumps(dropped, ensure_ascii=False))
