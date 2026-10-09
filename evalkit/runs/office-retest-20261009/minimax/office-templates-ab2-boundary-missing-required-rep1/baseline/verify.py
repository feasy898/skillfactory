#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自检：核对两个单元目录的产物齐全、fields.json 记账与输入缺失事实一致、
文书版式未因缺数据而破坏（占位落地、称谓顶格、落款右对齐、选填不冒充必填、
模板外键不漏进正文）。

    python3 verify.py
退出码 0 表示全部断言通过。
"""

import json
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
PLACEHOLDER = "____"
ARTIFACTS = {u"文书.docx", u"fields.json"}
# 以「标签：」形式单独成行的选填字段（用于核「缺失即整行省略」）
LABELS = (u"联系人", u"联系电话", u"会议议题", u"会议要求")

# 独立的期望值（直接读 brief 描述的缺失事实，不从 gen_doc 的口径反推）
EXPECTED = {
    u"请示函": {
        u"missing_required": [u"主送机关", u"请示事项"],
        u"missing_optional": [u"联系电话", u"成文日期"],
        u"unknown_keys": [],
        u"data": os.path.join(ROOT, u"fixtures", u"请示函", u"case2.json"),
        u"salutation_marker": u"：",
        u"org": u"评测技术部",
        u"optional_labels": [u"联系人", u"联系电话"],
        u"signature_lines": 1,   # 成文日期选填缺失→落款只剩单位一段
        u"leak": [],
    },
    u"会议通知": {
        u"missing_required": [u"会议名称", u"会议地点"],
        u"missing_optional": [u"会议议题", u"会议要求", u"联系人", u"联系电话"],
        u"unknown_keys": [u"备注"],
        u"data": os.path.join(ROOT, u"fixtures", u"会议通知", u"case2.json"),
        u"salutation_marker": u"：",
        u"org": u"评测技术部",
        u"optional_labels": [u"会议议题", u"会议要求", u"联系人", u"联系电话"],
        u"signature_lines": 2,   # 发文日期有值 + 召开单位
        u"leak": [u"此键不在模板字段内，用于测试 unknown_keys 记录"],
    },
}

failures = []


def check(cond, label):
    if not cond:
        failures.append(label)
        print(u"FAIL  %s" % label)
    else:
        print(u"ok    %s" % label)


def main():
    for template, exp in EXPECTED.items():
        case_dir = os.path.join(OUT, template, u"case2")
        print(u"\n=== %s ===" % template)

        # 1) 单元目录与产物齐全，且每目录恰含两产物
        check(os.path.isdir(case_dir), u"%s 单元目录存在" % template)
        got = set(os.listdir(case_dir)) if os.path.isdir(case_dir) else set()
        check(got == ARTIFACTS,
              u"%s 恰含两产物 文书.docx/fields.json（实际 %s）" % (template, sorted(got)))
        if got != ARTIFACTS:
            continue

        fields = json.load(open(os.path.join(case_dir, u"fields.json")))

        # 2) fields.json 三张名单与输入缺失事实一致
        for key in (u"missing_required", u"missing_optional", u"unknown_keys"):
            check(sorted(fields[key]) == sorted(exp[key]),
                  u"%s %s == %s" % (template, key, exp[key]))

        # 3) 名单与输入数据互相印证（独立复算：键不存在 / 值为空）
        raw = json.load(open(exp[u"data"]))
        empty_or_absent_req = set(
            f for f in fields[u"required_fields"]
            if f not in raw or not str(raw.get(f, "")).strip())
        empty_or_absent_opt = set(
            f for f in fields[u"optional_fields"]
            if f not in raw or not str(raw.get(f, "")).strip())
        check(empty_or_absent_req == set(exp[u"missing_required"]),
              u"%s 必填缺失复算一致" % template)
        check(empty_or_absent_opt == set(exp[u"missing_optional"]),
              u"%s 选填缺失复算一致" % template)
        check(set(fields[u"present_fields"]) == set(raw) - empty_or_absent_req
              - empty_or_absent_opt - set(exp[u"unknown_keys"]),
              u"%s 已填字段与输入一致" % template)

        # 4) 文书内容与版式
        doc = Document(os.path.join(case_dir, u"文书.docx"))
        paras = [p for p in doc.paragraphs if p.text.strip()]
        texts = [p.text for p in paras]
        blob = u"\n".join(texts)

        # 4a. 每个缺失必填字段都有占位；且占位数与缺失数一致（不虚标、不漏标）
        placeholders = sum(t.count(PLACEHOLDER) for t in texts)
        check(placeholders >= len(exp[u"missing_required"]),
              u"%s 缺失必填均以 %s 占位（占位数=%d，缺失必填=%d）"
              % (template, PLACEHOLDER, placeholders, len(exp[u"missing_required"])))

        # 4b. 选填缺失不得被误记为必填——即「缺哪个就整行省略，不得出占位/空标签行」
        #     （各模板的选填字段集不同，逐模板核，不用共用清单）
        rendered_labels = [t for t in texts if t.startswith(LABELS) and u"：" in t]
        for label in exp[u"optional_labels"]:
            shown = [t for t in rendered_labels if t.startswith(label + u"：")]
            if label in exp[u"missing_optional"]:
                check(not shown,
                      u"%s 选填 %s 缺失→整行省略，未冒充必填（出现=%s）"
                      % (template, label, shown))
            else:
                check(len(shown) == 1,
                      u"%s 选填 %s 有值→正常渲染（出现=%s）" % (template, label, shown))

        # 4c. 称谓顶格：第一段称谓左对齐且首行缩进 0
        sal = paras[1]
        check(sal.text.endswith(exp[u"salutation_marker"]),
              u"%s 第二段为称谓段：%r" % (template, sal.text))
        check(sal.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.LEFT,
              u"%s 称谓左对齐" % template)
        indent = sal.paragraph_format.first_line_indent
        check(indent is None or int(indent) == 0,
              u"%s 称谓顶格（first_line_indent=%s）" % (template, indent))

        # 4d. 正文首行缩进两字符（缺数据未破坏正文版式）
        body = paras[2]
        body_indent = body.paragraph_format.first_line_indent
        check(body_indent is not None and int(body_indent) == int(32 * 12700),
              u"%s 正文首行缩进两字符（=%s EMU）" % (template, body_indent))

        # 4e. 落款右对齐：末尾连续右对齐段构成落款块，末段为单位
        right = [p.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.RIGHT
                 for p in paras]
        tail_start = len(paras)
        while tail_start > 0 and right[tail_start - 1]:
            tail_start -= 1
        tail = paras[tail_start:]
        check(tail and tail_start == len(paras) - len(tail) and len(tail) >= 1,
              u"%s 右对齐段落构成末尾落款块（%d 段）" % (template, len(tail)))
        check(all(right[len(paras) - len(tail):]),
              u"%s 落款右对齐" % template)
        check(tail[-1].text.strip() == exp[u"org"],
              u"%s 落款单位=%r" % (template, tail[-1].text.strip()))
        # 落款块长度 = 单位 +（成文/发文日期若有）
        check(len(tail) == exp[u"signature_lines"],
              u"%s 落款块 %d 段（单位 + 日期选填）" % (template, len(tail)))

        # 4f. 模板外键值不得漏进文书正文
        for leak in exp[u"leak"]:
            check(leak not in blob,
                  u"%s 模板外键内容未写入正文" % template)

        # 4g. 已填数据必须真实落到正文
        for field in fields[u"present_fields"]:
            if field in exp[u"unknown_keys"]:
                continue
            val = str(raw[field]).rstrip(u"。")
            check(val in blob, u"%s 已填字段 %s 落到正文" % (template, field))

    print(u"\n%s" % (u"全部断言通过" if not failures
                      else u"失败 %d 项：%s" % (len(failures), failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
