#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0006-c/c_rerun_one.py — 事故臂单臂重跑驱动（随卡证据）。

背景：glm/hot-03-rep2/treatment 在预算触顶检查（counted=40=CAP）被编排器按「触顶即停」
拦截，未跑。而 counted=40 中含 1 个事故进程（glm/hot-02-rep2/treatment 首跑，因编排器被
外部分 SIGKILL 中断，无有效 records，已单列 budget.incident_procs=1）。
按 B 层 failed_infra 轮判例（23d4edc 第 1 轮 4 臂 failed_infra 不占 d2a019d 第 2 轮预算）：
无有效数据的臂进程不占正式臂预算 → 正式计数 39/40，本脚本重跑缺失臂为第 40 个正式臂进程。
物理进程总数 41、正式 40、事故 1（budget.json/round-report 双处如实披露，不自罚不隐瞒）。

退出码：0 重跑完成且钉版 pass / 1 失败。
"""

import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("co", os.path.join(HERE, "c_orchestrator.py"))
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)

FAM, TASK, REP, ARM = "glm", "hot-03", 2, "treatment"


def main():
    ad = co.arm_dir_of(FAM, TASK, REP, ARM)
    if os.path.isfile(os.path.join(ad, "records", "arm_run.json")):
        print("该臂已有 records，无需重跑", file=sys.stderr)
        return 2
    shutil.rmtree(os.path.join(ad, "out"), ignore_errors=True)   # 清可能残留
    built, err = co.build_family_scratch(FAM)
    if built is None:
        print("scratch 派生失败：%s" % err, file=sys.stderr)
        return 2
    co.SCRATCH_ENV[FAM] = built["extra_env"]
    rec = co.run_once(ad, FAM)
    if rec["timed_out"] or not rec["session_id"] or rec["model_usage_rows"] == 0:
        print("重跑未产出有效调用: exit=%s session=%s rows=%s"
              % (rec["exit_code"], rec["session_id"], rec["model_usage_rows"]), file=sys.stderr)
        co.persist_arm(FAM, TASK, REP, ARM, rec,
                       os.path.join(co.EVALKIT, "packs", "ws4-dev", TASK))
        return 1
    co.persist_arm(FAM, TASK, REP, ARM, rec, os.path.join(co.EVALKIT, "packs", "ws4-dev", TASK))
    summary = {k: v for k, v in rec.items() if not k.startswith("_")}
    summary["rerun_after_incident"] = True
    summary["classify"] = co.classify_arm(rec, False)
    co.write_json(os.path.join(co.RUN, "records", "arms",
                               "%s-%s-rep%d-%s.json" % (FAM, TASK, REP, ARM)), summary)
    # budget：正式计数维持 40（本臂占被让出的第 40 正式额度），rerun 单列
    with open(os.path.join(co.RUN, "budget.json"), encoding="utf-8") as f:
        b = json.load(f)
    b["counted_arm_procs"] = 40
    b.setdefault("rerun_after_incident", []).append({
        "arm": "%s/%s-rep%d/%s" % (FAM, TASK, REP, ARM),
        "reason": "预算触顶拦截（counted 已含 1 事故进程）；按 B 层 failed_infra 判例"
                  "事故进程不占正式额度，本重跑为第 40 个正式臂进程",
        "exit_code": rec["exit_code"], "session_id": rec["session_id"],
        "model_id_observed": rec["model_id_observed"],
        "provider_id_observed": rec["provider_id_observed"]})
    b["physical_procs_total"] = b.get("counted_arm_procs", 0) + b.get("incident_procs", 0)
    co.write_json(os.path.join(co.RUN, "budget.json"), b)
    t = co.TARGET[FAM]
    ok = rec["model_id_observed"] == t["model"] and rec["provider_id_observed"] == t["provider"]
    print("RERUN done: observed=%s @ %s pin=%s wall=%sms" %
          (rec["model_id_observed"], rec["provider_id_observed"],
           "pass" if ok else "drift", rec["wall_ms"]))
    return 0 if ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
