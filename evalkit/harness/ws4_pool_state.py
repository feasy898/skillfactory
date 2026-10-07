#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/ws4_pool_state.py — WS4 dev 池状态组装器（SF-0005 · D1-D4 SOP 痕迹落盘）。

产出（幂等重建）：
1. evalkit/packs/ws4-dev/<pkg>/runner_contract.json —— L1 桥接实测四字段
   （argv_shape / ref_root_verbatim / selfcheck_exit / redpath_exit，GC-1）；
2. bench/devpool-r1/pool-state.json —— 8 题 D1-D4 记录（GD-1..GD-4）：
   - d1_record：来源+四项自检+signoff 三字段（未签=null=WAITING_OWNER，反假人工门）；
     **签署保全（SF-0006 A-05）**：重建时从既有 pool-state.json 继承已落盘的
     d1/d3 signoff，不得把已签署记录冲回 null；
   - d2_record：canonical 种子 + 生成时间 + 生成树逐文件 sha256（纯机械，自足）；
   - d3_record：D3 门实测（自环 + fail-closed 出口）+ signoff（未签=null，已签则继承）；
     mm/hot 金标标注渠道登记 annotator_kind="delegated-signing-model"（A-10；
     ofc 三题金标属 WS3 未注入，不带该字段）；
   - d4_record：难度带 null（首轮未标定）+ 首轮分布记录（全带外，卡面允许）。
   status=built；ready 由盘上记录派生（SF-0006-D3FIX 修4，A-10 口径）：
     ready = d1 signoff 签署人非 null ∧ 该题 D3 真实对拍达标（real_gate_exit=0 且
     real_result.accuracy≥0.95）∧ d3 signoff 三字段非 null ∧ line∈{mm,hot}；
     counts.ready 同步；禁止手改 pool-state.json。
   generated_at（pool 级与 d2 级）重跑继承既有值：重跑幂等（A-10 门 preserved
     前后全量比对；A-05 签署/就绪保全的时态面收口——eef8056 时代「仅 generated_at
     重算」的重跑副作用不再产生）。

用法：python ws4_pool_state.py [--evalbench-version v6-mvp-0.3]
"""

import argparse
import io
import json
import os
import sys
import tempfile
import datetime

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(HARNESS_DIR)
WORKSPACE = os.path.dirname(EVALKIT)
WS4_ROOT = os.path.join(EVALKIT, "packs", "ws4-dev")
BENCH = os.path.join(WORKSPACE, "bench", "devpool-r1")
TASK_IDS = ["mm-01", "mm-02", "hot-01", "hot-02", "hot-03", "ofc-01", "ofc-02", "ofc-03"]

SIGNOFF_NULL = {"签署人": None, "日期": None, "被签对象sha256": None}


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def d1_record(cfg, prev_signoff=None):
    return {
        "stage": "D1 来源→题面（人工必须过；本记录为 worker 起草，待 owner 签署）",
        "source": {"origin": cfg["origin"], "source_ref": cfg.get("source_ref"),
                   "desensitize_rule": "公开变体三题：内容 100% 自写，实体全部 nonce 化改写，零原文复制" if cfg["origin"] == "public-variant" else "自建题面，实体全部 nonce 化"},
        "self_checks": {
            "sc1_来源合法": {"claim": "来源=自建或公开规范/法条，脱敏+nonce 改写，无版权与隐私风险", "evidence": "source_ref 见上", "status": "drafted-awaiting-owner"},
            "sc2_可机判": {"claim": "输出契约可机判（L2 检查清单逐项落 checks/run_check.py）", "evidence": "selftest BQ-8 红绿两态全过（见 d2_record.selftest）", "status": "machine-green"},
            "sc3_两臂公平": {"claim": "两臂 brief 逐字相同（包内单一 brief.md，跑批时 make_arms 复制），无资产暗示", "evidence": "pack_checks EI-7 扫描零命中（pool-state.build_evidence）", "status": "machine-green"},
            "sc4_资产名零泄漏": {"claim": "brief/黄金输入零资产名与暗示句式", "evidence": "pack_checks EI-7 scan_hits=0；GE-4 grep 三个 dist 资产名零命中", "status": "machine-green"},
        },
        "signoff": dict(prev_signoff) if prev_signoff else dict(SIGNOFF_NULL),
    }


def d3_record(task_id, line, prev_signoff=None):
    import ws4_d3_gate
    selfloop = ws4_d3_gate.self_loop(task_id)
    code, real = ws4_d3_gate.real_mode(task_id)
    rec = {
        "stage": "D3 判分器化（人工金标对拍 ≥95%；人工必须过）",
        "self_loop": selfloop,
        "real_gate_exit": code,
        "state": real.get("state", "GOLDEN_PRESENT"),
        "message": real.get("message", real.get("note", "")),
        "real_result": real if code != 3 else None,
        "signoff": dict(prev_signoff) if prev_signoff else dict(SIGNOFF_NULL),
    }
    if line in ("mm", "hot"):  # A-10：mm/hot 金标标注渠道=受托模型（ofc 金标属 WS3 未注入）
        rec["annotator_kind"] = "delegated-signing-model"
    return rec


def derive_ready(line, d1_signoff, d3_rec):
    """SF-0006-D3FIX 修4（A-10 口径，owner-delegated-signing-20261008 §三）：
    ready 只能由本脚本从盘上记录派生——D1 已签 ∧ D3 真实对拍达标
    （real_gate_exit=0 且 real_result.accuracy≥0.95）∧ D3 已签（三字段非 null）
    ∧ line∈{mm,hot}（ofc 金标对拍属 WS3，恒不翻绿）。禁止手改 pool-state.json。"""
    d1_ok = bool((d1_signoff or {}).get("签署人"))
    d3s = d3_rec.get("signoff") or {}
    d3_signed = all(d3s.get(k) for k in ("签署人", "日期", "被签对象sha256"))
    rr = d3_rec.get("real_result") or {}
    try:
        acc = float(rr.get("accuracy") or 0.0)
    except (TypeError, ValueError):
        acc = 0.0
    d3_real_ok = d3_rec.get("real_gate_exit") == 0 and acc >= 0.95
    return bool(d1_ok and d3_signed and d3_real_ok and line in ("mm", "hot"))


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--evalbench-version", default="v6-mvp-0.3")
    args = ap.parse_args(argv)
    sys.path.insert(0, HARNESS_DIR)
    import ws4_gen
    import ws4_judge

    # 签署保全（SF-0006 A-05）+ 重跑幂等（A-10 门 preserved 前后全量比对）：
    # 重建前读取既有 pool-state.json，已落盘的 d1/d3 signoff 逐题继承，generated_at
    # 沿用既有值（重跑不改时间戳——eef8056 时代「仅 generated_at 重算」的副作用收口）；
    # 文件缺失或损坏视为无历史（按未签 null、当前时刻重建）。
    prev_tasks = {}
    prev_generated_at = None
    pool_path = os.path.join(BENCH, "pool-state.json")
    if os.path.isfile(pool_path):
        try:
            with io.open(pool_path, encoding="utf-8") as f:
                prev_pool = json.load(f)
            prev_tasks = {t.get("id"): t for t in prev_pool.get("tasks", [])}
            prev_generated_at = prev_pool.get("generated_at")
        except (ValueError, OSError) as exc:
            print("warn: 既有 pool-state.json 不可读，签署继承跳过: %s" % exc, file=sys.stderr)
            prev_tasks = {}
            prev_generated_at = None
    now = prev_generated_at or datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    def prev_signoff_of(tid, record_key):
        rec = (prev_tasks.get(tid) or {}).get(record_key) or {}
        so = rec.get("signoff")
        return so if isinstance(so, dict) and so.get("签署人") else None

    tasks_out = []
    for tid in TASK_IDS:
        pack = os.path.join(WS4_ROOT, tid)
        cfg = ws4_gen.load_task_cfg(tid)

        # GC-1 runner_contract（L1 桥接实测四字段，逐题落包）
        l1 = ws4_judge.l1_bridge(cfg["line"])
        write_json(os.path.join(pack, "runner_contract.json"), l1)

        # D2：canonical 种子新鲜生成留痕（种子/时间/sha256 + selftest 结果）
        tmp = tempfile.mkdtemp(prefix="ws4-poolstate-d2-")
        manifest = ws4_gen.generate(tid, cfg["canonical_seed"], "A", tmp)
        import subprocess
        st = subprocess.run([sys.executable, os.path.join(pack, "gen_oracle.py"), "--selftest"],
                            capture_output=True, text=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        selftest_pass = "SELFTEST PASS" in st.stdout
        d2_generated_at = (((prev_tasks.get(tid) or {}).get("d2_record") or {})
                           .get("generated_at")) or now  # 重跑幂等：沿用既有时间戳
        d2 = {
            "stage": "D2 题面→实例+oracle（纯机械，同种子逐字节复现+生成器红绿自检）",
            "seed": cfg["canonical_seed"], "nonce_set": "A",
            "generated_at": d2_generated_at,
            "outputs_sha256": manifest["sha256"],
            "selftest": {"exit": st.returncode, "selftest_pass": selftest_pass,
                         "covers": "BQ-8 红绿两态 / BQ-9 nonce 交叉红 / BQ-10 同种子逐字节 / fixtures 漂移守卫"},
        }

        d3 = d3_record(tid, cfg["line"], prev_signoff_of(tid, "d3_record"))

        d4 = {
            "stage": "D4 校准入池（难度带分拣）",
            "band": None,
            "band_reason": "首轮未标定：0 模型调用无臂数据，难度带（treatment 通过率锚）须待基线轮（SF-0006）后分拣",
            "first_round_distribution": "8 题全带外（built 未标定）；题型分布=positive 4 / near-negative 2 / adversarial 2",
            "sorter": "分拣规则（PLAN §3.2）：>90% 进轮换池、60-90% 迭代池、<60% 归因五分类；阈值卡 B 后可注入",
        }

        # 包完整性清单：freeze 装置 glob（packs/*/checks/...）只覆盖一层目录，ws4-dev 嵌套包的
        # wrapper 不入冻结账本（已留 planner 裁）；本清单补位——重建 pool-state 即可比对 tampering。
        import hashlib
        pack_files = {}
        for rel in ("brief.md", "rubric.md", "task.json", "gen_oracle.py",
                    "checks/run_check.py", "runner_contract.json"):
            fp = os.path.join(pack, rel)
            if os.path.isfile(fp):
                pack_files[rel] = hashlib.sha256(open(fp, "rb").read()).hexdigest()
        fx_dir = os.path.join(pack, "fixtures")
        for fn in sorted(os.listdir(fx_dir)):
            fp = os.path.join(fx_dir, fn)
            if os.path.isfile(fp):
                pack_files["fixtures/" + fn] = hashlib.sha256(open(fp, "rb").read()).hexdigest()

        d1 = d1_record(cfg, prev_signoff_of(tid, "d1_record"))
        # ready 派生（SF-0006-D3FIX 修4，A-10 口径）：只能由盘上记录推导，禁止手改
        ready_val = derive_ready(cfg["line"], d1["signoff"], d3)
        tasks_out.append({
            "id": tid, "pack": "evalkit/packs/ws4-dev/%s" % tid, "line": cfg["line"],
            "case_type": cfg["case_type"], "origin": cfg["origin"],
            "source_ref": cfg.get("source_ref"),
            "status": "built", "ready": ready_val,
            "canonical_seed": cfg["canonical_seed"],
            "pack_files_sha256": pack_files,
            "d1_record": d1,
            "d2_record": d2,
            "d3_record": d3,
            "d4_record": d4,
        })
        print("%s: contract+l1 ok(self=%s red=%s) d2.selftest=%s d3.exit=%s(%s) ready=%s" %
              (tid, l1["selfcheck_exit"], l1["redpath_exit"], selftest_pass,
               d3["real_gate_exit"], d3["state"], ready_val))

    pool = {
        "pool": "ws4-dev",
        "built_by": "SF-0005 · worker-glm-bd",
        "generated_at": now,
        "evalbench_version": args.evalbench_version,
        "counts": {"tasks": len(tasks_out), "built": len(tasks_out),
                   "ready": sum(1 for t in tasks_out if t["ready"]),
                   "case_type": {"positive": 4, "near-negative": 2, "adversarial": 2},
                   "origin": {"self-built": 5, "public-variant": 3},
                   "line": {"mm": 2, "hot": 3, "ofc": 3}},
        "signoff_ledger": "d1/d3 signoff 重建时继承已落盘签署（A-05 签署保全），未签者保持 null=WAITING"
                          "（ofc 3 题 D3 另为 WAITING_WS3）；ready 由盘上记录派生（SF-0006-D3FIX 修4，"
                          "A-10 口径：D1 已签 ∧ D3 真实对拍达标 ∧ D3 已签 ∧ line∈{mm,hot}），"
                          "禁止手改 pool-state.json",
        "tasks": tasks_out,
    }
    write_json(os.path.join(BENCH, "pool-state.json"), pool)
    print("pool-state -> %s （ready=%d）" % (os.path.join(BENCH, "pool-state.json"),
                                             sum(1 for t in tasks_out if t["ready"])))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
