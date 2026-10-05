#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mm-02/checks/run_check.py — 双层判分器薄包装（L2 主判=task_outcome_*，L1 子轨只登记不判分）。

检查名契约（与 task.json expected_checks 一致）：
  - task_outcome_docx_present_opens
  - task_outcome_three_sections
  - task_outcome_entries_parseable
  - task_outcome_todo_table_header
  - task_outcome_entries_traceable_to_input
  - task_outcome_entry_owner_from_input
  - task_outcome_todo_rows_traceable
  - task_outcome_summary_selfconsistent
  - task_outcome_no_fabricated_timestamp
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PACK))), "harness")
sys.path.insert(0, HARNESS)
import ws4_judge  # noqa: E402

CHECKS = [
    "task_outcome_docx_present_opens",
    "task_outcome_three_sections",
    "task_outcome_entries_parseable",
    "task_outcome_todo_table_header",
    "task_outcome_entries_traceable_to_input",
    "task_outcome_entry_owner_from_input",
    "task_outcome_todo_rows_traceable",
    "task_outcome_summary_selfconsistent",
    "task_outcome_no_fabricated_timestamp"
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_judge.main_for(PACK, sys.argv[1:], declared=CHECKS))
