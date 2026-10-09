#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付件自检：源数据 8 字段是否逐字落入 文书.docx，以及 fields.json 的登记是否自洽。"""
import json
import os
import sys

from docx import Document

HERE = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(os.path.join(HERE, "lanshan_miji.json"), encoding="utf-8"))
doc = Document(os.path.join(HERE, "out", "文书.docx"))
text = "\n".join(p.text for p in doc.paragraphs)
footer_text = "\n".join(p.text for p in doc.sections[0].footer.paragraphs)
fields = json.load(open(os.path.join(HERE, "out", "fields.json"), encoding="utf-8"))

fails = []


def check(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


print("[1] 源数据 8 字段逐字落入 文书.docx")
for k, v in src.items():
    check(v in text, "%-6s = %s" % (k, v))

print("[2] 文种要件")
for label, needle in [
    ("标题「关于……的请示」", "关于购置档案密集架的请示"),
    ("主送机关顶格带冒号", "澜山物业管理有限公司："),
    ("结语「妥否，请批示。」", "妥否，请批示。"),
    ("发文机关署名", src["请示单位"]),
    ("成文日期", src["成文日期"]),
]:
    check(needle in text, label)
check("— 1 —" in footer_text, "页脚页码「— 1 —」")

print("[3] fields.json 自洽")
mapped = {e["源字段"]: e for e in fields["字段映射"]}
check(set(mapped) == set(src), "字段映射覆盖全部 8 个源字段")
check(fields["未落文字段"] == [], "无未落文字段")
for k, v in src.items():
    check(mapped[k]["源值"] == v, "%s 源值登记与源数据一致" % k)
    check(mapped[k]["文中表述"] in text or v in text,
          "%s 登记的文中表述确在文档中" % k)

print("[4] 版式")
sec = doc.sections[0]
mm = lambda emu: round(emu / 36000, 1)  # noqa: E731
check(mm(sec.page_width) == 210 and mm(sec.page_height) == 297, "A4 210×297mm")
check((mm(sec.top_margin), mm(sec.bottom_margin),
       mm(sec.left_margin), mm(sec.right_margin)) == (37.0, 35.0, 28.0, 26.0),
      "页边距 天头37/地脚35/订口28/切口26mm")
fonts = {r.font.name for p in doc.paragraphs for r in p.runs}
check({"仿宋_GB2312", "黑体", "方正小标宋简体"} <= fonts,
      "正文仿宋_GB2312 / 标题小标宋 / 一级标题黑体")

print()
if fails:
    print("FAILED: %d 项" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("ALL PASS")
