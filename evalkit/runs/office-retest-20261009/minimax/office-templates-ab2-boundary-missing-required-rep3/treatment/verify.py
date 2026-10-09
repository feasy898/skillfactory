#!/usr/bin/env python3
"""ab2-boundary-missing-required：交付前核对（缺数据不编造 + 如实记账 + 版式不破）。"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent
CASES = {
    "请示函": {
        "input": ROOT / "fixtures/请示函/case2.json",
        "outdir": ROOT / "out/请示函/case2",
        "required_missing": ["主送机关", "请示事项"],
        "optional_missing": ["联系电话", "成文日期"],
        "unknown": [],
        "title": "关于延期举办季度评审会的请示",
        "must_contain": ["____：", "联系人：李工", "联系电话：", "评测技术部"],
        "must_not_contain": [],
    },
    "会议通知": {
        "input": ROOT / "fixtures/会议通知/case2.json",
        "outdir": ROOT / "out/会议通知/case2",
        "required_missing": ["会议名称", "会议地点"],
        "optional_missing": ["会议议题", "会议要求", "联系人", "联系电话"],
        "unknown": ["备注"],
        "title": "关于召开____的通知",
        "must_contain": ["各部门：", "会议地点：____", "会议议题：", "联系人：", "联系电话：", "评测技术部"],
        "must_not_contain": ["会议要求", "一、"],
    },
}

fails = []


def check(cond, label):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        fails.append(label)


def align(p):
    pf = p.paragraph_format
    if pf.alignment is not None:
        return int(pf.alignment)
    return None


def first_line_indent(p):
    pf = p.paragraph_format
    return pf.first_line_indent


for tpl, spec in CASES.items():
    print(f"\n=== {tpl} ===")
    data = json.loads(spec["input"].read_text(encoding="utf-8"))
    outdir = spec["outdir"]

    # 1. 单元目录恰含两产物
    files = sorted(p.name for p in outdir.iterdir())
    check(files == ["fields.json", "文书.docx"], f"产物目录恰含两产物 {files}")

    fj = json.loads((outdir / "fields.json").read_text(encoding="utf-8"))
    s = fj["summary"]

    # 2. 缺失事实：键不存在或值 strip 后为空
    present = {k for k, v in data.items() if str(v).strip() != ""}
    names = {f["name"]: f for f in fj["fields"]}

    exp_req = sorted(n for n, f in names.items() if f["required"] and n not in present)
    exp_opt = sorted(n for n, f in names.items() if not f["required"] and n not in present)
    exp_unk = sorted(k for k in data if k not in names)

    check(sorted(s["missing_required_names"]) == exp_req == sorted(spec["required_missing"]),
          f"missing_required_names 与输入事实一致 {s['missing_required_names']} vs {exp_req}")
    check(exp_opt == sorted(spec["optional_missing"]),
          f"选填缺失名单与输入事实一致 {exp_opt}")
    check(sorted(s["unknown_keys"]) == exp_unk == sorted(spec["unknown"]),
          f"unknown_keys 与输入事实一致 {s['unknown_keys']}")

    # 3. 选填缺失不得误记为必填 / 必填缺失不得记为选填
    for n in spec["optional_missing"]:
        check(not names[n]["required"] and names[n]["status"] == "missing",
              f"选填 {n} 记为 missing 且 required=false")
    for n in spec["required_missing"]:
        check(names[n]["required"] and names[n]["status"] == "missing"
              and names[n]["rendered_as"] == "以____占位",
              f"必填 {n} 记为 missing 且以____占位")
    check(not names["会议要求"]["required"] if tpl == "会议通知" else True,
          "会议要求 未被误记为必填")

    # 4. 计数自洽
    check(s["total"] == len(fj["fields"]) and s["filled"] + s["missing"] == s["total"],
          f"summary 计数自洽 total={s['total']} filled={s['filled']} missing={s['missing']}")
    check(fj["title"] == spec["title"], f"title 公式一致：{fj['title']}")

    # 5. 文书版式与内容
    doc = Document(outdir / "文书.docx")
    paras = [(p.text, p) for p in doc.paragraphs]
    nonempty = [(i, txt, p) for i, (txt, p) in enumerate(paras) if txt.strip()]

    check(align(nonempty[0][2]) == 1, "标题居中")
    if tpl in ("请示函", "会议通知"):
        sal = nonempty[1][1]
        check(align(nonempty[1][2]) == 0 or align(nonempty[1][2]) is None,
              f"称谓顶格（无首行缩进/左对齐）：{sal}")
        check(first_line_indent(nonempty[1][2]) in (None, 0),
              "称谓段无首行缩进")
        check(sal.endswith("："), f"称谓全角冒号收尾：{sal}")

    body = "\n".join(t for _, (t, _) in enumerate(paras))
    for frag in spec["must_contain"]:
        check(frag in body, f"文书含「{frag}」")
    for frag in spec["must_not_contain"]:
        check(frag not in body, f"文书不含「{frag}」")

    # 占位数 = 必填缺失数
    n_ph = body.count("____")
    check(n_ph == len(spec["required_missing"]),
          f"文中占位符个数 {n_ph} == 必填缺失数 {len(spec['required_missing'])}")

    # 落款右对齐：末个非空段右对齐 + 右缩进
    last_i, last_txt, last_p = nonempty[-1]
    check(align(last_p) == 2, f"落款右对齐：{last_txt}")
    check(abs(last_p.paragraph_format.right_indent - Pt(32)) < Pt(1),
          f"落款右缩进两字 = {last_p.paragraph_format.right_indent.pt:.1f}pt")

    # 版心
    sec = doc.sections[0]
    cm = lambda v: round(v.cm, 1)
    check((cm(sec.top_margin), cm(sec.bottom_margin), cm(sec.left_margin), cm(sec.right_margin))
          == (3.7, 3.5, 2.8, 2.6),
          "页边距 GB/T 9704 版心")

    print(f"  [段落] " + " | ".join(repr(t) for _, (t, _) in enumerate(paras)))

print("\n" + ("ALL PASS" if not fails else f"FAIL x{len(fails)}: {fails}"))
sys.exit(1 if fails else 0)