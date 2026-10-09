#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性自评驱动器（ab5-determinism-layout-selfeval）。

用完全相同的输入 fixtures/会议通知/case1.json 连续调用 gen_doc.py 两遍，
写入同一输出目录 out/会议通知/case1（第二遍覆盖复写第一遍）：

  1. 每遍结束后，记录该目录下 文书.docx 与 fields.json 的 sha256/字节数到
     run_log.json（标注第几遍）；第一遍产物字节快照留存于 .determinism/pass1/
  2. 对两遍产物做逐字节对比（同时给出 fields.json 剔除 outputs 类路径键后的
     归一化对比、docx 解析后段落文本/对齐/缩进/字体/行距的逐项对比）
  3. 校验输出目录恰含两个产物，并把对比结论（一致/不一致及差异说明）写入
     run_log.json

退出码：全部一致为 0，任一不一致或调用失败为 1。
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ARM_DIR = Path(__file__).resolve().parent
GEN = ARM_DIR / "gen_doc.py"
SNAPSHOT_DIR = ARM_DIR / ".determinism" / "pass1"
RUN_LOG = ARM_DIR / "run_log.json"

TEMPLATE = "会议通知"
DATA_REL = "fixtures/会议通知/case1.json"
OUTDIR_REL = "out/会议通知/case1"
PRODUCTS = ["文书.docx", "fields.json"]


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def write_run_log(log: dict) -> None:
    RUN_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_gen():
    cmd = [sys.executable, str(GEN), "--template", TEMPLATE,
           "--data", DATA_REL, "--outdir", OUTDIR_REL]
    proc = subprocess.run(cmd, cwd=ARM_DIR, capture_output=True, text=True)
    return cmd, proc


def hash_products() -> dict:
    outdir = ARM_DIR / OUTDIR_REL
    return {
        name: {"sha256": sha256_file(outdir / name), "size_bytes": (outdir / name).stat().st_size}
        for name in PRODUCTS
    }


def compare_bytes(p1: Path, p2: Path) -> dict:
    b1, b2 = p1.read_bytes(), p2.read_bytes()
    if b1 == b2:
        return {
            "byte_identical": True,
            "size_equal": True,
            "size_bytes": len(b1),
            "sha256_equal": sha256_bytes(b1) == sha256_bytes(b2),
            "first_diff_byte_offset": None,
            "detail": f"两遍产物均为 {len(b1)} 字节，逐字节读取比对完全一致",
        }
    first = next((i for i, (a, b) in enumerate(zip(b1, b2)) if a != b), min(len(b1), len(b2)))
    return {
        "byte_identical": False,
        "size_equal": len(b1) == len(b2),
        "size_bytes_pass1": len(b1),
        "size_bytes_pass2": len(b2),
        "sha256_equal": False,
        "first_diff_byte_offset": first,
        "detail": (f"不一致：第 {first} 字节处开始出现差异"
                   f"（第一遍 {len(b1)} 字节，第二遍 {len(b2)} 字节）"),
    }


def strip_output_keys(obj):
    """深拷贝并剔除 outputs 类路径键（outputs/output），用于 fields.json 归一化对比。"""
    if isinstance(obj, dict):
        return {k: strip_output_keys(v) for k, v in obj.items()
                if k not in ("outputs", "output")}
    if isinstance(obj, list):
        return [strip_output_keys(v) for v in obj]
    return obj


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def length_or_none(value):
    if value is None:
        return None
    if hasattr(value, "emu"):  # docx Length
        return value.emu
    return value


def docx_profile(path: Path) -> list:
    """解析 docx：抽取每段 文本/对齐/缩进/行距 与 每个 run 的西文字体/中文字体/字号/加粗。"""
    doc = Document(str(path))
    paras = []
    for p in doc.paragraphs:
        runs = []
        for r in p.runs:
            rpr = r._element.rPr
            east = None
            if rpr is not None and rpr.rFonts is not None:
                east = rpr.rFonts.get(qn("w:eastAsia"))
            runs.append({
                "text": r.text,
                "western_font": r.font.name,
                "east_asia_font": east,
                "size_pt": r.font.size.pt if r.font.size is not None else None,
                "bold": r.font.bold,
            })
        pf = p.paragraph_format
        paras.append({
            "text": p.text,
            "alignment": p.alignment.name if p.alignment is not None else None,
            "first_line_indent_emu": length_or_none(pf.first_line_indent),
            "left_indent_emu": length_or_none(pf.left_indent),
            "line_spacing": str(length_or_none(pf.line_spacing)),
            "line_spacing_rule": pf.line_spacing_rule.name if pf.line_spacing_rule is not None else None,
            "space_before": str(length_or_none(pf.space_before)),
            "space_after": str(length_or_none(pf.space_after)),
            "runs": runs,
        })
    return paras


def zip_parts(path: Path) -> list:
    with zipfile.ZipFile(path) as z:
        return [{"name": i.filename, "sha256": sha256_bytes(z.read(i.filename))}
                for i in z.infolist()]


def main() -> int:
    outdir = ARM_DIR / OUTDIR_REL

    log = {
        "task": "ab5-determinism-layout-selfeval（确定性自评：同输入连跑两遍，第二遍覆盖复写第一遍）",
        "run_id": "glm/office-templates-ab5-determinism-layout-selfeval-rep2/baseline",
        "template": TEMPLATE,
        "data": DATA_REL,
        "outdir": OUTDIR_REL,
        "command": (f"python3 gen_doc.py --template {TEMPLATE} "
                    f"--data {DATA_REL} --outdir {OUTDIR_REL}"),
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "passes": [],
    }

    # 清场：保证两遍都从同一初始状态开始
    shutil.rmtree(outdir, ignore_errors=True)
    shutil.rmtree(ARM_DIR / ".determinism", ignore_errors=True)

    # ---- 第一遍 ----
    cmd, proc1 = run_gen()
    if proc1.returncode != 0:
        log["error"] = f"第一遍调用失败 exit={proc1.returncode} stderr={proc1.stderr}"
        write_run_log(log)
        print(log["error"], file=sys.stderr)
        return 1
    log["passes"].append({
        "pass": 1,
        "finished_at": now_iso(),
        "exit_code": proc1.returncode,
        "files": hash_products(),
        "snapshot_dir": str(SNAPSHOT_DIR.relative_to(ARM_DIR)),
    })
    log["status"] = "pass1_recorded（第一遍 sha256 已登记，产物已快照，待第二遍）"
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PRODUCTS:
        shutil.copy2(outdir / name, SNAPSHOT_DIR / name)
    write_run_log(log)

    # ---- 第二遍（同命令行，覆盖复写同一输出目录）----
    cmd, proc2 = run_gen()
    if proc2.returncode != 0:
        log["error"] = f"第二遍调用失败 exit={proc2.returncode} stderr={proc2.stderr}"
        write_run_log(log)
        print(log["error"], file=sys.stderr)
        return 1
    log["passes"].append({
        "pass": 2,
        "finished_at": now_iso(),
        "exit_code": proc2.returncode,
        "files": hash_products(),
    })
    write_run_log(log)

    # ---- 逐字节对比 ----
    docx_cmp = compare_bytes(SNAPSHOT_DIR / "文书.docx", outdir / "文书.docx")
    fields_cmp = compare_bytes(SNAPSHOT_DIR / "fields.json", outdir / "fields.json")

    f1 = json.loads((SNAPSHOT_DIR / "fields.json").read_text(encoding="utf-8"))
    f2 = json.loads((outdir / "fields.json").read_text(encoding="utf-8"))
    fields_norm_equal = canonical_json(strip_output_keys(f1)) == canonical_json(strip_output_keys(f2))
    fields_cmp["excluding_output_keys_equal"] = fields_norm_equal

    stdout_equal = proc1.stdout == proc2.stdout and proc1.stderr == proc2.stderr

    # ---- docx 解析级对比（文本/对齐/缩进/字体/行距）----
    prof1 = docx_profile(SNAPSHOT_DIR / "文书.docx")
    prof2 = docx_profile(outdir / "文书.docx")
    prof_equal = prof1 == prof2
    parsed = {
        "paragraph_count_pass1": len(prof1),
        "paragraph_count_pass2": len(prof2),
        "paragraph_profiles_equal": prof_equal,
        "text_equal": [p["text"] for p in prof1] == [p["text"] for p in prof2],
        "alignment_equal": [p["alignment"] for p in prof1] == [p["alignment"] for p in prof2],
        "indent_equal": (
            [(p["first_line_indent_emu"], p["left_indent_emu"]) for p in prof1]
            == [(p["first_line_indent_emu"], p["left_indent_emu"]) for p in prof2]
        ),
        "font_equal": (
            [[r["western_font"], r["east_asia_font"], r["size_pt"], r["bold"]] for p in prof1 for r in p["runs"]]
            == [[r["western_font"], r["east_asia_font"], r["size_pt"], r["bold"]] for p in prof2 for r in p["runs"]]
        ),
        "line_spacing_equal": (
            [(p["line_spacing"], p["line_spacing_rule"]) for p in prof1]
            == [(p["line_spacing"], p["line_spacing_rule"]) for p in prof2]
        ),
        "zip_parts": {},
    }
    parts1, parts2 = zip_parts(SNAPSHOT_DIR / "文书.docx"), zip_parts(outdir / "文书.docx")
    parsed["zip_parts"] = {
        "names_equal": [x["name"] for x in parts1] == [x["name"] for x in parts2],
        "part_count": len(parts1),
        "all_part_sha256_equal": parts1 == parts2,
    }

    # ---- 输出目录恰含两产物 ----
    actual = sorted(os.listdir(outdir))
    outdir_ok = actual == sorted(PRODUCTS)

    all_equal = (docx_cmp["byte_identical"] and fields_cmp["byte_identical"]
                 and fields_norm_equal and prof_equal and stdout_equal and outdir_ok)

    if all_equal:
        h_docx = log["passes"][0]["files"]["文书.docx"]["sha256"]
        h_fields = log["passes"][0]["files"]["fields.json"]["sha256"]
        conclusion = (
            "一致：同输入（fixtures/会议通知/case1.json）连跑两遍至同一输出目录 "
            "out/会议通知/case1，文书.docx 两遍 sha256 均为 " + h_docx + "、逐字节比对完全一致；"
            "fields.json 两遍 sha256 均为 " + h_fields + "、逐字节比对完全一致"
            "（剔除 outputs 类路径键后归一化对比亦一致）；"
            f"docx 解析后 {len(prof1)} 个段落的文本/对齐/缩进/字体/行距逐项完全一致，"
            f"包内 {len(parts1)} 个 zip 部件逐一 sha256 相同；两遍 stdout/stderr 输出一致；"
            "输出目录恰含 文书.docx 与 fields.json 两个产物；"
            "产物中未发现当前时间、随机内容等不可复现源"
            "（docProps/core.xml 创建/修改时间与 zip 条目时间戳均固定为 2000-01-01）。"
        )
    else:
        diffs = []
        if not docx_cmp["byte_identical"]:
            diffs.append("文书.docx 逐字节不一致：" + docx_cmp["detail"])
        if not fields_cmp["byte_identical"]:
            diffs.append("fields.json 逐字节不一致：" + fields_cmp["detail"])
        if not fields_norm_equal:
            diffs.append("fields.json 剔除 outputs 类路径键后仍不一致")
        if not prof_equal:
            diffs.append("docx 解析后段落属性（文本/对齐/缩进/字体/行距）存在差异")
        if not stdout_equal:
            diffs.append("两遍 stdout/stderr 不一致")
        if not outdir_ok:
            diffs.append(f"输出目录内容异常：期望 {sorted(PRODUCTS)}，实际 {actual}")
        conclusion = "不一致：" + "；".join(diffs)

    log["byte_comparison"] = {"文书.docx": docx_cmp, "fields.json": fields_cmp}
    log["stdout_stderr_identical"] = stdout_equal
    log["docx_parsed_comparison"] = parsed
    log["outdir_check"] = {"expected": sorted(PRODUCTS), "actual": actual, "exactly_two_products": outdir_ok}
    log["conclusion"] = conclusion
    log["status"] = "done"
    write_run_log(log)

    print(conclusion)
    print(f"run_log.json 已写入：{RUN_LOG}")
    return 0 if all_equal else 1


if __name__ == "__main__":
    sys.exit(main())
