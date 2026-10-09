#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py —— 自证脚本：独立复核 out/<模板>/case2/ 的产物与记账一致性

复核点（全部从输入 JSON 重新推导，不读 fields.json 的结论）：
  A. 产物齐全：每个单元目录恰含 文书.docx 与 fields.json 两个文件
  B. docx 结构合法：zip 完整、必需部件齐备、document.xml 可解析
  C. fields.json 记账与输入缺失事实一致（missing_required / missing_optional / unknown_keys）
  D. 必填缺失以 ____ 渲染；选填缺失未误记为必填、未渲染成必填占位
  E. 模板外键只记账、不进正文
  F. 版式：称谓顶格（左对齐且无缩进）、落款右对齐
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ROOT = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "____"
DOCX_NAME = "文书.docx"
FIELDS_NAME = "fields.json"

# 与 gen_doc.py 独立重述的「任务书事实」，用于交叉校验
CASES = [
    {
        "template": "请示函",
        "data": "fixtures/请示函/case2.json",
        "outdir": os.path.join("out", "请示函", "case2"),
        "required": ["主送机关", "请示事由", "请示缘由", "请示事项", "请示单位"],
        "optional": ["联系人", "联系电话", "成文日期"],
        "expect_missing_required": ["主送机关", "请示事项"],
        "expect_missing_optional": ["联系电话", "成文日期"],
        "expect_unknown": [],
        "salutation": "主送机关",
        "signature": ["请示单位"],
    },
    {
        "template": "会议通知",
        "data": "fixtures/会议通知/case2.json",
        "outdir": os.path.join("out", "会议通知", "case2"),
        "required": ["会议名称", "主送对象", "召开单位", "会议时间", "会议地点", "参会人员"],
        "optional": ["会议议题", "会议要求", "联系人", "联系电话", "发文日期"],
        "expect_missing_required": ["会议名称", "会议地点"],
        "expect_missing_optional": ["会议议题", "会议要求", "联系人", "联系电话"],
        "expect_unknown": ["备注"],
        "salutation": "主送对象",
        "signature": ["召开单位"],
    },
]

FAILS = []
CHECKS = [0]


def ck(cond, label):
    CHECKS[0] += 1
    if cond:
        print("  PASS  %s" % label)
    else:
        print("  FAIL  %s" % label)
        FAILS.append(label)


def para_texts(doc_root):
    """返回 [(文本, {jc, firstLineChars, firstLine})]，按文档顺序。"""
    out = []
    for p in doc_root.iter(W + "p"):
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        ppr = p.find(W + "pPr")
        jc = ind_fc = ind_fl = None
        if ppr is not None:
            j = ppr.find(W + "jc")
            if j is not None:
                jc = j.get(W + "val")
            i = ppr.find(W + "ind")
            if i is not None:
                ind_fc = i.get(W + "firstLineChars")
                ind_fl = i.get(W + "firstLine")
        out.append((text, {"jc": jc, "firstLineChars": ind_fc, "firstLine": ind_fl}))
    return out


def verify_case(case):
    print("\n== 单元 %s ==" % os.path.join(case["outdir"]))
    data = json.load(open(os.path.join(ROOT, case["data"]), encoding="utf-8"))
    outdir = os.path.join(ROOT, case["outdir"])

    # A. 产物齐全
    ck(os.path.isdir(outdir), "A 输出目录存在：%s" % case["outdir"])
    listing = sorted(os.listdir(outdir))
    ck(listing == sorted([DOCX_NAME, FIELDS_NAME]),
       "A 单元目录恰含两产物：%s（实际 %s）" % (sorted([DOCX_NAME, FIELDS_NAME]), listing))

    docx_path = os.path.join(outdir, DOCX_NAME)
    fields_path = os.path.join(outdir, FIELDS_NAME)

    # B. docx 结构合法
    ck(zipfile.is_zipfile(docx_path), "B 文书.docx 是合法 zip")
    with zipfile.ZipFile(docx_path) as zf:
        ck(zf.testzip() is None, "B zip 内容 CRC 全部正确")
        names = set(zf.namelist())
        need = {"[Content_Types].xml", "_rels/.rels", "word/document.xml",
                "word/styles.xml", "word/_rels/document.xml.rels"}
        ck(need <= names, "B 必需部件齐备（缺 %s）" % sorted(need - names))
        doc_root = ET.fromstring(zf.read("word/document.xml"))
        styles_root = ET.fromstring(zf.read("word/styles.xml"))
        ET.fromstring(zf.read("[Content_Types].xml"))
        ET.fromstring(zf.read("_rels/.rels"))
    ck(styles_root.tag == W + "styles", "B styles.xml 可解析")

    paras = para_texts(doc_root)
    ck(len(paras) >= 5, "B 正文段落数 %d ≥ 5" % len(paras))
    body_text = "".join(t for t, _ in paras)

    # C. 记账一致性（从输入独立推导）
    fields = json.load(open(fields_path, encoding="utf-8"))
    schema = case["required"] + case["optional"]
    truth_missing_required, truth_missing_optional = [], []
    for name in case["required"]:
        if name not in data or (isinstance(data.get(name), str) and data[name].strip() == ""):
            truth_missing_required.append(name)
    for name in case["optional"]:
        if name not in data or (isinstance(data.get(name), str) and data[name].strip() == ""):
            truth_missing_optional.append(name)
    truth_unknown = [k for k in data if k not in schema]

    ck(fields["missing_required"] == truth_missing_required,
       "C missing_required 与输入缺失事实一致：%s" % truth_missing_required)
    ck(fields["missing_optional"] == truth_missing_optional,
       "C missing_optional（选填 missing）与输入一致：%s" % truth_missing_optional)
    ck(fields["unknown_keys"] == truth_unknown,
       "C unknown_keys 与模板外键一致：%s" % truth_unknown)
    ck(fields["missing_required"] == case["expect_missing_required"],
       "C 与任务书所述缺失事实一致：%s" % case["expect_missing_required"])
    ck(fields["missing_optional"] == case["expect_missing_optional"],
       "C 与任务书所述选填缺失一致：%s" % case["expect_missing_optional"])
    ck(fields["unknown_keys"] == case["expect_unknown"],
       "C 与任务书所述模板外键一致：%s" % case["expect_unknown"])

    # D. 必填缺失以占位渲染；选填缺失不误记、不误渲染
    fmap = {f["name"]: f for f in fields["fields"]}
    for name in truth_missing_required:
        ck(fmap[name]["state"] == "missing_required" and fmap[name]["rendered"] == PLACEHOLDER,
           "D 必填缺失 %s 记为 missing_required 且渲染为 %s" % (name, PLACEHOLDER))
    for name in truth_missing_optional:
        ck(fmap[name]["state"] == "missing_optional",
           "D 选填缺失 %s 记为 missing_optional（未误记为必填）" % name)
        ck(fmap[name]["rendered"] == "",
           "D 选填缺失 %s 未渲染成必填占位" % name)
        ck(name not in fields["missing_required"],
           "D 选填缺失 %s 不在 missing_required 名单内" % name)
    ck(body_text.count(PLACEHOLDER) >= len(truth_missing_required),
       "D 正文含必填占位 %d 处 ≥ %d" % (body_text.count(PLACEHOLDER), len(truth_missing_required)))
    # 选填整段省略：字段名标签不出现在正文（避免空壳段落）
    for name in truth_missing_optional:
        if case["template"] == "会议通知" and name in ("会议议题", "会议要求"):
            ck(("%s：" % name) not in body_text,
               "D 选填字段 %s 缺失时整段省略（无空壳段落）" % name)

    # E. 模板外键只记账、不渲染
    for key in truth_unknown:
        ck(str(data[key]) not in body_text,
           "E 模板外键 %s 的值未进入正文" % key)
    ck(fields["unknown_key_values"].get(key) == data[key] if truth_unknown else True,
       "E 模板外键原值已在 fields.json 如实记账")

    # F. 版式：称谓顶格、落款右对齐
    sal = [p for p in paras if p[1]["jc"] == "left" and p[1]["firstLine"] is None]
    ck(len(sal) >= 1, "F 存在称谓段落（左对齐且无首行缩进 = 顶格）")
    if sal:
        ck(sal[0][0].endswith("："),
           "F 称谓顶格段落为「%s」，冒号收尾" % sal[0][0])
    right = [p for p in paras if p[1]["jc"] == "right"]
    ck(len(right) >= 1, "F 存在落款右对齐段落 %d 段" % len(right))
    ck(all(p[1]["firstLine"] is None for p in right),
       "F 落款段落无首行缩进（纯右对齐）")
    for name in case["signature"]:
        ck(any(p[0] == data[name] for p in right),
           "F 落款右对齐包含 %s=%s" % (name, data[name]))
    # 正文主段保持首行缩进 2 字符（缩进数随选填省略而变，故只要求至少 1 段）
    body_ind = [p for p in paras if p[1]["firstLine"] == "640"]
    ck(len(body_ind) >= 1, "F 正文段落保持首行缩进 2 字符（%d 段）" % len(body_ind))

    return fields


def main():
    print("VERIFY 单元目录与产物齐全性 / 记账一致性 / 版式")
    for case in CASES:
        verify_case(case)
    print("\n" + "=" * 60)
    print("断言总数 %d，失败 %d" % (CHECKS[0], len(FAILS)))
    if FAILS:
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("ALL PASS  EXIT=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())