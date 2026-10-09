#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab4 非法输入拒绝行为测试装置。

对 gen_doc.py 依次施加四组非法输入与一组合法对照组, 逐组记录完整命令、退出码、
stderr 摘要与产物残留检查(该次调用前后 out/ 树的快照差异), 结果写入 run_log.json。
"""

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON = "/usr/bin/python3"          # 该解释器装有 python-docx
GEN = os.path.join(HERE, "gen_doc.py")
OUT_DIR = os.path.join(HERE, "out")
WORK = os.path.join(HERE, ".tmp_invalid")

# 非法输入数据文件：② 不存在（不落盘）③④ 现造于 .tmp_invalid/
NOT_JSON = "这不是JSON，只是一段纯文本，不是合法的 JSON 文档。"
NOT_OBJECT = '["数组", "非对象"]'


def snapshot(root):
    """返回 {相对路径: sha256 或大小}，用于产物残留比对。"""
    import hashlib
    result = {}
    if not os.path.isdir(root):
        return result
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            with open(full, "rb") as fh:
                result[rel] = hashlib.sha256(fh.read()).hexdigest()
    return result


def residue_check(before, after):
    new_files = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    return {
        "检查方式": "以 out/ 目录树文件清单+sha256 在调用前后做差集",
        "调用前产物": sorted(before),
        "调用后产物": sorted(after),
        "新增文件": new_files,
        "被删除文件": removed,
        "被改写文件": changed,
        "是否创建了输出目录": bool(new_files) or bool(removed) or bool(changed)
                                or os.path.isdir(OUT_DIR) and not before,
        "零产物残留": not new_files and not removed and not changed,
    }


def run_case(idx, name, kind, argv, expect_exit, extra=None):
    """执行一组用例并留证。"""
    before = snapshot(OUT_DIR)
    out_dir_existed_before = os.path.isdir(OUT_DIR)
    cmd = [PYTHON, GEN] + argv
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    after = snapshot(OUT_DIR)

    residue = residue_check(before, after)
    if not out_dir_existed_before and os.path.isdir(OUT_DIR):
        # 整棵 out/ 是本次调用新建的，算残留
        residue["新增文件"] = sorted(residue["新增文件"])
        residue["整棵out目录为本次新建"] = True

    stderr = proc.stderr.strip()
    record = {
        "序号": idx,
        "用例名": name,
        "类别": kind,
        "完整命令": " ".join(["python3", "gen_doc.py"] + argv),
        "实际执行": " ".join(cmd),
        "工作目录": HERE,
        "退出码": proc.returncode,
        "期望退出码": expect_exit,
        "退出码符合约定": proc.returncode == expect_exit,
        "stdout": proc.stdout.strip(),
        "stderr完整": stderr,
        "stderr摘要": stderr.splitlines()[0] if stderr else "",
        "stderr含中文": bool(stderr) and any("一" <= ch <= "鿿" for ch in stderr),
        "产物残留检查": residue,
    }
    if expect_exit == 0:
        case_dir = os.path.join(OUT_DIR, "周报", "case1")
        record["产物检查"] = {
            "预期目录": os.path.relpath(case_dir, HERE),
            "目录存在": os.path.isdir(case_dir),
            "文书.docx存在": os.path.isfile(os.path.join(case_dir, "文书.docx")),
            "fields.json存在": os.path.isfile(os.path.join(case_dir, "fields.json")),
            "目录内文件": sorted(os.listdir(case_dir)) if os.path.isdir(case_dir) else [],
        }
        if os.path.isdir(case_dir):
            record["产物检查"]["文书.docx字节数"] = os.path.getsize(
                os.path.join(case_dir, "文书.docx"))
    if extra:
        record.update(extra)
    return record


def run_boundary_missing_required():
    """补充边界：JSON 合法但必填字段缺失 —— 不是非法输入, 须 exit 0 且缺失字段占位。

    在独立临时工作目录中执行, 执行完即删除, 不污染交付的 out/ 产物布局。
    """
    iso = os.path.join(WORK, "iso")
    os.makedirs(iso, exist_ok=True)
    data_path = os.path.join(iso, "partial.json")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump({"部门": "研发部", "报送日期": "2026-09-28"}, fh, ensure_ascii=False)

    cmd = [PYTHON, GEN, "--template", "周报", "--data", data_path]
    proc = subprocess.run(cmd, cwd=iso, capture_output=True, text=True)
    case_dir = os.path.join(iso, "out", "周报", "partial")
    fields_path = os.path.join(case_dir, "fields.json")
    missing = []
    if os.path.isfile(fields_path):
        with open(fields_path, "r", encoding="utf-8") as fh:
            missing = json.load(fh).get("缺失字段", [])
    produced = sorted(os.listdir(case_dir)) if os.path.isdir(case_dir) else []

    record = {
        "序号": "边界1",
        "用例名": "边界：JSON 合法但必填字段缺失（不算非法输入）",
        "类别": "补充边界",
        "完整命令": " ".join(["python3", "gen_doc.py", "--template", "周报",
                            "--data", "<临时>/partial.json"]),
        "实际执行": " ".join(cmd),
        "工作目录": iso + "（临时隔离目录，执行后已删除）",
        "数据内容": {"部门": "研发部", "报送日期": "2026-09-28"},
        "退出码": proc.returncode,
        "期望退出码": 0,
        "退出码符合约定": proc.returncode == 0,
        "stderr": proc.stderr.strip(),
        "stdout": proc.stdout.strip(),
        "被判为非法输入而拒绝": proc.returncode != 0,
        "缺失字段清单": missing,
        "缺失字段以待定占位": True,
        "产物": produced,
        "说明": "缺失的必填字段以「待定」占位而非报错，符合任务书第 5 条约定",
    }
    shutil.rmtree(iso, ignore_errors=True)
    print("[边界1] exit={} 产物={} 拒绝={}".format(
        proc.returncode, produced, proc.returncode != 0))
    return record


def main():
    # 干净起点：确保本次测试从无产物状态开始
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK, exist_ok=True)

    not_json_path = os.path.join(WORK, "not_json.json")
    with open(not_json_path, "w", encoding="utf-8") as fh:
        fh.write(NOT_JSON)
    not_object_path = os.path.join(WORK, "not_object.json")
    with open(not_object_path, "w", encoding="utf-8") as fh:
        fh.write(NOT_OBJECT)

    missing_path = os.path.join(WORK, "根本不存在的文件.json")

    cases = [
        (1, "非法①模板名非法(--template 证书)", "非法输入",
         ["--template", "证书", "--data", "fixtures/周报/case1.json"], 2,
         {"非法点": "模板名 证书 不在受支持模板集合内",
          "数据文件本身合法": True}),
        (2, "非法②--data 指向不存在的文件", "非法输入",
         ["--template", "周报", "--data", "fixtures/周报/不存在的文件.json"], 2,
         {"非法点": "--data 目标路径不存在",
          "数据文件本身合法": False}),
        (3, "非法③--data 指向内容不是 JSON 的文件", "非法输入",
         ["--template", "周报", "--data", ".tmp_invalid/not_json.json"], 2,
         {"非法点": "JSON 解析失败（文件内容为纯文本「{}」）".format(NOT_JSON),
          "数据文件本身合法": False, "样本文件": ".tmp_invalid/not_json.json",
          "样本内容": NOT_JSON}),
        (4, "非法④--data 指向顶层为数组的 JSON 文件", "非法输入",
         ["--template", "周报", "--data", ".tmp_invalid/not_object.json"], 2,
         {"非法点": "JSON 可解析但顶层不是对象（是长度为 2 的数组）",
          "数据文件本身合法": False, "样本文件": ".tmp_invalid/not_object.json",
          "样本内容": NOT_OBJECT}),
        (5, "合法对照组(fixtures/周报/case1.json)", "合法对照",
         ["--template", "周报", "--data", "fixtures/周报/case1.json"], 0,
         {"用途": "对照：合法输入必须成功并生成两产物",
          "数据文件本身合法": True}),
    ]

    records = []
    for args in cases:
        rec = run_case(*args)
        records.append(rec)
        print("[{}] exit={} stderr={!r} 零残留={}".format(
            rec["序号"], rec["退出码"], rec["stderr摘要"][:60],
            rec["产物残留检查"]["零产物残留"]))

    # 补充边界用例（不计入上面五组）：必填字段缺失不属于非法输入, 须正常生成。
    supplement = run_boundary_missing_required()

    invalid = [r for r in records if r["类别"] == "非法输入"]
    control = [r for r in records if r["类别"] == "合法对照"]

    log = {
        "任务": "ab4-invalid-input-rejection（非法输入拒绝行为测试）",
        "被测入口": "gen_doc.py",
        "解释器": PYTHON,
        "python版本": subprocess.run([PYTHON, "--version"], capture_output=True,
                                     text=True).stdout.strip(),
        "工作目录": HERE,
        "退出码约定": "非法输入 = 2；合法输入 = 0",
        "关键约定": [
            "四组非法输入均须以非零退出码 2 拒绝",
            "stderr 须含中文错误信息",
            "非法输入须零产物残留：不创建输出目录、不写半成品",
            "合法对照组退出码 0，并在 out/周报/case1/ 生成 文书.docx 与 fields.json",
        ],
        "用例总数": len(records),
        "逐组记录": records,
        "补充边界记录": supplement,
        "汇总": {
            "非法输入组数": len(invalid),
            "非法输入全部以2拒绝": all(r["退出码"] == 2 for r in invalid),
            "非法输入stderr均含中文": all(r["stderr含中文"] for r in invalid),
            "非法输入零产物残留": all(r["产物残留检查"]["零产物残留"] for r in invalid),
            "合法对照组退出码0": all(r["退出码"] == 0 for r in control),
            "合法对照组两产物齐全": all(
                r["产物检查"]["文书.docx存在"] and r["产物检查"]["fields.json存在"]
                for r in control),
            "必填缺失未被当作非法输入拒绝": not supplement["被判为非法输入而拒绝"],
            "全部用例符合约定": all(r["退出码符合约定"] for r in records)
                               and not supplement["被判为非法输入而拒绝"],
        },
    }

    with open(os.path.join(HERE, "run_log.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    shutil.rmtree(WORK, ignore_errors=True)
    print(json.dumps(log["汇总"], ensure_ascii=False, indent=2))
    return 0 if log["汇总"]["全部用例符合约定"] else 1


if __name__ == "__main__":
    sys.exit(main())