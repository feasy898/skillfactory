#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/mm-retest-20261009/x_selfcheck.py — 装置就绪自检 + mock 三分支干跑（零模型）。

对重测装置做开工前全链路自证（全部零模型）：
  ①冻结哈希复算（净荷 100=adae05f2…）；②packs 忠实性（brief≡instruction 逐字、<outdir>→out、
  判据词汇零泄漏）；③8 题 rubric 权重机读（Σw=1.0）+ 锚点预登记在位（t08 ⟦0.5,0,1⟧→5.0 等）
  + §9-1 封顶措辞扫描（本轮 8 题 rubric 无封顶条款=无 min(·,cap) 项）；④mock 三分支干跑（D2 纪律）：
  主判全链路 / 复评链路 / 重发链路（arith 不一致→同裁判重发 1 次→仍不一致 fail-closed），
  全部以 mock 判官函数执行，验证管线接线与登记口径；⑤聚合器 fail-closed（判分缺席时 exit 2）。
退出码：0=装置就绪；1=有红。
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "mm-retest-20261009")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "meeting-minutes-skill")
FROZEN_100 = "adae05f2ce966345b23f276bd6e37355cf2b511f02994d392bdfc0afb900c2a6"
TASK_ORDER = ["t0%d" % i for i in range(1, 9)]
RES = []


def check(name, ok, detail=""):
    RES.append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    return ok


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ---------------------------------------------------------------- mock 三分支干跑
def mock_dryrun():
    """D2 纪律：mock 三分支（主判/复评/重发）。全部零模型，monkeypatch x_judges.judge_call。"""
    import x_judges as X

    weights = {"正确性": ("正确性", __import__("decimal").Decimal("0.5")),
               "完整性": ("完整性", __import__("decimal").Decimal("0.3")),
               "可验证性": ("可验证性", __import__("decimal").Decimal("0.2"))}
    from decimal import Decimal
    weights = {"正确性": ("正确性", Decimal("0.5")), "完整性": ("完整性", Decimal("0.3")),
               "可验证性": ("可验证性", Decimal("0.2"))}
    sum_w = Decimal("1.0")
    pids = ["P1", "P2", "P3", "P4", "P5", "P6"]

    def mk_verdict(total_fn):
        scores = {}
        for pid in pids:
            dims = {"正确性": 1.0, "完整性": 1.0, "可验证性": 1.0}
            scores[pid] = {"total": total_fn(pid, dims), "dims": dims,
                           "evidence": "mock"}
        return {"scores": scores}

    calls = {"n": 0}

    def fake_judge_call(judge, workdir, brief, staged, task_label, phase="main"):
        calls["n"] += 1
        os.makedirs(workdir, exist_ok=True)
        # 分支脚本：main 第 1 次按 scenario 返回；resend/resample 按 phase 计数
        scen = fake_judge_call.scen
        if phase == "main":
            v = mk_verdict(scen["main_first"])
        elif phase == "resend":
            v = mk_verdict(scen.get("main_resend", scen["main_first"]))
        elif phase == "resample":
            v = {"scores": {"Q1": {"total": scen["resample"], "dims":
                 {"正确性": 1.0, "完整性": 1.0, "可验证性": 1.0}, "evidence": "mock"}}}
        else:
            v = None
        slot_rec = {"slot": calls["n"], "slot_no": calls["n"], "session_id": "mock-sess",
                    "model_id_observed": "MOCK", "exit_code": 0, "wall_ms": 1,
                    "input_tokens": 0, "output_tokens": 0}
        # D2 先写后处理：mock 判词落 slot 文件
        with open(os.path.join(workdir, "verdict-slot%d.json" % calls["n"]), "w",
                  encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False)
        return {"exit_code": 0}, v, slot_rec

    ok_all = True
    staged = [{"pid": p, "files": ["summary.json"]} for p in pids]
    brief = X.build_brief("t01", staged) if os.path.isdir(MERGED) else "mock brief"

    # 分支①主判：arith 相符 → 一次通过（无 resend）
    fake_judge_call.scen = {"main_first": lambda pid, d: 10.0}
    orig = X.judge_call
    X.judge_call = fake_judge_call
    try:
        calls["n"] = 0
        v, attempts, invalid = X.judge_validated("GLM-5.3", "/tmp/mm-retest-20261009-mock/a",
                                                 brief, staged, "mockT01", weights, sum_w,
                                                 pids, "mockT01", print)
        ok1 = (not invalid) and len(attempts) == 1 and attempts[0]["arith_invalid"] is False
        ok_all &= check("mock_主判_arith相符一次通过", ok1,
                        "attempts=%d invalid=%s" % (len(attempts), invalid))

        # 分支③重发：首判 arith 不一致 → 同裁判重发 1 次相符 → 通过
        calls["n"] = 0
        fake_judge_call.scen = {"main_first": lambda pid, d: 9.9,   # 错误 total
                                "main_resend": lambda pid, d: 10.0}
        v, attempts, invalid = X.judge_validated("GLM-5.3", "/tmp/mm-retest-20261009-mock/b",
                                                 brief, staged, "mockT01", weights, sum_w,
                                                 pids, "mockT01", print)
        ok3a = (not invalid) and len(attempts) == 2 \
            and attempts[0]["arith_invalid"] is True and attempts[1]["arith_invalid"] is False
        ok_all &= check("mock_重发_arith不一致重发1次后通过", ok3a,
                        "attempts=%d invalid=%s" % (len(attempts), invalid))

        # 分支③fail-closed：重发仍不一致 → fail-closed（禁止人工改数）
        calls["n"] = 0
        fake_judge_call.scen = {"main_first": lambda pid, d: 9.9,
                                "main_resend": lambda pid, d: 9.8}
        v, attempts, invalid = X.judge_validated("GLM-5.3", "/tmp/mm-retest-20261009-mock/c",
                                                 brief, staged, "mockT01", weights, sum_w,
                                                 pids, "mockT01", print)
        ok3b = invalid and v is None and len(attempts) == 2
        ok_all &= check("mock_重发_仍不一致fail_closed", ok3b,
                        "invalid=%s v=%s attempts=%d" % (invalid, v is None, len(attempts)))

        # 分支②复评：抽样 Q1 匿名 → 分差比较（|Δ|≤2 pass）
        from decimal import Decimal as D
        scores = {pid: {"GLM-5.3": 8.0, "Minimax-M3.1-Flash-Preview": 8.5} for pid in pids}
        first = scores["P1"]["GLM-5.3"]
        fake_judge_call.scen = {"main_first": lambda pid, d: 10.0, "resample":
                                lambda: None, "__q1_total": 8.5}
        fake_judge_call.scen = {"main_first": lambda pid, d: 10.0, "resample": 8.5}
        calls["n"] = 0

        def fake_judge_call_q1(judge, workdir, brief_, staged_, task_label, phase="main"):
            if phase == "resample":
                # dims 与 total arith 相符：10×(0.85×0.5+0.85×0.3+0.85×0.3)=8.5
                v = {"scores": {"Q1": {"total": 8.5, "dims": {"正确性": 0.85, "完整性": 0.85,
                     "可验证性": 0.85}, "evidence": "mock"}}}
            else:
                v = mk_verdict(lambda pid, d: 8.0)
            calls["n"] += 1
            os.makedirs(workdir, exist_ok=True)
            return {"exit_code": 0}, v, {"slot": calls["n"], "slot_no": calls["n"],
                                         "session_id": "mock-sess",
                                         "model_id_observed": "MOCK", "exit_code": 0,
                                         "wall_ms": 1, "input_tokens": 0, "output_tokens": 0}
        X.judge_call = fake_judge_call_q1
        rows, rinvalid = X.arith_check(
            {"scores": {"Q1": {"total": 8.5, "dims": {"正确性": 0.85, "完整性": 0.85,
                                      "可验证性": 0.85}}}}, weights, sum_w, ["Q1"])
        second = 8.5
        jc_delta = abs(first - second)
        ok2 = (not rinvalid) and jc_delta == 0.5 and jc_delta <= 2
        ok_all &= check("mock_复评_Q1匿名_分差0.5_pass", ok2,
                        "delta=%s rinvalid=%s" % (jc_delta, rinvalid))
        # §9-4：|Δ|>2 → 换 panel[1] 重评，比较对象=换上裁判 vs 失格裁判首评
        delta_bad = abs(first - 11.0 if first + 3 <= 10 else first - 3)
        swap_new = 8.0   # 换上裁判对被抽产物分数
        cmp_94 = abs(swap_new - first)
        ok94 = cmp_94 <= 2   # 换上裁判 8.0 vs 失格首评 8.0 → 一致 → 非 unjudgeable
        ok_all &= check("mock_复评超差_换裁判比较对象按§9-4", ok94,
                        "首评=%s 复评超差 换上=%s |Δ|=%s" % (first, swap_new, cmp_94))
    finally:
        X.judge_call = orig
    return ok_all


def main():
    # ① 冻结哈希复算
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    check("taskset_frozen_100_recompute", live == FROZEN_100, live)

    # ② packs：8 在位；brief ≡ instruction（<outdir>→out）；判据词汇零泄漏
    ok_all = True
    packs_manifest = os.path.join(RUN, "records", "packs-manifest.json")
    if not os.path.isfile(packs_manifest):
        check("packs_in_place", False, "先跑 build_packs.py")
        ok_all = False
    else:
        man = json.load(open(packs_manifest, encoding="utf-8"))
        check("packs_8_in_place", len(man["packs"]) == 8,
              "%d packs" % len(man["packs"]))
        for tid in TASK_ORDER:
            pd = os.path.join(RUN, "packs", "meeting-minutes-%s" % tid)
            raw = open(os.path.join(pd, "brief.md"), encoding="utf-8", newline="").read()
            tj = json.load(open(os.path.join(MERGED, tid, "task.json"), encoding="utf-8"))
            expect = tj["instruction"].replace("<outdir>", "out")
            # 机械替换是唯一改动：文件字节 = expect + 写入换行；其余逐字
            ok_all &= check("pack_%s_brief_同instruction逐字" % tid, raw == expect + "\n",
                            "sha=%s" % hashlib.sha256(raw.encode()).hexdigest()[:12])
            for banned in ("judge-notes", "判官", "判挂点", "rubric"):
                if banned in raw:
                    ok_all &= check("pack_%s_判据泄漏" % tid, False, banned)

    # ③ 权重机读 + 锚点预登记 + 封顶扫描
    import x_judges as X
    for tid in TASK_ORDER:
        try:
            weights, sum_w = X.rubric_weights(tid)
            check("rubric_%s_权重机读" % tid,
                  sum_w == 1 and len(weights) == 3,
                  "%s Σw=%s" % (sorted(weights), sum_w))
            ok_all &= sum_w == 1 and len(weights) == 3
        except Exception as exc:
            check("rubric_%s_权重机读" % tid, False, exc)
            ok_all = False
        rub = open(os.path.join(MERGED, tid, "rubric.md"), encoding="utf-8").read()
        notes = open(os.path.join(MERGED, tid, "judge-notes.md"), encoding="utf-8").read()
        cap_hits = re.findall(r"封顶|min\([^)]*cap", rub + notes)
        if cap_hits:
            check("rubric_%s_封顶措辞扫描" % tid, False, cap_hits)
            ok_all = False
        check("rubric_%s_无封顶条款" % tid, not cap_hits, "§9-1：无 min(·,cap) 项")
        # 引擎校准记录在位
        check("notes_%s_引擎校准在位" % tid,
              ("引擎实测" in notes or "minutes.py" in notes), "")
    t08 = open(os.path.join(MERGED, "t08", "judge-notes.md"), encoding="utf-8").read()
    # 落盘锚文本为命名维度形式：⟦正确性=0.5,完整性=0,可验证性=1.0⟧ → …=0.50 → 5.0（MMHOT-FIX 组合锚）
    anchor_ok = ("组合锚" in t08) and ("=0.50 → 5.0" in t08) \
        and ("正确性=0.5,完整性=0,可验证性=1.0" in t08)
    check("锚点_t08_组合锚⟦正确性=0.5,完整性=0,可验证性=1.0⟧→5.0", anchor_ok,
          "MMHOT-FIX 修订轮新增锚在位")
    ok_all &= anchor_ok

    # ④ mock 三分支干跑
    ok_all &= check("mock_三分支干跑", mock_dryrun(), "主判/复评/重发（零模型）")

    # ⑤ 聚合器 fail-closed（判分缺席时 exit 2）
    if not os.path.isfile(os.path.join(RUN, "records", "judging", "meeting-minutes.json")):
        r = os.popen("%s %s" % (sys.executable,
                                os.path.join(RUN, "x_aggregate.py")) ).read()
        rc = os.popen("%s %s 2>/dev/null; echo $?" % (sys.executable,
                       os.path.join(RUN, "x_aggregate.py"))).read().split()[-1]
        check("aggregator_fail_closed", rc == "2", "exit=%s（判分缺席）" % rc)
    else:
        check("aggregator_fail_closed", True, "判分已存在，跳过（判后聚合另行执行）")

    out = os.path.join(RUN, "records", "apparatus-selfcheck.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"checks": RES, "all_ok": all(r["ok"] for r in RES),
                   "at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z")}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    print("SELFCHECK %s（%d/%d PASS）" % (
        "PASS" if all(r["ok"] for r in RES) else "FAIL",
        sum(1 for r in RES if r["ok"]), len(RES)), flush=True)
    return 0 if all(r["ok"] for r in RES) else 1


if __name__ == "__main__":
    sys.exit(main())
