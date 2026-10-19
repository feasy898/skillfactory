#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/hot-retest-20261009/x_judges.py — hot 重测裁判面板驱动（盲态、异族 ≥2、位置轮换、
judge_arith_check 首轮即生效、§3.4 抽检）。

移植自 office-retest-20261009/x_judges.py，按本轮 round-plan 适配：
  面板：被测 glm → [step-router-v1, Minimax-M3.1-Flash-Preview]；被测 minimax → [step-router-v1, GLM-5.3]
  （≥2 族互裁；与被测族交集为空）。step=模型 API 直调（无 assistant-prefill）；
  glm/minimax=headless M4/M2。位置轮换：槽序按任务序奇偶互换。
判分协议（judge_prompt_version=S8-JUDGE-v2-2-HOTRETEST-1，随轮落盘）：
  8 题全部加权维度协议——每维度按档位赋分（满分档=1.0、零分档=0.0、中档=rubric 明示分，
  未明示取 0.5），加权分=round(10×Σ(维度分×权重)÷Σ权重,1)；通过线=task.json.pass_line。
  verdict 须含 dims 明细（键=正确性/完整性/可验证性 短名）。
judge_arith_check（EVAL-SPEC v0.2.2 §9-3 首轮即生效）：
  harness 对每份判词逐产物机算公式分 total=round(10×Σ(dims×权重)÷Σ权重,1)（hot rubric 无
  封顶条款，公式分即终值）；判官 total ≠ 机算 → 判词无效：同裁判新会话重发 1 次（判词整份
  替代，禁择优/人工改数）；仍不一致 → 该裁判失格；有效异族裁判 <2 → 任务 unjudgeable
  （fail-closed）。结果逐条落盘 judge_arith_check。
判据面（judge-notes 首批嵌入）：rubric.md 全文 + judge-notes.md 全文随 brief 投喂；投喂副本
  内 <pkg>→dist 引擎绝对路径、<workdir>→暂存根 机械替换（文件本体零改动）。
t07 对拍事实：harness 侧机械对拍（同参数重跑 gen.py + diff -r）产出 _replay_diff.json 随
  暂存进判据面（判官可按 judge-notes 命令本机复跑复核；headless 裁判可执行、step 裁判读事实）。
§3.4：每任务抽 1 份产物同裁判匿名复评；|Δ|>2 → 换面板内另一异族裁判重评全任务（比较对象
  按 §9-4=换上裁判对被抽产物分 vs 失格裁判首评）；仍>2 → task unjudgeable（fail-closed）。
产物收集：臂工作面全貌（排除 records/、.zcode/、fixtures/、brief.md、transcript_*——防臂
  身份泄露），路径/挂载痕迹漂白 + P1..Pn 洗牌匿名。
用法：python x_judges.py [--task <task_id>]
退出码：0 全任务判分落盘 / 1 有任务 unjudgeable 或装置失败（如实，不放宽）。
"""

import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_judge_lib as J  # noqa: E402

ROOT = J.ROOT
RUN = J.RUN
PANEL = {"glm": ["step-router-v1", "Minimax-M3.1-Flash-Preview"],
         "minimax": ["step-router-v1", "GLM-5.3"]}
JUDGE_OF_MODEL = {"step-router-v1": "step", "Minimax-M3.1-Flash-Preview": "minimax",
                  "GLM-5.3": "glm"}

TASK_ORDER = ["t01", "t02", "t03", "t04", "t05", "t06", "t07", "t08"]
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "hot-templates-skill")
DIST_GEN = os.path.join(ROOT, "dist", "hot-templates-skill", "scripts", "gen.py")
WEIGHTS = {
    "t01": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t02": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t03": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t04": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t05": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t06": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t07": {"正确性": 0.4, "完整性": 0.3, "可验证性": 0.3},
    "t08": {"正确性": 0.5, "完整性": 0.3, "可验证性": 0.2},
}
DIM_KEYS = ("正确性", "完整性", "可验证性")
COLLECT_EXCLUDE_DIRS = {"records", ".zcode", "fixtures", "__pycache__"}
COLLECT_EXCLUDE_PREFIX = ("transcript_",)

SCORING_RULE = """评分规则（S8-JUDGE-v2-2-HOTRETEST-1 / 加权维度协议，EVAL-SPEC v0.2.2）：
- rubric 表每行为一个维度（维度名/权重/满分档/中档/零分档）。对每维度独立定档并赋分：
  满分档=1.0；零分档=0.0；中档=该维度分（取 rubric 中明示的分值，如 0.4/0.5/0.3；rubric 未明示数值时取 0.5）。
- dims 键使用短名：「正确性」「完整性」「可验证性」（依次对应 rubric 表中带括号注的同名维度行）。
- 定档必须附实测证据（引用暂存文件中的具体事实/原文/数字，逐维 ≤150 字）；无证据的档位无效。
- 产物加权分 total = round(10 × Σ(维度分 × 权重) ÷ Σ权重, 1)，区间 [0,10]。这是唯一总分，不再另设项分平均。
  total 必须按此公式由你的 dims 严格算出（harness 会按维度分机算复核，不一致判词按无效处理并重发）。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与 judge-notes 与证据判分；实现路径与参照不同不扣分（端态原则），除非 rubric 显式考格式/结构。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "dims": {"正确性": d1, "完整性": d2, "可验证性": d3}, "evidence": "≤150 字逐维证据摘要"}}, ...}（dims 键名须为上述三个短名；除 scores 外不要其他顶层键）。"""


def dim_of(key):
    """判官 dims 键 → 短名（容忍带括号注全名）。未匹配返回 None。"""
    k = str(key).strip()
    for d in DIM_KEYS:
        if k == d or k.startswith(d):
            return d
    return None


def arith_total(task, dims):
    """§9-3 机算：round(10×Σ(d×w)/Σw, 1)。hot rubric 无封顶条款；未知维度键返回 None。"""
    w = WEIGHTS[task]
    num, den, seen = 0.0, 0.0, set()
    for k, v in (dims or {}).items():
        d = dim_of(k)
        if d is None or not isinstance(v, (int, float)):
            return None
        num += float(v) * w[d]
        den += w[d]
        seen.add(d)
    if den <= 0 or seen != set(DIM_KEYS):
        return None
    return round(10.0 * num / den, 1)


def totals_agree(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) <= 0.050001


def redact_text(s, arm_root):
    s = s.replace(arm_root, "<ARMROOT>")
    s = s.replace(ROOT, "<REPOROOT>")
    s = re.sub(r"\.zcode/skills/[A-Za-z0-9_\-]+", "<SKILL_MOUNT>", s)
    s = re.sub(r"\.zcode\\\\skills\\\\[A-Za-z0-9_\-]+", "<SKILL_MOUNT>", s)
    for key in ("arm", "engine", "run_id", "runId", "side", "arm_label", "session_id",
                "sessionId", "skill_mount", "asset"):
        s = re.sub(r'"%s"\s*:\s*"[^"]*"' % key, '"%s": "<redacted>"' % key, s)
        s = re.sub(r"'%s'\s*:\s*'[^']*'" % key, "'%s': '<redacted>'" % key, s)
    return s


def collect_workface(ad):
    """臂工作面全貌收集（排除可泄臂身份面）。"""
    files = {}
    for dp, dns, fns in os.walk(ad):
        dns[:] = [d for d in dns if d not in COLLECT_EXCLUDE_DIRS]
        for fn in fns:
            if fn.startswith(COLLECT_EXCLUDE_PREFIX) or fn in ("brief.md", "arm_run.json",
                                                               "model_pin.json", "telemetry.json"):
                continue
            src = os.path.join(dp, fn)
            files[os.path.relpath(src, ad)] = src
    if not files:  # 空工作面也是端态事实（t08 零产物合规边界）
        files["__empty_workface__.txt"] = None
    return files


def t07_replay_facts(staging_pdir, names):
    """t07 判据面：harness 机械对拍（同参数重跑 gen.py + 与该产物逐文件比对）。
    产出 _replay_diff.json 进暂存（判官可按 judge-notes 命令本机复跑复核）。"""
    facts = {"replay": "harness 机械对拍（gen.py 同参数重跑，判据工具非产物）", "files": {}}
    try:
        tmp = tempfile.mkdtemp(prefix="t07-replay-")
        cmd = ["/usr/bin/python3", DIST_GEN, "--platform", "wx", "--topic", "家庭应急包收纳",
               "--points", '["手电和备用电池分袋封装", "药品每半年核对效期更换", "证件复印件防水袋随身"]',
               "--outdir", tmp]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        facts["replay_exit_code"] = r.returncode
        for rel in ("骨架.md", "structure.json"):
            p = os.path.join(staging_pdir, rel)
            ref = os.path.join(tmp, rel)
            entry = {"ref_generated": os.path.isfile(ref)}
            if os.path.isfile(p) and os.path.isfile(ref):
                a = open(p, "rb").read()
                b = open(ref, "rb").read()
                entry["identical"] = a == b
                if a != b:
                    al, bl = a.decode("utf-8", "replace").splitlines(), \
                             b.decode("utf-8", "replace").splitlines()
                    diffs = ["line %d: staged=%r vs replay=%r" % (i + 1, al[i] if i < len(al) else "<EOF>",
                                                                  bl[i] if i < len(bl) else "<EOF>")
                             for i in range(max(len(al), len(bl))) if
                             (al[i] if i < len(al) else None) != (bl[i] if i < len(bl) else None)][:8]
                    entry["diff_head"] = diffs
                    entry["n_diff_lines"] = len([1 for i in range(max(len(al), len(bl)))
                                                 if (al[i] if i < len(al) else None)
                                                 != (bl[i] if i < len(bl) else None)])
            elif not os.path.isfile(p):
                entry["staged_present"] = False
            facts["files"][rel] = entry
        import shutil as _s
        _s.rmtree(tmp, ignore_errors=True)
    except Exception as exc:
        facts["replay_error"] = type(exc).__name__ + ":" + str(exc)[:200]
    with open(os.path.join(staging_pdir, "_replay_diff.json"), "w", encoding="utf-8",
              newline="\n") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
        f.write("\n")
    names.append("_replay_diff.json")
    return facts


def stage_products(task, unit_dirs, staging, seed):
    """收集产物→漂白→洗牌匿名化。返回 (staged, mapping, meta)。"""
    rng = random.Random(seed)
    items = []
    for rep, ad in unit_dirs:
        items.append({"rep": rep, "arm": os.path.basename(os.path.normpath(ad)),
                      "dir": ad, "files": collect_workface(ad)})
    rng.shuffle(items)
    os.makedirs(staging, exist_ok=True)
    mapping, staged, meta = {}, [], []
    for i, it in enumerate(items, 1):
        pid = "P%d" % i
        mapping[pid] = {"rep": it["rep"], "arm": it["arm"]}
        pdir = os.path.join(staging, pid)
        os.makedirs(pdir, exist_ok=True)
        names = []
        for rel, src in sorted(it["files"].items()):
            base = rel.replace("/", "__")
            dst = os.path.join(pdir, base)
            if src is None:  # 空工作面标记
                with open(dst, "w", encoding="utf-8", newline="\n") as f:
                    f.write("（臂工作目录在排除判分器/技能挂载/转录面后无任何交付文件——空工作面事实）\n")
                names.append(base)
                continue
            ext = os.path.splitext(rel)[1].lower()
            if ext in (".json", ".md", ".txt", ".log", ".py"):
                raw = open(src, encoding="utf-8", errors="replace").read()
                with open(dst, "w", encoding="utf-8", newline="\n") as f:
                    f.write(redact_text(raw, it["dir"]))
                names.append(base)
            else:
                import shutil
                shutil.copyfile(src, dst)
                names.append(base)
        if task == "t07":
            t07_replay_facts(pdir, names)
        staged.append({"pid": pid, "files": names})
        meta.append({"pid": pid, "n_files": len(names)})
    return staged, mapping, meta


def rubric_new(task):
    return open(os.path.join(MERGED, task, "rubric.md"), encoding="utf-8").read()


def judge_notes_new(task):
    p = os.path.join(MERGED, task, "judge-notes.md")
    return open(p, encoding="utf-8").read().rstrip() if os.path.isfile(p) else ""


def adapt_judging_text(text, staging_root):
    """判据面投喂副本机械替换：<pkg>→dist 引擎绝对路径、<workdir>→暂存根（文件本体零改动）。"""
    pkg_dir = os.path.join(ROOT, "dist", "hot-templates-skill")
    text = text.replace("<pkg>", pkg_dir).replace("<workdir>", staging_root)
    text = text.replace("<outdir>", "out").replace("<tmp>", "<判官本机临时目录>")
    return text


def build_brief(task, staged, staging_root):
    tj = json.load(open(os.path.join(MERGED, task, "task.json"), encoding="utf-8"))
    lines = ["# hot 重测盲评判分任务（%s，通过线 %s）" % (task, tj.get("pass_line")),
             "",
             "你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。",
             "", "## rubric（冻结原文，加权维度判分）", "", adapt_judging_text(rubric_new(task), staging_root).rstrip()]
    notes = judge_notes_new(task)
    if notes:
        lines += ["", "## judge-notes（判官专用：判挂点与期望值，判分必照此执行）", "",
                  adapt_judging_text(notes, staging_root)]
    lines += ["", SCORING_RULE,
              "", "（题目指令原文备查，判分只按 rubric 与 judge-notes）：", "```",
              tj["instruction"].rstrip(), "```"]
    lines += ["", "## 产物清单"]
    for s in staged:
        lines.append("- %s: %s" % (s["pid"], ", ".join(s["files"])))
    if task == "t07":
        lines += ["", "（t07 注记：各产物目录附 _replay_diff.json=harness 机械对拍事实"
                      "（gen.py 同参数重跑逐文件比对）；headless 裁判亦可按 judge-notes 命令本机复跑复核。"
                      "对拍差异仅限尾随空白/换行且 ≤3 处 → 正确性中档 0.5；任何占位符被内容替换或"
                      "structure 被改写 → 正确性 0；端态/台账是否同时破坏按 judge-notes 两档归档，"
                      "存疑从严归破坏档。）"]
    lines += ["", "请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。"]
    return "\n".join(lines)


def parse_verdict_json(text):
    """提取含 "scores" 的最后一个平衡 JSON 对象（容忍围栏/推理散文）。"""
    best = None
    for m in re.finditer(r'"scores"', text):
        i = text.rfind("{", 0, m.start())
        if i < 0:
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    cand = text[i:j + 1]
                    try:
                        obj = json.loads(cand)
                        if isinstance(obj, dict) and isinstance(obj.get("scores"), dict):
                            best = obj
                    except Exception:
                        pass
                    break
    return best


STAGING_ROOTS = {}


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    p = os.path.join(RUN, "progress.log")
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    print(line, flush=True)


def judge_call(judge, workdir, brief, staged, task_label):
    """单裁判单次调用。step=HTTP（产物内容内联）；glm/minimax=headless CLI。
    判词按 slot 先写后处理（D2 纪律）：response.txt/verdict.json 先落盘再解析。"""
    chan = JUDGE_OF_MODEL[judge]
    slot = J.budget_judge({"judge": judge, "channel": chan,
                           "task": task_label, "judge_prompt_version": J.JUDGE_PROMPT_VERSION,
                           "ts_intent": time.strftime("%H:%M:%S"), "status": "pending"})
    try:
        if chan == "step":
            parts = ["【输出纪律（最高优先级）】你是评分器。禁止展示任何思考、草稿、advisor 对话或分步分析；你的回复必须直接以 { 开头、以 } 结尾，内容仅为最终 verdict JSON。", "", brief, "", "# 产物内容（暂存文件全文）"]
            for s in staged:
                src_base = STAGING_ROOTS[task_label]
                for fn in s["files"]:
                    cand = [os.path.join(src_base, s["pid"], fn), os.path.join(src_base, fn)]
                    p = next((c for c in cand if os.path.isfile(c)), None)
                    if p is None:
                        continue
                    parts.append("=== %s/%s ===\n%s" % (s["pid"], fn,
                                 open(p, encoding="utf-8", errors="replace").read()[:24000]))
            r = J.step_chat([{"role": "user", "content": "\n".join(
                parts + ["", '现在直接输出最终评分 JSON：直接以 { 开头、以 } 结尾，最外层恰有一个 "scores" 键；每个产品一个键，键含 "total" 与 "dims" 与 "evidence"；除该 JSON 外不得输出任何文字，不得重复输出 JSON。'])}],
                max_tokens=32000)
            with open(os.path.join(workdir, "response.txt"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(r["text"])
            v = parse_verdict_json(r["text"])
            if v is not None:
                J.write_json(os.path.join(workdir, "verdict.json"), v)
            rec = {"exit_code": 0 if v else 1, "wall_ms": r["wall_ms"], "session_id": r["id"],
                   "model_id_observed": r["model"], "channel": "http-api",
                   "input_tokens": r["prompt_tokens"], "output_tokens": r["completion_tokens"]}
        else:
            with open(os.path.join(workdir, "brief.md"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(brief + "\n")
            for s in staged:
                src_pdir = os.path.join(STAGING_ROOTS[task_label], s["pid"])
                dst_pdir = os.path.join(workdir, s["pid"])
                if os.path.isdir(src_pdir):
                    import shutil as sh
                    sh.copytree(src_pdir, dst_pdir, dirs_exist_ok=True)
            rec = J.cli_judge(workdir, chan)
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


def arith_check_task(task, judge, label, verdict, log_rows):
    """§9-3：对单份判词逐产物机算。返回 (ok, rows)。不一致行写入 log_rows。"""
    ok = True
    rows = []
    for pid, sv in (verdict.get("scores") or {}).items():
        jt = sv.get("total")
        comp = arith_total(task, sv.get("dims"))
        match = totals_agree(jt, comp)
        rows.append({"judge": judge, "call": label, "product": pid,
                     "judge_total": jt, "computed_total": comp,
                     "dims": sv.get("dims"), "match": match})
        if not match:
            ok = False
    log_rows.extend(rows)
    if not (verdict.get("scores") or {}):
        ok = False
    return ok


def task_unit_dirs(task, fam, reps):
    out = []
    for rep in reps:
        ad = os.path.join(RUN, fam, "hot-templates-%s-rep%d" % (task, rep))
        out.append((rep, os.path.join(ad, "baseline")))
        out.append((rep, os.path.join(ad, "treatment")))
    return out


def fam_of_task(task):
    return "glm" if TASK_ORDER.index(task) % 2 == 0 else "minimax"  # 1-based 奇=glm


def main():
    only = None
    if "--task" in sys.argv:
        only = sys.argv[sys.argv.index("--task") + 1]
    reps = [1, 2, 3]
    jp = os.path.join(RUN, "records", "judging", "hot-templates.json")
    results = json.load(open(jp, encoding="utf-8")) if os.path.isfile(jp) else {}
    for ti, task in enumerate(TASK_ORDER, 1):
        if only and task != only:
            continue
        if isinstance(results.get(task), dict) and results[task].get("status") in ("judged", "unjudgeable"):
            print("SKIP judged %s" % task, flush=True)
            continue
        try:
            fam = fam_of_task(task)
            units = task_unit_dirs(task, fam, reps)
            missing = [u for u in units if not os.path.isfile(os.path.join(u[1], "records", "arm_run.json"))]
            if missing:
                results[task] = {"status": "infra_error", "missing": missing}
                J.write_json(jp, results)
                continue
            staging = os.path.join(RUN, "judge-work", "_staging", task)
            STAGING_ROOTS[task] = staging
            seed = zlib.crc32(("hot-retest-20261009|%s" % task).encode()) & 0xffffff
            staged, mapping, meta = stage_products(task, units, staging, seed)
            J.write_json(os.path.join(RUN, "records", "judge-staging", "%s.mapping.json" % task),
                         {"mapping": mapping, "staged": staged, "seed": seed})
            brief = build_brief(task, staged, staging)
            panel = PANEL[fam][:]
            if ti % 2 == 0:            # 位置轮换：偶数任务槽序互换
                panel = panel[::-1]
            scores, verdicts, arith_rows = {}, {}, []

            def _one_judge(judge, tag=""):
                wdir = os.path.join(RUN, "judge-work", task, judge.replace("/", "_") + tag)
                os.makedirs(wdir, exist_ok=True)
                return judge_call(judge, wdir, brief, staged, task)

            # 主判 + §9-3 arith：无效判词同裁判重发 1 次（新会话新目录），仍无效 → 失格
            for judge in panel:
                rec, v = _one_judge(judge)
                verdicts[judge] = v
                ok = v and isinstance(v.get("scores"), dict) and \
                    arith_check_task(task, judge, "main", v, arith_rows)
                if not ok:
                    log("ARITH/VERDICT 无效 %s@%s → 同裁判重发 1 次" % (task, judge))
                    rec2, v2 = _one_judge(judge, "#resend")
                    verdicts[judge + "#resend"] = v2
                    ok2 = v2 and isinstance(v2.get("scores"), dict) and \
                        arith_check_task(task, judge, "resend", v2, arith_rows)
                    if ok2:
                        verdicts[judge] = v2   # 整份替代（禁择优：重发即唯一有效判词）
                    else:
                        verdicts[judge] = None  # 失格
                if verdicts[judge] and isinstance(verdicts[judge].get("scores"), dict):
                    for pid, sv in verdicts[judge]["scores"].items():
                        scores.setdefault(pid, {})[judge] = sv.get("total")

            def _scored_judges():
                return {j for d in scores.values() for j in d if d[j] is not None}

            final_action_note = None
            if len(_scored_judges()) < 2:
                results[task] = {"status": "unjudgeable", "tested_family": fam, "panel": panel,
                                 "reason": "有效异族裁判 <2（arith 重发后仍无效/无 verdict），fail-closed（§9-3）",
                                 "mapping": mapping, "per_judge_scores": scores,
                                 "judge_arith_check": arith_rows,
                                 "judge_prompt_version": J.JUDGE_PROMPT_VERSION,
                                 "protocol": "weighted-dims"}
                J.write_json(jp, results)
                print("UNJUDGEABLE %s fam=%s" % (task, fam), flush=True)
                continue
            # §3.4 抽检：按任务序轮换抽 1 份（覆盖两臂），同裁判匿名复评（复评判词同过 arith）
            sampled_pid = staged[(ti - 1) % len(staged)]["pid"]
            judge0 = panel[0]
            wdir2 = os.path.join(RUN, "judge-work", task, judge0.replace("/", "_") + "-resample")
            os.makedirs(wdir2, exist_ok=True)
            staged2 = [{"pid": "Q1", "files": next(s["files"] for s in staged if s["pid"] == sampled_pid)}]
            brief2 = build_brief(task, staged2, staging)
            STAGING_ROOTS["%s-resample" % task] = os.path.join(staging, sampled_pid + "_resample")
            os.makedirs(STAGING_ROOTS["%s-resample" % task], exist_ok=True)
            import shutil as _sh
            _sh.copytree(os.path.join(staging, sampled_pid),
                         STAGING_ROOTS["%s-resample" % task], dirs_exist_ok=True)

            def _resample_call():
                return judge_call(judge0, wdir2, brief2, staged2, "%s-resample" % task)

            rec2_, v2_ = _resample_call()
            if not (v2_ and isinstance(v2_.get("scores"), dict)
                    and arith_check_task(task, judge0, "resample", v2_, arith_rows)):
                log("抽检复评判词无效 %s@%s → 重发 1 次" % (task, judge0))
                rec2_, v2_ = _resample_call()
                if v2_ and isinstance(v2_.get("scores"), dict):
                    arith_check_task(task, judge0, "resample-resend", v2_, arith_rows)
            second = v2_.get("scores", {}).get("Q1", {}).get("total") if v2_ else None
            first = scores.get(sampled_pid, {}).get(judge0)
            jc_delta = (abs(first - second) if (first is not None and second is not None) else None)
            final_scores = {pid: (sum([s for s in d.values() if s is not None]) /
                                  len([s for s in d.values() if s is not None])
                                  if d and any(s is not None for s in d.values()) else None)
                            for pid, d in scores.items()}
            action = "pass"
            if jc_delta is not None and jc_delta > 2:
                action = "re-judged"
                judge1 = panel[1]
                if verdicts.get(judge1) and isinstance(verdicts[judge1].get("scores"), dict):
                    news = {pid: sv.get("total") for pid, sv in verdicts[judge1]["scores"].items()}
                    final_scores = {pid: news.get(pid) for pid in final_scores}
                    # §9-4 比较对象=换上裁判对被抽产物分 vs 失格裁判（judge0）对该产物首评
                    if news.get(sampled_pid) is not None and first is not None \
                            and abs(news[sampled_pid] - first) > 2:
                        action = "unjudgeable"
                else:
                    action = "unjudgeable"
                final_action_note = ("re-judge 比较两端（§9-4）：judge1=%s 对 %s 分 vs 失格/首评判官"
                                     "%s 首评 %s" % (judge1, sampled_pid, judge0, first))
            J.write_json(os.path.join(RUN, "records", "judging", "%s.json" % task),
                         {"tested_family": fam, "panel": panel,
                          "panel_rotation": "task_idx=%d parity=%s" % (ti, ti % 2),
                          "verdicts": {k: v for k, v in verdicts.items()},
                          "per_judge_scores": scores, "final_scores": final_scores,
                          "judge_arith_check": arith_rows,
                          "judge_consistency": {"task": task, "resample_of": sampled_pid,
                                                "first_score": first, "second_score": second,
                                                "delta": jc_delta, "action": action,
                                                "comparison_ends": ("§9-4：换上裁判对被抽产物分 vs "
                                                                    "失格裁判首评" if action != "pass" else
                                                                    "同裁判（%s）首评 vs 匿名复评" % judge0)},
                          "action_note": final_action_note,
                          "judge_prompt_version": J.JUDGE_PROMPT_VERSION,
                          "protocol": "weighted-dims",
                          "protocol_note": ("judge-notes 首批嵌入；判据面投喂副本 <pkg>/<workdir> 机械替换；"
                                            "t07 附 harness 机械对拍 _replay_diff.json（判官可复跑复核）；"
                                            "hot rubric 无封顶条款，公式分即终值（§9-1 上限语义预登记）")})
            results[task] = {"status": "judged" if action != "unjudgeable" else "unjudgeable",
                             "tested_family": fam, "panel": panel,
                             "final_scores": final_scores, "mapping": mapping,
                             "judge_arith_check_rows": len(arith_rows),
                             "judge_arith_all_match": all(r["match"] for r in arith_rows),
                             "judge_consistency": {"task": task, "resample_of": sampled_pid,
                                                   "first_score": first, "second_score": second,
                                                   "delta": jc_delta, "action": action}}
            J.write_json(jp, results)
            print("JUDGED %s fam=%s action=%s" % (task, fam, action), flush=True)
        except Exception as exc:
            import traceback
            results[task] = {"status": "infra_error",
                             "error": type(exc).__name__ + ":" + str(exc)[:300],
                             "trace": traceback.format_exc()[-1500:]}
            J.write_json(jp, results)
            print("INFRA_ERROR %s: %s" % (task, exc), flush=True)
            continue
    J.write_json(os.path.join(RUN, "records", "judge-results.json"),
                 {"hot-templates": results})
    bad = [1 for t in results.values() if t.get("status") in ("unjudgeable", "infra_error")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
