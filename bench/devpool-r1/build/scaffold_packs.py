#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bench/devpool-r1/build/scaffold_packs.py — WS4 dev 题池 8 包静态脚手架（SF-0005）。

产出（幂等）：
- evalkit/packs/ws4-dev/<pkg>/task.json          任务卡配置（judge/gen 双方共读）
- evalkit/packs/ws4-dev/<pkg>/gen_oracle.py      生成器薄包装 → harness/ws4_gen.py
- evalkit/packs/ws4-dev/<pkg>/checks/run_check.py 判分器薄包装 → harness/ws4_judge.py
- out/ transcript/ records/ 空目录（EI-20 六件齐之一）
brief.md / rubric.md / fixtures/ 由 worker 手写/生成（不经本脚本）。

用法：python scaffold_packs.py
"""

import io
import json
import os

EVALKIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "evalkit")
WS4 = os.path.join(EVALKIT, "packs", "ws4-dev")

MM_CHECKS = [
    "task_outcome_docx_present_opens",
    "task_outcome_three_sections",
    "task_outcome_entries_parseable",
    "task_outcome_todo_table_header",
    "task_outcome_entries_traceable_to_input",
    "task_outcome_entry_owner_from_input",
    "task_outcome_todo_rows_traceable",
    "task_outcome_summary_selfconsistent",
]
MM_CHECKS_DIRTY = MM_CHECKS + ["task_outcome_no_fabricated_timestamp"]
HOT_CHECKS = [
    "task_outcome_artifacts_present",
    "task_outcome_structure_selfconsistent",
    "task_outcome_platform_elements_frozen",
    "task_outcome_platform_shape_rules",
    "task_outcome_points_filled_in_slots",
    "task_outcome_placeholder_accounting",
    "task_outcome_no_banned_absolute_terms",
    "task_outcome_no_template_residue",
]
OFC_CHECKS = [
    "task_outcome_docx_present_opens_safe",
    "task_outcome_layout_title_centered",
    "task_outcome_layout_body_indent",
    "task_outcome_layout_signature_right",
    "task_outcome_fields_selfconsistent",
    "task_outcome_values_verbatim_in_docx",
    "task_outcome_missing_reported_and_blank",
]
OFC_CHECKS_SALUT = OFC_CHECKS[:2] + ["task_outcome_layout_salutation_flush"] + OFC_CHECKS[2:]

TASKS = {
    "mm-01": {"line": "mm", "case_type": "positive", "origin": "self-built", "source_ref": None,
              "canonical_seed": 4201, "expected_checks": MM_CHECKS},
    "mm-02": {"line": "mm", "case_type": "near-negative", "origin": "public-variant",
              "source_ref": "公开规范条目：《党政机关公文处理工作条例》（中办发〔2012〕14号，公开发布）"
                            "「纪要」文种定义 + GB/T 9704-2012《党政机关公文格式》（国家标准全文公开系统 "
                            "openstd.samr.gov.cn，条目号 GB/T 9704-2012）；题面内容 100% 自写，"
                            "实体全部 nonce 化改写，零原文复制",
              "canonical_seed": 4202, "no_timestamp_input": True, "expected_checks": MM_CHECKS_DIRTY},
    "hot-01": {"line": "hot", "case_type": "positive", "origin": "public-variant",
               "source_ref": "公开规范页：抖音创作者服务中心公开规范（creator.douyin.com，社区公约/内容规范）"
                             "+《中华人民共和国广告法》第九条绝对化用语条款（公开法条）；"
                             "题面/卖点全部自写+nonce 改写，零原文复制",
               "canonical_seed": 4203, "platform": "dy", "expected_checks": HOT_CHECKS},
    "hot-02": {"line": "hot", "case_type": "positive", "origin": "self-built", "source_ref": None,
               "canonical_seed": 4204, "platform": "xhs", "expected_checks": HOT_CHECKS},
    "hot-03": {"line": "hot", "case_type": "near-negative", "origin": "self-built", "source_ref": None,
               "canonical_seed": 4205, "platform": "wx", "expected_checks": HOT_CHECKS},
    "ofc-01": {"line": "ofc", "case_type": "positive", "origin": "self-built", "source_ref": None,
               "canonical_seed": 4206, "template": "周报", "expected_checks": OFC_CHECKS},
    "ofc-02": {"line": "ofc", "case_type": "adversarial", "origin": "public-variant",
               "source_ref": "公开国标：GB/T 9704-2012《党政机关公文格式》（国家标准全文公开系统 "
                             "openstd.samr.gov.cn，条目号 GB/T 9704-2012）——标题居中/称谓顶格/正文缩进/"
                             "落款右对齐版式判据源自公开国标与公文通行版式；题面内容自写+nonce 化",
               "canonical_seed": 4207, "template": "请示函", "expected_checks": OFC_CHECKS_SALUT},
    "ofc-03": {"line": "ofc", "case_type": "adversarial", "origin": "self-built", "source_ref": None,
               "canonical_seed": 4208, "template": "会议通知", "expected_checks": OFC_CHECKS_SALUT},
}

GEN_WRAPPER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""%(pkg)s/gen_oracle.py — 生成器薄包装 → harness/ws4_gen.py（判分逻辑零副本）。

用法：
    python gen_oracle.py [--seed N] [--nonce-set A|B] --out <dir>   生成实例+oracle
    python gen_oracle.py --selftest                                 BQ-8/9/10 三合一自检
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "harness")
sys.path.insert(0, HARNESS)
import ws4_gen  # noqa: E402

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_gen.main(os.path.basename(HERE), sys.argv[1:]))
'''

CHECK_WRAPPER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""%(pkg)s/checks/run_check.py — 双层判分器薄包装（L2 主判=task_outcome_*，L1 子轨只登记不判分）。

检查名契约（与 task.json expected_checks 一致）：
%(checks_block)s
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PACK))), "harness")
sys.path.insert(0, HARNESS)
import ws4_judge  # noqa: E402

CHECKS = %(checks_literal)s

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_judge.main_for(PACK, sys.argv[1:], declared=CHECKS))
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    for pkg, cfg in sorted(TASKS.items()):
        root = os.path.join(WS4, pkg)
        cfg = dict(cfg)
        cfg["id"] = pkg
        write(os.path.join(root, "task.json"), json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        write(os.path.join(root, "gen_oracle.py"), GEN_WRAPPER % {"pkg": pkg})
        checks = cfg["expected_checks"]
        block = "\n".join("  - %s" % c for c in checks)
        write(os.path.join(root, "checks", "run_check.py"),
              CHECK_WRAPPER % {"pkg": pkg, "checks_block": block,
                               "checks_literal": json.dumps(checks, ensure_ascii=False, indent=4)})
        for d in ("out", "transcript", "records", "fixtures"):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        print("scaffolded %s (%s/%s)" % (pkg, cfg["line"], cfg["case_type"]))


if __name__ == "__main__":
    main()
