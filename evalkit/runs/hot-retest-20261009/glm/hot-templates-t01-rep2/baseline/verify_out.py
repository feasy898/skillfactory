#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_out.py — 对 out/ 两产物做端态断言（口径：wx 满 3 卖点冻结规格）。

断言清单（全部可机判，任一失败 exit 1）：
  1  两产物存在且非空；UTF-8 可解码；LF 换行（无 CRLF）。
  2  structure.json 合法 JSON；顶层关键端态值：element_count=5、topic 原文、
     points_input_count=3、points_used=3 条卖点原文（零改写）、points_unused=[]。
  3  要素 id 顺序 = lead_in → thesis_what → thesis_why → thesis_how → golden_ending；
     三个 thesis 要素 text 分别以「一、是什么」「二、为什么」「三、怎么办」开头。
  4  thesis_how 三行格式：`N. <卖点原文>——【占位:展开：具体做法+一个例子】`（卖点零改写）。
  5  filled 语义：thesis_how.filled_from_input=[point#1,point#2,point#3]；
     lead_in/thesis_what/thesis_why/golden_ending 各含 "topic"；
     total_filled_from_input=7。
  6  golden_ending text 含「<topic>这件事，」与「共勉。」。
  7  占位统计：对 elements[].text 逐要素跑 【占位:([^】]*)】 求和 = 10
     （lead_in 1 + thesis_what 2 + thesis_why 3 + thesis_how 3 + golden_ending 1）；
     与各要素 placeholder_count、placeholder_stats.total_open/by_element 一致。
  8  骨架.md「占位符统计」节与 structure.json 同源：
     `- 未填占位符（待人工/AI 补写）：**10 处**`、`- 已从输入填充：7 处（…）`、逐要素处数行。
  9  纯净：两产物无 `{{`/`}}` 残留。
 10  确定性复跑：同参数重跑生成器到临时目录，与 out/ 逐字节一致。
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MD = os.path.join(OUT, "骨架.md")
SJ = os.path.join(OUT, "structure.json")
PH_RE = re.compile(r"【占位:([^】]*)】")

TOPIC = "宿舍省电费"
POINTS = ["离开寝室随手断插排", "空调设 26 度配合风扇", "插座改用带开关款"]
IDS = ["lead_in", "thesis_what", "thesis_why", "thesis_how", "golden_ending"]
PER_EL = dict(zip(IDS, [1, 2, 3, 3, 1]))

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


md_raw = open(MD, "rb").read() if os.path.isfile(MD) else None
sj_raw = open(SJ, "rb").read() if os.path.isfile(SJ) else None
check("1 两产物存在且非空", bool(md_raw and sj_raw and md_raw.strip() and sj_raw.strip()))
md_text = md_raw.decode("utf-8")
sj_text = sj_raw.decode("utf-8")
check("1 UTF-8/LF（无 CRLF）", b"\r" not in md_raw and b"\r" not in sj_raw)

try:
    sj = json.loads(sj_text)
    json_ok = True
except Exception as e:
    sj, json_ok = {}, False
check("2 structure.json 合法 JSON", json_ok)

els = sj.get("elements", [])
by_id = {e.get("id"): e for e in els}
check("2 element_count=5", sj.get("element_count") == 5, repr(sj.get("element_count")))
check("2 topic 原文", sj.get("topic") == TOPIC, repr(sj.get("topic")))
check("2 points_input_count=3", sj.get("points_input_count") == 3)
check("2 points_used=3 条卖点原文（零改写）", sj.get("points_used") == POINTS, repr(sj.get("points_used")))
check("2 points_unused=[]", sj.get("points_unused") == [], repr(sj.get("points_unused")))

check("3 要素 id 顺序", [e.get("id") for e in els] == IDS, repr([e.get("id") for e in els]))
prefixes = {"thesis_what": "一、是什么", "thesis_why": "二、为什么", "thesis_how": "三、怎么办"}
for eid, pref in prefixes.items():
    t = by_id.get(eid, {}).get("text", "")
    check("3 %s text 以「%s」开头" % (eid, pref), t.startswith(pref), repr(t[:20]))

how_text = by_id.get("thesis_how", {}).get("text", "")
how_lines = how_text.split("\n")
exp_lines = ["三、怎么办", "落到操作层面，给你三个抓手："] + \
            ["%d. %s——【占位:展开：具体做法+一个例子】" % (i, p) for i, p in enumerate(POINTS, 1)]
check("4 thesis_how 三抓手行逐字（卖点原文+——+占位）", how_lines == exp_lines,
      "got=%r" % how_lines)

for eid in ("lead_in", "thesis_what", "thesis_why", "golden_ending"):
    check("5 %s filled_from_input 含 topic" % eid, "topic" in by_id.get(eid, {}).get("filled_from_input", []))
check("5 thesis_how filled_from_input=[point#1..3]",
      by_id.get("thesis_how", {}).get("filled_from_input") == ["point#1", "point#2", "point#3"])
stats = sj.get("placeholder_stats", {})
check("5 total_filled_from_input=7", stats.get("total_filled_from_input") == 7,
      repr(stats.get("total_filled_from_input")))

ge_text = by_id.get("golden_ending", {}).get("text", "")
check("6 金句含「%s这件事，」" % TOPIC, ("「%s这件事，" % TOPIC) in ge_text, repr(ge_text))
check("6 金句含「共勉。」", "共勉。" in ge_text)

total_ph = 0
for eid, expect_n in PER_EL.items():
    n = len(PH_RE.findall(by_id.get(eid, {}).get("text", "")))
    total_ph += n
    check("7 %s 占位 %d 处" % (eid, expect_n), n == expect_n, "got %d" % n)
    check("7 %s placeholder_count 一致" % eid, by_id.get(eid, {}).get("placeholder_count") == n)
check("7 elements[].text 占位合计=10", total_ph == 10, "got %d" % total_ph)
check("7 stats.total_open=10", stats.get("total_open") == 10, repr(stats.get("total_open")))
check("7 stats.by_element 逐要素一致", stats.get("by_element") == PER_EL, repr(stats.get("by_element")))

m_total = re.search(r"未填占位符（待人工/AI 补写）：\*\*(\d+) 处\*\*", md_text)
check("8 骨架.md 统计节 未填=**10 处**", bool(m_total) and m_total.group(1) == "10",
      m_total.group(0) if m_total else "未找到该行")
m_filled = re.search(r"已从输入填充：(\d+) 处（([^）]*)）", md_text)
exp_filled_list = "、".join(["topic", "topic", "topic", "point#1", "point#2", "point#3", "topic"])
check("8 骨架.md 统计节 已填=7 处（槽位清单同源）",
      bool(m_filled) and m_filled.group(1) == "7" and m_filled.group(2) == exp_filled_list,
      m_filled.group(0) if m_filled else "未找到该行")
for order, eid in enumerate(IDS, 1):
    name = by_id.get(eid, {}).get("name", "")
    pat = r"  - %d\. %s：%d 处" % (order, re.escape(name), PER_EL[eid])
    check("8 骨架.md 统计节 %s：%d 处" % (name, PER_EL[eid]), re.search(pat, md_text) is not None)
check("8 骨架.md 占位符统计节存在", "## 占位符统计" in md_text)

check("9 无 {{ }} 残留", "{{" not in md_text and "}}" not in md_text
      and "{{" not in sj_text and "}}" not in sj_text)

tmp = tempfile.mkdtemp(prefix="wx-replay-")
r = subprocess.run([sys.executable, os.path.join(HERE, "gen_wx_skeleton.py"),
                    "--topic", TOPIC,
                    "--points", json.dumps(POINTS, ensure_ascii=False),
                    "--outdir", tmp], capture_output=True)
same = (r.returncode == 0
        and open(os.path.join(tmp, "骨架.md"), "rb").read() == md_raw
        and open(os.path.join(tmp, "structure.json"), "rb").read() == sj_raw)
check("10 同参数重跑逐字节一致（确定性）", same,
      r.stderr.decode("utf-8", "replace")[:200] if r.returncode else "产物字节不一致")

print("\n结果：%s（失败 %d 项）" % ("ALL PASS" if not fails else "FAIL", len(fails)))
sys.exit(1 if fails else 0)
