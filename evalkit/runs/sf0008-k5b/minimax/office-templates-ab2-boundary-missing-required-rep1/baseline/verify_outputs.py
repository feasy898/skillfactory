#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产物核验：独立于 main.py 重新推导缺失事实，并检查 fields.json 与 docx 版式。

    python3 verify_outputs.py

不依赖 main.py 的中间结果：直接从 fixtures/*.json 出发推导应当记账的名单，
再与 fields.json 逐项对拍；版式检查直接读 docx 的段落属性与全文。
"""

import json
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.abspath(__file__))

# 模板必填/选填契约（与 main.py 同源定义，此处显式写出以便独立对拍）
CONTRACT = {
    "请示函": {
        "required": ["主送机关", "请示事由", "请示缘由", "请示事项", "请示单位"],
        "optional": ["联系人", "联系电话", "成文日期"],
        "salutation": 1,      # 顶格称谓所在段序
    },
    "会议通知": {
        "required": ["会议名称", "会议时间", "会议地点", "参会人员", "召开单位"],
        "optional": ["主送对象", "会议议题", "会议要求", "联系人", "联系电话", "发文日期"],
        "salutation": 1,
    },
}

CASES = [("请示函", "case2"), ("会议通知", "case2")]

fails = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def blank(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def main():
    for template, case in CASES:
        data_path = os.path.join(ROOT, "fixtures", template, f"{case}.json")
        out_dir = os.path.join(ROOT, "out", template, case)
        docx_path = os.path.join(out_dir, "文书.docx")
        fields_path = os.path.join(out_dir, "fields.json")
        tag = f"{template}/{case}"

        # 1) 单元目录恰含两产物
        present = sorted(os.listdir(out_dir))
        check(present == ["fields.json", "文书.docx"], f"[{tag}] 目录产物不齐: {present}")
        if fails:
            continue

        with open(data_path, encoding="utf-8") as fh:
            data = json.load(fh)
        with open(fields_path, encoding="utf-8") as fh:
            fd = json.load(fh)

        contract = CONTRACT[template]

        # 2) 从输入独立推导缺失事实，与 fields.json 对拍
        exp_req = [n for n in contract["required"] if blank(data.get(n))]
        exp_opt = [n for n in contract["optional"] if blank(data.get(n))]
        exp_unknown = [k for k in data if k not in contract["required"] + contract["optional"]]
        check(sorted(fd["missing_required"]) == sorted(exp_req),
              f"[{tag}] 必填缺失名单不符: {fd['missing_required']} != {exp_req}")
        check(sorted(fd["missing_optional"]) == sorted(exp_opt),
              f"[{tag}] 选填缺失名单不符: {fd['missing_optional']} != {exp_opt}")
        check(sorted(fd["unknown_keys"]) == sorted(exp_unknown),
              f"[{tag}] unknown_keys 不符: {fd['unknown_keys']} != {exp_unknown}")

        # 3) 选填缺失不得误记为必填；已填字段值必须与输入逐字一致（无编造）
        check(not (set(fd["missing_optional"]) & set(fd["missing_required"])),
              f"[{tag}] 选填缺失被误记为必填缺失")
        exp_filled = [n for n in contract["required"] + contract["optional"]
                      if not blank(data.get(n))]
        check(sorted(fd["filled"]) == sorted(exp_filled),
              f"[{tag}] filled 名单不符: {fd['filled']} != {exp_filled}")
        for n in exp_filled:
            check(fd["fields"][n]["value"] == data[n].strip(),
                  f"[{tag}] 字段 {n} 值与输入不符（疑编造）")

        # 4) 必填缺失一律以 ____ 占位渲染；选填缺失不得渲染出值
        for n in exp_req:
            check(fd["fields"][n]["rendered"] == "____",
                  f"[{tag}] 必填缺失 {n} 未以 ____ 占位渲染")
        for n in exp_opt:
            check(fd["fields"][n]["rendered"] == "",
                  f"[{tag}] 选填缺失 {n} 未留空")

        # 5) 版式：称谓顶格、落款右对齐，且缺数据未破坏排版
        doc = Document(docx_path)
        pars = [(p.text, p) for p in doc.paragraphs if p.text.strip()]
        sal_text, sal_par = pars[contract["salutation"]]
        pf = sal_par.paragraph_format
        check(pf.left_indent in (None, 0) and pf.first_line_indent in (None, 0),
              f"[{tag}] 称谓未顶格: {sal_text}")
        check(any("____" in t for t, _ in pars), f"[{tag}] 文书中未出现 ____ 占位")
        sign_paras = [p for _, p in pars if p.alignment == WD_ALIGN_PARAGRAPH.RIGHT]
        check(len(sign_paras) >= 2, f"[{tag}] 落款右对齐段落不足: {len(sign_paras)}")
        # 每个缺失必填字段的 ____ 都必须真实出现在文书里（键缺失与空串同面）
        body_text = "\n".join(t for t, _ in pars)
        for n in exp_req:
            check("____" in body_text and n in body_text,
                  f"[{tag}] 必填缺失 {n} 未在文书中体现为字段 + ____ 占位")
        # 每个非落款、非称谓的正文段落不得含有编造的补值文本
        check(len(pars) >= 4, f"[{tag}] 版式段落过少，疑似因缺数据塌陷")

    print(f"checks={checks} fails={len(fails)}")
    for f in fails:
        print("FAIL:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())