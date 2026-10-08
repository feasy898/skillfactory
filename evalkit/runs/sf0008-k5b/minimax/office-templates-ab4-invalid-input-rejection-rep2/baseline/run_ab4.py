#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_ab4.py — ab4 非法输入拒绝行为测试台。

逐组调用 office_tpl.py，每次调用前后对整个臂目录做文件树快照，
差集即为「该次调用的产物残留」。结果写入 run_log.json。
"""

import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/bin/python3"
CLI = os.path.join(BASE, "office_tpl.py")

GROUPS = [
    {"group": "非法组①模板名非法", "kind": "illegal", "template": "证书",
     "data": "fixtures/周报/case1.json", "case": "非法-模板名非法",
     "expect_exit": 2, "expect_reject": "模板名「证书」不在可用模板集合内"},
    {"group": "非法组②数据文件不存在", "kind": "illegal", "template": "周报",
     "data": "fixtures/周报/__不存在的文件__.json", "case": "非法-数据文件不存在",
     "expect_exit": 2, "expect_reject": "数据文件路径不存在"},
    {"group": "非法组③数据非JSON", "kind": "illegal", "template": "周报",
     "data": "fixtures/非法输入/not_json.json", "case": "非法-数据非JSON",
     "expect_exit": 2, "expect_reject": "JSON 解析失败"},
    {"group": "非法组④数据顶层非对象", "kind": "illegal", "template": "周报",
     "data": "fixtures/非法输入/top_level_array.json", "case": "非法-数据顶层非对象",
     "expect_exit": 2, "expect_reject": "顶层为数组而非对象"},
    {"group": "合法对照组", "kind": "legal", "template": "周报",
     "data": "fixtures/周报/case1.json", "case": "case1",
     "expect_exit": 0, "expect_reject": "正常生成，退出码 0 并写出两产物"},
]


def snapshot():
    """返回 {相对路径: True}，覆盖整个臂目录（含空目录标记）。"""
    snap = set()
    for root, dirs, files in os.walk(BASE):
        for d in dirs:
            snap.add(os.path.relpath(os.path.join(root, d), BASE) + os.sep)
        for f in files:
            snap.add(os.path.relpath(os.path.join(root, f), BASE))
    return snap


def summarize(text, limit=400):
    t = (text or "").strip()
    if len(t) > limit:
        t = t[:limit] + " …（已截断）"
    return t


def main():
    entries = []
    for g in GROUPS:
        cmd = [PY, "office_tpl.py", "--template", g["template"],
               "--data", g["data"], "--out", "out", "--case", g["case"]]
        before = snapshot()
        t0 = time.time()
        p = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
        dt = time.time() - t0
        after = snapshot()

        created = sorted(after - before)
        removed = sorted(before - after)
        residue = bool(created)
        stderr = p.stderr or ""
        has_cn = any("一" <= ch <= "鿿" for ch in stderr)
        unit_dir = os.path.join("out", g["template"], g["case"])
        art = {n: os.path.isfile(os.path.join(unit_dir, n))
               for n in ("文书.docx", "fields.json")}

        entries.append({
            "group": g["group"],
            "kind": g["kind"],
            "name": g["group"],
            "case": g["case"],
            "template": g["template"],
            "data": g["data"],
            "command": " ".join(
                ["./" + os.path.relpath(CLI, BASE)] + cmd[2:]),
            "cwd": ".",
            "exit_code": p.returncode,
            "expect_exit": g["expect_exit"],
            "exit_code_as_expected": p.returncode == g["expect_exit"],
            "stdout": summarize(p.stdout),
            "stderr": summarize(stderr),
            "stderr_非空": bool(stderr.strip()),
            "stderr_含中文": has_cn,
            "stderr_摘要行": summarize(stderr.splitlines()[0] if stderr.strip() else ""),
            "拒绝原因": g["expect_reject"],
            "residue": residue,
            "产物残留": residue,
            "residue_paths": created,
            "removed_paths": removed,
            "residue_detail": ("本次调用新建了 %d 个路径：%s" % (len(created), created))
                              if created else "本次调用未创建任何目录或文件（零残留）",
            "unit_dir_exists": os.path.isdir(unit_dir),
            "artifacts": art,
            "duration_s": round(dt, 3),
        })
        print("[%s] exit=%d residue=%s" % (g["group"], p.returncode, created))

    illegal = [e for e in entries if e["kind"] == "illegal"]
    legal = [e for e in entries if e["kind"] == "legal"][0]
    summary = {
        "非法组数": len(illegal),
        "非法组退出码全为2": all(e["exit_code"] == 2 for e in illegal),
        "非法组stderr含中文": all(e["stderr_含中文"] for e in illegal),
        "非法组零产物残留": all(not e["residue"] for e in illegal),
        "非法组均未创建单元目录": all(not e["unit_dir_exists"] for e in illegal),
        "合法对照组退出码": legal["exit_code"],
        "合法对照组两产物齐备": all(legal["artifacts"].values()),
        "产物残留组数": sum(1 for e in illegal if e["residue"]),
    }
    summary["总体结论"] = (
        "PASS：四组非法输入均以退出码 2 拒绝、stderr 有中文错误信息、零产物残留；"
        "合法对照组退出码 0 并在 out/周报/case1/ 生成 文书.docx 与 fields.json。"
        if (summary["非法组退出码全为2"] and summary["非法组stderr含中文"]
            and summary["非法组零产物残留"] and legal["exit_code"] == 0
            and all(legal["artifacts"].values()))
        else "FAIL：存在未达标项，见各组 exit_code / residue 字段。")

    doc = {
        "task": "ab4-invalid-input-rejection",
        "arm": "baseline",
        "rep": 2,
        "entry_point": "office_tpl.py",
        "python": PY,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "residue_probe": "每次调用前后对臂目录全量 os.walk 快照，差集=该次调用产物残留",
        "约定退出码": 2,
        "缺失必填字段口径": "必填缺失不算非法输入：以 ____ 占位、记入 fields.json 台账，退出码 0",
        "runs": entries,
        "summary": summary,
    }
    with open(os.path.join(BASE, "run_log.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["总体结论"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
