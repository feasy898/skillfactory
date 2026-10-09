# verify.py — 程序化校验 out/文书.docx + out/fields.json
# 1) fields.json 恰含全部有效字段、不含杂项键
# 2) 文书正文逐字包含全部有效字段值；杂项键名与杂项键值零出现
# 3) docx 为合法 ZIP 且 word/document.xml 可解析、含页脚页码域
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

JUNK_KEYS = ["Zebra", "_private", "abc", "备用3", "📋备注"]
REAL_KEYS = [
    "会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "参会人员",
    "会议议题", "会议要求", "1号议程", "附件编号", "联系电话", "发文日期",
]
# 必须逐字出现在文书里的非空字段值
REQUIRED_VALUES = [
    rawv for k in REAL_KEYS for rawv in [json.load(open("qingheng_dongji.json", encoding="utf-8"))[k]]
    if isinstance(rawv, str) and rawv.strip() != ""
]
JUNK_VALUES = ["draft", "内部备注勿删", "测试遗留键", "待定", "emoji 键排序锚点"]

fails = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        fails.append(name)


# ---- fields.json ----
fields = json.load(open("out/fields.json", encoding="utf-8"))
check("fields.json 键集 = 有效字段集", sorted(fields) == sorted(REAL_KEYS),
      f"多:{sorted(set(fields) - set(REAL_KEYS))} 少:{sorted(set(REAL_KEYS) - set(fields))}")
check("fields.json 无杂项键", not (set(JUNK_KEYS) & set(fields)))
src = json.load(open("qingheng_dongji.json", encoding="utf-8"))
check("fields.json 值与源数据一致", all(fields[k] == src[k] for k in REAL_KEYS))

# ---- docx ----
zf = zipfile.ZipFile("out/文书.docx")
check("docx 为合法 ZIP", zf.testzip() is None)
docxml = zf.read("word/document.xml").decode("utf-8")
root = ET.fromstring(docxml)
paras = []
for p in root.iter(f"{W}p"):
    text = "".join(t.text or "" for t in p.iter(f"{W}t"))
    if text.strip():
        paras.append(text)
fulltext = "\n".join(paras)
print("---- 文书正文 ----")
for p in paras:
    print("  " + p)
print("------------------")

for v in REQUIRED_VALUES:
    check(f"正文含字段值「{v}」", v in fulltext)
for v in JUNK_VALUES:
    check(f"正文不含杂项值「{v}」", v not in fulltext)
for k in JUNK_KEYS:
    check(f"正文不含杂项键名「{k}」", k not in fulltext)
check("正文不含 Markdown 残留", not re.search(r"^#|\*\*|^- ", fulltext, re.M))
check("含结语「特此通知。」", "特此通知。" in fulltext)
check("标题含文种「的通知」", "的通知" in paras[0])
check("页脚含页码域", "PAGE" in zf.read("word/footer1.xml").decode("utf-8"))
check("单页文书（段落量适中）", 8 <= len(paras) <= 20, f"段落数={len(paras)}")

print(f"\nEXIT={'0' if not fails else '1'}  ({len(fails)} failures)")
sys.exit(1 if fails else 0)
