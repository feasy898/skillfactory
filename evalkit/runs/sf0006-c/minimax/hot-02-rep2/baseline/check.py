#!/usr/bin/env python3
"""Independent check of out/ against brief.md rules. Reads files, re-derives from input.json."""
import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, "fixtures", "input.json"), encoding="utf-8"))
raw = open(os.path.join(BASE, "out", "structure.json"), encoding="utf-8").read()
md = open(os.path.join(BASE, "out", "骨架.md"), encoding="utf-8").read()
s = json.loads(raw, object_pairs_hook=dict)  # preserves key order via dict

fails = []
def ck(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond: fails.append(label)

# keys, exact order
keys = ["template_version","platform","platform_name","structure_name","topic",
        "points_input_count","points_used","points_unused","element_count","elements","placeholder_stats"]
ck(list(s.keys()) == keys, f"top-level key order == spec ({len(s.keys())} keys)")

ck(s["platform"] == "xhs", 'platform == "xhs"')
ck(s["platform_name"] == "图文笔记", 'platform_name == "图文笔记"')
ck(s["structure_name"] == "数字标题 + 开头 + 要点×3 + 标签", 'structure_name exact')
ck(s["topic"] == data["topic"], "topic == input topic")
ck(s["points_input_count"] == len(data["points"]), "points_input_count == input count")

# points partition: exact set, no dup, no extra
used, unused = s["points_used"], s["points_unused"]
ck(sorted(used + unused) == sorted(data["points"]), "points_used+unused == input points (set)")
ck(len(used) + len(unused) == len(data["points"]), "no extra/dup points")

ck(s["element_count"] == 6, "element_count == 6")
ck(s["element_count"] == len(s["elements"]), "element_count matches len(elements)")
names = [e["name"] for e in s["elements"]]
ck(names == ["标题","开头","要点1","要点2","要点3","标签"], f"element name sequence verbatim: {names}")
ck(all(set(e.keys()) == {"name","content"} for e in s["elements"]), "each element has exactly name+content")

ck(s["placeholder_stats"] == {"slots":3,"filled":3,"placeholders":0}, "placeholder_stats exact")

# title: arabic digit + emoji
title = s["elements"][0]["content"]
ck(re.search(r"[0-9]", title) is not None, "标题 contains arabic digit")
emo = [c for c in title if ord(c) > 0x1F000 or c in "✅🔥💡📌🌱🚀✨"]
ck(len(emo) >= 1, f"标题 contains emoji codepoint(s): {emo}")

# tags: space separated, 3-8, #-prefixed
tags = s["elements"][5]["content"]
tl = tags.split()
ck(len(tl) == len(tags.split(" ")), "tags space-separated (no stray whitespace)")
ck(3 <= len(tl) <= 8, f"tag count in 3-8: {len(tl)}")
ck(all(t.startswith("#") and len(t) > 1 for t in tl), f"all tags #-prefixed: {tl}")

# 要点N contains point N verbatim
for i in range(3):
    c = s["elements"][2+i]["content"]
    ck(data["points"][i] in c, f"要点{i+1} contains point {i+1} verbatim")

# redline across BOTH files
RED = ["国家级","世界级","最高级","最佳","第一","顶级","独家","万能","百分百","绝对","永久有效","全网第一"]
for w in RED:
    ck(w not in raw, f"structure.json free of redline 「{w}」")
    ck(w not in md, f"骨架.md free of redline 「{w}」")

ck("{{" not in raw and "}}" not in raw, "structure.json no {{ }} placeholder")
ck("{{" not in md and "}}" not in md, "骨架.md no {{ }} placeholder")

# md format: one paragraph per element, 【name】content, same order/content
lines = md.rstrip("\n").split("\n")
ck(len(lines) == 6, f"md has 6 paragraph lines ({len(lines)})")
for i, e in enumerate(s["elements"]):
    ck(lines[i] == f"【{e['name']}】{e['content']}", f"md line {i+1} == 【{e['name']}】+content")

print("\n" + ("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)