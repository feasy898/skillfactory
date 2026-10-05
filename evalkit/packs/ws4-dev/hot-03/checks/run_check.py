#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hot-03/checks/run_check.py — 双层判分器薄包装（L2 主判=task_outcome_*，L1 子轨只登记不判分）。

检查名契约（与 task.json expected_checks 一致）：
  - task_outcome_artifacts_present
  - task_outcome_structure_selfconsistent
  - task_outcome_platform_elements_frozen
  - task_outcome_platform_shape_rules
  - task_outcome_points_filled_in_slots
  - task_outcome_placeholder_accounting
  - task_outcome_no_banned_absolute_terms
  - task_outcome_no_template_residue
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PACK))), "harness")
sys.path.insert(0, HARNESS)
import ws4_judge  # noqa: E402

CHECKS = [
    "task_outcome_artifacts_present",
    "task_outcome_structure_selfconsistent",
    "task_outcome_platform_elements_frozen",
    "task_outcome_platform_shape_rules",
    "task_outcome_points_filled_in_slots",
    "task_outcome_placeholder_accounting",
    "task_outcome_no_banned_absolute_terms",
    "task_outcome_no_template_residue"
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_judge.main_for(PACK, sys.argv[1:], declared=CHECKS))
