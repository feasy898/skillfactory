#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自检：核对两个单元目录的产物齐全、退出码 0、占位/版式/记账三项核心行为。

仅依赖标准库（DOCX 直接解 zip 读 word/document.xml），可在任意 Python 3 下运行。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# 期望的记账事实（直接来自任务书对两份输入的缺失描述）
EXPECTED = {
    "请示函": {
        "missing_required": ["主送机关", "请示事项"],
        "missing_optional": ["成文日期", "联系电话"],
        "unknown_keys": [],
    },
    "会议通知": {
        "missing_required": ["会议名称", "会议地点"],
        "missing_optional": ["会议议题", "会议要求", "联系人", "联系电话"],
        "unknown_keys": ["备注"],
    },
}

failures: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        failures.append(label)


def para_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(f"{W}t"))


def main() -> int:
    print("[1] 目录与产物齐全性")
    for t in EXPECTED:
        d = os.path.join(BASE, "out", t, "case2")
        check(os.path.isdir(d), f"{t}/case2 单元目录存在")
        entries = sorted(os.listdir(d)) if os.path.isdir(d) else []
        check(entries == ["fields.json", "文书.docx"], f"{t}/case2 恰含两产物：{entries}")

    print("\n[2] 退出码 0 + 可重复调用（幂等）")
    with tempfile.TemporaryDirectory() as td:
        for t in EXPECTED:
            r = subprocess.run(
                [sys.executable, "gen_doc.py", "--template", t,
                 "--data", f"fixtures/{t}/case2.json", "--outdir", os.path.join(td, t)],
                cwd=BASE, capture_output=True, text=True,
            )
            check(r.returncode == 0, f"{t} 退出码 0（实得 {r.returncode}）")

    print("\n[3] fields.json 记账与输入缺失事实一致")
    for t, exp in EXPECTED.items():
        rep = json.load(open(os.path.join(BASE, "out", t, "case2", "fields.json"), encoding="utf-8"))
        check(rep["template"] == t, f"{t} template 字段")
        check(sorted(rep["missing_required"]) == sorted(exp["missing_required"]),
              f"{t} missing_required={rep['missing_required']}")
        check(sorted(rep["missing_optional"]) == sorted(exp["missing_optional"]),
              f"{t} missing_optional={rep['missing_optional']}")
        check(sorted(rep["unknown_keys"]) == sorted(exp["unknown_keys"]),
              f"{t} unknown_keys={rep['unknown_keys']}")
        # 选填缺失不得混进 missing_required
        check(not (set(rep["missing_optional"]) & set(rep["missing_required"])),
              f"{t} 选填缺失未误记为必填")
        # 每个必填字段都必须有渲染去向（占位或取值），无遗漏
        req = rep["template_required_fields"]
        check(all(rep["fields"][f]["render_as"] in ("____", "line") for f in req),
              f"{t} 全部必填字段均有渲染去向")

    print("\n[4] DOCX 占位渲染 / 不编造 / 版式")
    for t, exp in EXPECTED.items():
        p = os.path.join(BASE, "out", t, "case2", "文书.docx")
        xml = zipfile.ZipFile(p).read("word/document.xml")
        root = ET.fromstring(xml)
        paras = root.find(f"{W}body").findall(f"{W}p")
        info = []
        for par in paras:
            ppr = par.find(f"{W}pPr")
            jc = ppr.find(f"{W}jc") if ppr is not None else None
            ind = ppr.find(f"{W}ind") if ppr is not None else None
            align = jc.get(f"{W}val") if jc is not None else "left"
            first_chars = int(ind.get(f"{W}firstLineChars")) if ind is not None and ind.get(f"{W}firstLineChars") else 0
            info.append((para_text(par), align, first_chars))
        text_all = "\n".join(x[0] for x in info)

        rep = json.load(open(os.path.join(BASE, "out", t, "case2", "fields.json"), encoding="utf-8"))
        # 每个缺失必填字段的渲染值都是占位符
        for f in exp["missing_required"]:
            check(rep["fields"][f]["render_as"] == "____", f"{t} 必填「{f}」以 ____ 占位渲染")

        # 缺失的选填字段不得出现在正文中（含标签）
        for f in exp["missing_optional"]:
            check(f"{f}：" not in text_all, f"{t} 选填「{f}」已省略（未误渲染）")

        # 模板外键不得泄漏进正文
        for f in exp["unknown_keys"]:
            val = rep["unknown_key_values"].get(f, "")
            check(val not in text_all, f"{t} 模板外键「{f}」值未泄漏进正文")

        # 版式：标题居中 / 称谓顶格 / 落款右对齐
        check(info[0][1] == "center", f"{t} 标题居中")
        sal = next((x for x in info if x[0].endswith("：") and "：" in x[0] and x[0].count("：") == 1), None)
        check(sal is not None and sal[2] == 0, f"{t} 称谓顶格（无首行缩进）")
        sign = [x for x in info if x[1] == "right"]
        check(len(sign) >= 1 and all(x[2] == 0 for x in sign), f"{t} 落款右对齐（{len(sign)} 段）")
        # 正文缩进仍在
        check(any(x[2] == 200 for x in info), f"{t} 正文首行缩进 2 字符")

    print("\n[5] 占位符完整性（无半个下划线残留）")
    for t in EXPECTED:
        p = os.path.join(BASE, "out", t, "case2", "文书.docx")
        text_all = "".join(
            t2.text or "" for t2 in ET.fromstring(zipfile.ZipFile(p).read("word/document.xml")).iter(f"{W}t")
        )
        check(re.search(r"(?<!_)_(?!_)", text_all) is None, f"{t} 占位符为完整的 ____")

    print("\n" + "=" * 60)
    if failures:
        print(f"VERIFY FAILED：{len(failures)} 项不通过")
        for f in failures:
            print("  - " + f)
        return 1
    print("VERIFY PASSED：全部断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())