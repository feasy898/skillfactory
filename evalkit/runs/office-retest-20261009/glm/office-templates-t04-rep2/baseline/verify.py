# verify.py — 程序化校验 out/文书.docx + out/fields.json（会议通知模板字段口径）
# 判据（全部可机判）：
#  1) fields.json.summary 计数：total=11 / filled=8 / missing=3 / missing_required=0 / missing_required_names=[]
#  2) unknown_keys 与 7 元素码点序期望序列逐项相等（Python sorted() 口径）
#  3) 台账明细与汇总一致；缺失字段恰为 会议议题/会议要求/联系人；联系人 rendered_as=留空
#  4) 文书正文：标题正确；8 个有值字段值逐字出现；「会议议题：」「联系人：」标签保留且其后为空；
#     「会议要求」整节不出现；7 个杂项键名与值零泄入；页脚含页码域
#  5) docx 为合法 ZIP 且 word/document.xml 可解析
import json
import pathlib
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ROOT = pathlib.Path(__file__).resolve().parent
SRC = json.loads((ROOT / "qingheng_dongji.json").read_text(encoding="utf-8"))

EXPECTED_UNKNOWN = ["1号议程", "Zebra", "_private", "abc", "备用3", "附件编号", "📋备注"]
EXPECTED_MISSING = {"会议议题", "会议要求", "联系人"}
FILLED_VALUES = [
    "关于召开冬季送暖协调会的通知",
    "青蘅茶社志愿组", "各分社负责人", "2026年11月3日 10:00",
    "青蘅茶社一层品鉴室", "各分社负责人、志愿组骨干", "137-5566-0099", "2026年10月28日",
]
JUNK_VALUES = ["暖炉采购比价", "draft", "内部备注勿删", "测试遗留键", "待定", "QN-2026-118", "emoji 键排序锚点"]

fails = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        fails.append(name)


# ---- fields.json ----
ledger = json.loads((ROOT / "out" / "fields.json").read_text(encoding="utf-8"))
s = ledger["summary"]
check("summary 计数 total/filled/missing = 11/8/3",
      (s["total"], s["filled"], s["missing"]) == (11, 8, 3),
      f"got {s['total']}/{s['filled']}/{s['missing']}")
check("summary missing_required=0 且名单为空",
      s["missing_required"] == 0 and s["missing_required_names"] == [])
check("unknown_keys 与期望序列逐项相等（码点序）", s["unknown_keys"] == EXPECTED_UNKNOWN,
      f"got {s['unknown_keys']}")

fields = ledger["fields"]
check("台账明细 11 项与 summary 计数一致",
      len(fields) == s["total"]
      and sum(1 for r in fields if r["status"] == "filled") == s["filled"]
      and sum(1 for r in fields if r["status"] == "missing") == s["missing"])
check("缺失字段恰为 会议议题/会议要求/联系人",
      {r["name"] for r in fields if r["status"] == "missing"} == EXPECTED_MISSING)
check("有值字段台账值与源数据一致",
      all(r["value"] == SRC[r["name"]] for r in fields if r["status"] == "filled"))
lx = next(r for r in fields if r["name"] == "联系人")
check("联系人记 missing 且 rendered_as=留空（渲染为空字符串）",
      lx["status"] == "missing" and lx["rendered_as"] == "留空（渲染为空字符串）")

# ---- 文书.docx ----
zf = zipfile.ZipFile(ROOT / "out" / "文书.docx")
check("docx 为合法 ZIP 且含 word/document.xml", "word/document.xml" in zf.namelist())
doc_root = ET.fromstring(zf.read("word/document.xml"))
paras = ["".join(t.text or "" for t in p.iter(f"{W}t")) for p in doc_root.iter(f"{W}p")]
paras = [p for p in paras if p != ""]
full = "\n".join(paras)

check("标题 = 关于召开冬季送暖协调会的通知", paras[0] == FILLED_VALUES[0], f"got {paras[0]!r}")
check("8 个有值字段值逐字出现", all(v in full for v in FILLED_VALUES),
      f"缺: {[v for v in FILLED_VALUES if v not in full]}")

for label in ("会议议题", "联系人"):
    hit = [p for p in paras if f"{label}：" in p]
    after = {p.split(f"{label}：", 1)[1] for p in hit}
    check(f"「{label}：」标签保留且标签后为空", len(hit) == 1 and after == {""}, f"paras={hit}")

check("「会议要求」整节不出现（节头与条目均无）", "会议要求" not in full)
check("7 个杂项键名零泄入正文", not any(k in full for k in EXPECTED_UNKNOWN),
      f"泄入: {[k for k in EXPECTED_UNKNOWN if k in full]}")
check("7 个杂项键值零泄入正文", not any(v in full for v in JUNK_VALUES),
      f"泄入: {[v for v in JUNK_VALUES if v in full]}")

footer_xml = b"".join(zf.read(n) for n in zf.namelist() if "footer" in n)
check("页脚含页码域（PAGE）", b"PAGE" in footer_xml)

print("-" * 60)
if fails:
    print(f"FAILED: {len(fails)} 项 → " + "; ".join(fails))
    sys.exit(1)
print("ALL PASS")
