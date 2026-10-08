#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0008-k5b/s8_checkers.py — SF-0008 确定性断言 checker（零模型，rubric 锚点子集）。

对每单元产物做可程序判定的 rubric 锚点断言，输出 records/checker-results.json：
  {"<pkg>|<task>": {"<arm>-rep<k>": {"assertion_pass": true/false/null, "detail": …,
                                     "anchors": {名: {pass, detail}}}}}
assertion_pass=null 表示该单元无不可判锚点之外的失败（不可判锚点如实留 N/A）。
断言门语义（s8_aggregate.py）：treatment 侧零显式失败；baseline 结果如实记录不进门。
golden.json/tasks.json 冻结零改动；本脚本只读臂产物。
"""

import json
import os
import re
import sys

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0008-k5b")
REPS = {"meeting-minutes": 2, "office-templates": 2, "hot-templates": 3}


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def docx_paras(path):
    from docx import Document
    d = Document(path)
    return d


def para_facts(p):
    from docx.oxml.ns import qn
    pf = p.paragraph_format
    fli_chars = None
    pPr = p._p.pPr
    if pPr is not None:
        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            fli_chars = ind.get(qn("w:firstLineChars"))
    fonts = []
    for r in p.runs:
        sz = r.font.size.pt if r.font.size else None
        east = None
        rPr = r._p.rPr
        if rPr is not None:
            rf = rPr.find(qn("w:rFonts"))
            if rf is not None:
                east = rf.get(qn("w:eastAsia"))
        fonts.append((east or r.font.name, sz))
    return {"text": p.text, "align": str(p.alignment), "firstLineChars": fli_chars,
            "fonts": fonts}


def all_paras(path):
    d = docx_paras(path)
    return [para_facts(p) for p in d.paragraphs]


def tables_text(path):
    d = docx_paras(path)
    out = []
    for tb in d.tables:
        out.append([[c.text for c in row.cells] for row in tb.rows])
    return out


def anchors_result(anchors):
    """可判锚点全过 → True；有显式失败 → False；全不可判 → None。"""
    vals = [v["pass"] for v in anchors.values() if v["pass"] is not None]
    if not vals:
        return None
    return all(vals)


# ---------------------------------------------------------------- mm
def check_mm(task, ad):
    from docx import Document
    out = os.path.join(ad, "out")
    docx_p = os.path.join(out, "纪要.docx")
    sj_p = os.path.join(out, "summary.json")
    a = {}
    if not (os.path.isfile(docx_p) and os.path.isfile(sj_p)):
        return {"assertion_pass": False, "detail": "产物缺失", "anchors": {"files": {"pass": False, "detail": "缺 docx/summary.json"}}}
    try:
        paras = all_paras(docx_p)
        s = jload(sj_p)
    except Exception as exc:
        return {"assertion_pass": False, "detail": "解析失败:%s" % exc, "anchors": {}}
    text_all = "\n".join(p["text"] for p in paras)
    a["三节标题逐字"] = {"pass": all(h in text_all for h in
                     ("一、决议事项", "二、待办事项", "三、风险与关注")),
                     "detail": "三节标题逐字在位"}
    a["summary四键"] = {"pass": isinstance(s, dict) and all(k in s for k in
                       ("决议事项", "待办事项", "风险与关注", "合计")),
                       "detail": str(sorted(s.keys()))[:120]}
    if isinstance(s, dict) and all(k in s for k in ("决议事项", "待办事项", "风险与关注", "合计")):
        try:
            tot = s["决议事项"] + s["待办事项"] + s["风险与关注"]
            a["合计自洽"] = {"pass": s["合计"] == tot, "detail": "合计=%s 和=%s" % (s["合计"], tot)}
        except Exception:
            a["合计自洽"] = {"pass": False, "detail": "键非数值"}
    # 转写原文逐字引用核查（输入内嵌于 pack brief）
    brief = open(os.path.join(RUN, "packs", "meeting-minutes-%s" % task, "brief.md"),
                 encoding="utf-8").read()
    turns = re.findall(r"\[(\d{1,2}:\d{2})\]\s*([^：:]+?)\s*[：:]\s*(.+)", brief)
    tmap = {"%s %s" % (t, sp): c for t, sp, c in turns}
    quotes = re.findall(r"【([^】]+)】\s*([^【\n]+)", text_all)
    if quotes:
        hit = miss = 0
        for tag, body in quotes:
            body = body.strip().lstrip("0123456789．.、)） ").strip()
            key = tag.strip()
            matched = any(key.endswith(t) and t in key and body == c.strip()
                          for (t, sp), c in [((k.split(" ")[0], k.split(" ", 1)[1]), v)
                                             for k, v in tmap.items()] if key.endswith(k.split(" ")[0]))
            hit += 1 if matched else 0
            miss += 0 if matched else 1
        a["逐字引用抽核"] = {"pass": miss == 0, "detail": "引语 %d 条，未命中原文 %d 条" % (hit + miss, miss)}
    else:
        a["逐字引用抽核"] = {"pass": False, "detail": "正文未检出【时间 · 说话人】引语"}
    # 待办表格（t1 口径：三列表头）— 对全部任务统一抽「表格在位」
    tbs = tables_text(docx_p)
    a["待办表格"] = {"pass": any(len(r) >= 3 for tb in tbs for r in tb),
                   "detail": "%d 张表" % len(tbs)}
    return {"assertion_pass": anchors_result(a), "detail": "%d 锚点" % len(a), "anchors": a}


# ---------------------------------------------------------------- office
OFFICE_EXPECT = {
 "ab1-standard-four-templates": {"units": [("周报","case1"),("请示函","case1"),("会议通知","case1"),("工作总结","case1")],
                                 "filled_total": {"周报":7,"请示函":8,"会议通知":11,"工作总结":7}},
 "ab2-boundary-missing-required": {"units": [("请示函","case2"),("会议通知","case2")],
   "missing_required": {"请示函": ["主送机关","请示事项"], "会议通知": ["会议名称","会议地点"]},
   "unknown": {"会议通知": ["备注"]}},
 "ab3-empty-and-string-lists": {"units": [("周报","case2"),("工作总结","case2")],
   "missing_required": {"周报": ["部门","周期","本周工作内容"], "工作总结": ["总结主体","主要成绩"]},
   "titles": {"周报": "____工作周报", "工作总结": "____2026年9月工作总结"},
   "string_list_value": "完成评测平台月度巡检"},
 "ab4-invalid-input-rejection": {"units": [("周报","case1")]},
 "ab5-determinism-layout-selfeval": {"units": [("会议通知","case1")]},
}


def check_office(task, ad):
    spec = OFFICE_EXPECT[task]
    a = {}
    out = os.path.join(ad, "out")
    # 单元产物
    units_ok = True
    for tpl, case in spec["units"]:
        u = os.path.join(out, tpl, case)
        ok = os.path.isfile(os.path.join(u, "文书.docx")) and os.path.isfile(os.path.join(u, "fields.json"))
        units_ok = units_ok and ok
    a["单元产物"] = {"pass": units_ok, "detail": "%d 单元" % len(spec["units"])}
    if not units_ok:
        return {"assertion_pass": anchors_result(a), "detail": "单元缺失", "anchors": a}
    # 版式四要素抽核（首个单元）：标题居中、正文缩进200、落款右对齐
    for tpl, case in spec["units"][:1]:
        paras = all_paras(os.path.join(out, tpl, case, "文书.docx"))
        title = next((p for p in paras if p["text"].strip()), None)
        a["标题居中"] = {"pass": title is not None and "CENTER" in title["align"],
                      "detail": "%s… %s" % (title["text"][:16], title["align"]) if title else "无段落"}
        body = [p for p in paras if len(p["text"]) > 30]
        a["正文缩进200"] = {"pass": any(p["firstLineChars"] == "200" for p in body),
                         "detail": "%d 长段" % len(body)}
        sig = [p for p in paras if p["text"].strip() and p != title][-1] if len(paras) > 1 else None
        a["落款右对齐"] = {"pass": sig is not None and "RIGHT" in sig["align"],
                        "detail": sig["text"][:16] if sig else "无"}
        fj = jload(os.path.join(out, tpl, case, "fields.json"))
        a["fields.json 台账结构"] = {"pass": isinstance(fj, dict) and ("fields" in fj or any(
            isinstance(v, (list, dict)) for v in fj.values())),
            "detail": str(sorted(fj.keys()))[:140]}
    # 任务特定锚点
    if task == "ab2-boundary-missing-required":
        for tpl, case in spec["units"]:
            fj = jload(os.path.join(out, tpl, case, "fields.json"))
            flat = json.dumps(fj, ensure_ascii=False)
            mr = spec["missing_required"][tpl]
            a["%s missing_required" % tpl] = {"pass": all(m in flat for m in mr),
                                              "detail": ",".join(mr)}
            paras = all_paras(os.path.join(out, tpl, case, "文书.docx"))
            t_all = "\n".join(p["text"] for p in paras)
            a["%s ____占位" % tpl] = {"pass": "____" in t_all, "detail": "占位在位"}
        fj = jload(os.path.join(out, "会议通知", "case2", "fields.json"))
        flat = json.dumps(fj, ensure_ascii=False)
        a["模板外键记账"] = {"pass": "备注" in flat, "detail": "unknown 含 备注"}
    if task == "ab3-empty-and-string-lists":
        paras = all_paras(os.path.join(out, "周报", "case2", "文书.docx"))
        t_all = "\n".join(p["text"] for p in paras)
        a["空列表占位条目"] = {"pass": "1．____" in t_all or "____" in t_all, "detail": "周报占位"}
        fj = jload(os.path.join(out, "工作总结", "case2", "fields.json"))
        flat = json.dumps(fj, ensure_ascii=False)
        a["字符串列表单项化"] = {"pass": spec["string_list_value"] in flat, "detail": "工作回顾值"}
        for tpl in ("周报", "工作总结"):
            title_expect = spec["titles"][tpl]
            paras = all_paras(os.path.join(out, tpl, "case2", "文书.docx"))
            title = next((p["text"] for p in paras if p["text"].strip()), "")
            a["%s 标题占位" % tpl] = {"pass": title_expect in title,
                                   "detail": title[:24]}
    if task == "ab4-invalid-input-rejection":
        rl_p = os.path.join(ad, "run_log.json")
        if not os.path.isfile(rl_p):
            a["run_log"] = {"pass": False, "detail": "run_log.json 缺失"}
        else:
            rl = jload(rl_p)
            entries = rl if isinstance(rl, list) else rl.get("runs", rl.get("cases", []))
            illegal = [e for e in entries if isinstance(e, dict)
                       and (e.get("kind") == "illegal" or "非法" in str(e.get("name", "")) or
                            (isinstance(e.get("case"), str) and "非法" in e["case"]))]
            if not illegal:
                a["非法组记录"] = {"pass": None, "detail": "run_log 无显式非法组标记（N=%d）" % len(entries)}
            else:
                codes = [e.get("exit_code", e.get("exit")) for e in illegal]
                a["非法组退出码2"] = {"pass": all(c == 2 for c in codes if c is not None),
                                "detail": str(codes)}
                residue = [e for e in illegal if e.get("residue") or e.get("产物残留")]
                a["零产物残留"] = {"pass": not residue, "detail": "%d 组残留" % len(residue)}
    if task == "ab5-determinism-layout-selfeval":
        rl_p = os.path.join(ad, "run_log.json")
        if not os.path.isfile(rl_p):
            a["run_log"] = {"pass": False, "detail": "run_log.json 缺失"}
        else:
            rl = json.dumps(jload(rl_p), ensure_ascii=False)
            has2 = rl.count("sha") >= 2 or "两遍" in rl or "第2遍" in rl or "第二遍" in rl
            a["两遍哈希记录"] = {"pass": has2 and ("一致" in rl or "identical" in rl.lower()),
                            "detail": "run_log 含哈希与一致性结论"}
    return {"assertion_pass": anchors_result(a), "detail": "%d 锚点" % len(a), "anchors": a}


# ---------------------------------------------------------------- hot
def check_hot(task, ad):
    out = os.path.join(ad, "out")
    sj_p = os.path.join(out, "structure.json")
    md_p = os.path.join(out, "骨架.md")
    a = {}
    if not (os.path.isfile(sj_p) and os.path.isfile(md_p)):
        return {"assertion_pass": False, "detail": "产物缺失", "anchors": {"files": {"pass": False}}}
    try:
        sj = jload(sj_p)
        md = open(md_p, encoding="utf-8").read()
    except Exception as exc:
        return {"assertion_pass": False, "detail": "解析失败:%s" % exc, "anchors": {}}
    els = sj.get("elements", [])
    ids = [e.get("id") for e in els]
    emap = {e.get("id"): e for e in els}
    a["无模板残留"] = {"pass": "{{" not in md and "}}" not in md and "{{" not in json.dumps(sj),
                    "detail": "无 {{ }}"}
    ps = sj.get("placeholder_stats", {})
    if isinstance(ps, dict) and "total_open" in ps:
        bysum = sum((ps.get("by_element") or {}).values()) if isinstance(ps.get("by_element"), dict) else None
        a["占位统计自洽"] = {"pass": (bysum == ps.get("total_open")) if bysum is not None else None,
                        "detail": "total=%s sum=%s" % (ps.get("total_open"), bysum)}
        a["骨架统计节"] = {"pass": "占位符统计" in md, "detail": "「占位符统计」节在位"}
    if task == "ab-001":
        a["六要素顺序"] = {"pass": ids == ["hook_3s","pain_point","value_1","value_2","value_3","cta"],
                       "detail": str(ids)}
        a["钩子CTA非空"] = {"pass": bool(emap.get("hook_3s",{}).get("text")) and bool(emap.get("cta",{}).get("text")),
                       "detail": ""}
        vals = json.dumps([emap.get("value_%d"%i,{}) for i in (1,2,3)], ensure_ascii=False)
        a["卖点填充"] = {"pass": all(("point#%d"%i) in vals for i in (1,2,3)) and "【占位" not in vals,
                     "detail": "filled_from_input/占位"}
    if task == "ab-002":
        a["七要素"] = {"pass": ids == ["title","hook_block","point_block_1","point_block_2","point_block_3","summary_block","tag_group"], "detail": str(ids)}
        t = emap.get("title",{}).get("text","")
        a["标题数字emoji"] = {"pass": "🔥" in t and re.search(r"3", t) is not None, "detail": t[:30]}
        a["截断策略"] = {"pass": all(("point#%d"%i) in json.dumps(emap.get("point_block_%d"%i,{}),ensure_ascii=False) for i in (1,2,3))
                      and len(sj.get("points_unused",[])) == 2 and sj.get("points_used") is not None,
                      "detail": "used=%s unused=%d" % (str(sj.get("points_used"))[:40], len(sj.get("points_unused",[])))}
        tg = emap.get("tag_group",{}).get("text","")
        ntag = tg.count("#")
        a["标签组"] = {"pass": 3 <= ntag <= 8 and "租房避坑" in tg, "detail": "%d 个#" % ntag}
        a["emoji映射"] = {"pass": "✅" in json.dumps(emap.get("hook_block",{}),ensure_ascii=False)
                      and "📌" in json.dumps(emap.get("summary_block",{}),ensure_ascii=False)
                      and "🏷️" in tg, "detail": ""}
    if task == "ab-003":
        a["五要素三段论"] = {"pass": ids == ["lead_in","thesis_what","thesis_why","thesis_how","golden_ending"]
                        and emap.get("thesis_what",{}).get("text","").startswith("一、是什么")
                        and emap.get("thesis_why",{}).get("text","").startswith("二、为什么")
                        and emap.get("thesis_how",{}).get("text","").startswith("三、怎么办"),
                        "detail": str(ids)}
        how = json.dumps(emap.get("thesis_how",{}), ensure_ascii=False)
        a["零卖点占位"] = {"pass": all(("【占位:价值点%d】"%i) in how for i in (1,2,3))
                      and sj.get("points_used") == [None,None,None], "detail": str(sj.get("points_used"))[:40]}
        a["金句收尾"] = {"pass": "共勉" in emap.get("golden_ending",{}).get("text",""), "detail": ""}
    if task == "ab-004":
        a["六镜"] = {"pass": ids == ["shot_%d"%i for i in range(1,7)], "detail": str(ids)}
        a["表头四列"] = {"pass": "| 序号 | 时间轴 | 画面 | 口播 | 字幕 |" in md.replace(" "," ").replace("｜","|"), "detail": ""}
        a["冻结时间轴"] = {"pass": "共 45 秒" in md or "共45秒" in md, "detail": ""}
        s3 = json.dumps(emap.get("shot_3",{}),ensure_ascii=False)
        s45 = json.dumps([emap.get("shot_4",{}),emap.get("shot_5",{})],ensure_ascii=False)
        a["缺失槽位"] = {"pass": "point#1" in s3 and "【占位:价值点2】" in s45 and "【占位:价值点3】" in s45,
                     "detail": ""}
        a["分镜总表"] = {"pass": "分镜总表" in md, "detail": ""}
    if task == "ab-005":
        rl_p = os.path.join(ad, "run_log.json")
        if not os.path.isfile(rl_p):
            a["run_log"] = {"pass": False, "detail": "run_log.json 缺失"}
        else:
            rl = jload(rl_p)
            flat = json.dumps(rl, ensure_ascii=False)
            a["确定性双跑"] = {"pass": ("一致" in flat or "identical" in flat.lower() or
                              ("sha" in flat.lower() and flat.count("sha") >= 2)),
                           "detail": ""}
            a["失败路径"] = {"pass": flat.count("2") > 0 and ("bilibili" in flat or "非法" in flat), "detail": ""}
    return {"assertion_pass": anchors_result(a), "detail": "%d 锚点" % len(a), "anchors": a}


def main():
    FAM = {}
    for p in jload(os.path.join(RUN, "round-plan.json"))["arm_allocation"]["per_package"]:
        for t in p["glm_tasks"]:
            FAM[("%s|%s" % (p["pkg"], t))] = "glm"
        for t in p["minimax_tasks"]:
            FAM[("%s|%s" % (p["pkg"], t))] = "minimax"
    CHECK = {"meeting-minutes": check_mm, "office-templates": check_office, "hot-templates": check_hot}
    results = {}
    for pkg, fn in CHECK.items():
        tasks = ([t["id"] for t in jload(os.path.join(ROOT, "v2/evalbench-v02/meeting-minutes/tasks.json"))]
                 if pkg == "meeting-minutes" else
                 [t["id"] for t in jload(os.path.join(ROOT, "dist", PKGS[pkg], "eval/golden.json"))["ab_tasks"]])
        for task in tasks:
            key = "%s|%s" % (pkg, task)
            fam = FAM[key]
            results[key] = {}
            for rep in range(1, REPS[pkg] + 1):
                for arm in ("baseline", "treatment"):
                    ad = os.path.join(RUN, fam, "%s-%s-rep%d" % (pkg, task, rep), arm)
                    if not os.path.isdir(ad):
                        continue
                    try:
                        results[key]["%s-rep%d" % (arm, rep)] = fn(task, ad)
                    except Exception as exc:
                        results[key]["%s-rep%d" % (arm, rep)] = {
                            "assertion_pass": False, "detail": "checker 异常:%s" % exc, "anchors": {}}
    out = os.path.join(RUN, "records", "checker-results.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        f.write("\n")
    n_pass = sum(1 for k in results.values() for v in k.values() if v.get("assertion_pass") is True)
    n_fail = sum(1 for k in results.values() for v in k.values() if v.get("assertion_pass") is False)
    print("checker: pass=%d fail=%d units=%d" % (n_pass, n_fail,
          sum(len(k) for k in results.values())))
    return 0


PKGS = {"meeting-minutes": "meeting-minutes-skill",
        "office-templates": "office-templates-skill",
        "hot-templates": "hot-templates-skill"}

if __name__ == "__main__":
    sys.exit(main())
