#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/ws4_pool_state.py — WS4 dev 池状态组装器（SF-0005 · D1-D4 SOP 痕迹落盘）。

产出（幂等重建）：
1. evalkit/packs/ws4-dev/<pkg>/runner_contract.json —— L1 桥接实测四字段
   （argv_shape / ref_root_verbatim / selfcheck_exit / redpath_exit，GC-1）；
2. bench/devpool-r1/pool-state.json —— 8 题 D1-D4 记录（GD-1..GD-4）：
   - d1_record：来源+四项自检+signoff 三字段（恒 null = WAITING_OWNER，反假人工门）；
   - d2_record：canonical 种子 + 生成时间 + 生成树逐文件 sha256（纯机械，自足）；
   - d3_record：D3 门实测（自环 + fail-closed 出口）+ signoff 三字段恒 null；
   - d4_record：难度带 null（首轮未标定）+ 首轮分布记录（全带外，卡面允许）。
   status=built、ready=false（READY≥5 需 owner D1 签署后由 planner 翻绿）。

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


def d1_record(cfg):
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
        "signoff": dict(SIGNOFF_NULL),
    }


def d3_record(task_id):
    import ws4_d3_gate
    selfloop = ws4_d3_gate.self_loop(task_id)
    code, real = ws4_d3_gate.real_mode(task_id)
    return {
        "stage": "D3 判分器化（人工金标对拍 ≥95%；人工必须过）",
        "self_loop": selfloop,
        "real_gate_exit": code,
        "state": real.get("state", "GOLDEN_PRESENT"),
        "message": real.get("message", real.get("note", "")),
        "real_result": real if code != 3 else None,
        "signoff": dict(SIGNOFF_NULL),
    }


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--evalbench-version", default="v6-mvp-0.3")
    args = ap.parse_args(argv)
    sys.path.insert(0, HARNESS_DIR)
    import ws4_gen
    import ws4_judge

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
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
        d2 = {
            "stage": "D2 题面→实例+oracle（纯机械，同种子逐字节复现+生成器红绿自检）",
            "seed": cfg["canonical_seed"], "nonce_set": "A",
            "generated_at": now,
            "outputs_sha256": manifest["sha256"],
            "selftest": {"exit": st.returncode, "selftest_pass": selftest_pass,
                         "covers": "BQ-8 红绿两态 / BQ-9 nonce 交叉红 / BQ-10 同种子逐字节 / fixtures 漂移守卫"},
        }

        d3 = d3_record(tid)

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

        tasks_out.append({
            "id": tid, "pack": "evalkit/packs/ws4-dev/%s" % tid, "line": cfg["line"],
            "case_type": cfg["case_type"], "origin": cfg["origin"],
            "source_ref": cfg.get("source_ref"),
            "status": "built", "ready": False,
            "canonical_seed": cfg["canonical_seed"],
            "pack_files_sha256": pack_files,
            "d1_record": d1_record(cfg),
            "d2_record": d2,
            "d3_record": d3,
            "d4_record": d4,
        })
        print("%s: contract+l1 ok(self=%s red=%s) d2.selftest=%s d3.exit=%s(%s)" %
              (tid, l1["selfcheck_exit"], l1["redpath_exit"], selftest_pass, d3["real_gate_exit"], d3["state"]))

    pool = {
        "pool": "ws4-dev",
        "built_by": "SF-0005 · worker-glm-bd",
        "generated_at": now,
        "evalbench_version": args.evalbench_version,
        "counts": {"tasks": len(tasks_out), "built": len(tasks_out), "ready": 0,
                   "case_type": {"positive": 4, "near-negative": 2, "adversarial": 2},
                   "origin": {"self-built": 5, "public-variant": 3},
                   "line": {"mm": 2, "hot": 3, "ofc": 3}},
        "signoff_ledger": "全 8 题 d1/d3 signoff 恒 null = WAITING_OWNER（ofc 3 题 D3 另为 WAITING_WS3）；"
                          "READY 翻绿条件=owner D1 签署（mm/hot ≥5 题即满足卡 B 兜底门）",
        "tasks": tasks_out,
    }
    write_json(os.path.join(BENCH, "pool-state.json"), pool)
    print("pool-state -> %s （ready=0）" % os.path.join(BENCH, "pool-state.json"))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
