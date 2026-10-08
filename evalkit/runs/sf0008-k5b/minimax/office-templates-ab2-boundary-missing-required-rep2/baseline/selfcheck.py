#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 brief 的行为要求做独立自检。

期望值在本文件内独立写死（不读 render.py 的内部状态），从 fixtures 重新推导，
逐条核对 out/ 下的产物。退出码 0 = 全部通过。
"""

import json
import os
import subprocess
import sys
import tempfile
import zipfile
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as R  # noqa: E402

# 与 brief 文字对应的期望（模板 -> 必填、选填）
EXPECT = {
    "请示函": {
        "required": ["主送机关", "请示事由", "请示缘由", "请示事项", "请示单位"],
        "optional": ["联系人", "联系电话", "成文日期"],
        "case": "case2",
    },
    "会议通知": {
        "required": ["会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "参会人员", "发文日期"],
        "optional": ["会议议题", "会议要求", "联系人", "联系电话"],
        "case": "case2",
    },
}

failures = []
checks = 0


def ck(cond, label):
    global checks
    checks += 1
    if not cond:
        failures.append(label)
    print("%s %s" % ("PASS" if cond else "FAIL", label))


def docx_paragraphs(path):
    """直接读 document.xml，取每段的纯文本与对齐/缩进属性。"""
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    out = []
    for chunk in re.findall(r"<w:p>.*?</w:p>", xml, re.S):
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", chunk, re.S))
        jc = re.search(r'<w:jc w:val="(\w+)"/>', chunk)
        indent = "firstLineChars" in chunk
        out.append({"text": text, "align": jc.group(1) if jc else None, "indent": indent})
    return out


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


for template, exp in EXPECT.items():
    case = exp["case"]
    fixture = os.path.join("fixtures", template, "%s.json" % case)  # 相对路径，与 out/ 中留存产物同口径
    fixture_abs = os.path.join(HERE, fixture)
    unit = os.path.join(HERE, "out", template, case)
    tag = "[%s/%s]" % (template, case)

    # --- 单元目录结构：恰含两产物 ---
    ck(os.path.isdir(unit), "%s 单元目录存在" % tag)
    files = sorted(os.listdir(unit)) if os.path.isdir(unit) else []
    ck(files == ["fields.json", "文书.docx"] or sorted(files) == sorted(["文书.docx", "fields.json"]),
       "%s 恰含两产物（实际 %s）" % (tag, files))
    ck(len(files) == 2, "%s 产物数 == 2" % tag)

    docx_path = os.path.join(unit, "文书.docx")
    fields_path = os.path.join(unit, "fields.json")
    if not (os.path.isfile(docx_path) and os.path.isfile(fields_path)):
        continue

    # --- 契约重跑：命令行契约可用、退出码 0、幂等 ---
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "render.py"),
             "--template", template, "--data", fixture, "--outdir", td],
            capture_output=True, text=True, cwd=HERE,
        )
        ck(proc.returncode == 0, "%s 命令行契约退出码 0（实际 %d）" % (tag, proc.returncode))
        ck(sorted(os.listdir(td)) == sorted(["fields.json", "文书.docx"]),
           "%s 重跑产物齐全" % tag)
        with open(os.path.join(td, "fields.json"), encoding="utf-8") as fh:
            re_fields = json.load(fh)
    ck(re_fields == json.load(open(fields_path, encoding="utf-8")), "%s 重跑结果幂等" % tag)

    data = json.load(open(fixture_abs, encoding="utf-8"))
    rec = json.load(open(fields_path, encoding="utf-8"))

    # --- 记账名单与输入缺失事实一致 ---
    known = set(exp["required"]) | set(exp["optional"])
    exp_miss_req = [n for n in exp["required"] if n not in data or blank(data[n])]
    exp_miss_opt = [n for n in exp["optional"] if n not in data or blank(data[n])]
    exp_unknown = [k for k in data if k not in known]

    ck(rec["missing_required"] == exp_miss_req,
       "%s missing_required == %s（实际 %s）" % (tag, exp_miss_req, rec["missing_required"]))
    ck(rec["missing_optional"] == exp_miss_opt,
       "%s missing_optional == %s（实际 %s）" % (tag, exp_miss_opt, rec["missing_optional"]))
    ck(rec["unknown_keys"] == exp_unknown,
       "%s unknown_keys == %s（实际 %s）" % (tag, exp_unknown, rec["unknown_keys"]))
    ck(not (set(rec["missing_required"]) & set(rec["missing_optional"])),
       "%s 必填缺失与选填缺失无交集（未误记）" % tag)
    for name in rec["missing_optional"]:
        f = next(x for x in rec["fields"] if x["name"] == name)
        ck(f["required"] is False, "%s 选填 %s 未标为必填" % (tag, name))

    # --- 正文：必填缺失占位、不编造；选填缺失省略；模板外键不入正文 ---
    paras = docx_paragraphs(docx_path)
    texts = [p["text"] for p in paras]
    full = "\n".join(texts)
    for name in exp_miss_req:
        ck(any(t.startswith(name + "：") and R.PLACEHOLDER in t for t in texts),
           "%s 必填 %s 以 %s 占位渲染" % (tag, name, R.PLACEHOLDER))
        ck(not re.search(re.escape(name) + r"：\s*\S", full.replace(name + "：" + R.PLACEHOLDER, "")),
           "%s 必填 %s 未被编造赋值" % (tag, name))
    for name in exp_miss_opt:
        ck(name not in full, "%s 选填 %s 缺失时正文不出现该段" % (tag, name))
    for key in exp_unknown:
        ck(key not in full and str(data[key]) not in full,
           "%s 模板外键 %s 未进入正文" % (tag, key))

    # 已填字段必须逐字进正文（不丢内容）
    for name in exp["required"] + exp["optional"]:
        if name in data and not blank(data[name]):
            ck(str(data[name]) in full, "%s 已填字段 %s 逐字进正文" % (tag, name))

    # --- 版式：称谓顶格、落款右对齐 ---
    spec = R.TEMPLATES[template]
    sal = [p for p in paras if p["text"].startswith(spec["salutation_field"] + "：") or
           (p["text"].endswith("：") and p["indent"] is False and p["align"] == "left")]
    ck(bool(sal) and all(p["indent"] is False and p["align"] == "left" for p in sal),
       "%s 称谓顶格（无首行缩进、左对齐）" % tag)
    tail = [p for p in paras if p["text"] and p["align"] == "right"]
    ck(bool(tail), "%s 存在右对齐落款行（实际 %d 行）" % (tag, len(tail)))
    ck(all(p["indent"] is False for p in tail), "%s 落款行无首行缩进（对齐不被缺数据破坏）" % tag)
    ck(any(data[spec["issuer_field"]] == p["text"] for p in tail), "%s 落款含发文单位" % tag)

    ck(not any("None" in t or "null" in t for t in texts), "%s 正文无 None/null 泄漏" % tag)

print()
if failures:
    print("自检失败 %d/%d：" % (len(failures), checks))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("自检全部通过：%d/%d" % (checks, checks))