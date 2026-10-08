#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/build_packs.py — office 重测 13 任务臂任务包构建（零模型）。

任务源（双源，均冻结）：
  原始 5 ab 任务 = dist/office-templates-skill/eval/golden.json ab_tasks（golden 冻结，K5B-09；
    臂任务书照 sf0008-k5b OFFICE_BRIEFS 逐字复用——「禁止参照物进臂」约束下的忠实改写，
    fixtures 输入原样取自 reference/inputs）。
  增订 8 新题 = planning/taskset-redesign/merged/office-templates-skill/t01..t08
    （任务集冻结 9e7f57c6…；本轮开工实算复算相符）；臂 brief.md = task.json.instruction
    机械替换 <outdir>→out（照 sf0008-k5b meeting-minutes packs 先例），fixtures/ 空目录在位
    （make_arms 装置要求；输入数据内嵌于 instruction，臂自存数据文件属任务面）。
判据面（rubric.md/judge-notes.md/golden rubric/runner/oracle）一律不进 pack。
退出码：0=13 包构建完成且校验过。
"""
import hashlib
import json
import os
import shutil
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "office-retest-20261009")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "office-templates-skill")
FROZEN_96 = "9e7f57c6f4094f184483fab0d59f61121abd82316b1779072e9e99df43c0c535"

# 与 sf0008-k5b/s8_arms.py OFFICE_BRIEFS 逐字一致（忠实改写冻结复用）
OFFICE_BRIEFS = {
 "ab1-standard-four-templates": {
   "inputs": [("周报","case1"),("请示函","case1"),("会议通知","case1"),("工作总结","case1")],
   "text": ("把 fixtures/ 目录下四类模板的 case1 数据 JSON（周报、请示函、会议通知、工作总结各一份，字段全部齐全）分别生成为公文产物。\n"
            "命令行契约：--template <周报|请示函|会议通知|工作总结> --data <数据json路径> --outdir <输出目录>，每次调用在该目录下生成 文书.docx 与 fields.json 两个产物。\n"
            "产物写入 out/<模板>/case1/（四类各一个单元目录，每目录恰含 文书.docx 与 fields.json）。\n"
            "风格要求：GB/T 9704 公文风格（A4 版面）。缺数据不编造：必填缺失以____占位、选填缺失留空或省略，并在 fields.json 中如实记账。\n"
            "fields.json 顶层需含 title、fields 明细（每个字段：名称、是否必填、状态、值/渲染方式）与 summary（filled/missing/total 计数）。\n"
            "实现方式不限（可自行编写脚本后调用）。完成后确认四个单元目录与产物齐全。")},
 "ab2-boundary-missing-required": {
   "inputs": [("请示函","case2"),("会议通知","case2")],
   "text": ("处理两份含缺失字段的边界数据：fixtures/请示函/case2.json（主送机关关键缺失、请示事项为空字符串、联系电话/成文日期选填缺失）与 "
            "fixtures/会议通知/case2.json（会议名称缺失、会议地点空字符串、会议议题/会议要求/联系人/联系电话选填缺失、含模板外键「备注」）。\n"
            "命令行契约：--template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>，每次调用生成 文书.docx 与 fields.json。\n"
            "产物写入 out/<模板>/case2/（两个单元目录，每目录恰含两产物）。\n"
            "核心行为要求（缺数据不编造、如实记账）：必填缺失以____占位渲染且程序正常结束（退出码 0）；选填缺失留空或省略、不得误记为必填；"
            "模板外键记入 unknown_keys 类记账；fields.json 的 missing_required/选填 missing/unknown_keys 名单必须与输入的缺失事实一致；版式不因缺数据而破坏（称谓顶格、落款右对齐）。\n"
            "实现方式不限。完成后确认两个单元目录与产物齐全。")},
 "ab3-empty-and-string-lists": {
   "inputs": [("周报","case2"),("工作总结","case2")],
   "text": ("处理两份列表字段边界数据：fixtures/周报/case2.json（周期为空字符串、本周工作内容为空数组、问题与需协调事项选填缺失）与 "
            "fixtures/工作总结/case2.json（总结主体缺失、主要成绩为空数组、工作回顾为字符串型列表、存在问题与成文日期选填缺失）。\n"
            "命令行契约：--template <周报|工作总结> --data <数据json路径> --outdir <输出目录>，每次调用生成 文书.docx 与 fields.json。\n"
            "产物写入 out/<模板>/case2/（两个单元目录，每目录恰含两产物）。\n"
            "核心行为要求：空列表按必填缺失处理——渲染占位条目（如「1．____」）并在 fields.json 记占位语义；字符串型列表按单项化处理——渲染为单项条目且 fields.json 中该字段值为单元素数组；"
            "选填小节缺失整节省略（正文不出现该节头）但 fields.json 仍记 missing（required=false）；必填缺失以____占位（如标题「____工作周报」「____2026年9月工作总结」）；小节编号「一、二、三、」条目编号「1．2．3．」规范；落款右对齐不因空日期/缺主体破坏。\n"
            "实现方式不限。完成后确认两个单元目录与产物齐全。")},
 "ab4-invalid-input-rejection": {
   "inputs": [("周报","case1")],
   "text": ("非法输入拒绝行为测试：对你的生成入口分别施加四组非法输入——① --template 证书（模板名非法）② --data 指向不存在的文件 ③ --data 指向内容为「不是JSON」的文件（JSON 解析失败）④ --data 指向内容为 [\"数组\",\"非对象\"] 的文件（顶层非对象）；另以 fixtures/周报/case1.json 作合法对照组。\n"
            "逐组记录到 run_log.json：完整命令、退出码、stderr 摘要、产物残留检查（该次调用是否创建了输出目录/写出了 文书.docx 或 fields.json 等任何文件）。\n"
            "核心行为要求：四组非法输入应以非零退出码（约定值 2）拒绝、stderr 有中文错误信息、且零产物残留（不创建输出目录、不写半成品）；合法对照组退出码 0 并在 out/周报/case1/ 生成 文书.docx 与 fields.json 两产物；含必填缺失的输入不算非法（不得把缺失当错误拒绝）。\n"
            "产物布局：run_log.json（逐组记录）+ out/周报/case1/（合法对照组产物）。")},
 "ab5-determinism-layout-selfeval": {
   "inputs": [("会议通知","case1")],
   "text": ("确定性自评：用完全相同的输入 fixtures/会议通知/case1.json 连续运行生成两遍到同一输出目录 out/会议通知/case1（第二遍覆盖复写第一遍）。\n"
            "每遍后记录该目录下 文书.docx 与 fields.json 的 sha256 到 run_log.json（标注第几遍），并对两遍产物做逐字节对比，把对比结论（一致/不一致及差异说明）写入 run_log.json。\n"
            "核心行为要求：同输入连跑两遍产物逐字节一致（fields.json 除 outputs 类路径键外逐字节一致；docx 解析后的段落文本/对齐/缩进/字体/行距完全一致，无当前时间、随机内容等不可复现源）；输出目录恰含两产物。\n"
            "命令行契约：--template 会议通知 --data <数据json路径> --outdir out/会议通知/case1，每次调用生成 文书.docx 与 fields.json。实现方式不限。")},
}
AB_ORDER = ["ab1-standard-four-templates", "ab2-boundary-missing-required",
            "ab3-empty-and-string-lists", "ab4-invalid-input-rejection",
            "ab5-determinism-layout-selfeval"]
NEW_ORDER = ["t0%d" % i for i in range(1, 9)]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    # 冻结复算（开工自证）
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    assert live == FROZEN_96, "任务集冻结哈希复算不符：%s" % live
    golden_sha = sha256_file(os.path.join(ROOT, "dist/office-templates-skill/eval/golden.json"))
    manifest = {"run": "office-retest-20261009", "taskset_frozen_sha256_96": live,
                "taskset_frozen_cmd": cmd, "golden_json_sha256": golden_sha,
                "golden_frozen_expected": "2fa58b07481b44bc2840b2fdd757ef19faa5ebe37e1918baf936b2b923f4ecbf",
                "packs": []}
    assert golden_sha == manifest["golden_frozen_expected"], "dist golden sha 与 REGISTRY 登记不符"
    for tid in AB_ORDER + NEW_ORDER:
        pd = os.path.join(RUN, "packs", "office-templates-%s" % tid)
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)
        rec = {"task": tid, "pack": os.path.relpath(pd, ROOT)}
        lines = None  # 每任务必须重建；防跨任务残留（装置缺陷防线）
        if tid in OFFICE_BRIEFS:
            spec = OFFICE_BRIEFS[tid]
            src_in = os.path.join(ROOT, "dist", "office-templates-skill", "reference", "inputs")
            fixtures = []
            for tpl, case in spec["inputs"]:
                dst = os.path.join(pd, "fixtures", tpl)
                os.makedirs(dst, exist_ok=True)
                fn = os.path.join(dst, "%s.json" % case)
                shutil.copyfile(os.path.join(src_in, tpl, "%s.json" % case), fn)
                fixtures.append({"file": os.path.relpath(fn, pd), "sha256": sha256_file(fn)})
            lines = ["# office 重测臂任务（%s）" % tid, "", spec["text"],
                     "（注：本任务书为 golden.json ab 任务在「禁止参照物进臂」约束下的忠实改写；"
                     "输入数据原样来自冻结任务集。）"]
            rec["source"] = "dist/office-templates-skill/eval/golden.json ab_tasks（忠实改写照 sf0008-k5b）"
            rec["fixtures"] = fixtures
        else:
            tj = json.load(open(os.path.join(MERGED, tid, "task.json"), encoding="utf-8"))
            assert tj["id"] == tid, "id 与目录名不符: %s" % tid
            brief = tj["instruction"].replace("<outdir>", "out")
            assert brief != tj["instruction"] or "<outdir>" not in tj["instruction"], \
                "%s 含未替换 <outdir> 占位符" % tid
            lines = [brief]
            rec["source"] = "planning/taskset-redesign/merged/office-templates-skill/%s/task.json.instruction（<outdir>→out 机械替换）" % tid
            rec["dim"] = tj.get("dim")
            rec["pass_line"] = tj.get("pass_line")
        assert lines is not None, "brief 内容未生成: %s" % tid
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        rec["brief_sha256"] = sha256_file(os.path.join(pd, "brief.md"))
        manifest["packs"].append(rec)
    out = os.path.join(RUN, "records", "packs-manifest.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0, "packs": len(manifest["packs"]), "taskset_sha_ok": True,
                      "golden_sha_ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
