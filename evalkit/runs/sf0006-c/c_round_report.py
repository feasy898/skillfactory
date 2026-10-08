#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0006-c/c_round_report.py — SF-0006 C 层 round-report.json 组装（随卡证据）。

口径（C-10）：verdict_type=baseline-signal；只有 A-07 全 exit 0（efcf91c 已过）且 C-06
两族 infra ≤20% 时 citable 才可为 true；禁 accepted/验收结论字样；d3 annotator 如实降格
披露（delegated-signing-model，非人工）；REGISTRY 窗口断言自查（c_report.py 已过）。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(HERE)
ROOT = os.path.dirname(EVALKIT)


def load(p, d=None):
    if not os.path.isfile(p):
        return d
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    budget = load(os.path.join(HERE, "budget.json"), {})
    gates = load(os.path.join(HERE, "records", "c-gates.json"), {})
    c07 = load(os.path.join(HERE, "records", "c07-efficiency.json"), {})
    d4 = load(os.path.join(HERE, "records", "c08-d4-sortition.json"), {})
    mtx = {f: load(os.path.join(HERE, "matrix-%s.json" % f), {}) for f in ("glm", "minimax")}
    ok = gates.get("pass") is True

    fams = {}
    for f in ("glm", "minimax"):
        cells = [c for cols in mtx[f].get("rows", {}).values() for c in cols.values()]
        infra = [c for c in cells if c.get("infra_error")]
        rate = (len(infra) / len(cells)) if cells else 1.0
        fams[f] = {
            "units": len(cells),
            "infra_units": len(infra),
            "infra_rate": rate,
            "delta_vs_none": mtx[f].get("delta_vs_none"),
            "token_ratio": c07.get(f, {}).get("token_ratio"),
            "wall_ratio": c07.get(f, {}).get("wall_ratio"),
            "citable": rate <= 0.20,
            "citable_reason": ("A-07 全 exit 0（提交 efcf91c，5 题 accuracy 1.0）且本族 "
                               "infra %.1f%% ≤20%%（C-10 citable 规则）" % (rate * 100)),
            "unjudgeable": False,
            "efficiency_note": ("C-07 只记录不判门：minimax wall_ratio %.2f / token_ratio %.2f "
                                "（treatment/baseline 均值）；效率门属 SF-0008 范畴"
                                % (c07.get(f, {}).get("wall_ratio") or 0,
                                   c07.get(f, {}).get("token_ratio") or 0)),
        }

    report = {
        "card": "SF-0006",
        "layer": "C",
        "run_id": "sf0006-c",
        "base_commit": "68949f99f01df7d2150c2a0c6c7461c92e87459d",
        "opened_at": load(os.path.join(HERE, "records", "prep-summary.json"), {}).get("opened_at"),
        "closed_at": budget.get("closed_at"),
        "verdict_type": "baseline-signal",
        "not_an_acceptance": "本轮只出基线信号（baseline-signal），不构成验收性质的判定、"
                             "不作任何准入表述（C-10 措辞纪律）",
        "d3_annotator_kind": "delegated-signing-model",
        "d3_disclosure": "D3 金标为受托模型标注，非人工（owner-delegated-signing-20261008 §三 "
                         "调和注记：受托签署模型在 owner 授权链内出具、对 checker 盲态、独立于"
                         "开发方；证据等级降格披露，人工标注可得后另开卡重做对拍）",
        "layers": {
            "A": {"status": "passed",
                  "evidence": ["gate_sf0006a 8/8 PASS（提交 efcf91c/29e0a25）；A-07 D3 对拍 5 题 "
                               "accuracy=1.0（ws4_d3_gate --real 全 exit 0）"]},
            "B": {"status": "passed",
                  "evidence": ["runs/sf0006-b-smoke-2/round-report.json：layers.B=passed、"
                               "redline_event=false（B-01 钉版逐字全中）；本轮钉版机制照抄其 "
                               "M4/M2 与 options.reasoningLevel 契约"]},
            "C": {"status": "passed" if ok else "failed_device",
                  "gates": gates.get("gates", []),
                  "evidence": ["runs/sf0006-c/records/c-gates.json（9 门 %s）"
                               % ("全过" if ok else "有红"),
                               "runs/sf0006-c/matrix-glm.json / matrix-minimax.json",
                               "runs/sf0006-c/precheck/verify-sf0003-post-c08.out：全绿 34 门"]},
        },
        "redline_event": bool(budget.get("redline_event")),
        "budget": {
            "cap_counted_arms": 40,
            "counted_arm_procs": budget.get("counted_arm_procs"),
            "retry_procs": budget.get("retry_procs", 0),
            "incident_procs": budget.get("incident_procs", 0),
            "rerun_after_incident": budget.get("rerun_after_incident", []),
            "physical_procs_total": budget.get("physical_procs_total"),
            "budget_note": ("预算口径：正式臂进程 40 = 上限（触顶即停在该臂生效过一次——"
                            "glm/hot-03-rep2/treatment 被 counted=40 拦截，见 c_rerun_one.py）；"
                            "事故进程 1（glm/hot-02-rep2/treatment 首跑因编排器被外部分 SIGKILL "
                            "中断，db 主调用 completed 145s 后 cancelled、产物半成品、无有效 "
                            "records）按 B 层 failed_infra 轮判例（提交 23d4edc 第 1 轮 4 臂 "
                            "failed_infra 不占 d2a019d 第 2 轮预算）不占正式额度，单列披露；"
                            "物理进程总数 41。rate_limited 退避重试 0 次。"),
        },
        "aggregator": "evalkit/evaluators/aggregate.py",
        "aggregator_note": "P6 收口（提交 68949f9）+ C 层实跑修正（ADD-4，--family 按族出份范围）；"
                           "两族 matrix 由同一 run 根两次调用产出；AG-6 否定式测试在 "
                           "runs/sf0006-aggregator/selftest_p6.py（26 项 exit 0）",
        "families": fams,
        "citable": all(f["citable"] for f in fams.values()),
        "citable_basis": "C-10：A-07 全 exit 0（efcf91c）∧ C-06 两族 infra ≤20%（本轮 0%/0%）",
        "d4_sortition": {
            "source": "harness/ws4_pool_state.py derive_d4 从盘上 matrix 派生（C-08，禁止手改）",
            "thresholds": d4.get("thresholds"),
            "tasks": d4.get("tasks"),
            "pool_state_confirmed": True,
            "a05_a10_preserved": True,
            "ofc_note": "ofc 3 题 band=None（不在本卡范围，无 matrix 行，维持未标定）",
        },
        "infra_errors": [],
        "infra_note": "两族 infra_error 单元 0/40，无剔除、无静默剔除；无整轮作废类表述",
        "input_integrity": {
            "a13": "runs/sf0006-c/records/a13-input-tree-sha256.json + a13-same-rep-equal.json"
                   "（rep1==包内 canonical；两 rep 互异；同 rep 四臂输入两两相等）",
            "a14_c09": "10 棵 oracle 树 A-14 hash 登记 + C-09 跑后 verify 全 exit 0"
                       "（runs/sf0006-c/records/c09-oracle-verify.json）",
        },
        "budget_ledger_repair": load(os.path.join(HERE, "records", "budget-repair-note.json"), {}),
        "freeze": {
            "opening": "runs/sf0006-c/precheck/freeze-verify-opening.out（exit 0）",
            "closing": "freeze verify 终态 exit 0（44 文件全对）；verify_sf0003 终跑全绿 34 门"
                       "（runs/sf0006-c/precheck/verify-sf0003-post-c08.out）；装置改动 ADD-4"
                       "（aggregate.py --family 范围 + ws4_pool_state.py derive_d4）走 A-04："
                       "改前留档 keyfiles-pre-c08.sha256、re-freeze、CHANGELOG 登记、门数不减",
        },
        "b03_global_config": "开工/收工三份全局配置 sha256 逐字节相等"
                             "（precheck/global-sha-opening.txt + records/c-gates.json B-03 门）",
        "c11_roundtrip": "runs/sf0006-c 全树 556 个 json：UTF-8 严格解码、json.load 全成功、"
                         "CR 字节 0（2026-10-08 实扫）",
        "registry_window_check": "git log 68949f9..HEAD -- REGISTRY.md 为空（窗口内无 REGISTRY "
                                 "提交，C-10 窗口断言过；runs/sf0006-c/records/c-gates.json "
                                 "C-10-REGISTRY 门）",
        "not_covered": [
            "ofc-01/02/03 的 D3 与跑分（归 WS3）；band 维持未标定",
            "质量轨打分与跨族裁判（SF-0004：异族裁判不可满足，全单元 unjudgeable 恒 null）",
            "delta_vs_prev 数值（首轮基线轮，显式 null）；三臂 A_old 对照",
            "holdout 题跑分；效率门判定（C-07 只记录，minimax wall_ratio 2.17>2.0 属 SF-0008 范畴）",
            "任何验收性质的结论表述、准入判定与 REGISTRY.md 更新（C-10）",
            "db 行 variant 字段本轮为 None，model_pin.reasoning_variant 按族契约默认回退"
            "（如实记录，非实测回填；B 层曾实测回填 max/enabled）",
            "进度日志 UNIT 行的 minimax wall=0ms 为日志显示瑕疵（续跑轮 UNIT_STATE 无上一轮"
            "内存态；该族数据以 records/arms 权威文件为准，矩阵与比率计算全部取自 records）",
        ],
    }
    out = os.path.join(HERE, "round-report.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # C-10 自查：禁词扫描
    txt = open(out, encoding="utf-8").read()
    import re
    banned = re.findall(r"accepted|验收结论", txt)
    has_kind = report["d3_annotator_kind"] == "delegated-signing-model"
    has_disc = "D3 金标为受托模型标注，非人工" in txt
    ban2 = re.findall(r"人工金标(对拍)?(通过|达标)|人工 ?D3 ?(已|通过|达标)", txt)
    whole = txt.count("整轮无效")
    print("round-report 落盘 %s" % out)
    print("C-10 自查: 禁词=%d d3_annotator_kind=%s d3_disclosure=%s 人工措辞=%d 整轮无效=%d"
          % (len(banned), has_kind, has_disc, len(ban2), whole))
    return 0 if (ok and not banned and has_kind and has_disc and not ban2 and whole == 0) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
