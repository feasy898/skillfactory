#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/x_selfcheck.py — 装置就绪自检（零模型）。

对重测装置做开工前全链路自证：冻结哈希复算、packs 忠实性、双臂树隔离、挂载面对照、
判分数据通路干跑（以 sf0008-k5b ab5 真实交付臂为样本：staging 盲态/简报构建/verdict 解析/
面板异族性）、聚合器 fail-closed。退出码 0=装置就绪；1=有红。
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "office-retest-20261009")
K5B = os.path.join(ROOT, "evalkit", "runs", "sf0008-k5b")
MERGED = os.path.join(ROOT, "planning", "taskset-redesign", "merged", "office-templates-skill")
FROZEN_96 = "9e7f57c6f4094f184483fab0d59f61121abd82316b1779072e9e99df43c0c535"
GOLDEN_SHA = "2fa58b07481b44bc2840b2fdd757ef19faa5ebe37e1918baf936b2b923f4ecbf"
TASK_ORDER = ["ab1-standard-four-templates", "ab2-boundary-missing-required",
              "ab3-empty-and-string-lists", "ab4-invalid-input-rejection",
              "ab5-determinism-layout-selfeval",
              "t01", "t02", "t03", "t04", "t05", "t06", "t07", "t08"]
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


def main():
    # docx 抽取依赖 python-docx：缺依赖时以装置 venv 重执行自身
    try:
        import docx  # noqa: F401
    except ImportError:
        vpy = os.path.join(ROOT, ".venv-dev", "bin", "python")
        if os.path.abspath(sys.executable) != os.path.abspath(vpy) and os.path.exists(vpy):
            os.execv(vpy, [vpy, os.path.abspath(__file__)] + list(sys.argv[1:]))
    # 1) 冻结哈希复算
    cmd = ("find planning/taskset-redesign/merged -type f ! -name index.json ! -name selection.tsv "
           "! -name 'BLIND-REVIEW*' ! -name 'REVISION-LOG.md' | sort | xargs sha256sum | sha256sum")
    live = os.popen("cd %s && %s" % (ROOT, cmd)).read().split()[0]
    check("taskset_frozen_96_recompute", live == FROZEN_96, live)
    g = sha256_file(os.path.join(ROOT, "dist/office-templates-skill/eval/golden.json"))
    check("golden_frozen_unchanged", g == GOLDEN_SHA, g)

    # 2) packs：13 在位；新题 brief ≡ instruction（<outdir>→out）；ab brief 正文与 K5B 逐字同
    ok_all = True
    for tid in TASK_ORDER:
        pb = os.path.join(RUN, "packs", "office-templates-%s" % tid, "brief.md")
        if not os.path.isfile(pb):
            ok_all = check("pack_%s" % tid, False, "缺 brief.md")
            continue
        if tid.startswith("t"):
            instr = json.load(open(os.path.join(MERGED, tid, "task.json"),
                                   encoding="utf-8"))["instruction"]
            want = instr.replace("<outdir>", "out") + "\n"
            ok_all &= check("pack_%s_brief≡instruction" % tid,
                            open(pb, encoding="utf-8").read() == want, os.path.getsize(pb))
        else:
            kb = os.path.join(K5B, "packs", "office-templates-%s" % tid, "brief.md")
            mine = open(pb, encoding="utf-8").read().splitlines()
            k5 = open(kb, encoding="utf-8").read().splitlines() if os.path.isfile(kb) else []
            # K5B 头两行 = "# SF-0008 office 臂任务（%s）" + 空行；本轮头 = "# office 重测臂任务…"
            same = mine[2:] == k5[2:] and mine[0].endswith("（%s）" % tid)
            ok_all &= check("pack_%s_body≡K5B" % tid, same,
                            "lines=%d/%d" % (len(mine), len(k5)))
    check("packs_all", ok_all)

    # 3) 双臂树隔离复跑（39 单元 × 2 臂）
    import x_arms as X
    alloc, fam_of = X.plan_allocation()
    fails = []
    n_units = 0
    for tid in TASK_ORDER:
        fam = fam_of[("office-templates", tid)]
        for rep in (1, 2, 3):
            ud = X.unit_dir(fam, tid, rep)
            if not os.path.isdir(ud):
                fails.append("缺单元 %s" % ud)
                continue
            n_units += 1
            for arm in ("baseline", "treatment"):
                ad = X.arm_dir_of(fam, tid, rep, arm)
                for ban in ("reference", "oracle"):
                    for dp, _dns, _fns in os.walk(ad):
                        if os.path.basename(dp) == ban:
                            fails.append("%s 含 %s" % (ad, ban))
                for dp, _dns, fns in os.walk(ad):
                    for fn in fns:
                        if fn in ("runner.py", "golden.json", "rubric.md", "judge-notes.md"):
                            fails.append("%s 含判分器面 %s" % (ad, fn))
                if not os.path.isfile(os.path.join(ad, "brief.md")):
                    fails.append("%s 缺 brief" % ad)
            b1 = X.sha256_file(X.arm_dir_of(fam, tid, rep, "baseline") + "/brief.md")
            b2 = X.sha256_file(X.arm_dir_of(fam, tid, rep, "treatment") + "/brief.md")
            if b1 != b2:
                fails.append("%s-rep%d 两臂 brief 不同" % (tid, rep))
            if os.path.isdir(X.arm_dir_of(fam, tid, rep, "baseline") + "/.zcode"):
                fails.append("%s-rep%d baseline 含 .zcode" % (tid, rep))
            if not os.path.isdir(X.arm_dir_of(fam, tid, rep, "treatment")
                                 + "/.zcode/skills/office-templates"):
                fails.append("%s-rep%d treatment 缺挂载" % (tid, rep))
    check("arm_trees_isolated_%d_units" % n_units, n_units == 39 and not fails, "; ".join(fails[:5]))

    # 4) 挂载面 == 重打包后 dist 可交付面（sha 逐一对照）+ 排除面不在挂载
    mm = json.load(open(os.path.join(RUN, "records", "mount-manifest.json")))
    ent = mm["office-templates-skill"]
    ok_m = True
    for rel, s in ent["file_sha256"].items():
        ok_m &= sha256_file(os.path.join(RUN, "assets", "office-templates-skill", rel)) == s
    ok_m &= sha256_file(os.path.join(ROOT, "dist/office-templates-skill/SKILL.md")) == \
        ent["file_sha256"]["SKILL.md"]
    excl_ok = all(not os.path.exists(os.path.join(RUN, "assets", "office-templates-skill", e))
                  for e in ("eval", "reference", "EVALUATION.md"))
    check("mount_face_matches_repacked_dist", ok_m and excl_ok,
          "files=%d excluded_absent=%s" % (len(ent["files"]), excl_ok))

    # 5) 判分数据通路干跑（零模型）：以 K5B ab5 rep1 真实臂为样本
    import x_judges as G
    import x_judge_lib as J
    units = [(1, os.path.join(K5B, "glm/office-templates-ab5-determinism-layout-selfeval-rep1/baseline")),
             (1, os.path.join(K5B, "glm/office-templates-ab5-determinism-layout-selfeval-rep1/treatment"))]
    staging = os.path.join(RUN, "judge-work", "_selfcheck-staging", "ab5-dry")
    G.STAGING_ROOTS["selfcheck-ab5"] = staging
    staged, mapping, meta = G.stage_products("ab5-determinism-layout-selfeval", units, staging,
                                             seed=20261009)
    blind_ok = True
    for s in staged:
        for fn in s["files"]:
            p = os.path.join(staging, s["pid"], fn)
            if os.path.isfile(p) and fn.endswith((".json", ".txt", ".md", ".log")):
                raw = open(p, encoding="utf-8", errors="replace").read()
                if re.search(r"baseline|treatment", raw.replace("<redacted>", "")):
                    blind_ok = False
    check("staging_blind_no_arm_labels", blind_ok,
          "pids=%s" % [s["pid"] for s in staged])
    mapping_only = {v["arm"] for v in mapping.values()}
    check("staging_mapping_kept_off_judge_face", mapping_only == {"baseline", "treatment"},
          json.dumps({k: v["arm"] for k, v in mapping.items()}, ensure_ascii=False))
    brief = G.build_brief("ab5-determinism-layout-selfeval", staged, True)
    check("brief_ab5_has_rubric_and_replay_note",
          "runner 自校验红绿双向成立" in brief and "_replay_facts.json" in brief
          and "9827318" in brief, "len=%d" % len(brief))
    tj_files = {os.path.join(MERGED, "t01", f) for f in ("rubric.md",)}
    brief2 = G.build_brief("t01", staged, False)
    check("brief_t01_weighted_protocol",
          "加权分 total = round(10" in brief2 and "维度分 × 权重" in brief2
          and "pass_line" in json.dumps({"pass_line": json.load(
              open(os.path.join(MERGED, "t01/task.json"), encoding="utf-8"))["pass_line"]}),
          "len=%d" % len(brief2))
    v = G.parse_verdict_json('推理散文…… ```json\n{"scores": {"P1": {"total": 7.6, '
                             '"evidence": "样例"}}, "junk": 1}\n```')
    check("verdict_parser_roundtrip", bool(v) and v["scores"]["P1"]["total"] == 7.6, str(v))
    panels_ok = True
    for fam, target_model in (("glm", "GLM-5.3"), ("minimax", "Minimax-M3.1-Flash-Preview")):
        if any(G.JUDGE_OF_MODEL[j] == fam for j in G.PANEL[fam]) or target_model in G.PANEL[fam]:
            panels_ok = False
    check("panel_cross_family_no_self", panels_ok, json.dumps(G.PANEL, ensure_ascii=False))
    replay_facts_ok = []
    for f in ("glm_ab5-rep2_treatment", "glm_ab5-rep1_treatment"):
        p = os.path.join(RUN, "records/ab5-replay-validation", f + ".facts.json")
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            rg = d["runner_redgreen"]
            replay_facts_ok.append(rg["green"]["exit_code"] == 0 and rg["green"]["checks_total"] == 68
                                   and rg["red"]["exit_code"] == 1)
    check("ab5_replay_tool_validated_on_k5b_arms", len(replay_facts_ok) == 2
          and all(replay_facts_ok), "green68/red1 facts=%s" % replay_facts_ok)

    # 6) 聚合器 fail-closed（判分记录缺席须 exit 2，不出数）
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(RUN, "x_aggregate.py")],
                       capture_output=True)
    check("aggregate_failclosed_before_judging", r.returncode == 2,
          r.stderr.decode("utf-8", "replace")[-120:])

    bad = [c for c in RES if not c["ok"]]
    out = {"run": "office-retest-20261009", "total": len(RES), "failed": len(bad),
           "checks": RES}
    with open(os.path.join(RUN, "records", "apparatus-selfcheck.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": 0 if not bad else 1, "total": len(RES), "failed": len(bad)},
                     ensure_ascii=False))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
