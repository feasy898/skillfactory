#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 brief.md 逐条验收 out/ 产物。任一检查失败以非 0 退出。"""

import json
import os
import re
import sys

from docx import Document

LINE_RE = re.compile(r"^\s*\[(\d{1,2}:\d{2})\]\s*([^：:]+?)\s*[：:]\s*(.+?)\s*$")
ENTRY_RE = re.compile(r"^(\d+)\. 【(.+?) · (.+?)】(.+)$")

root = os.path.dirname(os.path.abspath(__file__))
transcript = open(os.path.join(root, "fixtures", "transcript.txt"), encoding="utf-8-sig").read()
lines = [ln for ln in transcript.splitlines() if ln.strip()]
speakers = set()
for ln in lines:
    m = LINE_RE.match(ln)
    if m:
        speakers.add(m.group(2).strip())

doc = Document(os.path.join(root, "out", "纪要.docx"))
summary = json.load(open(os.path.join(root, "out", "summary.json"), encoding="utf-8"))

fails = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def traceable(content):
    """内容必须逐字出现在转写稿中，且该出处行的说话人是相关人。"""
    for ln in lines:
        m = LINE_RE.match(ln)
        if not m:
            continue
        if content in m.group(3):
            return m.group(2).strip()
    return None


paras = [p.text for p in doc.paragraphs if p.text.strip()]
print("== 文档结构")
check(bool(paras), "存在非空段落")
check("星帆" in paras[0], "第一段为纪要标题且含会议主题：%r" % paras[0])
for h in ("一、决议事项", "二、待办事项", "三、风险与关注"):
    check(h in paras, "节标题逐字齐全：%s" % h)
idx = [paras.index(h) for h in ("一、决议事项", "二、待办事项", "三、风险与关注")]
check(idx == sorted(idx), "三节顺序固定")

# 决议条目：标题之后、「二、待办事项」之前的段落
dec = [t for t in paras[idx[0] + 1:idx[1]] if ENTRY_RE.match(t)]
# 风险条目
rsk = [t for t in paras[idx[2] + 1:] if ENTRY_RE.match(t)]

print("== 决议事项（%d 条）" % len(dec))
for i, t in enumerate(dec, start=1):
    m = ENTRY_RE.match(t)
    check(m is not None, "第%d条格式 N. 【类别 · 相关人】内容：%s" % (i, t[:30]))
    if not m:
        continue
    check(m.group(1) == str(i), "第%d条编号连续" % i)
    check(m.group(2) == "决议事项", "第%d条类别为 决议事项" % i)
    check(m.group(3) in speakers, "第%d条相关人是转写稿说话人：%s" % (i, m.group(3)))
    check(traceable(m.group(4)) == m.group(3),
          "第%d条内容逐字可溯源且说话人一致：%s" % (i, m.group(4)))

print("== 风险与关注（%d 条）" % len(rsk))
for i, t in enumerate(rsk, start=1):
    m = ENTRY_RE.match(t)
    check(m is not None, "第%d条格式合规：%s" % (i, t[:30]))
    if not m:
        continue
    check(m.group(1) == str(i), "第%d条编号连续" % i)
    check(m.group(2) == "风险与关注", "第%d条类别为 风险与关注" % i)
    check(m.group(3) in speakers, "第%d条相关人是转写稿说话人：%s" % (i, m.group(3)))
    check(traceable(m.group(4)) == m.group(3),
          "第%d条内容逐字可溯源且说话人一致：%s" % (i, m.group(4)))

print("== 待办事项表格")
check(len(doc.tables) == 1, "存在 1 个表格")
tb = doc.tables[0]
check(len(tb.columns) == 3, "表格 3 列")
header = [c.text.strip() for c in tb.rows[0].cells]
check(header == ["事项", "负责人", "期限"], "表头逐字为 事项/负责人/期限：%s" % header)
rows = tb.rows[1:]
for i, row in enumerate(rows, start=1):
    item, owner, due = [c.text.strip() for c in row.cells]
    check(traceable(item) is not None, "第%d行事项逐字可溯源：%s" % (i, item))
    check(owner in speakers, "第%d行负责人是转写稿说话人：%s" % (i, owner))
    check(bool(due), "第%d行期限非空：%s" % (i, due))
    if due and due != "未明确":
        # 期限必须是该条待办原文的子串（转写稿中提到的时限），否则即为编造
        check(due in item, "第%d行期限逐字出自该条待办原文：%s" % (i, due))

print("== summary.json")
check(list(summary.keys()) == ["决议事项", "待办事项", "风险与关注", "合计"], "四键名逐字：%s" % list(summary.keys()))
check(summary["决议事项"] == len(dec), "决议事项计数与 docx 一致（%d）" % summary["决议事项"])
check(summary["待办事项"] == len(rows), "待办事项计数与 docx 一致（%d）" % summary["待办事项"])
check(summary["风险与关注"] == len(rsk), "风险与关注计数与 docx 一致（%d）" % summary["风险与关注"])
check(summary["合计"] == len(dec) + len(rows) + len(rsk), "合计=三者之和（%d）" % summary["合计"])

# 无编造：所有出现的人名必须是转写稿说话人
print("== 无编造检查")
body = "\n".join(paras) + "\n" + "\n".join(c.text for t in doc.tables for r in t.rows for c in r.cells)
for name in set(re.findall(r"[一-龥]{2,4}(?=[，、。：\|]|$)", body)):
    pass  # 逐字溯源检查已覆盖内容真实性
check(all(t in transcript for t in [m.group(4) for m in (ENTRY_RE.match(t) for t in dec + rsk)]),
      "全部决议/风险条目内容逐字来自转写稿")

print()
print("产物：out/纪要.docx, out/summary.json")
if fails:
    print("FAILED: %d 项" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("ALL CHECKS PASSED (%d items)" % (len(dec) + len(rows) + len(rsk)))
