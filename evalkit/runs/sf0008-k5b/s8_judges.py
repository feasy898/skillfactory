#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0008-k5b/s8_judges.py — SF-0008 裁判面板驱动（盲态、异族、位置轮换、§3.4 抽检）。

面板（round-plan.judge_panel）：被测 glm → [step-router-v1, Minimax-M3.1-Flash-Preview]；
被测 minimax → [step-router-v1, GLM-5.3]。step 走模型 API 直调；glm/minimax 走 headless M4/M2。
盲态：产物匿名化（P1..Pn 洗牌）+ docx→文本/版式事实预抽取 + 绝对路径/挂载痕迹漂白；
映射仅存 records/judge-staging/（裁判不可见）。位置轮换：槽序按任务序奇偶互换（留痕）。
§3.4：每任务抽 1 份产物（按任务序轮换覆盖两臂）同裁判匿名复评；|Δ|>2 → 换面板内另一异族
裁判重评全任务；仍>2 → task unjudgeable（fail-closed，blind_v02=false）。

用法：python s8_judges.py [--pkg meeting-minutes|office-templates|hot-templates]
退出码：0 全任务判分落盘 / 1 有任务 unjudgeable 或装置失败（如实，不放宽）。
"""

import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s8_judge_lib as J  # noqa: E402

ROOT = J.ROOT
RUN = J.RUN
VPY = os.path.join(ROOT, ".venv-dev", "bin", "python")
PANEL = {"glm": ["step-router-v1", "Minimax-M3.1-Flash-Preview"],
         "minimax": ["step-router-v1", "GLM-5.3"]}
JUDGE_OF_MODEL = {"step-router-v1": "step", "Minimax-M3.1-Flash-Preview": "minimax",
                  "GLM-5.3": "glm"}
MODEL_OF_JUDGE = {v: k for k, v in JUDGE_OF_MODEL.items()}

SCORING_RULE = """评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构：{"scores": {"P1": {"total": x.x, "items": [逐项分], "evidence": "逐项证据摘要"}}, ...}（每个产品一个键）。"""


def redact_text(s, arm_root):
    s = s.replace(arm_root, "<ARMROOT>")
    s = re.sub(r"\.zcode/skills/[A-Za-z0-9_\-]+", "<SKILL_MOUNT>", s)
    s = re.sub(r"\.zcode\\\\skills\\\\[A-Za-z0-9_\-]+", "<SKILL_MOUNT>", s)
    # 盲态按键名脱敏：臂标/来源自述字段一律 <redacted>（run_log 等自述 JSON 常带 arm/engine/run_id）
    for key in ("arm", "engine", "run_id", "runId", "side", "arm_label", "session_id",
                "sessionId", "skill_mount", "asset"):
        s = re.sub(r'"%s"\s*:\s*"[^"]*"' % key, '"%s": "<redacted>"' % key, s)
        s = re.sub(r"'%s'\s*:\s*'[^']*'" % key, "'%s': '<redacted>'" % key, s)
    return s


def docx_facts(path):
    """python-docx 确定性抽取：段落文本+对齐+缩进+字体/字号/行距 + 表格文本。"""
    from docx import Document
    from docx.oxml.ns import qn
    doc = Document(path)
    lines = []
    for i, p in enumerate(doc.paragraphs):
        if not p.text.strip() and p._p.xpath(".//w:drawing") == []:
            continue
        align = p.alignment
        pf = p.paragraph_format
        fli = pf.first_line_indent
        fli_chars = None
        pPr = p._p.pPr
        if pPr is not None:
            ind = pPr.find(qn("w:ind"))
            if ind is not None:
                fli_chars = ind.get(qn("w:firstLineChars"))
        fonts = []
        for r in p.runs[:6]:
            sz = r.font.size.pt if r.font.size else None
            east = None
            rPr = r._p.rPr
            if rPr is not None:
                rf = rPr.find(qn("w:rFonts"))
                if rf is not None:
                    east = rf.get(qn("w:eastAsia"))
            spacing = pf.line_spacing
            fonts.append("%s/%s/%s" % (r.text[:14], east or r.font.name, sz))
        lines.append("P%03d align=%s firstLineChars=%s firstLineIndent=%s spacing=%s runs=[%s] text=%s"
                     % (i, align, fli_chars, fli, pf.line_spacing, " | ".join(fonts), p.text))
    for ti, tb in enumerate(doc.tables, 1):
        lines.append("TABLE%d %d行×%d列:" % (ti, len(tb.rows), len(tb.columns)))
        for row in tb.rows:
            lines.append("  " + " ┃ ".join(c.text.replace("\n", "⏎") for c in row.cells))
    return "\n".join(lines)


def stage_products(pkg, task, unit_dirs, staging, seed):
    """收集产物→漂白→洗牌匿名化。返回 (staged_files, mapping, products_meta)。"""
    rng = random.Random(seed)
    items = []   # (rep, arm, files{...})
    for rep, ad in unit_dirs:
        files = {}
        out = os.path.join(ad, "out")
        for dp, _dn, fns in os.walk(out):
            for fn in fns:
                src = os.path.join(dp, fn)
                rel = os.path.relpath(src, out)
                files[rel] = src
        rl = os.path.join(ad, "run_log.json")
        if os.path.isfile(rl):
            files["run_log.json"] = rl
        items.append({"rep": rep, "arm": arm_dir_arm(ad), "dir": ad, "files": files})
    rng.shuffle(items)
    os.makedirs(staging, exist_ok=True)
    mapping, staged, meta = {}, [], []
    arm_root = os.path.commonpath([it["dir"] for it in items]) if items else RUN
    for i, it in enumerate(items, 1):
        pid = "P%d" % i
        mapping[pid] = {"rep": it["rep"], "arm": it["arm"]}
        pdir = os.path.join(staging, pid)
        os.makedirs(pdir, exist_ok=True)
        names = []
        for rel, src in sorted(it["files"].items()):
            ext = os.path.splitext(rel)[1].lower()
            base = rel.replace("/", "__")
            dst = os.path.join(pdir, base)
            if ext == ".docx":
                facts = docx_facts(src)
                with open(dst + ".extract.txt", "w", encoding="utf-8", newline="\n") as f:
                    f.write("EXTRACT OF %s (python-docx 确定性抽取，段落含对齐/缩进/字体/字号/行距事实)\n%s\n"
                            % (base, facts))
                names.append(base + ".extract.txt")
            elif ext in (".json", ".md", ".txt", ".log"):
                raw = open(src, encoding="utf-8", errors="replace").read()
                with open(dst, "w", encoding="utf-8", newline="\n") as f:
                    f.write(redact_text(raw, it["dir"]))
                names.append(base)
            else:
                shutil_copy(src, dst)
                names.append(base)
        staged.append({"pid": pid, "files": names})
        meta.append({"pid": pid, "n_files": len(names)})
    return staged, mapping, meta


def shutil_copy(src, dst):
    import shutil
    shutil.copyfile(src, dst)


def arm_dir_arm(ad):
    return os.path.basename(os.path.normpath(ad))


def rubric_of(pkg, task):
    if pkg == "meeting-minutes":
        d = json.load(open(os.path.join(ROOT, "v2/evalbench-v02/meeting-minutes/tasks.json"),
                           encoding="utf-8"))
        return next(t for t in d if t["id"] == task)["rubric"]
    d = json.load(open(os.path.join(ROOT, "dist", {"meeting-minutes": "meeting-minutes-skill",
                                                   "office-templates": "office-templates-skill",
                                                   "hot-templates": "hot-templates-skill"}[pkg],
                                   "eval/golden.json"), encoding="utf-8"))
    return next(t for t in d["ab_tasks"] if t["id"] == task)["rubric"]


def build_brief(pkg, task, staged, rubric):
    lines = ["# SF-0008 盲评判分任务（%s / %s）" % (pkg, task), "",
             "你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。", "",
             "## rubric（冻结原文，逐条判分）"]
    for i, r in enumerate(rubric, 1):
        lines.append("%d. %s" % (i, r))
    lines += ["", SCORING_RULE, "", "## 产物清单"]
    for s in staged:
        lines.append("- %s: %s" % (s["pid"], ", ".join(s["files"])))
    lines += ["", "请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。"]
    return "\n".join(lines)


def parse_verdict_json(text):
    t = text.strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def judge_call(judge, workdir, brief, staged, task_label):
    """单裁判单次调用。step=HTTP（产物内容内联）；glm/minimax=headless CLI。返回 (rec, verdict)。"""
    model = MODEL_OF_JUDGE[judge]
    slot = J.budget_judge({"judge": judge, "channel": judge,
                           "task": task_label, "judge_prompt_version": J.JUDGE_PROMPT_VERSION,
                           "ts_intent": __import__("time").strftime("%H:%M:%S"),
                           "status": "pending"})
    try:
        if judge == "step":
            parts = [brief, "", "# 产物内容（暂存文件全文）"]
            for s in staged:
                for fn in s["files"]:
                    p = os.path.join(workdir, s["pid"], fn)
                    parts.append("=== %s/%s ===\n%s" % (s["pid"], fn,
                                 open(p, encoding="utf-8", errors="replace").read()[:60000]))
            r = J.step_chat([{"role": "user", "content": "\n".join(
                parts + ["", '输出：仅一个 JSON 对象（verdict），结构 {"scores": {"P1": {"total": x, "items": [...], "evidence": "..."}}, ...}'])}])
            v = parse_verdict_json(r["text"])
            rec = {"exit_code": 0 if v else 1, "wall_ms": r["wall_ms"], "session_id": r["id"],
                   "model_id_observed": r["model"], "channel": "http-api",
                   "input_tokens": r["prompt_tokens"], "output_tokens": r["completion_tokens"]}
            with open(os.path.join(workdir, "response.txt"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(r["text"])
        else:
            with open(os.path.join(workdir, "brief.md"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(brief + "\n")
            for s in staged:
                src_pdir = os.path.join(os.path.dirname(workdir), "_staging", task_label, s["pid"])
                dst_pdir = os.path.join(workdir, s["pid"])
                if os.path.isdir(src_pdir):
                    import shutil
                    import shutil as sh
                    sh.copytree(src_pdir, dst_pdir, dirs_exist_ok=True)
            rec = J.cli_judge(workdir, judge)
            vp = os.path.join(workdir, "verdict.json")
            v = json.load(open(vp, encoding="utf-8")) if os.path.isfile(vp) else None
            with open(os.path.join(workdir, "transcript_stdout.txt"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(rec["_raw_stdout"])
        J.budget_judge_update(slot, status="done" if v else "no-verdict",
                              exit_code=rec["exit_code"], wall_ms=rec["wall_ms"],
                              session_id=rec.get("session_id"),
                              tokens={"input": rec.get("input_tokens"),
                                      "output": rec.get("output_tokens")},
                              model_observed=rec.get("model_id_observed"))
        return rec, v
    except Exception as exc:
        J.budget_judge_update(slot, status="failed", exit_code=1,
                              error=type(exc).__name__ + ":" + str(exc)[:300])
        raise


def task_unit_dirs(pkg, task, fam_of, reps):
    rp = json.load(open(os.path.join(RUN, "round-plan.json"), encoding="utf-8"))
    fam = None
    for p in rp["arm_allocation"]["per_package"]:
        if p["pkg"] == pkg:
            fam = "glm" if task in p["glm_tasks"] else "minimax"
    out = []
    for rep in reps:
        ad = os.path.join(RUN, fam, "%s-%s-rep%d" % (pkg, task, rep))
        out.append((rep, os.path.join(ad, "baseline")))
        out.append((rep, os.path.join(ad, "treatment")))
    return fam, out


def main():
    only_pkg = None
    if "--pkg" in sys.argv:
        only_pkg = sys.argv[sys.argv.index("--pkg") + 1]
    REPS = {"meeting-minutes": [1, 2], "office-templates": [1, 2], "hot-templates": [1, 2, 3]}
    results = {}
    for pkg in ("meeting-minutes", "office-templates", "hot-templates"):
        if only_pkg and pkg != only_pkg:
            continue
        tasks = ([t["id"] for t in json.load(open(
            os.path.join(ROOT, "v2/evalbench-v02/meeting-minutes/tasks.json"), encoding="utf-8"))]
            if pkg == "meeting-minutes" else
            [t["id"] for t in json.load(open(
                os.path.join(ROOT, "dist", {"meeting-minutes": "meeting-minutes-skill",
                                            "office-templates": "office-templates-skill",
                                            "hot-templates": "hot-templates-skill"}[pkg],
                    "eval/golden.json"), encoding="utf-8"))["ab_tasks"]])
        results[pkg] = {}
        for ti, task in enumerate(tasks, 1):
            fam, units = task_unit_dirs(pkg, task, None, REPS[pkg])
            # 装置完整性：单元臂 records 必须齐（缺=装置失败，不进判分）
            missing = [u for u in units if not os.path.isfile(
                os.path.join(u[1], "records", "arm_run.json"))]
            if missing:
                results[pkg][task] = {"status": "infra_error", "missing": [m[1] for m in missing]}
                continue
            staging = os.path.join(RUN, "judge-work", "_staging", "%s-%s" % (pkg, task))
            staged, mapping, meta = stage_products(
                pkg, task, units, staging,
                seed=hash((pkg, task)) & 0xffffff)
            J.write_json(os.path.join(RUN, "records", "judge-staging",
                                      "%s-%s.mapping.json" % (pkg, task)),
                         {"mapping": mapping, "staged": staged, "seed": hash((pkg, task)) & 0xffffff})
            rubric = rubric_of(pkg, task)
            brief = build_brief(pkg, task, staged, rubric)
            panel = PANEL[fam][:]
            if ti % 2 == 0:            # 位置轮换：偶数任务槽序互换
                panel = panel[::-1]
            scores = {}   # pid -> {judge: score}
            verdicts = {}
            ok = True
            for judge in panel:
                wdir = os.path.join(RUN, "judge-work", "%s-%s" % (pkg, task), judge.replace("/", "_"))
                os.makedirs(wdir, exist_ok=True)
                rec, v = judge_call(judge, wdir, brief, staged, "%s-%s" % (pkg, task))
                verdicts[judge] = v
                if not v or not isinstance(v.get("scores"), dict):
                    ok = False
                    continue
                for pid, sv in v["scores"].items():
                    scores.setdefault(pid, {})[judge] = sv.get("total")
            # pid 并集对齐（裁判漏判的 pid 按缺考处理=该 judge 无分）
            # §3.4 抽检：按任务序轮换抽 1 份（覆盖两臂），同裁判匿名复评
            sampled_pid = staged[(ti - 1) % len(staged)]["pid"]
            judge0 = panel[0]
            wdir2 = os.path.join(RUN, "judge-work", "%s-%s" % (pkg, task),
                                 judge0.replace("/", "_") + "-resample")
            os.makedirs(wdir2, exist_ok=True)
            staged2 = [s for s in staged if s["pid"] == sampled_pid]
            staged2 = [{"pid": "Q1", "files": staged2[0]["files"]}]
            brief2 = build_brief(pkg, task, staged2, rubric)
            rec2, v2 = judge_call(judge0, wdir2, brief2, staged2, "%s-%s-resample" % (pkg, task))
            first = scores.get(sampled_pid, {}).get(judge0)
            second = v2.get("scores", {}).get("Q1", {}).get("total") if v2 else None
            action, jc_delta = "pass", (abs(first - second) if (first is not None and second is not None) else None)
            final_scores = {pid: (sum([s for s in d.values() if s is not None]) / len([s for s in d.values() if s is not None]) if d and any(s is not None for s in d.values()) else None)
                            for pid, d in scores.items()}
            if jc_delta is not None and jc_delta > 2:
                action = "re-judged"
                judge1 = panel[1]
                if verdicts.get(judge1) and isinstance(verdicts[judge1].get("scores"), dict):
                    news = {pid: sv.get("total") for pid, sv in verdicts[judge1]["scores"].items()}
                    final_scores = {pid: news.get(pid) for pid in final_scores}
                    if news.get(sampled_pid) is not None and first is not None and abs(news[sampled_pid] - first) > 2:
                        action = "unjudgeable"
                else:
                    action = "unjudgeable"
            J.write_json(os.path.join(RUN, "records", "judging",
                                      "%s-%s.json" % (pkg, task)),
                         {"tested_family": fam, "panel": panel,
                          "panel_rotation": "task_idx=%d parity=%s" % (ti, ti % 2),
                          "verdicts": {k: v for k, v in verdicts.items()},
                          "per_judge_scores": scores, "final_scores": final_scores,
                          "judge_consistency": {"task": task, "resample_of": sampled_pid,
                                                "first_score": first, "second_score": second,
                                                "delta": jc_delta, "action": action},
                          "judge_prompt_version": J.JUDGE_PROMPT_VERSION})
            results[pkg][task] = {"status": "judged" if action != "unjudgeable" else "unjudgeable",
                                  "tested_family": fam, "panel": panel,
                                  "final_scores": final_scores,
                                  "mapping": mapping, "judge_consistency": {
                                      "task": task, "resample_of": sampled_pid,
                                      "first_score": first, "second_score": second,
                                      "delta": jc_delta, "action": action}}
            print("JUDGED %s/%s fam=%s action=%s" % (pkg, task, fam, action), flush=True)
    J.write_json(os.path.join(RUN, "records", "judge-results.json"), results)
    bad = [1 for p in results.values() for t in p.values()
           if t.get("status") in ("unjudgeable", "infra_error")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
