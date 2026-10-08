#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性自评驱动（ab5-determinism-layout-selfeval）。

用同一输入 fixtures/会议通知/case1.json，以完全相同的命令行连跑两遍生成器，
两遍都写入同一输出目录 out/会议通知/case1（第二遍覆盖复写第一遍）。每遍结束后
把 文书.docx 与 fields.json 的 sha256 记入 run_log.json（标注第几遍），随后对两遍
产物做逐字节对比与 docx 解析版式对比，并把结论写入 run_log.json。

run_log.json 本身不含任何当前时间/随机内容，可与产物一并复核。
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = "会议通知"
DATA = "fixtures/会议通知/case1.json"
OUTDIR = "out/会议通知/case1"
DOCX_NAME = "文书.docx"
FIELDS_NAME = "fields.json"
SNAP_DIR = os.path.join(BASE, ".selfeval_tmp")
RUN_LOG = os.path.join(BASE, "run_log.json")

CMD = [sys.executable, "generate.py", "--template", TEMPLATE,
       "--data", DATA, "--outdir", OUTDIR]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_log(log: dict) -> None:
    with open(RUN_LOG, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(log, ensure_ascii=False, indent=2) + "\n")


def run_pass(pass_no: int, log: dict) -> dict:
    """执行一遍生成，登记 sha256，返回该遍记录。"""
    proc = subprocess.run(CMD, cwd=BASE, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout + proc.stderr, file=sys.stderr)
        raise SystemExit(f"第 {pass_no} 遍生成失败：exit {proc.returncode}")
    paths = {DOCX_NAME: os.path.join(BASE, OUTDIR, DOCX_NAME),
             FIELDS_NAME: os.path.join(BASE, OUTDIR, FIELDS_NAME)}
    for name, path in paths.items():
        if not os.path.isfile(path):
            raise SystemExit(f"第 {pass_no} 遍产物缺失：{name}")
    record = {
        "第几遍": pass_no,
        "命令行": CMD,
        "sha256": {name: sha256_file(path) for name, path in paths.items()},
    }
    log["passes"].append(record)
    write_log(log)  # 每遍后立即落盘 run_log.json
    return {name: paths[name] for name in paths}


def byte_compare(p1: str, p2: str) -> dict:
    """逐字节对比两个文件。"""
    with open(p1, "rb") as f:
        b1 = f.read()
    with open(p2, "rb") as f:
        b2 = f.read()
    if b1 == b2:
        return {"identical": True, "bytes": len(b1), "first_diff_offset": None}
    first_diff = next((i for i, (x, y) in enumerate(zip(b1, b2)) if x != y),
                      min(len(b1), len(b2)))
    return {"identical": False, "bytes_pass1": len(b1), "bytes_pass2": len(b2),
            "first_diff_offset": first_diff,
            "说明": "两遍文件长度{}，首个差异字节偏移 {}"
                    .format("相同" if len(b1) == len(b2) else "不同", first_diff)}


# ---------- docx 解析版式转储（文本/对齐/缩进/字体/行距 + 页面设置） ----------

try:
    import docx  # noqa: F401
except ModuleNotFoundError:
    import site

    for _cand in (site.getusersitepackages(),):
        if os.path.isdir(_cand) and _cand not in sys.path:
            sys.path.insert(0, _cand)
    import docx

from docx.oxml.ns import qn  # noqa: E402


def _pt(v):
    return round(v.pt, 3) if v is not None else None


def dump_layout(path: str) -> dict:
    d = docx.Document(path)
    sec = d.sections[0]
    out = {
        "page": {
            "width_cm": round(sec.page_width.cm, 3),
            "height_cm": round(sec.page_height.cm, 3),
            "margins_cm": {k: round(getattr(sec, f"{k}_margin").cm, 3)
                           for k in ("top", "bottom", "left", "right")},
        },
        "paragraphs": [],
    }
    for p in d.paragraphs:
        pf = p.paragraph_format
        runs = []
        for r in p.runs:
            rpr = r._element.rPr
            east = (rpr.rFonts.get(qn("w:eastAsia"))
                    if rpr is not None and rpr.rFonts is not None else None)
            runs.append({
                "text": r.text,
                "font_ascii": r.font.name,
                "font_east_asia": east,
                "size_pt": _pt(r.font.size),
                "bold": r.font.bold,
            })
        out["paragraphs"].append({
            "text": p.text,
            "alignment": str(p.alignment),
            "first_line_indent_pt": _pt(pf.first_line_indent),
            "left_indent_pt": _pt(pf.left_indent),
            "right_indent_pt": _pt(pf.right_indent),
            "line_spacing": _pt(pf.line_spacing) if pf.line_spacing is not None else None,
            "line_spacing_rule": str(pf.line_spacing_rule),
            "space_before_pt": _pt(pf.space_before),
            "space_after_pt": _pt(pf.space_after),
            "runs": runs,
        })
    return out


def scan_nonreproducible(docx_path: str, fields_path: str) -> dict:
    """扫描产物中的不可复现源：当前日期/时钟文本、zip 条目真实 mtime。"""
    import datetime

    now = datetime.datetime.now()
    needles = [
        now.strftime("%Y-%m-%d"), now.strftime("%Y/%m/%d"), now.strftime("%Y%m%d"),
        f"{now.year}年{now.month}月{now.day}日",
    ]
    clock = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")
    hits = []

    with zipfile.ZipFile(docx_path) as z:
        names = [zi.filename for zi in z.infolist()
                 if zi.filename.endswith((".xml", ".rels"))]
        mtimes = sorted({str(zi.date_time) for zi in z.infolist()})
        for n in names:
            text = z.read(n).decode("utf-8", errors="ignore")
            hits += [f"{n} 含当前日期 {nd!r}" for nd in needles if nd in text]
            hits += [f"{n} 含时钟时间 {m.group(0)!r}" for m in clock.finditer(text)]

    with open(fields_path, "r", encoding="utf-8") as f:
        ftext = f.read()
    hits += [f"fields.json 含当前日期 {nd!r}" for nd in needles if nd in ftext]
    hits += [f"fields.json 含时钟时间 {m.group(0)!r}"
             for m in clock.finditer(ftext)]

    return {
        "发现": hits,
        "docx_zip_mtime集合": mtimes,
        "结论": ("未发现当前时间/随机内容等不可复现源（docx 全部 zip 条目 mtime 固定为 "
                 "1980-01-01 00:00:00）") if not hits and mtimes == ["(1980, 1, 1, 0, 0, 0)"]
                else "存在疑似不可复现源，见「发现」",
    }


def main() -> int:
    outdir_abs = os.path.join(BASE, OUTDIR)
    if os.path.commonpath([os.path.abspath(outdir_abs), BASE]) != BASE:
        raise SystemExit("输出目录越界，拒绝执行")
    shutil.rmtree(outdir_abs, ignore_errors=True)   # 自评前清空本任务自己的输出目录
    shutil.rmtree(SNAP_DIR, ignore_errors=True)
    os.makedirs(os.path.join(SNAP_DIR, "pass1"), exist_ok=True)

    log = {
        "task": "ab5-determinism-layout-selfeval",
        "template": TEMPLATE,
        "case": "case1",
        "input": {
            "path": DATA,
            "sha256": sha256_file(os.path.join(BASE, DATA)),
            "说明": "两遍使用完全相同的输入与命令行",
        },
        "outdir": OUTDIR,
        "passes": [],
    }
    write_log(log)

    # 第 1 遍：生成 → 记 sha256 → 快照两产物（供第二遍覆盖后对拍）
    p1 = run_pass(1, log)
    snap = {}
    for name, path in p1.items():
        snap[name] = os.path.join(SNAP_DIR, "pass1", name)
        shutil.copyfile(path, snap[name])

    # 第 2 遍：同一命令行重跑，覆盖复写第 1 遍
    p2 = run_pass(2, log)

    # 逐字节对比 + docx 解析版式对比
    byte_cmp = {name: byte_compare(snap[name], p2[name]) for name in p2}
    layout1, layout2 = dump_layout(snap[DOCX_NAME]), dump_layout(p2[DOCX_NAME])
    layout_identical = layout1 == layout2

    all_bytes_identical = all(v["identical"] for v in byte_cmp.values())
    scan = scan_nonreproducible(p2[DOCX_NAME], p2[FIELDS_NAME])
    entries = sorted(os.listdir(outdir_abs))
    outdir_exact = entries == sorted([DOCX_NAME, FIELDS_NAME])

    if all_bytes_identical:
        byte_conclusion, byte_detail = "一致", (
            "两遍产物逐字节相同（长度相等且逐字节比对无差异，sha256 相同）；"
            "fields.json 亦整体逐字节一致（本自评两遍输出目录相同，"
            "outputs 路径键本就无差异）")
    else:
        diffs = [f"{n}: {v}" for n, v in byte_cmp.items() if not v["identical"]]
        byte_conclusion, byte_detail = "不一致", "；".join(diffs)

    log["byte_comparison"] = {
        "conclusion": byte_conclusion,
        "说明": byte_detail,
        "per_file": byte_cmp,
    }
    log["docx_layout_comparison"] = {
        "对比维度": ["段落文本", "对齐", "缩进（首行/左右）", "字体（中西文/字号/加粗）",
                  "行距（含规则）", "段前段后间距", "页面尺寸与页边距"],
        "paragraph_count": len(layout2["paragraphs"]),
        "identical": layout_identical,
        "结论": ("第 1 遍与第 2 遍 docx 解析后的段落文本/对齐/缩进/字体/行距完全一致"
                 if layout_identical else "两遍 docx 解析版式存在差异"),
    }
    log["nonreproducible_scan"] = scan
    log["outdir_contents"] = entries
    log["outdir_exactly_two_artifacts"] = outdir_exact
    log["verdict"] = "PASS（同输入连跑两遍，产物逐字节一致，版式一致，输出目录恰含两产物，未发现不可复现源）" \
        if (all_bytes_identical and layout_identical and outdir_exact
            and not scan["发现"]) else "FAIL（见上各项明细）"
    write_log(log)

    shutil.rmtree(SNAP_DIR, ignore_errors=True)  # 快照仅作对拍中介，不留存

    print(json.dumps({
        "byte_comparison": byte_conclusion,
        "layout_identical": layout_identical,
        "outdir_contents": entries,
        "verdict": log["verdict"],
    }, ensure_ascii=False, indent=2))
    return 0 if log["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
