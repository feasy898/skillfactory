#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自检：核对 out/文书.docx 与 out/fields.json 是否忠实、完整、合版式。"""

import json
import os
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "lanshan_miji.json")
DOCX = os.path.join(BASE, "out", "文书.docx")
FIELDS = os.path.join(BASE, "out", "fields.json")

ok = True


def check(cond, label, detail=""):
    global ok
    if not cond:
        ok = False
    print(("  PASS  " if cond else "  FAIL  ") + label + (("  -> " + detail) if detail and not cond else ""))


with open(SRC, encoding="utf-8") as f:
    data = json.load(f)
with open(FIELDS, encoding="utf-8") as f:
    meta = json.load(f)
doc = Document(DOCX)

paras = doc.paragraphs
texts = [p.text for p in paras]
full = "\n".join(texts)

print("=== 一、数据落点（逐字命中）===")
for k in ("主送机关", "请示缘由", "请示事项", "请示单位", "成文日期"):
    check(data[k] in full, "「{}」原文出现".format(k), data[k])
check(data["联系人"] in full, "「联系人」原文出现", data["联系人"])
check(data["联系电话"] in full, "「联系电话」原文出现", data["联系电话"])
check("澜山物业综合管理部关于购置档案密集架的请示" in full, "标题完整成文")
check("澜山物业管理有限公司：" in full, "主送机关带冒号顶格")

print("=== 二、文种与结构要件 ===")
check("妥否，请批示" in full, "请示专用结语")
check(texts[0] == "澜山物业综合管理部关于购置档案密集架的请示", "标题位于首段", repr(texts[0]))
check(texts[-3] == data["请示单位"], "倒数第 3 段为发文机关署名", repr(texts[-3]))
check(texts[-2] == data["成文日期"], "倒数第 2 段为成文日期", repr(texts[-2]))
check("联系人" in texts[-1] and "联系电话" in texts[-1], "附注合并联系人与电话")

print("=== 三、版式 ===")
sec = doc.sections[0]
check(abs(sec.page_width - Mm(210)) < 1000, "纸张宽度 A4")
check(abs(sec.page_height - Mm(297)) < 1000, "纸张高度 A4")
check(abs(sec.top_margin - Mm(37)) < 1000, "上边距 37mm")
check(abs(sec.bottom_margin - Mm(35)) < 1000, "下边距 35mm")
check(abs(sec.left_margin - Mm(28)) < 1000, "左边距 28mm")
check(abs(sec.right_margin - Mm(26)) < 1000, "右边距 26mm")

grids = sec._sectPr.findall(qn("w:docGrid"))
check(len(grids) == 1, "docGrid 唯一（无重复元素）", "找到 %d 个" % len(grids))
check(grids and grids[0].get(qn("w:linePitch")) == "580",
      "文档网格行距 580（≈28.99pt，每面 22 行）")
check(sec._sectPr.find(qn("w:evenAndOddHeaders")) is None,
      "evenAndOddHeaders 未误入 sectPr")
from docx.oxml.ns import nsmap
check(doc.settings.element.find(qn("w:evenAndOddHeaders")) is not None,
      "evenAndOddHeaders 位于 settings.xml")

for i, p in enumerate(paras):
    ls = p.paragraph_format.line_spacing
    if ls is None or abs(ls - Pt(28.8)) > 500:
        check(False, "段 {} 固定行距 28.8 磅".format(i), str(ls))
        break
else:
    check(True, "全部 {} 段固定行距 28.8 磅".format(len(paras)))

t0 = paras[0].runs[0]
check(t0.font.size == Pt(18), "标题小 2 号（18pt，单行不拆词）", str(t0.font.size))
check(t0.font.name == "方正小标宋简体", "标题小标宋", str(t0.font.name))
check(str(paras[0].alignment) .startswith("CENTER"), "标题居中", str(paras[0].alignment))

# 主送机关：顶格（无缩进）
zhu = next(p for p in paras if p.text.startswith(data["主送机关"]))
check(zhu.paragraph_format.left_indent in (None, 0), "主送机关居左顶格")
zhu_ind = zhu._element.pPr.find(qn("w:ind"))
check(zhu_ind is None or not zhu_ind.get(qn("w:leftChars")), "主送机关无字符左缩进")

# 正文首行缩进 2 字
for role_txt in (data["请示缘由"], data["请示事项"], "妥否，请批示。"):
    p = next(p for p in paras if p.text == role_txt)
    ind = p._element.pPr.find(qn("w:ind"))
    check(ind is not None and ind.get(qn("w:firstLineChars")) == "200",
          "正文段「{}…」首行缩进 2 字".format(role_txt[:8]))
    check(p.runs[0].font.name == "仿宋_GB2312" and p.runs[0].font.size == Pt(16),
          "正文段「{}…」仿宋 3 号".format(role_txt[:8]))

# 落款右空四字
for role_txt in (data["请示单位"], data["成文日期"]):
    p = next(p for p in paras if p.text == role_txt)
    ind = p._element.pPr.find(qn("w:ind"))
    check(ind is not None and ind.get(qn("w:rightChars")) == "400",
          "落款「{}」右空四字".format(role_txt))

# 页码
ftr = sec.footer
ftxt = "".join(r.text for r in ftr.paragraphs[0].runs) if ftr.paragraphs else ""
check("PAGE" in ftr._element.xml, "单页脚含 PAGE 域")
check("—" in ftxt, "页码格式「— n —」", repr(ftxt))
check(str(ftr.paragraphs[0].alignment).startswith("RIGHT"), "单页码居右")
check(ftr.paragraphs[0].runs and all(
    r.font.size == Pt(14) for r in ftr.paragraphs[0].runs if r.text),
    "页码 4 号（14pt）",
    str([(r.text, r.font.size) for r in ftr.paragraphs[0].runs]))
check('w:val="28"' in ftr._element.xml, "PAGE 域内部字号 28 半磅（4 号）")
eftr = sec.even_page_footer
check("PAGE" in eftr._element.xml, "双页脚含 PAGE 域")
check(str(eftr.paragraphs[0].alignment).startswith("LEFT"), "双页码居左（外侧对齐）")

# fldChar 必须包在 w:r 内，否则 Word 判文件损坏
for name, el in (("单页脚", ftr._element), ("双页脚", eftr._element)):
    bad = [fc for fc in el.iter(qn("w:fldChar")) if fc.getparent().tag != qn("w:r")]
    check(not bad, "{} fldChar 均包在 w:r 内".format(name), "%d 个游离" % len(bad))
    kinds = [fc.get(qn("w:fldCharType")) for fc in el.iter(qn("w:fldChar"))]
    check(kinds == ["begin", "separate", "end"],
          "{} 域字符 begin/separate/end 齐全且有序".format(name), str(kinds))
    check(el.findall(qn("w:p")) and
          not el.findall(qn("w:fldChar")),
          "{} 游离在 w:p 下的 fldChar 为 0".format(name))

print("=== 四、fields.json 自洽 ===")
check(meta["field_count"] == 8 == len(meta["fields"]), "8 个字段全部登记")
check([f["key"] for f in meta["fields"]] == list(data.keys()), "字段键与源数据一一对应且同序")
for f in meta["fields"]:
    pl = f["placement"]
    check(pl is not None and texts[pl["paragraph_index"]] == pl["paragraph_text"],
          "字段「{}」落点索引可回查".format(f["key"]))
    check(f["value"] == data[f["key"]], "字段「{}」值与源数据一致".format(f["key"]))
    if f["key"] != "请示事由":
        check(f["value"] in full, "字段「{}」值确实出现在文书中".format(f["key"]))
check(meta["document"]["文种"] == "请示", "文种=请示")
check(meta["document"]["标题"] == texts[0], "标题与文书首段一致")

print("=== 五、OOXML 结构合法性 ===")
PPR_SEQ = [
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
    "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
]
order_ok = stray_ok = True
for i, p in enumerate(paras):
    pPr = p._element.pPr
    if pPr is None:
        continue
    names = ["w:" + c.tag.split("}")[-1] for c in pPr]
    ranks = [PPR_SEQ.index(n) for n in names if n in PPR_SEQ]
    if ranks != sorted(ranks):
        order_ok = False
        print("      段 {} 顺序错: {}".format(i, names))
    for tag in ("w:fldChar", "w:ind", "w:autoSpaceDE", "w:autoSpaceDN"):
        if p._element.findall(qn(tag)):
            stray_ok = False
check(order_ok, "全部 {} 段 pPr 子元素合 OOXML schema 顺序".format(len(paras)))
check(stray_ok, "无游离在 w:p 下的手工插入元素")

# 缩进 twips 与「N 字」换算必须一致（1 磅 = 20 twips）
sign = next(p for p in paras if p.text == data["请示单位"])._element.pPr.find(qn("w:ind"))
check(sign.get(qn("w:right")) == "1280", "落款右空四字 = 1280 twips",
      str(sign.get(qn("w:right"))))
body = next(p for p in paras if p.text == data["请示缘由"])._element.pPr.find(qn("w:ind"))
check(body.get(qn("w:firstLine")) == "640", "正文首行缩进 2 字 = 640 twips",
      str(body.get(qn("w:firstLine"))))

# 中西文自动间距须显式关闭，否则 Word 会在数字与汉字之间插空
autospace_ok = True
for i, p in enumerate(paras):
    pPr = p._element.pPr
    if pPr is None:
        continue
    de, dn = pPr.find(qn("w:autoSpaceDE")), pPr.find(qn("w:autoSpaceDN"))
    if de is None or dn is None or de.get(qn("w:val")) != "0" or dn.get(qn("w:val")) != "0":
        autospace_ok = False
check(autospace_ok, "全部 {} 段关闭中西文/数字自动间距".format(len(paras)))

check("：" in texts[2] and texts[2].endswith("："), "主送机关行末为全角冒号")
check(not any("  " in t or " 年" in t or " 组" in t for t in texts),
      "源文本未混入半角空格")

print()
print("段落清单：")
for i, t in enumerate(texts):
    print("  [{}] {}".format(i, t))

print()
print("EXIT=" + ("0" if ok else "1"))
sys.exit(0 if ok else 1)