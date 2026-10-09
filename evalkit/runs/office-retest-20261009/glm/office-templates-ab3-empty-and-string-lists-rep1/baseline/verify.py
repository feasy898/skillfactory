#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baseline 臂产物核验（ab3-empty-and-string-lists）。

核对两个单元目录（out/周报/case2、out/工作总结/case2）：
  1) 每目录恰含 文书.docx 与 fields.json 两产物；
  2) docx 段落序列、标题占位、小节重编号、条目编号「1．」（U+FF0E）、
     选填小节省略（正文不出现该节头）、落款右对齐（jc=right）；
  3) fields.json：空列表占位语义、字符串型列表单项化（值=单元素数组）、
     选填缺失记 missing（required=false）、必填缺失 ____ 占位。

全过 EXIT=0；任一断言失败打印 FAIL 并 EXIT=1。
"""

import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

FAILURES = []


def check(cond: bool, label: str):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILURES.append(label)


def docx_paragraphs(path: Path):
    """返回 [(text, jc, style)]，按文档顺序；body 直属段落。"""
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find(f"{W}body")
    out = []
    for p in body.findall(f"{W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{W}t"))
        ppr = p.find(f"{W}pPr")
        jc = ppr.find(f"{W}jc").get(f"{W}val") if ppr is not None and ppr.find(f"{W}jc") is not None else None
        style = (ppr.find(f"{W}pStyle").get(f"{W}val")
                 if ppr is not None and ppr.find(f"{W}pStyle") is not None else None)
        out.append((text, jc, style))
    return out


def check_unit(unit: str, expect_title: str, expect_paras: list,
               absent_texts: list, sig_count: int, fields_checks: list,
               extra_doc_checks=None):
    d = BASE / "out" / unit / "case2"
    check(d.is_dir(), f"[{unit}] 单元目录存在：out/{unit}/case2")
    files = sorted(p.name for p in d.iterdir())
    check(files == ["fields.json", "文书.docx"],
          f"[{unit}] 目录恰含两产物：{files}")

    paras = docx_paragraphs(d / "文书.docx")
    texts = [t for t, _, _ in paras]
    check(texts[0] == expect_title, f"[{unit}] 标题=「{expect_title}」：{texts[0]!r}")
    check(texts == expect_paras, f"[{unit}] 段落序列逐项一致：{texts}")
    for absent in absent_texts:
        check(all(absent not in t for t in texts), f"[{unit}] 正文未出现「{absent}」（选填整节省略）")
    sig = paras[-sig_count:]
    check(all(jc == "right" for _, jc, _ in sig),
          f"[{unit}] 落款 {sig_count} 行全部 jc=right：{[jc for _, jc, _ in sig]}")
    check(paras[0][1] == "center", f"[{unit}] 标题居中")

    f = json.loads((d / "fields.json").read_text(encoding="utf-8"))
    for label, cond in fields_checks:
        check(cond, f"[{unit}] {label}")
    if extra_doc_checks:
        for label, cond in extra_doc_checks:
            check(cond, f"[{unit}] {label}")
    return f


def main() -> int:
    # ------------------------------------------------ 周报
    zhou = check_unit(
        "周报",
        expect_title="____工作周报",
        expect_paras=[
            "____工作周报",
            "一、本周工作内容",
            "1．____",
            "二、下周工作计划",
            "1．整理缺陷清单并分派责任人",
            "填报人：赵倩",
            "报送日期：2026-09-28",
        ],
        absent_texts=["问题与需协调事项", "三、"],
        sig_count=2,
        fields_checks=[
            ("周期：required=true 且 status=missing_placeholder（空字符串→标题____占位）",
             lambda f: f["fields"]["周期"]["required"] is True
             and f["fields"]["周期"]["status"] == "missing_placeholder"
             and f["fields"]["周期"]["missing_kind"] == "empty_string"
             and f["fields"]["周期"]["placeholder"] == "____"),
            ("周期：fields.json 记占位语义（rendered.title=____工作周报）",
             lambda f: f["fields"]["周期"]["rendered"]["title"] == "____工作周报"),
            ("本周工作内容：空列表→必填缺失占位（placeholder_entry=1．____）",
             lambda f: f["fields"]["本周工作内容"]["status"] == "missing_placeholder"
             and f["fields"]["本周工作内容"]["missing_kind"] == "empty_list"
             and f["fields"]["本周工作内容"]["placeholder_entry"] == "1．____"),
            ("下周工作计划：filled，条目=1．整理缺陷清单并分派责任人",
             lambda f: f["fields"]["下周工作计划"]["status"] == "filled"
             and f["fields"]["下周工作计划"]["rendered"]["entries"]
             == ["1．整理缺陷清单并分派责任人"]),
            ("问题与需协调事项：required=false 且记 missing（整节省略）",
             lambda f: f["fields"]["问题与需协调事项"]["required"] is False
             and f["fields"]["问题与需协调事项"]["status"] == "missing_omitted"
             and f["fields"]["问题与需协调事项"]["rendered"]["section_omitted"] is True),
            ("rendered_sections：仅两节，编号 一、二、（无三、）",
             lambda f: [s["heading"] for s in f["rendered_sections"]]
             == ["一、本周工作内容", "二、下周工作计划"]),
            ("signature：右对齐两行，无省略",
             lambda f: f["signature"]["alignment"] == "right"
             and f["signature"]["lines"] == ["填报人：赵倩", "报送日期：2026-09-28"]
             and f["signature"]["omitted_fields"] == []),
        ],
    )

    # ------------------------------------------------ 工作总结
    zong = check_unit(
        "工作总结",
        expect_title="____2026年9月工作总结",
        expect_paras=[
            "____2026年9月工作总结",
            "一、工作回顾",
            "1．完成评测平台月度巡检",
            "二、主要成绩",
            "1．____",
            "三、下一步工作打算",
            "1．制定四季度评测排期",
            "____",
        ],
        absent_texts=["存在问题", "四、"],
        sig_count=1,
        fields_checks=[
            ("总结主体：必填缺失→____ 占位（标题+落款两用）",
             lambda f: f["fields"]["总结主体"]["required"] is True
             and f["fields"]["总结主体"]["status"] == "missing_placeholder"
             and f["fields"]["总结主体"]["rendered"]["title"] == "____2026年9月工作总结"
             and f["fields"]["总结主体"]["rendered"]["signature_line"] == "____"),
            ("总结时段：filled=2026年9月",
             lambda f: f["fields"]["总结时段"]["status"] == "filled"
             and f["fields"]["总结时段"]["value"] == "2026年9月"),
            ("工作回顾：字符串型列表单项化——值为单元素数组",
             lambda f: f["fields"]["工作回顾"]["raw_value"] == "完成评测平台月度巡检"
             and f["fields"]["工作回顾"]["value"] == ["完成评测平台月度巡检"]
             and f["fields"]["工作回顾"]["normalized_from"] == "string"),
            ("工作回顾：渲染为单项条目 1．完成评测平台月度巡检",
             lambda f: f["fields"]["工作回顾"]["rendered"]["entries"]
             == ["1．完成评测平台月度巡检"]),
            ("主要成绩：空列表→必填缺失占位（1．____）",
             lambda f: f["fields"]["主要成绩"]["status"] == "missing_placeholder"
             and f["fields"]["主要成绩"]["missing_kind"] == "empty_list"
             and f["fields"]["主要成绩"]["placeholder_entry"] == "1．____"),
            ("存在问题：required=false 且记 missing（整节省略）",
             lambda f: f["fields"]["存在问题"]["required"] is False
             and f["fields"]["存在问题"]["status"] == "missing_omitted"
             and f["fields"]["存在问题"]["rendered"]["section_omitted"] is True),
            ("下一步工作打算：filled，条目=1．制定四季度评测排期",
             lambda f: f["fields"]["下一步工作打算"]["status"] == "filled"
             and f["fields"]["下一步工作打算"]["rendered"]["entries"]
             == ["1．制定四季度评测排期"]),
            ("成文日期：required=false 记 missing，落款行省略",
             lambda f: f["fields"]["成文日期"]["required"] is False
             and f["fields"]["成文日期"]["status"] == "missing_omitted"
             and f["fields"]["成文日期"]["rendered"].get("signature_line_omitted") is True),
            ("rendered_sections：省略「存在问题」后重编号 一二三",
             lambda f: [s["heading"] for s in f["rendered_sections"]]
             == ["一、工作回顾", "二、主要成绩", "三、下一步工作打算"]),
            ("signature：右对齐单行 ____；成文日期在 omitted_fields",
             lambda f: f["signature"]["alignment"] == "right"
             and f["signature"]["lines"] == ["____"]
             and [o["field"] for o in f["signature"]["omitted_fields"]] == ["成文日期"]),
        ],
    )

    # 通用：条目编号用全角句点 U+FF0E、小节编号用顿号 U+3001
    for name, doc in (("周报", zhou), ("工作总结", zong)):
        check(all(s["heading"][1] == "、" for s in doc["rendered_sections"]),
              f"[{name}] 小节编号第二字符为顿号（一、二、三、）")
        check(all(e[1] == "．" for s in doc["rendered_sections"] for e in s["entries"]),
              f"[{name}] 条目编号第二字符为全角句点（1．2．3．）")

    print()
    if FAILURES:
        print(f"核验失败 {len(FAILURES)} 项")
        return 1
    print("全部核验通过（两个单元目录 × 两产物，docx 与 fields.json 逐项断言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
