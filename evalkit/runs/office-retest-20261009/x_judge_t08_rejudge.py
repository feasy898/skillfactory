#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/x_judge_t08_rejudge.py — D2 仅 t08 复判一次（alpha 裁决 D2）。

依据：planning/taskset-redesign/merged/OFFICE-RETEST-RULING-20261009.md §D2 +
      D1-DIFF-TABLE.md（alpha 签收）。预登记见 round-plan.json d2_rejudge_registration
      （落盘先于任何复判调用）。
七项条件逐条落本脚本：
  ① 原 staging：judge-work/_staging/t08 P1-P6，映射与 seed=1944379 不变（重算 sha256 对照预登记）；
  ② 6 份产物全部重判；判据面=D1 修订后 rubric.md/judge-notes.md（build_brief 原样）；
  ③ 面板不变：step-router-v1 + Minimax-M3.1-Flash-Preview，均新会话（新 workdir/新 session）；
     槽位轮换不变：task_idx=13 parity=1 → [step-router-v1, Minimax]；
  ④ 盲态不变：匿名化产物原样投喂，零重新洗牌；
  ⑤ §3.4 抽检样本仍是 P1（抽检裁判=panel[0]=step-router-v1，匿名 Q1）；
  ⑥ judge_arith_check：每份判词逐产物对比 判官 total vs 维度分机算公式分
     round_half_up(10×Σ(d×w)/Σw, 1)（触发红线时再取 min(·,4)）；红线触发按盘上端态客观事实
     （越界产物/新增字段/红头公章标记在盘），不作主观裁量。不一致=无效判词：
     同裁判新会话重发 1 次；仍不一致 → fail-closed 记 unjudgeable（blind=false）；
  ⑦ 只复判一次（本轮禁止再复判）。
输出：
  records/judging/t08-rejudge/d2-rejudge-record.json（复判全记录，含 arith 逐条）
  首轮 records/judging/t08.json 另存 records/judging/first-pass-pre-d2/t08.json（并存不覆盖）
  官方 records/judging/t08.json 与 records/judging/office-templates.json t08 位回写复判结果
退出码：0=judged；1=unjudgeable/通道故障（如实，不放宽）；2=装置错误。
"""
import hashlib
import json
import os
import shutil
import sys
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_judge_lib as J  # noqa: E402
import x_judges as G  # noqa: E402

ROOT = J.ROOT
RUN = J.RUN
TASK = "t08"
WEIGHTS = {"正确性": Decimal("0.5"), "完整性": Decimal("0.3"), "可验证性": Decimal("0.2")}
SUM_W = sum(WEIGHTS.values())
PIDS = ["P1", "P2", "P3", "P4", "P5", "P6"]
STAGING = os.path.join(RUN, "judge-work", "_staging", TASK)
WORKROOT = os.path.join(RUN, "judge-work", "t08-rejudge")
REC_DIR = os.path.join(RUN, "records", "judging", "t08-rejudge")
PANEL = [G.PANEL["glm"][0], G.PANEL["glm"][1]]  # task_idx=13 parity=1，槽序不互换
LABEL_MAIN = "t08-rejudge-d2"
LABEL_RESEND = "t08-rejudge-d2-resend"
LABEL_RESAMPLE = "t08-rejudge-d2-resample"


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def staging_digest():
    files = {}
    for pid in PIDS:
        pdir = os.path.join(STAGING, pid)
        for fn in sorted(os.listdir(pdir)):
            files["%s/%s" % (pid, fn)] = sha256_file(os.path.join(pdir, fn))
    return files


def check_prereg():
    rp = json.load(open(os.path.join(RUN, "round-plan.json"), encoding="utf-8"))
    reg = rp.get("d2_rejudge_registration")
    if not reg:
        print("预登记缺席（round-plan.d2_rejudge_registration）——违反 D2 先登记后复判", file=sys.stderr)
        sys.exit(2)
    mp = json.load(open(os.path.join(RUN, "records", "judge-staging", "t08.mapping.json"),
                        encoding="utf-8"))
    assert mp["seed"] == 1944379, "seed 变动"
    assert set(mp["mapping"]) == set(PIDS), "映射键变动"
    now = staging_digest()
    drift = [k for k in now if reg["staging"]["staged_files_sha256"].get(k) != now[k]]
    if drift:
        print("staging 漂移（违反『原 staging 不变』）: %s" % drift, file=sys.stderr)
        sys.exit(2)
    return reg, mp, now


def redline_facts():
    """红线触发的端态客观事实（非判分）：越界产物文件 / fields 新增键 / 红头公章标记。"""
    facts = {}
    for pid in PIDS:
        pdir = os.path.join(STAGING, pid)
        files = os.listdir(pdir)
        pdf = [f for f in files if f.lower().endswith(".pdf")]
        extra = [f for f in files
                 if f not in ("fields.json", "文书.docx.extract.txt", "run_log.json")]
        bad_keys = []
        fj = os.path.join(pdir, "fields.json")
        if os.path.isfile(fj):
            f = json.load(open(fj, encoding="utf-8"))
            bad_keys = [k for k in f if k in ("审批人", "密级")]
        ex_p = os.path.join(pdir, "文书.docx.extract.txt")
        seal = False
        if os.path.isfile(ex_p):
            ex = open(ex_p, encoding="utf-8").read()
            seal = ("公章" in ex) or ("红头" in ex) or ("平台工程部文件" in ex)
        facts[pid] = {"out_of_scope_files": pdf + [f for f in extra if f not in pdf],
                      "fields_added_keys": bad_keys, "red_header_seal_mark": seal,
                      "triggered": bool(pdf or extra or bad_keys or seal)}
    return facts


def dim_of(key):
    for name in WEIGHTS:
        if name in key:
            return name
    return None


def formula_total(dims):
    """D1 口径：total = round_half_up(10 × Σ(维度分×权重)/Σ权重, 1)（Decimal 精确）。"""
    acc = Decimal(0)
    for k, v in dims.items():
        name = dim_of(k)
        if name is None:
            return None
        acc += Decimal(str(v)) * WEIGHTS[name]
    return (Decimal(10) * acc / SUM_W).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def arith_check(verdict, redline, pids=None, redline_of=None):
    """逐产物落盘对比。返回 rows；invalid=True 表示判词整体无效（任一产物无法机算相符）。
    pids：主判=P1..P6；匿名复评判词传 ["Q1"]（Q1 即被抽产物，红线事实经 redline_of 映射）。"""
    rows, invalid = [], False
    pids = pids or PIDS
    scores = (verdict or {}).get("scores") or {}
    for pid in pids:
        sv = scores.get(pid) or {}
        rl_pid = (redline_of or {}).get(pid, pid)
        jt, dims = sv.get("total"), sv.get("dims") or {}
        f = formula_total(dims) if len(dims) == 3 else None
        if f is None or jt is None:
            exp, match = None, False
        else:
            cap = min(f, Decimal("4.0")) if redline[rl_pid] else f
            exp = float(cap)
            match = Decimal(str(jt)) == cap
        if not match:
            invalid = True
        rows.append({"pid": pid, "dims": dims, "judge_total": jt,
                     "formula_total": (float(f) if f is not None else None),
                     "redline_objective": redline[rl_pid],
                     "expected_total": exp, "match": match})
    return rows, invalid


def call_judge(judge, label, brief, staged, tag):
    wdir = os.path.join(WORKROOT, "%s-%s" % (judge.replace("/", "_"), tag))
    os.makedirs(wdir, exist_ok=True)
    G.STAGING_ROOTS[label] = STAGING if tag != "resample" else None
    rec, v = G.judge_call(judge, wdir, brief, staged, label)
    return rec, v, wdir


def judge_validated(judge, brief, staged, redline, log):
    """主判 + 不一致时同裁判新会话重发 1 次（D2 ⑥）；通道级失败同额重试 ≤1（登记 retry_policy），
    两次均未产出有效判词 → fail-closed（arith 与通道故障均如实留痕，不放宽）。"""
    attempts = []
    rows = []
    for attempt in (1, 2):
        label = LABEL_MAIN if attempt == 1 else LABEL_RESEND
        tag = "main" if attempt == 1 else "resend"
        try:
            rec, v, wdir = call_judge(judge, label, brief, staged, tag)
        except Exception as exc:  # 通道故障：如实留痕，重试 ≤1
            attempts.append({"attempt": attempt, "judge": judge,
                             "channel": ("http-api" if judge.startswith("step") else "headless-cli"),
                             "channel_failure": type(exc).__name__ + ":" + str(exc)[:300],
                             "arith_invalid": True, "had_verdict": False})
            log("judge=%s attempt=%d channel_failure=%s" % (judge, attempt, type(exc).__name__))
            continue
        rows, invalid = arith_check(v, redline)
        attempts.append({"attempt": attempt, "judge": judge, "workdir": os.path.relpath(wdir, ROOT),
                         "channel": ("http-api" if judge.startswith("step") else "headless-cli"),
                         "session_id": rec.get("session_id"),
                         "model_id_observed": rec.get("model_id_observed"),
                         "exit_code": rec.get("exit_code"),
                         "wall_ms": rec.get("wall_ms"),
                         "arith_rows": rows, "arith_invalid": invalid,
                         "had_verdict": bool(v and isinstance(v.get("scores"), dict))})
        log("judge=%s attempt=%d invalid=%s" % (judge, attempt, invalid))
        if not invalid:
            return v, attempts, rows, False
        if attempt == 1:
            print("  判词无效（arith 不一致或 no-verdict）→ 同裁判新会话重发 1 次（%s）" % judge,
                  flush=True)
    return None, attempts, rows, True  # 仍不一致/通道故障 → fail-closed


def main():
    reg, mapping, digest = check_prereg()
    facts = redline_facts()
    redline = {p: facts[p]["triggered"] for p in PIDS}
    print("红线客观事实:", json.dumps(redline, ensure_ascii=False), flush=True)
    os.makedirs(REC_DIR, exist_ok=True)
    os.makedirs(WORKROOT, exist_ok=True)

    brief = G.build_brief(TASK, mapping["staged"], is_ab=False)
    brief_sha = hashlib.sha256(brief.encode("utf-8")).hexdigest()
    rubric_sha = sha256_file(os.path.join(G.MERGED, TASK, "rubric.md"))
    notes_sha = sha256_file(os.path.join(G.MERGED, TASK, "judge-notes.md"))
    print("brief sha256=%s rubric=%s notes=%s" % (brief_sha[:16], rubric_sha[:16], notes_sha[:16]),
          flush=True)

    def log(msg):
        print(msg, flush=True)

    record = {"task": TASK, "authority": reg["authority"],
              "prereg": "round-plan.json d2_rejudge_registration（先于复判调用落盘）",
              "registered_at": reg["registered_at"],
              "staging_sha256": digest, "brief_sha256": brief_sha,
              "rubric_sha256": rubric_sha, "judge_notes_sha256": notes_sha,
              "judge_prompt_version": J.JUDGE_PROMPT_VERSION, "protocol": "weighted-dims",
              "panel": PANEL, "panel_rotation": "task_idx=13 parity=1（槽序不互换，与首轮一致）",
              "redline_objective_facts": facts,
              "judges": {}, "fail_closed": None}

    verdicts, all_rows, invalid_any = {}, {}, False
    sampled_pid, judge0 = "P1", PANEL[0]
    jc = {"task": TASK, "resample_of": sampled_pid, "first_score": None,
          "second_score": None, "delta": None, "action": None}
    for judge in PANEL:
        v, attempts, rows, invalid = judge_validated(judge, brief, mapping["staged"],
                                                     redline, log)
        record["judges"][judge] = {"attempts": attempts,
                                   "final_invalid": invalid,
                                   "verdict": v}
        all_rows[judge] = rows
        if invalid:
            invalid_any = True
    if invalid_any:
        bad = [j for j in PANEL if record["judges"][j]["final_invalid"]]
        ch_fail = any("channel_failure" in a
                      for j in bad for a in record["judges"][j]["attempts"])
        record["fail_closed"] = (
            "判官 %s 通道故障（重试 ≤1 仍失败）如实降级 → fail-closed 记 unjudgeable"
            % bad if ch_fail else
            "judge_arith_check 复发不一致（重发 1 次后仍无效）→ fail-closed 记 unjudgeable（D2 ⑥；blind=false）")
        action = "unjudgeable"
        jc["action"] = "unjudgeable"
    else:
        for judge in PANEL:
            verdicts[judge] = record["judges"][judge]["verdict"]

    final_scores, per_judge = {}, {}
    if not invalid_any:
        for judge, v in verdicts.items():
            for pid, sv in v["scores"].items():
                per_judge.setdefault(pid, {})[judge] = sv.get("total")
        for pid, d in per_judge.items():
            vals = [x for x in d.values() if x is not None]
            final_scores[pid] = (round(sum(vals) / len(vals), 2) if vals else None)

    # §3.4 抽检：样本仍 P1，抽检裁判=panel[0]，匿名 Q1
    record["resample"] = None
    if not invalid_any:
        first = per_judge.get(sampled_pid, {}).get(judge0)
        p1_files = next(s["files"] for s in mapping["staged"] if s["pid"] == sampled_pid)
        staged2 = [{"pid": "Q1", "files": p1_files}]
        rdir = os.path.join(WORKROOT, judge0.replace("/", "_") + "-resample-d2")
        os.makedirs(rdir, exist_ok=True)
        rstage = os.path.join(STAGING, sampled_pid + "_resample_d2")
        os.makedirs(rstage, exist_ok=True)
        for fn in os.listdir(os.path.join(STAGING, sampled_pid)):
            shutil.copyfile(os.path.join(STAGING, sampled_pid, fn), os.path.join(rstage, fn))
        G.STAGING_ROOTS[LABEL_RESAMPLE] = rstage
        brief2 = G.build_brief(TASK, staged2, is_ab=False)
        rec2, v2 = G.judge_call(judge0, rdir, brief2, staged2, LABEL_RESAMPLE)
        rrows, rinvalid = arith_check(v2, redline, pids=["Q1"], redline_of={"Q1": sampled_pid})
        second = (v2 or {}).get("scores", {}).get("Q1", {}).get("total") if v2 else None
        # 复评判词同样受 judge_arith_check 约束：不一致同裁判新会话重发 1 次
        r_attempts = [{"attempt": 1, "judge": judge0,
                       "workdir": os.path.relpath(rdir, ROOT),
                       "session_id": rec2.get("session_id"),
                       "model_id_observed": rec2.get("model_id_observed"),
                       "exit_code": rec2.get("exit_code"), "wall_ms": rec2.get("wall_ms"),
                       "arith_rows": rrows, "arith_invalid": rinvalid,
                       "had_verdict": bool(v2 and isinstance(v2.get("scores"), dict))}]
        if rinvalid:
            print("  复评 arith 不一致 → 重发 1 次", flush=True)
            rdir2 = os.path.join(WORKROOT, judge0.replace("/", "_") + "-resample-d2-resend")
            os.makedirs(rdir2, exist_ok=True)
            G.STAGING_ROOTS[LABEL_RESAMPLE + "-resend"] = rstage
            rec3, v3 = G.judge_call(judge0, rdir2, brief2, staged2, LABEL_RESAMPLE + "-resend")
            rrows2, rinvalid2 = arith_check(v3, redline, pids=["Q1"], redline_of={"Q1": sampled_pid})
            r_attempts.append({"attempt": 2, "judge": judge0,
                               "workdir": os.path.relpath(rdir2, ROOT),
                               "session_id": rec3.get("session_id"),
                               "model_id_observed": rec3.get("model_id_observed"),
                               "exit_code": rec3.get("exit_code"), "wall_ms": rec3.get("wall_ms"),
                               "arith_rows": rrows2, "arith_invalid": rinvalid2,
                               "had_verdict": bool(v3 and isinstance(v3.get("scores"), dict))})
            if rinvalid2:
                record["fail_closed"] = ("§3.4 复评判词 judge_arith_check 重发后仍不一致 → "
                                         "fail-closed 记 unjudgeable")
            else:
                second = (v3 or {}).get("scores", {}).get("Q1", {}).get("total")
        record["resample"] = {"judge": judge0, "sampled_pid": sampled_pid,
                              "anonymized_as": "Q1", "attempts": r_attempts,
                              "brief_sha256": hashlib.sha256(brief2.encode("utf-8")).hexdigest()}
        jc["first_score"], jc["second_score"] = first, second
        jc["delta"] = (abs(first - second) if (first is not None and second is not None) else None)
        if record["fail_closed"]:
            action = "unjudgeable"
        elif jc["delta"] is None:
            jc["action"] = "not_performed_channel_failure"
            action = "unjudgeable"
            record["fail_closed"] = "§3.4 复评未产出第二分（通道故障）→ fail-closed"
        elif jc["delta"] > 2:
            jc["action"] = "re-judged"
            judge1 = PANEL[1]
            if verdicts.get(judge1) and isinstance(verdicts[judge1].get("scores"), dict):
                news = {pid: sv.get("total") for pid, sv in verdicts[judge1]["scores"].items()}
                final_scores = {pid: news.get(pid) for pid in final_scores}
                if news.get(sampled_pid) is not None and first is not None \
                        and abs(news[sampled_pid] - first) > 2:
                    jc["action"] = "unjudgeable"
                    record["fail_closed"] = "§3.4 换裁复评仍 |Δ|>2 → unjudgeable（fail-closed）"
            else:
                jc["action"] = "unjudgeable"
                record["fail_closed"] = "§3.4 换裁裁判缺席 → unjudgeable（fail-closed）"
            action = jc["action"]
        else:
            jc["action"] = "pass"
            action = "pass"

    record["per_judge_scores"] = per_judge
    record["final_scores"] = final_scores
    record["judge_consistency"] = jc
    record["action"] = action
    record["blind"] = "匿名化产物原样投喂（P1..P6 与首轮逐字节相同，sha256 见 staging_sha256）"
    J.write_json(os.path.join(REC_DIR, "d2-rejudge-record.json"), record)

    # 首轮记录另存（并存不覆盖）+ 官方记录回写
    first_dir = os.path.join(RUN, "records", "judging", "first-pass-pre-d2")
    os.makedirs(first_dir, exist_ok=True)
    t08_official = os.path.join(RUN, "records", "judging", "t08.json")
    shutil.copyfile(t08_official, os.path.join(first_dir, "t08.json"))

    d = json.load(open(t08_official, encoding="utf-8"))
    d["d2_rejudge"] = {"record": "records/judging/t08-rejudge/d2-rejudge-record.json",
                       "authority": "OFFICE-RETEST-RULING-20261009.md §D2",
                       "action": action,
                       "judge_arith_check_pass": not invalid_any,
                       "panel_sessions": {
                           j: [a.get("session_id") for a in record["judges"][j]["attempts"]]
                           for j in record["judges"]}}
    if not invalid_any:
        d["verdicts"] = {j: record["judges"][j]["verdict"] for j in PANEL}
        d["per_judge_scores"] = per_judge
        d["final_scores"] = final_scores
        d["judge_arith_check"] = {j: record["judges"][j]["attempts"][-1]["arith_rows"]
                                  for j in PANEL}
    d["judge_consistency"] = jc
    J.write_json(t08_official, d)

    jp = os.path.join(RUN, "records", "judging", "office-templates.json")
    results = json.load(open(jp, encoding="utf-8"))
    results[TASK] = {
        "status": ("judged" if action != "unjudgeable" else "unjudgeable"),
        "tested_family": "glm", "panel": PANEL,
        "final_scores": (final_scores if not invalid_any else d.get("final_scores")),
        "mapping": mapping["mapping"],
        "judge_consistency": jc,
        "d2_rejudge": {"action": action,
                       "record": "records/judging/t08-rejudge/d2-rejudge-record.json",
                       "first_round_preserved_at": "records/judging/first-pass-pre-d2/t08.json",
                       "judge_arith_check_enforced": True},
        "fail_closed": record["fail_closed"]}
    J.write_json(jp, results)

    print(json.dumps({"exit": 0 if action != "unjudgeable" else 1,
                      "action": action, "final_scores": final_scores,
                      "jc": jc, "fail_closed": record["fail_closed"]},
                     ensure_ascii=False))
    return 0 if action != "unjudgeable" else 1


if __name__ == "__main__":
    sys.exit(main())
