#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成结果自检：断言两份文书的落盘文件、字段状态与正文占位符一致。

零模型调用，纯程序化核验。任一断言失败 exit 1。
"""

import json
import os
import sys

from docx import Document

ROOT = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "［未填写］"

CASES = [
    {
        "name": "A / 请示函",
        "src": "fixtures/qingshi_empty.json",
        "out": "out/请示函-empty",
        "expect_missing": ["标题", "主送机关", "请示事由", "请示事项",
                           "落款单位", "成文日期"],
        "expect_blank": [],
    },
    {
        "name": "B / 工作总结",
        "src": "fixtures/zongjie_blank.json",
        "out": "out/工作总结-blank",
        "expect_missing": ["标题", "落款单位"],
        "expect_blank": ["总结主体", "总结时段", "工作回顾", "主要成绩",
                         "存在问题", "下一步工作打算", "成文日期"],
    },
]

failures = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        failures.append(msg)


for case in CASES:
    src = os.path.join(ROOT, case["src"])
    out = os.path.join(ROOT, case["out"])
    tag = case["name"]

    check(os.path.isfile(src), "%s 源数据缺失 %s" % (tag, case["src"]))

    docx_path = os.path.join(out, "文书.docx")
    fields_path = os.path.join(out, "fields.json")
    check(os.path.isfile(docx_path), "%s 未产出 文书.docx" % tag)
    check(os.path.isfile(fields_path), "%s 未产出 fields.json" % tag)
    if not (os.path.isfile(docx_path) and os.path.isfile(fields_path)):
        continue

    # ---- fields.json 结构与状态
    with open(fields_path, encoding="utf-8") as fh:
        fields = json.load(fh)
    for key in ("文书类型", "源数据", "字段清单", "统计", "未填写字段", "处理说明"):
        check(key in fields, "%s fields.json 缺少键 %s" % (tag, key))

    with open(src, encoding="utf-8") as fh:
        raw = json.load(fh)
    check(fields["源数据"] == raw, "%s fields.json 源数据与输入不一致" % tag)

    records = {r["字段"]: r for r in fields["字段清单"]}
    check(len(fields["字段清单"]) == fields["统计"]["字段总数"],
          "%s 字段清单长度与统计不一致" % tag)

    for name in case["expect_missing"]:
        r = records.get(name)
        check(r is not None, "%s 字段清单缺少「%s」" % (tag, name))
        if r:
            check(r["状态"] == "缺失", "%s「%s」状态应为缺失，实为 %s" % (tag, name, r["状态"]))
            check(r["原文"] is None, "%s「%s」原文应为空" % (tag, name))
            check(r["正文取值"] == PLACEHOLDER, "%s「%s」正文取值应为占位符" % (tag, name))

    for name in case["expect_blank"]:
        r = records.get(name)
        check(r is not None, "%s 字段清单缺少「%s」" % (tag, name))
        if r:
            check(r["状态"] == "空白", "%s「%s」状态应为空白，实为 %s" % (tag, name, r["状态"]))
            check(r["正文取值"] == PLACEHOLDER, "%s「%s」正文取值应为占位符" % (tag, name))
            # 空白字段的原文必须逐字节保真（含全角空格/空格列表）
            check(r["原文"] == raw.get(name), "%s「%s」原文未如实保真" % (tag, name))

    # 所有字段都已记录，且都给出了正文取值
    for r in fields["字段清单"]:
        check("正文取值" in r and "状态" in r, "%s 字段记录不完整：%s" % (tag, r.get("字段")))

    # ---- docx 可打开、结构完整、占位符落位
    doc = Document(docx_path)
    paras = [p.text for p in doc.paragraphs]
    nonempty = [t for t in paras if t.strip()]
    check(len(nonempty) >= 5, "%s 正文段落过少（%d 段）" % (tag, len(nonempty)))

    body_text = "\n".join(paras)
    expected_placeholders = fields["统计"]["占位符渲染数"]
    actual_placeholders = body_text.count(PLACEHOLDER)
    check(actual_placeholders >= 1, "%s 正文未出现占位符" % tag)
    check(actual_placeholders <= expected_placeholders + 1,
          "%s 占位符出现次数异常：%d（字段占位 %d）"
          % (tag, actual_placeholders, expected_placeholders))

    # 结构性骨架不能因为数据为空而丢失
    if "请示函" in tag:
        for kw in ("请示事由", "请示事项", "妥否，请批示"):
            check(any(kw in t for t in paras), "%s 正文缺少骨架段落「%s」" % (tag, kw))
        check(paras and paras[0].strip() == PLACEHOLDER,
              "%s 标题行未渲染占位符" % tag)
    else:
        for kw in ("工作回顾", "主要成绩", "存在问题", "下一步工作打算"):
            check(any(kw in t for t in paras), "%s 正文缺少骨架段落「%s」" % (tag, kw))
        for i, kw in enumerate(("一、", "二、", "三、", "四、"), 1):
            check(any(t.startswith(kw) for t in nonempty),
                  "%s 缺少第 %d 级小标题" % (tag, i))
        check(any(t.strip() == PLACEHOLDER for t in nonempty),
              "%s 正文未渲染占位符内容" % tag)

    check(fields["错误"] == [], "%s 记录了错误：%s" % (tag, fields["错误"]))

print("自检断言 %d 条，失败 %d 条" % (checks, len(failures)))
for f in failures:
    print("  FAIL: %s" % f)
sys.exit(1 if failures else 0)
