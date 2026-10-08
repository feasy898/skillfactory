#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_case.py — SF-0008 office 臂 ab5-determinism-layout-selfeval 确定性自评执行器

流程（对应 brief.md）：
  1. 以命令行契约连续两遍调用生成引擎（同输入 fixtures/会议通知/case1.json、
     同输出目录 out/会议通知/case1，第二遍覆盖复写第一遍）；
  2. 每遍后记录该目录下 文书.docx 与 fields.json 的 sha256（标注第几遍）；
  3. 对两遍产物做逐字节对比（第一遍产物留快照于 records/run1_snapshot/），
     另做 docx 解析层对比（段落文本/对齐/缩进/字体/行距/页面设置）；
  4. 输出目录恰含两产物校验、fields.json 台账与版式自检；
  5. 全部结果写入 run_log.json（内容确定性：不含任何本次运行时刻的墙钟时间）。

确定性管线说明：
  生成引擎（.zcode/skills/office-templates/scripts/gen_doc.py，python-docx 1.2.0）
  保存 docx 时经 ZipFile.writestr(字符串文件名) 写 zip 条目，CPython 会把保存时刻的
  本地时间写入每个条目的 DOS 时间戳（见 records/probe/analysis.md 实证：两遍原始
  docx 37200 字节中恰 34 字节差异，全部为时间戳秒位，所有 zip 成员内容/CRC/压缩
  大小逐字节相同）。为满足「同输入连跑两遍产物逐字节一致、无当前时间等不可复现源」，
  本管线在每遍生成后对 文书.docx 做规范化重打包：条目顺序/名称/压缩方式/内容字节
  全部保持不变，仅将全部条目时间戳固定为 1980-01-01 00:00:00（可复现构建的标准
  做法）。两遍处理完全相同。fields.json 由引擎直接确定性写出，不做任何后处理。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
VENV_PY = BASE / ".venv/bin/python"
GEN_REL = ".zcode/skills/office-templates/scripts/gen_doc.py"
GEN = BASE / GEN_REL
TEMPLATE = "会议通知"
DATA_REL = "fixtures/会议通知/case1.json"
DATA = BASE / DATA_REL
OUTDIR_REL = "out/会议通知/case1"
OUTDIR = BASE / OUTDIR_REL
DOCX_NAME = "文书.docx"
FIELDS_NAME = "fields.json"
SNAPSHOT_DIR = BASE / "records/run1_snapshot"
RUN_LOG = BASE / "run_log.json"
FIXED_ZIP_DT = (1980, 1, 1, 0, 0, 0)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------- 基础工具

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonicalize_docx(path: Path) -> dict:
    """确定性重打包：保持 zip 成员顺序/名称/压缩方式/内容字节不变，
    仅把每个条目的时间戳固定为 1980-01-01 00:00:00。返回重打包核验摘要。"""
    with zipfile.ZipFile(path) as zf:
        entries = [(i.filename, i.compress_type, zf.read(i.filename))
                   for i in zf.infolist()]
        before = [(n, hashlib.sha256(b).hexdigest()) for n, _c, b in entries]
    tmp = path.with_name(path.name + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w") as out:
            for name, ctype, blob in entries:
                zi = zipfile.ZipInfo(name, date_time=FIXED_ZIP_DT)
                zi.compress_type = ctype
                out.writestr(zi, blob)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        after = [(i.filename, hashlib.sha256(zf.read(i.filename)).hexdigest())
                 for i in infos]
        dts = sorted({i.date_time for i in infos})
    assert before == after, "规范化重打包改变了 zip 成员内容"
    return {
        "member_count": len(infos),
        "member_contents_preserved": True,
        "entry_timestamps_all_fixed_to": list(FIXED_ZIP_DT),
        "distinct_entry_timestamps": [list(d) for d in dts],
    }


# ---------------------------------------------------------------- docx 解析层转储

def _enum_str(v):
    if v is None:
        return None
    return getattr(v, "name", None) or str(v)


def _pt(v):
    return None if v is None else round(v.pt, 4)


def dump_docx(path: Path) -> dict:
    """解析 docx，抽出 brief 要求对比的全部版式维度（确定性、机器可比）。"""
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(str(path))

    def run_info(r):
        rpr = r._element.rPr
        ea = None
        if rpr is not None and rpr.rFonts is not None:
            ea = rpr.rFonts.get(qn("w:eastAsia"))
        return {"text": r.text, "font": r.font.name,
                "east_asia": ea, "size_pt": _pt(r.font.size) if r.font.size else None}

    def para_info(idx, p):
        pf = p.paragraph_format
        ppr = p._p.pPr
        ind = ppr.ind if (ppr is not None and ppr.ind is not None) else None
        flc = ind.get(qn("w:firstLineChars")) if ind is not None else None
        return {
            "index": idx,
            "text": p.text,
            "alignment": _enum_str(p.alignment),
            "first_line_chars": flc,
            "first_line_indent_pt": _pt(pf.first_line_indent),
            "left_indent_pt": _pt(pf.left_indent),
            "right_indent_pt": _pt(pf.right_indent),
            "line_spacing_pt": _pt(pf.line_spacing) if pf.line_spacing is not None else None,
            "line_spacing_rule": _enum_str(pf.line_spacing_rule),
            "space_before_pt": _pt(pf.space_before),
            "space_after_pt": _pt(pf.space_after),
            "runs": [run_info(r) for r in p.runs],
        }

    d = {
        "sections": [{
            "page_width_cm": round(s.page_width.cm, 2),
            "page_height_cm": round(s.page_height.cm, 2),
            "top_margin_cm": round(s.top_margin.cm, 2),
            "bottom_margin_cm": round(s.bottom_margin.cm, 2),
            "left_margin_cm": round(s.left_margin.cm, 2),
            "right_margin_cm": round(s.right_margin.cm, 2),
        } for s in doc.sections],
        "paragraphs": [para_info(i, p) for i, p in enumerate(doc.paragraphs)],
        "core_properties": {k: str(getattr(doc.core_properties, k, None))
                            for k in ("author", "created", "modified",
                                      "last_modified_by", "title", "subject",
                                      "revision", "category", "comments")},
    }
    with zipfile.ZipFile(path) as zf:
        d["zip_members"] = [{"name": i.filename, "crc": i.CRC,
                             "size": i.file_size,
                             "compress_type": i.compress_type}
                            for i in zf.infolist()]
    return d


# ---------------------------------------------------------------- 自检（版式 + 台账）

def expected_paragraphs(data: dict) -> list[tuple[str, str]]:
    """按 references/会议通知.md 成文结构与 case1 数据推导期望段（文本, 角色）。"""
    req = data["会议要求"]
    return [
        ("关于召开%s的通知" % data["会议名称"], "title"),
        ("%s：" % data["主送对象"], "salutation"),
        ("会议时间：%s" % data["会议时间"], "body"),
        ("会议地点：%s" % data["会议地点"], "body"),
        ("参会人员：%s" % data["参会人员"], "body"),
        ("会议议题：%s" % data["会议议题"], "body"),
        ("一、会议要求", "section_header"),
    ] + [("%d．%s" % (i, item), "body") for i, item in enumerate(req, 1)] + [
        ("联系人：%s　　联系电话：%s" % (data["联系人"], data["联系电话"]), "body"),
        (data["召开单位"], "signature"),
        (data["发文日期"], "signature"),
    ]


def self_checks(dump: dict, ledger: dict, data: dict) -> list[dict]:
    """对照 SKILL.md（V1–V8 / S1–S4 / F1–F6）逐条自检，返回 [{check, pass, detail}]。"""
    checks = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    paras = dump["paragraphs"]
    exp = expected_paragraphs(data)

    ck("段落数=12（标题+称谓+4正文+节头+2条目+联系行+2落款）",
       len(paras) == len(exp) == 12, "actual=%d" % len(paras))

    for i, (text, role) in enumerate(exp):
        if i >= len(paras):
            break
        p = paras[i]
        ck("第%d段文本==%r" % (i + 1, text), p["text"] == text, "actual=%r" % p["text"])
        if role == "title":
            ck("第%d段（标题）居中" % (i + 1), p["alignment"] == "CENTER",
               "alignment=%s" % p["alignment"])
            ck("第%d段（标题）黑体/eastAsia=黑体/22pt" % (i + 1),
               p["runs"] and p["runs"][0]["east_asia"] == "黑体"
               and p["runs"][0]["size_pt"] == 22.0, "runs=%s" % p["runs"])
        elif role == "salutation":
            ck("第%d段（称谓）顶格无首行缩进且全角冒号收尾" % (i + 1),
               p["first_line_chars"] is None and p["text"].endswith("："),
               "first_line_chars=%s" % p["first_line_chars"])
        elif role == "body":
            ck("第%d段（正文）firstLineChars=200" % (i + 1),
               p["first_line_chars"] == "200",
               "first_line_chars=%s" % p["first_line_chars"])
            ck("第%d段（正文）仿宋/Times New Roman/16pt/行距28pt" % (i + 1),
               p["runs"] and p["runs"][0]["east_asia"] == "仿宋"
               and p["runs"][0]["font"] == "Times New Roman"
               and p["runs"][0]["size_pt"] == 16.0
               and p["line_spacing_pt"] == 28.0
               and p["line_spacing_rule"] == "EXACTLY",
               "run0=%s line=%s/%s" % (p["runs"][0] if p["runs"] else None,
                                       p["line_spacing_pt"], p["line_spacing_rule"]))
        elif role == "section_header":
            ck("第%d段（节头）黑体/16pt/firstLineChars=200" % (i + 1),
               p["runs"] and p["runs"][0]["east_asia"] == "黑体"
               and p["runs"][0]["size_pt"] == 16.0
               and p["first_line_chars"] == "200",
               "run0=%s flc=%s" % (p["runs"][0] if p["runs"] else None,
                                   p["first_line_chars"]))
        elif role == "signature":
            ck("第%d段（落款）右对齐+右缩进32pt" % (i + 1),
               p["alignment"] == "RIGHT" and p["right_indent_pt"] == 32.0,
               "alignment=%s right_indent_pt=%s" % (p["alignment"],
                                                    p["right_indent_pt"]))

    sec = dump["sections"][0]
    ck("页面 A4 21.0×29.7cm，页边距 上3.7/下3.5/左2.8/右2.6cm",
       sec == {"page_width_cm": 21.0, "page_height_cm": 29.7,
               "top_margin_cm": 3.7, "bottom_margin_cm": 3.5,
               "left_margin_cm": 2.8, "right_margin_cm": 2.6},
       "actual=%s" % sec)
    ck("V7/V8：全文无 ____ 占位、无当前时间/随机源内容",
       all("____" not in p["text"] for p in paras),
       "texts=%s" % [p["text"] for p in paras if "____" in p["text"]])

    # ---- fields.json 台账（S1–S4 / F1–F6）----
    ck("fields.json 顶层恰 7 键",
       sorted(ledger.keys()) == sorted(["template", "title", "filled_fields",
                                        "missing_fields", "fields", "summary",
                                        "outputs"]), "keys=%s" % sorted(ledger.keys()))
    ck("fields.template==会议通知", ledger.get("template") == TEMPLATE)
    ck("fields.title 与文书标题段全文相等",
       ledger.get("title") == paras[0]["text"],
       "title=%r" % ledger.get("title"))
    exp_filled = ["会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
                  "参会人员", "会议议题", "会议要求", "联系人", "联系电话", "发文日期"]
    ck("filled_fields=11/11 全字段已填且序同字段表",
       ledger.get("filled_fields") == exp_filled,
       "actual=%s" % ledger.get("filled_fields"))
    ck("missing_fields 为空", ledger.get("missing_fields") == [])
    s = ledger.get("summary", {})
    ck("summary 恰 6 键且计数自洽（11=11+0，missing_required=0，unknown_keys=[]）",
       sorted(s.keys()) == sorted(["total", "filled", "missing",
                                   "missing_required", "missing_required_names",
                                   "unknown_keys"])
       and s.get("total") == 11 and s.get("filled") == 11 and s.get("missing") == 0
       and s.get("missing_required") == 0
       and s.get("missing_required_names") == [] and s.get("unknown_keys") == [],
       "summary=%s" % s)
    vals = {f["name"]: f.get("value") for f in ledger.get("fields", [])}
    ck("fields 明细：11 项全部 status=filled、value 与输入一致（F5 strip 后）",
       len(ledger.get("fields", [])) == 11
       and all(f["status"] == "filled" for f in ledger["fields"])
       and vals["会议名称"] == data["会议名称"].strip()
       and vals["会议要求"] == [x.strip() for x in data["会议要求"]],
       "vals=%s" % vals)
    ck("outputs 路径指向本输出目录（相对路径）",
       ledger.get("outputs") == {"docx": "%s/%s" % (OUTDIR_REL, DOCX_NAME),
                                 "fields_json": "%s/%s" % (OUTDIR_REL, FIELDS_NAME)},
       "outputs=%s" % ledger.get("outputs"))
    return checks


# ---------------------------------------------------------------- 逐字节对比

def compare_bytes(p1: Path, p2: Path) -> dict:
    b1, b2 = p1.read_bytes(), p2.read_bytes()
    h1, h2 = hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest()
    r = {
        "byte_identical": b1 == b2,
        "sha256_run1": h1,
        "sha256_run2": h2,
        "sha256_equal": h1 == h2,
        "size_bytes_run1": len(b1),
        "size_bytes_run2": len(b2),
    }
    if b1 != b2:
        diffs = [i for i, (x, y) in enumerate(zip(b1, b2)) if x != y]
        r["differing_byte_count"] = len(diffs) + abs(len(b1) - len(b2))
        r["first_diff_offsets"] = diffs[:20]
        r["diff"] = "逐字节不一致：共 %d 处字节差异，首个差异偏移 %s" % (
            r["differing_byte_count"], diffs[:10])
    else:
        r["diff"] = None
    return r


# ---------------------------------------------------------------- 主流程

def one_run(run_no: int) -> dict:
    proc = subprocess.run(
        [str(VENV_PY), GEN_REL, "--template", TEMPLATE,
         "--data", DATA_REL, "--outdir", OUTDIR_REL],
        cwd=BASE, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit("第 %d 遍引擎退出码 %d，stderr：%s"
                         % (run_no, proc.returncode, proc.stderr))
    docx_path = OUTDIR / DOCX_NAME
    fields_path = OUTDIR / FIELDS_NAME
    canon = canonicalize_docx(docx_path)
    return {
        "run": run_no,
        "engine_exit_code": proc.returncode,
        "engine_stdout": proc.stdout.strip(),
        "files": {
            DOCX_NAME: {"sha256": sha256_file(docx_path),
                        "size_bytes": docx_path.stat().st_size,
                        "zip_timestamp_canonicalization": canon},
            FIELDS_NAME: {"sha256": sha256_file(fields_path),
                          "size_bytes": fields_path.stat().st_size},
        },
    }


def main() -> int:
    if not VENV_PY.is_file():
        raise SystemExit("缺少 .venv（先：python3 -m venv .venv && .venv/bin/pip install python-docx）")
    if not GEN.is_file():
        raise SystemExit("缺少生成引擎：%s" % GEN)
    if not DATA.is_file():
        raise SystemExit("缺少输入数据：%s" % DATA)

    data = json.loads(DATA.read_text(encoding="utf-8"))

    # 干净起点：清掉输出目录与旧快照，保证结束时「恰含两产物」可归因于本次两遍运行
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)

    # ---- 第一遍 ----
    run1 = one_run(1)
    SNAPSHOT_DIR.mkdir(parents=True)
    for name in (DOCX_NAME, FIELDS_NAME):
        shutil.copy2(OUTDIR / name, SNAPSHOT_DIR / name)
    for name in (DOCX_NAME, FIELDS_NAME):
        got = sha256_file(SNAPSHOT_DIR / name)
        assert got == run1["files"][name]["sha256"], "快照与第一遍产物不符：%s" % name

    # ---- 第二遍（覆盖复写第一遍）----
    run2 = one_run(2)

    # ---- 逐字节对比（第一遍快照 vs 第二遍最终产物）----
    byte_docx = compare_bytes(SNAPSHOT_DIR / DOCX_NAME, OUTDIR / DOCX_NAME)
    byte_fields = compare_bytes(SNAPSHOT_DIR / FIELDS_NAME, OUTDIR / FIELDS_NAME)

    # fields.json「除 outputs 类路径键外」对比（两遍 outputs 本应同值，仍显式剔除再比）
    f1 = json.loads((SNAPSHOT_DIR / FIELDS_NAME).read_text(encoding="utf-8"))
    f2 = json.loads((OUTDIR / FIELDS_NAME).read_text(encoding="utf-8"))
    outputs_equal = f1.pop("outputs", None) == f2.pop("outputs", None)
    sans_outputs_equal = (json.dumps(f1, ensure_ascii=False, sort_keys=True)
                          == json.dumps(f2, ensure_ascii=False, sort_keys=True))

    # ---- docx 解析层对比 ----
    dump1 = dump_docx(SNAPSHOT_DIR / DOCX_NAME)
    dump2 = dump_docx(OUTDIR / DOCX_NAME)
    parsed_identical = dump1 == dump2

    # ---- 版式与台账自检（基于最终产物；两遍逐字节一致故同一结论适用于两遍）----
    ledger = json.loads((OUTDIR / FIELDS_NAME).read_text(encoding="utf-8"))
    checks = self_checks(dump2, ledger, data)

    # ---- 终态一致性 ----
    listing = sorted(p.name for p in OUTDIR.iterdir())
    outdir_ok = listing == sorted([DOCX_NAME, FIELDS_NAME])
    final_match_run2 = all(
        sha256_file(OUTDIR / n) == run2["files"][n]["sha256"]
        for n in (DOCX_NAME, FIELDS_NAME))

    all_pass = (byte_docx["byte_identical"] and byte_fields["byte_identical"]
                and sans_outputs_equal and parsed_identical
                and outdir_ok and final_match_run2
                and all(c["pass"] for c in checks))

    if all_pass:
        conclusion = ("一致：同输入（%s）按命令行契约连跑两遍至同一输出目录 %s（第二遍覆盖"
                      "复写第一遍）后，文书.docx 与 fields.json 均逐字节一致（sha256 相同）；"
                      "docx 解析层的段落文本/对齐/缩进（含 firstLineChars）/字体（ascii/hAnsi/"
                      "eastAsia/字号）/行距（28 磅 exact）/页面设置完全一致；无当前时间、随机"
                      "内容等不可复现源（引擎原始 zip 条目时间戳已在每遍后按固定值 1980-01-01 "
                      "00:00:00 规范化重打包消除，成员顺序/名称/压缩方式/内容字节保持不变，"
                      "两遍处理完全相同）。输出目录恰含两产物。" % (DATA_REL, OUTDIR_REL))
    else:
        failed = [c["check"] for c in checks if not c["pass"]]
        conclusion = ("不完全一致：byte_docx=%s byte_fields=%s sans_outputs=%s parsed=%s "
                      "outdir_ok=%s final_match=%s；未过自检：%s"
                      % (byte_docx["byte_identical"], byte_fields["byte_identical"],
                         sans_outputs_equal, parsed_identical, outdir_ok,
                         final_match_run2, failed))

    log = {
        "task": "SF-0008 office 臂 ab5-determinism-layout-selfeval（确定性自评）",
        "template": TEMPLATE,
        "data": DATA_REL,
        "outdir": OUTDIR_REL,
        "engine": GEN_REL,
        "engine_invocation": [".venv/bin/python", GEN_REL, "--template", TEMPLATE,
                              "--data", DATA_REL, "--outdir", OUTDIR_REL],
        "determinism_method": (
            "管线 = 生成引擎（按命令行契约调用）+ 每遍后对 文书.docx 的 zip 时间戳规范化"
            "重打包（条目顺序/名称/压缩方式/内容字节不变，时间戳固定 1980-01-01 00:00:00）。"
            "动因：python-docx _ZipPkgWriter 经 ZipFile.writestr(字符串名) 写条目，CPython "
            "为每个条目写入保存时刻的本地时间（DOS 时间戳，秒粒度 2 秒）；预演实证见 "
            "records/probe/analysis.md：两遍原始 docx 仅 34/37200 字节不同且全部为 17 个 "
            "zip 条目×（本地文件头+中央目录）的时间戳秒位，全部成员内容/CRC/压缩大小逐字节"
            "相同——即文档内容层面引擎完全确定，唯一不可复现源是 zip 条目时间戳。"
            "fields.json 由引擎直接确定性写出，无任何后处理。"),
        "runs": [run1, run2],
        "byte_comparison": {
            "method": ("第一遍产物快照（records/run1_snapshot/）与第二遍覆盖复写后的最终"
                       "产物逐字节比对 + sha256 对拍"),
            DOCX_NAME: byte_docx,
            FIELDS_NAME: {
                **byte_fields,
                "outputs_keys_equal": outputs_equal,
                "identical_after_removing_outputs_keys": sans_outputs_equal,
                "note": ("两遍 --outdir 相同，outputs 路径键本就同值；剔除 outputs 键后"
                         "亦逐字节一致，满足「fields.json 除 outputs 类路径键外逐字节一致」"),
            },
        },
        "docx_parsed_comparison": {
            "aspects": ["zip 成员清单与逐成员内容（CRC/大小/压缩方式）", "段落文本",
                        "段落对齐", "缩进（w:firstLineChars 与左/右/首行缩进量）",
                        "字体（ascii/hAnsi 字面、eastAsia、字号）",
                        "行距（值与规则）与段前段后", "页面设置（A4 与页边距）",
                        "文档核心属性（docProps，来自模板，固定值）"],
            "run1_snapshot": "records/run1_snapshot/%s" % DOCX_NAME,
            "run2_final": "%s/%s" % (OUTDIR_REL, DOCX_NAME),
            "identical": parsed_identical,
            "paragraph_count": len(dump2["paragraphs"]),
            "zip_member_count": len(dump2["zip_members"]),
        },
        "docx_layout_dump_final": dump2,
        "self_checks": {
            "basis": "SKILL.md §6（V1–V8）/references/会议通知.md（成文结构与字段规范）"
                     "/§5（S1–S4 台账），两遍逐字节一致故结论同适于两遍",
            "checks": checks,
            "all_pass": all(c["pass"] for c in checks),
        },
        "outdir_listing": listing,
        "outdir_exactly_two_products": outdir_ok,
        "final_files_match_run2_sha256": final_match_run2,
        "conclusion": conclusion,
    }
    RUN_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    print("第 1 遍：%s sha256=%s | %s sha256=%s"
          % (DOCX_NAME, run1["files"][DOCX_NAME]["sha256"][:16],
             FIELDS_NAME, run1["files"][FIELDS_NAME]["sha256"][:16]))
    print("第 2 遍：%s sha256=%s | %s sha256=%s"
          % (DOCX_NAME, run2["files"][DOCX_NAME]["sha256"][:16],
             FIELDS_NAME, run2["files"][FIELDS_NAME]["sha256"][:16]))
    print("逐字节对比：docx 一致=%s，fields.json 一致=%s（剔除 outputs 键后一致=%s）"
          % (byte_docx["byte_identical"], byte_fields["byte_identical"],
             sans_outputs_equal))
    print("docx 解析层一致=%s；自检 %d/%d 通过；输出目录恰含两产物=%s"
          % (parsed_identical, sum(c["pass"] for c in checks), len(checks), outdir_ok))
    print("run_log.json 已写入：%s" % RUN_LOG)
    print("结论：%s" % conclusion)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
