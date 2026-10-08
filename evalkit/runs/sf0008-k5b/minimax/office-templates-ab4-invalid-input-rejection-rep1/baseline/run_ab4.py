#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4 非法输入拒绝行为测试台。

对 gen_doc.py 生成入口施加四组非法输入 + 一组合法对照组，逐组记录到
run_log.json：完整命令、退出码、stderr 摘要、产物残留检查。

非法组：
  ① --template 证书              （模板名非法）
  ② --data 指向不存在的文件        （文件缺失）
  ③ --data 指向内容为「不是JSON」的文件（JSON 解析失败）
  ④ --data 指向内容为 ["数组","非对象"] 的文件（顶层非对象）
对照组：
  ⑤ fixtures/周报/case1.json      （合法输入）
"""

import json
import os
import shlex
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(BASE, ".venv", "bin", "python")
GEN = os.path.join(BASE, "gen_doc.py")
TMP = os.path.join(BASE, ".tmp-invalid")
FIXTURE = os.path.join(BASE, "fixtures", "周报", "case1.json")

NOT_JSON = os.path.join(TMP, "非法-不是JSON.json")
ARRAY_JSON = os.path.join(TMP, "非法-顶层数组.json")
MISSING = os.path.join(TMP, "非法-不存在.json")


def snapshot(root):
    """收集 root 下的相对路径集合（用于产物残留检查）。"""
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            seen.add(os.path.relpath(os.path.join(dirpath, d), root))
        for fn in filenames:
            seen.add(os.path.relpath(os.path.join(dirpath, fn), root))
    return seen


def summarize_stderr(text, limit=400):
    text = (text or "").strip()
    if not text:
        return ""
    one_line = " | ".join(line.strip() for line in text.splitlines() if line.strip())
    one_line = one_line.replace(BASE + os.sep, "").replace(BASE, ".")
    if len(one_line) > limit:
        one_line = one_line[:limit] + "…"
    return one_line


def run_group(name, group, template, data, expect_exit, expect_artifacts, outdir):
    argv = [PY, GEN, "--template", template, "--data", data, "--outdir", outdir]
    before = snapshot(outdir) if os.path.isdir(outdir) else set()
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=BASE)
    after = snapshot(outdir) if os.path.isdir(outdir) else set()
    created = sorted(after - before)
    created_files = [p for p in created
                     if os.path.isfile(os.path.join(outdir, p))]
    outdir_created = os.path.isdir(outdir) and len(after) > len(before)
    if expect_exit != 0 and not os.path.isdir(outdir):
        outdir_created = False
    if expect_exit == 0:
        # 合法组：仅允许「数据文件名对应单元目录」下的两个产物
        allowed = {os.path.relpath(a, outdir) for a in expect_artifacts if a}
        residue_files = [p for p in created_files if p not in allowed]
    else:
        # 非法组：任何新增文件都算残留
        residue_files = list(created_files)
    entry = {
        "name": name,
        "kind": "illegal" if expect_exit != 0 else "legal",
        "group": group,
        "command": " ".join(shlex.quote(a) for a in
                            ["python3", "gen_doc.py", "--template", template,
                             "--data", os.path.relpath(data, BASE) if data.startswith(BASE)
                             else data,
                             "--outdir", os.path.relpath(outdir, BASE)]),
        "argv": argv,
        "exit_code": proc.returncode,
        "expected_exit_code": expect_exit,
        "exit_ok": proc.returncode == expect_exit,
        "stderr_summary": summarize_stderr(proc.stderr),
        "stderr_has_chinese": any("一" <= ch <= "鿿" for ch in (proc.stderr or "")),
        "stdout_summary": summarize_stderr(proc.stdout, 200),
        "output_dir": os.path.relpath(outdir, BASE),
        "output_dir_created": bool(outdir_created),
        "files_created": created_files,
        "dirs_created": [p for p in created
                         if os.path.isdir(os.path.join(outdir, p))],
        "residue": residue_files,
        "产物残留": residue_files,
        "clean": not residue_files,
    }
    if expect_exit == 0:
        entry["expected_artifacts"] = [os.path.relpath(a, BASE)
                                       for a in expect_artifacts]
        entry["artifacts_present"] = {
            os.path.relpath(a, BASE): os.path.isfile(a) for a in expect_artifacts}
        entry["clean"] = (entry["clean"]
                          and all(entry["artifacts_present"].values()))
    return entry, created


def main():
    os.makedirs(TMP, exist_ok=True)
    with open(NOT_JSON, "w", encoding="utf-8") as f:
        f.write("不是JSON")
    with open(ARRAY_JSON, "w", encoding="utf-8") as f:
        f.write('["数组", "非对象"]')
    if os.path.exists(MISSING):
        os.remove(MISSING)

    entries = []
    order = []

    # ① 模板名非法
    e, _ = run_group("非法组①-模板名非法", "① --template 证书（模板名非法）",
                     "证书", FIXTURE, 2, [], os.path.join(BASE, "out-illegal-1"))
    entries.append(e); order.append(e)

    # ② data 指向不存在的文件
    e, _ = run_group("非法组②-数据文件不存在", "② --data 指向不存在的文件",
                     "周报", MISSING, 2, [], os.path.join(BASE, "out-illegal-2"))
    entries.append(e); order.append(e)

    # ③ data 内容为「不是JSON」
    e, _ = run_group("非法组③-JSON解析失败", "③ --data 指向内容为「不是JSON」的文件",
                     "周报", NOT_JSON, 2, [], os.path.join(BASE, "out-illegal-3"))
    entries.append(e); order.append(e)

    # ④ data 顶层为数组（非对象）
    e, _ = run_group("非法组④-顶层非对象", "④ --data 指向内容为 [\"数组\",\"非对象\"] 的文件",
                     "周报", ARRAY_JSON, 2, [], os.path.join(BASE, "out-illegal-4"))
    entries.append(e); order.append(e)

    # ⑤ 合法对照组
    out = os.path.join(BASE, "out")
    artifacts = [os.path.join(out, "周报", "case1", "文书.docx"),
                 os.path.join(out, "周报", "case1", "fields.json")]
    e, _ = run_group("合法对照组-周报case1", "⑤ 合法输入 fixtures/周报/case1.json",
                     "周报", FIXTURE, 0, artifacts, out)
    entries.append(e); order.append(e)

    # ⑥ 边界组：必填缺失 + 模板外键（应正常退出、占位记账，不得当成非法输入拒绝）
    boundary_data = os.path.join(TMP, "边界-必填缺失.json")
    with open(boundary_data, "w", encoding="utf-8") as f:
        json.dump({"填报人": "李四", "本周工作内容": [], "报送日期": "2026-10-01",
                   "备注": "模板外键"}, f, ensure_ascii=False, indent=2)
    bound_out = os.path.join(TMP, "out-boundary")
    bound_art = [os.path.join(bound_out, "周报", "边界-必填缺失", "文书.docx"),
                 os.path.join(bound_out, "周报", "边界-必填缺失", "fields.json")]
    e, _ = run_group("边界组-必填缺失以占位处理",
                     "⑥ 必填字段缺失（部门/周期/本周工作内容）+模板外键「备注」",
                     "周报", boundary_data, 0, bound_art, bound_out)
    fj_p = bound_art[1]
    if os.path.isfile(fj_p):
        bj = json.load(open(fj_p, encoding="utf-8"))
        e["missing_required"] = bj.get("missing_required", [])
        e["missing_optional"] = bj.get("missing_optional", [])
        e["unknown_keys"] = bj.get("unknown_keys", [])
        e["summary"] = bj.get("summary", {})
        from docx import Document
        btxt = "\n".join(x.text for x in
                         Document(bound_art[0]).paragraphs)
        e["placeholder_in_docx"] = "____" in btxt
        e["必填缺失占位"] = e["placeholder_in_docx"]
    entries.append(e); order.append(e)

    illegal = [e for e in entries if e["kind"] == "illegal"]
    legal = [e for e in entries if e["kind"] == "legal"]
    boundary = [e for e in entries if e["name"].startswith("边界组")]
    summary = {
        "非法组数": len(illegal),
        "合法对照组数": len(legal),
        "边界组数": len(boundary),
        "非法组退出码全为2": all(e["exit_code"] == 2 for e in illegal),
        "非法组stderr含中文": all(e["stderr_has_chinese"] for e in illegal),
        "非法组零产物残留": all(not e["residue"] and not e["output_dir_created"]
                            for e in illegal),
        "对照组退出码0": all(e["exit_code"] == 0 for e in legal),
        "对照组两产物齐全": all(all(e["artifacts_present"].values()) for e in legal),
        "必填缺失未被当作非法": all(e["exit_code"] == 0 and e.get("placeholder_in_docx")
                                for e in boundary),
    }
    summary["全项通过"] = all(v for v in summary.values())

    log = {
        "task": "ab4-invalid-input-rejection",
        "run_id": "minimax/office-templates-ab4-invalid-input-rejection-rep1",
        "arm": "baseline",
        "entry": "gen_doc.py --template <模板> --data <json> --outdir <目录>",
        "约定退出码": {"非法输入": 2, "合法输入": 0},
        "产物布局": {
            "run_log": "run_log.json",
            "对照组产物": "out/周报/case1/{文书.docx, fields.json}",
        },
        "runs": entries,
        "summary": summary,
    }
    with open(os.path.join(BASE, "run_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for e in entries:
        print("[%s] exit=%d clean=%s residue=%s | %s"
              % (e["kind"], e["exit_code"], e["clean"], e["residue"], e["name"]))
        print("    stderr: %s" % e["stderr_summary"][:160])
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["全项通过"] else 1


if __name__ == "__main__":
    sys.exit(main())
