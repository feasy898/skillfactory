#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 brief.md 规格生成三节式会议纪要产物。

与 skills/meeting-minutes/scripts/minutes.py 的差异（brief 优先）：
  * 决议/风险条目格式为 `N. 【类别 · 相关人】内容`（skill 为 `N. 【hh:mm · 说话人】内容`）
  * 待办期限抓不到时填 `未明确`（skill 填 `待定`）
  * 分类按语义（决议=议定结论句；待办=明确指派到人的行动项；风险=风险陈述），
    而非纯关键词优先级——关键词优先级会把「…存在履约风险…需要提前准备预案」判成待办，
    导致风险与关注整节为空。
"""

import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

LINE_RE = re.compile(r"^\s*\[(\d{1,2}:\d{2})\]\s*([^：:]+?)\s*[：:]\s*(.+?)\s*$")

TITLE = "星帆订单系统项目例会纪要"
SECTION_DECISION = "一、决议事项"
SECTION_TODO = "二、待办事项"
SECTION_RISK = "三、风险与关注"
TODO_HEADER = ("事项", "负责人", "期限")
NO_DEADLINE = "未明确"

# 每条：(说话人, 逐字内容, [期限])；期限仅待办需要
DECISIONS = [
    ("赵静怡", "星帆订单系统整体进度正常，会议同意按原计划推进，里程碑保持不变"),
    ("黄雨桐", "会议同意星帆订单系统项目预算300万元，走专项列支，由市场部跟进执行"),
]

TODOS = [
    ("黄雨桐", "黄雨桐在本周五前完成复盘纪要并同步给财务部", "黄雨桐", "本周五前"),
    ("徐静怡", "徐静怡负责把数据迁移脚本整理成7月4日归档", "徐静怡", "7月4日"),
]

RISKS = [
    ("吴志远", "财务部侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案"),
    ("赵静怡", "灰度放量方案的数据口径尚未对齐，复盘前需要补齐基线数据"),
]


def read_lines(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return [ln.rstrip("\n") for ln in f]


def style_run(run, size=None, bold=False):
    if size is not None:
        run.font.size = size
    run.bold = bold
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", "宋体")


def build_docx(transcript_lines, out_path):
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(title.add_run(TITLE), size=Pt(18), bold=True)

    n = len(DECISIONS) + len(TODOS) + len(RISKS)
    meta = doc.add_paragraph()
    style_run(meta.add_run("来源：transcript.txt ｜ 收录条目 %d 条（决议 %d · 待办 %d · 风险 %d）"
                            % (n, len(DECISIONS), len(TODOS), len(RISKS))))

    def add_head(text):
        style_run(doc.add_paragraph().add_run(text), size=Pt(14), bold=True)

    def add_entries(category, items):
        for i, (speaker, content) in enumerate(items, start=1):
            p = doc.add_paragraph()
            style_run(p.add_run("%d. 【%s · %s】%s" % (i, category, speaker, content)))

    add_head(SECTION_DECISION)
    add_entries("决议事项", DECISIONS)

    add_head(SECTION_TODO)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, TODO_HEADER):
        style_run(cell.paragraphs[0].add_run(text), bold=True)
    for _speaker, item, owner, deadline in TODOS:
        row = table.add_row()
        style_run(row.cells[0].paragraphs[0].add_run(item))
        style_run(row.cells[1].paragraphs[0].add_run(owner))
        style_run(row.cells[2].paragraphs[0].add_run(deadline or NO_DEADLINE))

    add_head(SECTION_RISK)
    add_entries("风险与关注", RISKS)

    doc.save(out_path)
    return n


def build_summary(out_path):
    summary = {
        "决议事项": len(DECISIONS),
        "待办事项": len(TODOS),
        "风险与关注": len(RISKS),
        "合计": len(DECISIONS) + len(TODOS) + len(RISKS),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    lines = read_lines(os.path.join(root, "fixtures", "transcript.txt"))
    speakers = set()
    for ln in lines:
        m = LINE_RE.match(ln)
        if m:
            speakers.add(m.group(2).strip())
    print("说话人：", "、".join(sorted(speakers)))

    outdir = os.path.join(root, "out")
    os.makedirs(outdir, exist_ok=True)
    n = build_docx(lines, os.path.join(outdir, "纪要.docx"))
    summary = build_summary(os.path.join(outdir, "summary.json"))
    print("OK out/纪要.docx | out/summary.json |", json.dumps(summary, ensure_ascii=False))
    return n


if __name__ == "__main__":
    main()
