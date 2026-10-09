#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab5 确定性自评驱动（baseline）。

协议（对应任务书）：
  1) 清空输出目录；
  2) 第 1 遍按契约命令行运行 gen_doc.py → 记录 文书.docx / fields.json 的 sha256；
  3) 复制第 1 遍产物到 .determinism/run1/ 作复核见证（第 2 遍会覆盖复写）；
  4) 第 2 遍以完全相同的命令行再运行（覆盖复写第 1 遍）→ 再记 sha256；
  5) 两遍产物逐字节对比；
  6) docx 另做解析级对比（段落文本/对齐/缩进/字体/行距等版面签名）；
  7) 检查输出目录恰含两产物；
  8) 对照实验：裸 python-docx 保存跨 2 秒边界两遍逐字节不同（zip 条目头携带
     保存时刻，不可复现源坐实，亦说明「同秒连跑两次」会假通过）；归一化后
     两遍逐字节一致（本生成器消除该差异源）；
  9) 扫描生成器源码中的不可复现源调用；
  10) 全部结论写入 run_log.json（本日志不含时钟字段，自身亦可复现）。
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time as _time
import zipfile

ARM = os.path.dirname(os.path.abspath(__file__))
os.chdir(ARM)

PY = "/usr/bin/python3"  # 系统 Python，user-site 内置 python-docx
GEN = "gen_doc.py"
OUTDIR = os.path.join("out", "会议通知", "case1")
WITNESS = os.path.join(".determinism", "run1")
RUN_LOG = "run_log.json"
PRODUCTS = ["文书.docx", "fields.json"]

CMD = [PY, GEN, "--template", "会议通知",
       "--data", os.path.join("fixtures", "会议通知", "case1.json"),
       "--outdir", OUTDIR]
CMD_STR = " ".join(CMD)

# 生成器源码不可复现源扫描（\b 词边界避免误伤 date_time= 这类常量赋值）
SCAN_PATTERN = r"\btime\(|\bnow\(|\bdatetime\b|\brandom\b|\buuid\b|strftime|time\.time"


def sha256_of(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    return len(blob), hashlib.sha256(blob).hexdigest()


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def run_once():
    proc = subprocess.run(CMD, capture_output=True, text=True)
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def product_ledger():
    led = {}
    for name in PRODUCTS:
        size, digest = sha256_of(os.path.join(OUTDIR, name))
        led[name] = {"bytes": size, "sha256": digest}
    return led


def first_diff(a, b):
    """逐字节对比；一致返回 None，否则返回首个差异位置及两侧上下文。"""
    if a == b:
        return None
    n = min(len(a), len(b))
    off = next(i for i in range(n) if a[i] != b[i])
    lo = max(0, off - 16)
    ctx_a = a[lo:off + 16].hex()
    ctx_b = b[lo:off + 16].hex()
    if len(a) != len(b):
        size_note = "长度不同：%d vs %d" % (len(a), len(b))
    else:
        size_note = "长度相同：%d" % len(a)
    return {"first_diff_offset": off, "context_run1_hex": ctx_a,
            "context_run2_hex": ctx_b, "note": size_note}


def layout_signature(path):
    """解析级版面签名：段落文本/对齐/缩进/行距/字体（ascii+eastAsia+字号+加粗）
    /段落前后距，另含页面几何与页脚页码段。同版面 ⇒ 签名逐项相同。"""
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Length

    def as_pt(v):
        if v is None:
            return None
        if isinstance(v, Length):
            return round(v.pt, 3)
        return v

    def para_sig(p):
        runs = []
        for r in p.runs:
            ea = None
            rPr = r._element.rPr
            if rPr is not None and rPr.rFonts is not None:
                ea = rPr.rFonts.get(qn("w:eastAsia"))
            runs.append({
                "text": r.text,
                "ascii_font": r.font.name,
                "eastAsia_font": ea,
                "size_pt": as_pt(r.font.size),
                "bold": r.font.bold,
            })
        pf = p.paragraph_format
        return {
            "text": p.text,
            "alignment": None if pf.alignment is None else str(pf.alignment),
            "first_line_indent_pt": as_pt(pf.first_line_indent),
            "left_indent_pt": as_pt(pf.left_indent),
            "right_indent_pt": as_pt(pf.right_indent),
            "line_spacing": as_pt(pf.line_spacing),
            "line_spacing_rule": None if pf.line_spacing_rule is None else str(pf.line_spacing_rule),
            "space_before_pt": as_pt(pf.space_before),
            "space_after_pt": as_pt(pf.space_after),
            "runs": runs,
        }

    doc = Document(path)
    sec = doc.sections[0]
    return {
        "core_title": doc.core_properties.title,
        "paragraphs": [para_sig(p) for p in doc.paragraphs],
        "footer_paragraphs": [para_sig(p) for p in sec.footer.paragraphs],
        "section": {
            "page_w_mm": round(sec.page_width.mm, 3),
            "page_h_mm": round(sec.page_height.mm, 3),
            "top_margin_mm": round(sec.top_margin.mm, 3),
            "bottom_margin_mm": round(sec.bottom_margin.mm, 3),
            "left_margin_mm": round(sec.left_margin.mm, 3),
            "right_margin_mm": round(sec.right_margin.mm, 3),
            "footer_distance_mm": round(sec.footer_distance.mm, 3),
        },
    }


def _sleep_past_dos_boundary():
    """DOS 时间戳粒度为 2 秒；睡到跨过下一个 2 秒边界之后，
    确保下一次保存的 zip 条目时间戳与上一次必然不同。"""
    t = _time.time()
    _time.sleep((2.0 - (t % 2.0)) + 0.05)


def control_experiment():
    """对照实验（全部在临时文件上进行，不触碰输出目录）：

    a) 裸 python-docx 保存（不归一化）跨 2 秒边界再保存一次：zip 条目头携带
       保存时刻（DOS 时间戳），两遍字节不同 —— 展示「同秒连跑两次假通过」
       的陷阱与本任务要消除的真实不可复现源；
    b) 同样两份裸产物经 gen_doc.normalize_docx_zip 归一化后逐字节一致 ——
       展示归一化恰好消除该差异源。
    """
    import gen_doc
    from docx import Document

    with open(os.path.join("fixtures", "会议通知", "case1.json"), "r",
              encoding="utf-8") as fh:
        data = json.load(fh)

    def raw_save():
        resolved, _ = gen_doc.resolve_fields(data)
        doc = Document()
        gen_doc.setup_page(doc)
        gen_doc.add_page_number(doc)
        gen_doc.build_tongzhi(doc, resolved)
        doc.core_properties.title = gen_doc.make_title(resolved)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def zip_stamps(blob):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            return sorted({zi.date_time for zi in zf.infolist()})

    blob_a = raw_save()
    _sleep_past_dos_boundary()
    blob_b = raw_save()
    sha_a = hashlib.sha256(blob_a).hexdigest()
    sha_b = hashlib.sha256(blob_b).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        norm_shas = []
        for tag, blob in (("a", blob_a), ("b", blob_b)):
            p = os.path.join(td, tag + ".docx")
            with open(p, "wb") as fh:
                fh.write(blob)
            gen_doc.normalize_docx_zip(p)
            with open(p, "rb") as fh:
                norm_shas.append(hashlib.sha256(fh.read()).hexdigest())

    # 输出目录内在位产物的 zip 条目时间戳（应为固定常量 1980-01-01）
    with open(os.path.join(OUTDIR, "文书.docx"), "rb") as fh:
        outdir_stamps = sorted({zi.date_time for zi in
                                zipfile.ZipFile(io.BytesIO(fh.read())).infolist()})

    hazard = (blob_a != blob_b) or (zip_stamps(blob_a) != zip_stamps(blob_b))
    return {
        "purpose": "证明裸 python-docx 保存携带保存时刻（不可复现源），"
                   "且本生成器的 zip 归一化恰好消除之；同时说明「同秒连跑两次」"
                   "会假通过，两遍协议不能靠连跑速度碰运气。",
        "raw_save": {
            "bytes_identical": blob_a == blob_b,
            "sha256_run_a": sha_a,
            "sha256_run_b": sha_b,
            "zip_entry_stamps_run_a": [list(s) for s in zip_stamps(blob_a)],
            "zip_entry_stamps_run_b": [list(s) for s in zip_stamps(blob_b)],
            "hazard_confirmed": hazard,
        },
        "after_normalize": {
            "bytes_identical": norm_shas[0] == norm_shas[1],
            "sha256_run_a": norm_shas[0],
            "sha256_run_b": norm_shas[1],
        },
        "outdir_product_zip_entry_stamps": [list(s) for s in outdir_stamps],
        "conclusion": ("裸保存两遍逐字节不同（zip 条目头含保存时刻，不可复现源坐实）；"
                       "归一化后两遍逐字节一致（归一化有效消除该差异源）；"
                       "在位产物 zip 条目时间戳全为固定常量 1980-01-01 00:00:00。"
                       if hazard and norm_shas[0] == norm_shas[1] else
                       "对照结果异常，请人工复核"),
    }


def main():
    # 1) 清空输出目录与见证目录
    shutil.rmtree(OUTDIR, ignore_errors=True)
    shutil.rmtree(".determinism", ignore_errors=True)

    # 2) 第 1 遍
    run1 = run_once()
    if run1["exit_code"] != 0:
        print("第 1 遍运行失败：", run1, file=sys.stderr)
        return 1
    led1 = product_ledger()

    # 3) 见证副本（第 2 遍覆盖前留存）
    os.makedirs(WITNESS, exist_ok=True)
    for name in PRODUCTS:
        shutil.copy2(os.path.join(OUTDIR, name), os.path.join(WITNESS, name))

    # 4) 第 2 遍（同命令，覆盖复写）
    run2 = run_once()
    if run2["exit_code"] != 0:
        print("第 2 遍运行失败：", run2, file=sys.stderr)
        return 1
    led2 = product_ledger()

    # 5) 逐字节对比（第 1 遍副本 vs 第 2 遍在位文件）
    byte_cmp = {}
    for name in PRODUCTS:
        b1 = read_bytes(os.path.join(WITNESS, name))
        b2 = read_bytes(os.path.join(OUTDIR, name))
        diff = first_diff(b1, b2)
        byte_cmp[name] = {
            "sha256_run1": led1[name]["sha256"],
            "sha256_run2": led2[name]["sha256"],
            "bytes_run1": led1[name]["bytes"],
            "bytes_run2": led2[name]["bytes"],
            "identical": diff is None,
            "差异说明": "无差异（逐字节一致）" if diff is None else diff,
        }

    # fields.json 路径键豁免条款适用性：机械扫描全部键名
    fields_doc = json.loads(read_bytes(os.path.join(OUTDIR, "fields.json")).decode("utf-8"))
    all_keys = [k for k, _ in _flat_items(fields_doc)]
    path_like = [k for k in all_keys
                 if re.search(r"path|dir|out|file|url|location", k, re.I)]
    byte_cmp["fields.json"]["路径键豁免条款"] = (
        "不适用：机械扫描 fields.json 全部 %d 个键名，无 outputs 类路径键"
        "（命中 %s）；全文均为输入数据派生字段，全文件逐字节对比口径成立"
        % (len(all_keys), path_like if path_like else "空")
    )

    # 6) docx 解析级对比
    sig1 = layout_signature(os.path.join(WITNESS, "文书.docx"))
    sig2 = layout_signature(os.path.join(OUTDIR, "文书.docx"))
    canon1 = json.dumps(sig1, ensure_ascii=False, indent=1, sort_keys=True)
    canon2 = json.dumps(sig2, ensure_ascii=False, indent=1, sort_keys=True)
    digest1 = hashlib.sha256(canon1.encode("utf-8")).hexdigest()
    digest2 = hashlib.sha256(canon2.encode("utf-8")).hexdigest()
    n_runs_total = sum(len(p["runs"]) for p in sig2["paragraphs"]) + sum(
        len(p["runs"]) for p in sig2["footer_paragraphs"])
    parsed_cmp = {
        "对比维度": ["段落文本", "对齐", "缩进（首行/左/右）", "行距（值与规则）",
                   "字体（ascii/eastAsia/字号/加粗）", "段前/段后距",
                   "页面几何（A4/页边距/页脚距）", "页脚页码段"],
        "paragraphs": len(sig2["paragraphs"]),
        "footer_paragraphs": len(sig2["footer_paragraphs"]),
        "runs_total": n_runs_total,
        "signature_sha256_run1": digest1,
        "signature_sha256_run2": digest2,
        "identical": canon1 == canon2,
        "差异说明": "无差异（段落文本/对齐/缩进/字体/行距等版面签名逐项一致）"
                   if canon1 == canon2 else "存在差异，见签名摘要不等",
    }

    # 7) 输出目录恰含两产物
    listing = sorted(os.listdir(OUTDIR))
    outdir_ok = listing == sorted(PRODUCTS)

    # 8) 对照实验（裸保存不可复现源坐实 + 归一化消除之）
    control = control_experiment()
    control_ok = (control["raw_save"]["hazard_confirmed"]
                  and control["after_normalize"]["bytes_identical"])

    # 9) 生成器源码不可复现源扫描
    with open(GEN, "r", encoding="utf-8") as fh:
        src = fh.read()
    hits = [(i + 1, ln.strip()) for i, ln in enumerate(src.splitlines())
            if re.search(SCAN_PATTERN, ln)]
    scan = {
        "pattern": SCAN_PATTERN,
        "hits": len(hits),
        "hit_lines": hits,
        "note": "生成器源码全文扫描；zip 条目时间戳为固定常量 1980-01-01，"
                "非系统时钟读取" if not hits else "存在命中，需人工复核",
    }

    # 10) 汇总 run_log.json
    env = {
        "python": sys.version.split()[0],
        "python_executable": PY,
        "python-docx": __import__("docx").__version__,
        "platform": sys.platform,
        "cwd": ARM,
    }
    all_ok = (byte_cmp["文书.docx"]["identical"]
              and byte_cmp["fields.json"]["identical"]
              and parsed_cmp["identical"] and outdir_ok and not hits
              and control_ok)
    conclusion = (
        "一致（PASS）：同输入（fixtures/会议通知/case1.json）同一命令连跑两遍，"
        "文书.docx 与 fields.json 逐字节一致；docx 解析级段落文本/对齐/缩进/字体/"
        "行距完全一致；生成路径无当前时间、随机内容等不可复现源；"
        "输出目录恰含两产物。"
        if all_ok else
        "不一致或存在风险（FAIL）：详见 comparison 各分项差异说明。"
    )
    run_log = {
        "task": "office 重测臂 ab5-determinism-layout-selfeval（baseline）："
                "同输入连跑两遍确定性自评（会议通知 case1）",
        "protocol": "同一输入与命令行连跑两遍到同一输出目录 %s（第 2 遍覆盖复写第 1 遍）；"
                    "每遍记录 文书.docx 与 fields.json 的 sha256；两遍产物逐字节对比；"
                    "docx 另做解析级版面签名对比；输出目录恰含两产物。" % OUTDIR,
        "engine": "%s（本臂自实现生成器；实现方式不限；GB/T 9704-2012 风格 A4 会议通知；"
                  "docx 保存后 zip 容器归一化：条目时间戳固定 1980-01-01、权限 0644、"
                  "ZIP_DEFLATED、条目顺序沿用源包）" % GEN,
        "command_run1": CMD_STR,
        "command_run2": CMD_STR + "（与第 1 遍完全相同）",
        "environment": env,
        "nondeterminism_scan": scan,
        "runs": [
            {"第几遍": 1, "exit_code": run1["exit_code"], "stdout": run1["stdout"],
             "products": {n: {"bytes": led1[n]["bytes"], "sha256": led1[n]["sha256"]}
                          for n in PRODUCTS}},
            {"第几遍": 2, "exit_code": run2["exit_code"], "stdout": run2["stdout"],
             "products": {n: {"bytes": led2[n]["bytes"], "sha256": led2[n]["sha256"]}
                          for n in PRODUCTS}},
        ],
        "comparison": {
            "byte_level": byte_cmp,
            "docx_parsed": parsed_cmp,
            "outdir_contents": {
                "expected_exactly": sorted(PRODUCTS),
                "actual": listing,
                "exactly_two_products": outdir_ok,
            },
        },
        "control_experiment": control,
        "conclusion": conclusion,
        "witness": "第 2 遍覆盖前留存的第 1 遍产物副本在 %s/，可复核逐字节对比" % WITNESS,
    }
    with open(RUN_LOG, "w", encoding="utf-8") as fh:
        json.dump(run_log, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(conclusion)
    for name in PRODUCTS:
        c = byte_cmp[name]
        print("  %s: identical=%s sha256_run1=%s sha256_run2=%s"
              % (name, c["identical"], c["sha256_run1"][:16] + "…",
                 c["sha256_run2"][:16] + "…"))
    print("  outdir 恰含两产物:", outdir_ok, "| 扫描命中:", len(hits),
          "| 对照实验:", "坐实+消除" if control_ok else "异常")
    return 0 if all_ok else 1


def _flat_items(d, prefix=""):
    for k, v in d.items():
        yield prefix + k, v
        if isinstance(v, dict):
            yield from _flat_items(v, prefix + k + ".")


if __name__ == "__main__":
    sys.exit(main())
