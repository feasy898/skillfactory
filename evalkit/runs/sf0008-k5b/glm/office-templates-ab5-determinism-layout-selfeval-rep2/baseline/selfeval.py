#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性自评驱动（ab5-determinism-layout-selfeval）。

流程（对应任务书）：
  1. 用完全相同的输入 fixtures/会议通知/case1.json 连续运行 generate.py 两遍，
     输出到同一目录 out/会议通知/case1（第二遍覆盖复写第一遍）；
  2. 每遍结束后记录该目录下 文书.docx 与 fields.json 的 sha256 到 run_log.json
     （标注第几遍）；
  3. 第一遍产物先快照到 records/determinism/pass1_snapshot/，第二遍完成后对两遍
     产物做逐字节对比；
  4. 对两遍 docx 分别做解析后布局摘要（段落文本/对齐/缩进/字体/行距/页面设置），
     比较摘要是否完全一致；
  5. 把对比结论（一致/不一致及差异说明）与输出目录清单校验一并写入 run_log.json。

说明：run_log.json 为证据台账，刻意不记录墙钟时间（全部字段可复现），
     遍次以 pass 序号标注。
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

OUTDIR_REL = "out/会议通知/case1"
DATA_REL = "fixtures/会议通知/case1.json"
TEMPLATE = "会议通知"
ARTIFACTS = ["文书.docx", "fields.json"]

RECORDS = ROOT / "records" / "determinism"
SNAP_DIR = RECORDS / "pass1_snapshot"

CMD = [sys.executable, "generate.py", "--template", TEMPLATE, "--data", DATA_REL, "--outdir", OUTDIR_REL]

try:
    from docx import Document
    from docx.oxml.ns import qn
except ModuleNotFoundError:
    import os

    _user_site = os.path.expanduser("~/.local/lib/python3.12/site-packages")
    if os.path.isdir(_user_site) and _user_site not in sys.path:
        sys.path.insert(0, _user_site)
    from docx import Document
    from docx.oxml.ns import qn


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def artifact_records(outdir: Path) -> dict:
    return {
        name: {"sha256": sha256_file(outdir / name), "bytes": (outdir / name).stat().st_size}
        for name in ARTIFACTS
    }


def run_pass() -> dict:
    proc = subprocess.run(CMD, cwd=ROOT, capture_output=True, text=True)
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def byte_compare(a: Path, b: Path) -> dict:
    """逐字节对比两个文件（全量读入后逐位置比较，不做哈希近似）。"""
    ba, bb = a.read_bytes(), b.read_bytes()
    if ba == bb:
        return {"equal": True, "differing_bytes": 0, "size_pass1": len(ba), "size_pass2": len(bb)}
    positional = sum(1 for x, y in zip(ba, bb) if x != y)
    length_gap = abs(len(ba) - len(bb))
    return {"equal": False, "differing_bytes": positional + length_gap,
            "size_pass1": len(ba), "size_pass2": len(bb)}


def layout_document(docx_path: Path) -> dict:
    """解析 docx，导出段落文本/对齐/缩进/行距/字体/页面设置的规范结构。"""

    def pt_len(v):
        return None if v is None else v.pt

    d = Document(str(docx_path))
    sec = d.sections[0]
    page = {
        "width_pt": pt_len(sec.page_width),
        "height_pt": pt_len(sec.page_height),
        "margin_pt": {
            "top": pt_len(sec.top_margin),
            "bottom": pt_len(sec.bottom_margin),
            "left": pt_len(sec.left_margin),
            "right": pt_len(sec.right_margin),
        },
    }
    paragraphs = []
    for i, p in enumerate(d.paragraphs):
        pf = p.paragraph_format
        runs = []
        for r in p.runs:
            ea = None
            rpr = r._element.rPr
            if rpr is not None and rpr.rFonts is not None:
                ea = rpr.rFonts.get(qn("w:eastAsia"))
            runs.append({
                "text": r.text,
                "ascii_font": r.font.name,
                "east_asia_font": ea,
                "size_pt": pt_len(r.font.size),
                "bold": r.font.bold,
            })
        ls = pf.line_spacing
        paragraphs.append({
            "index": i,
            "text": p.text,
            "style": p.style.name,
            "alignment": p.alignment.name if p.alignment is not None else None,
            "first_line_indent_pt": pt_len(pf.first_line_indent),
            "left_indent_pt": pt_len(pf.left_indent),
            "line_spacing_pt": pt_len(ls) if not isinstance(ls, (int, float)) else ls,
            "line_spacing_rule": pf.line_spacing_rule.name if pf.line_spacing_rule is not None else None,
            "space_before_pt": pt_len(pf.space_before),
            "space_after_pt": pt_len(pf.space_after),
            "runs": runs,
        })
    return {"page": page, "paragraphs": paragraphs}


def canonical_json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def main() -> int:
    outdir = ROOT / OUTDIR_REL

    # 快照区复位（自评可重复执行）
    if RECORDS.exists():
        shutil.rmtree(RECORDS)
    SNAP_DIR.mkdir(parents=True)

    log = {
        "task": "ab5-determinism-layout-selfeval",
        "template": TEMPLATE,
        "case": "case1",
        "data": DATA_REL,
        "outdir": OUTDIR_REL,
        "command": shlex.join(CMD),
        "note_no_wallclock": "run_log 为确定性证据台账，不记录墙钟时间；遍次以 pass 序号标注",
        "passes": [],
    }

    # ---------------- 第 1 遍 ----------------
    p1 = run_pass()
    if p1["exit_code"] != 0:
        print(f"第 1 遍生成失败 exit={p1['exit_code']}\n{p1['stderr']}", file=sys.stderr)
        return 1
    pass1 = {
        "pass": 1,
        "command": shlex.join(CMD),
        "exit_code": p1["exit_code"],
        "outdir_entries_after": sorted(q.name for q in outdir.iterdir()),
        "artifacts": artifact_records(outdir),
    }
    log["passes"].append(pass1)
    print(f"[pass 1] ok; sha256: " + ", ".join(f"{k}={v['sha256'][:12]}…" for k, v in pass1["artifacts"].items()))

    # 第 1 遍产物快照（供第 2 遍覆盖后逐字节对拍）
    for name in ARTIFACTS:
        shutil.copyfile(outdir / name, SNAP_DIR / name)

    # ---------------- 第 2 遍（同命令同输入，覆盖复写第 1 遍） ----------------
    p2 = run_pass()
    if p2["exit_code"] != 0:
        print(f"第 2 遍生成失败 exit={p2['exit_code']}\n{p2['stderr']}", file=sys.stderr)
        return 1
    pass2 = {
        "pass": 2,
        "command": shlex.join(CMD),
        "exit_code": p2["exit_code"],
        "outdir_entries_after": sorted(q.name for q in outdir.iterdir()),
        "artifacts": artifact_records(outdir),
    }
    log["passes"].append(pass2)
    print(f"[pass 2] ok; sha256: " + ", ".join(f"{k}={v['sha256'][:12]}…" for k, v in pass2["artifacts"].items()))

    # ---------------- 两遍产物逐字节对比 ----------------
    byte_cmp = {}
    for name in ARTIFACTS:
        res = byte_compare(SNAP_DIR / name, outdir / name)
        res["method"] = "全量读入逐字节比较（快照第1遍 vs 第2遍现存产物）"
        res["pass1_sha256"] = pass1["artifacts"][name]["sha256"]
        res["pass2_sha256"] = pass2["artifacts"][name]["sha256"]
        res["sha256_equal"] = res["pass1_sha256"] == res["pass2_sha256"]
        byte_cmp[name] = res
    log["byte_compare"] = byte_cmp

    # ---------------- docx 解析后布局对比 ----------------
    layout1 = layout_document(SNAP_DIR / "文书.docx")
    layout2 = layout_document(outdir / "文书.docx")
    (RECORDS / "layout_pass1.json").write_bytes(canonical_json(layout1) + b"\n")
    (RECORDS / "layout_pass2.json").write_bytes(canonical_json(layout2) + b"\n")
    log["docx_layout_compare"] = {
        "parsed_facets": [
            "段落文本", "对齐(alignment)", "缩进(first_line/left)", "行距(line_spacing/rule)",
            "字体(ascii/eastAsia/size/bold)", "段前段后间距", "页面设置(尺寸/页边距)",
        ],
        "pass1_layout_sha256": digest(layout1),
        "pass2_layout_sha256": digest(layout2),
        "equal": canonical_json(layout1) == canonical_json(layout2),
        "detail_files": ["records/determinism/layout_pass1.json", "records/determinism/layout_pass2.json"],
    }

    # ---------------- 输出目录契约校验 ----------------
    final_entries = sorted(q.name for q in outdir.iterdir())
    log["outdir_final_entries"] = final_entries
    log["outdir_exactly_two_artifacts"] = final_entries == sorted(ARTIFACTS)

    # ---------------- 结论 ----------------
    problems = []
    for name in ARTIFACTS:
        if not byte_cmp[name]["equal"]:
            c = byte_cmp[name]
            problems.append(
                f"{name} 两遍字节不一致（差异 {c['differing_bytes']} 字节，"
                f"第1遍 {c['size_pass1']}B / 第2遍 {c['size_pass2']}B，"
                f"sha256 {c['pass1_sha256'][:12]}… vs {c['pass2_sha256'][:12]}…）"
            )
    if not log["docx_layout_compare"]["equal"]:
        problems.append("docx 解析后布局摘要不一致（段落文本/对齐/缩进/字体/行距或页面设置存在差异）")
    if not log["outdir_exactly_two_artifacts"]:
        problems.append(f"输出目录清单非恰含两产物：{final_entries}")

    if problems:
        log["conclusion"] = "不一致：" + "；".join(problems)
    else:
        log["conclusion"] = (
            "一致：同输入连跑两遍（第二遍覆盖复写第一遍）产物逐字节一致——"
            "文书.docx 与 fields.json 的两遍 sha256 相同且全量逐字节比较零差异"
            "（fields.json 含 outputs 类路径键亦逐字节一致，两遍 outdir 相同）；"
            "docx 解析后段落文本/对齐/缩进/字体/行距（含页面设置）完全一致，"
            "产物中无当前时间、随机内容等不可复现源；输出目录恰含 文书.docx 与 fields.json 两产物。"
        )
    log["verdict"] = "PASS" if not problems else "FAIL"

    (ROOT / "run_log.json").write_bytes(
        (json.dumps(log, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    print(f"[byte compare] " + ", ".join(f"{n}:{'一致' if v['equal'] else '不一致'}" for n, v in byte_cmp.items()))
    print(f"[layout compare] {'一致' if log['docx_layout_compare']['equal'] else '不一致'} "
          f"({log['docx_layout_compare']['pass1_layout_sha256'][:12]}…)")
    print(f"[outdir] {final_entries} (恰含两产物: {log['outdir_exactly_two_artifacts']})")
    print(f"[verdict] {log['verdict']}: {log['conclusion']}")
    return 0 if log["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
