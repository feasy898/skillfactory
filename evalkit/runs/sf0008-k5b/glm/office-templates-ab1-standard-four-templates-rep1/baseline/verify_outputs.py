#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产物自检：目录契约、A4 版面、字体、字段值忠实渲染、fields.json 记账对拍。"""

import json
import os
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
QN = lambda tag: "{%s}%s" % (W, tag)
TEMPLATES = ["周报", "请示函", "会议通知", "工作总结"]
BOILERPLATE = {"妥否，请批示。", "特此通知。"}  # 文种固定结语，非数据编造

fails = []


def check(cond, msg):
    if cond:
        print("  PASS  " + msg)
    else:
        print("  FAIL  " + msg)
        fails.append(msg)


def docx_paras_and_xml(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    root = ET.fromstring(xml)
    paras = ["".join(t.text or "" for t in p.iter(QN("t"))) for p in root.iter(QN("p"))]
    return paras, xml, root


for t in TEMPLATES:
    case_dir = os.path.join("out", t, "case1")
    print("== {} ==".format(t))
    check(sorted(os.listdir(case_dir)) == ["fields.json", "文书.docx"],
          "目录 {} 恰含 文书.docx 与 fields.json".format(case_dir))

    with open(os.path.join("fixtures", t, "case1.json"), encoding="utf-8") as f:
        data = json.load(f)
    rec = json.load(open(os.path.join(case_dir, "fields.json"), encoding="utf-8"))

    paras, xml, root = docx_paras_and_xml(os.path.join(case_dir, "文书.docx"))
    full_text = "\n".join(paras)

    # A4 版面与 GB/T 9704 页边距（twips: 21cm=11906, 29.7cm=16838; 3.7/3.5/2.8/2.6cm）
    sect = root.find(".//" + QN("sectPr"))
    pgSz, pgMar = sect.find(QN("pgSz")), sect.find(QN("pgMar"))
    check((pgSz.get(QN("w")), pgSz.get(QN("h"))) == ("11906", "16838"), "A4 版面 21×29.7cm")
    check((pgMar.get(QN("top")), pgMar.get(QN("bottom")), pgMar.get(QN("left")), pgMar.get(QN("right")))
          == ("2098", "1984", "1587", "1474"), "页边距 上3.7/下3.5/左2.8/右2.6cm")

    # 公文字体声明
    check("方正小标宋简体" in xml and "仿宋_GB2312" in xml and "Times New Roman" in xml,
          "字体声明：标题小标宋 / 正文仿宋_GB2312 / 西文 Times New Roman")

    # 标题居中且为记账 title
    check(rec["title"] in paras, "标题段「{}」存在".format(rec["title"]))

    # fields.json 顶层契约
    check(all(k in rec for k in ("title", "fields", "summary")), "fields.json 含 title/fields/summary")

    names = [f["name"] for f in rec["fields"]]
    check(set(names) == set(data.keys()) and len(names) == len(data.keys()),
          "fields 名称与输入字段一一对应")
    check(all(all(k in f for k in ("name", "required", "status", "value", "rendered_as"))
              for f in rec["fields"]), "每字段含 名称/是否必填/状态/值/渲染方式")

    s = rec["summary"]
    nf = sum(1 for f in rec["fields"] if f["status"] == "filled")
    nm = sum(1 for f in rec["fields"] if f["status"] == "missing")
    check(s == {"filled": nf, "missing": nm, "total": nf + nm}, "summary 计数自洽 filled/missing/total")

    for f in rec["fields"]:
        v = f["value"]
        if f["status"] == "filled":
            check(v == data[f["name"]], "字段 {} filled 值与输入完全一致".format(f["name"]))
            # 值忠实出现在正文（标量整串 / 列表逐项）
            vals = v if isinstance(v, list) else [v]
            for item in vals:
                check(str(item) in full_text, "字段 {} 的值出现在文书正文".format(f["name"]))
            # 已填字段的「字段名：」全角冒号形态（称谓字段为 值+： 顶格，此处宽松校验名称出现）
            check(any(p.startswith(f["name"] + "：") or p == str(v) + "：" or
                      ("（" in p and f["name"] + "：" in p) for p in paras),
                  "字段 {} 以全角冒号形态渲染".format(f["name"]))
        else:
            check(v is None, "字段 {} missing 记账 value=null".format(f["name"]))

    # 本 case 数据全齐：正文不应出现占位符
    check("____" not in full_text, "字段全齐时正文无 ____ 占位（不虚构缺失）")

    # 正文除字段值/标题/固定结语外无其它实质内容（防编造）
    known = set(BOILERPLATE) | {rec["title"]}
    for p in paras:
        if p.strip() == "":
            continue
        if p in known or p.startswith(tuple(n + "：" for n in names)) or \
           any(str(v) in p for v in [x for xx in data.values() for x in (xx if isinstance(xx, list) else [xx])]) or \
           any(p == str(v) + "：" for v in data.values() if isinstance(v, str)):
            continue
        check(False, "出现未记账内容：{}".format(p[:40]))

print()
if fails:
    print("共 {} 项 FAIL".format(len(fails)))
    sys.exit(1)
print("全部检查通过")
