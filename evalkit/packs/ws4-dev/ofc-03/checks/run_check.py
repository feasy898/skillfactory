#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ofc-03/checks/run_check.py — 双层判分器薄包装（L2 主判=task_outcome_*，L1 子轨只登记不判分）。

检查名契约（与 task.json expected_checks 一致）：
  - task_outcome_docx_present_opens_safe
  - task_outcome_layout_title_centered
  - task_outcome_layout_salutation_flush
  - task_outcome_layout_body_indent
  - task_outcome_layout_signature_right
  - task_outcome_fields_selfconsistent
  - task_outcome_values_verbatim_in_docx
  - task_outcome_missing_reported_and_blank
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PACK))), "harness")
sys.path.insert(0, HARNESS)
import ws4_judge  # noqa: E402

CHECKS = [
    "task_outcome_docx_present_opens_safe",
    "task_outcome_layout_title_centered",
    "task_outcome_layout_salutation_flush",
    "task_outcome_layout_body_indent",
    "task_outcome_layout_signature_right",
    "task_outcome_fields_selfconsistent",
    "task_outcome_values_verbatim_in_docx",
    "task_outcome_missing_reported_and_blank"
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_judge.main_for(PACK, sys.argv[1:], declared=CHECKS))
