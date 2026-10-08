#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""healthcheck_forms.py — 分形态体检入口（WS9 新增；与旧 healthcheck.py 并列，不改旧逻辑）。

背景：v3/tools/healthcheck 旧口径只懂 dist skill 包形态（5 项检查，spec.md §3 R2 冻结）。
按 REGISTRY.md 2026-10-08 ④裁（体检形态豁免注记）要求，本入口补齐 MCP / agent / tooling
三套分形态检查；旧 5 项 skill 形态检查继续走 package/healthcheck.py，行为零改动。

用法（--target 为被体检的「包目录」，即各形态资产的 package/）：

    python healthcheck_forms.py --form mcp     --target <MCP 包目录>     --out <报告目录>
    python healthcheck_forms.py --form agent   --target <agent 包目录>   --out <报告目录>
    python healthcheck_forms.py --form tooling --target <工具包目录>     --out <报告目录>

形态与检查项（口径出处见各模块 docstring 与产物 REPORT.md「检查口径出处」节）：
  mcp      mcp_checks.py：mcp_server_parsable / server_info_identity / tools_decl_match_impl /
           no_mutation_exposure / install_md_complete（5 项）
  agent    agent_checks.py：agent_md_sections / schema_fields_exact / example_valid /
           no_promise_wording（4 项）
  tooling  tooling_checks.py：cli_executable / eval_runner_red_green /
           skill_md_fields_relaxed（3 项）

产物：<out>/report.json + <out>/REPORT.md（schema 与 skill 形态 R9/R10 同构，tool 字段为
healthcheck-forms.py 1.0.0 (<form> 形态)，另含 form 字段；评级锚点行「评级：**X**」不变）。
评级 = R8 同规则（失败数 0→A / 1→B / ≥2→C；skip 不计失败）。

退出码（R11 同口径）：0 = 报告已写出（红绿都 0，体检只报告不设门）；
2 = 参数缺失 / 未知形态 / --target 不是目录（此时不创建 --out、不写任何产物）。
"""

import argparse
import os
import sys

from forms import agent_checks, common, mcp_checks, tooling_checks

FORM_MODULES = {
    "mcp": mcp_checks,
    "agent": agent_checks,
    "tooling": tooling_checks,
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="healthcheck_forms.py",
        description="分形态体检（mcp / agent / tooling）；skill 形态请用 package/healthcheck.py")
    parser.add_argument("--form", required=True, choices=sorted(FORM_MODULES),
                        help="体检形态")
    parser.add_argument("--target", required=True, help="被体检的包目录（各形态资产的 package/）")
    parser.add_argument("--out", required=True, help="报告输出目录（report.json + REPORT.md）")
    args = parser.parse_args(argv)  # 缺参/未知形态 → argparse usage + exit 2

    if not os.path.isdir(args.target):
        # R1/R11 同口径：exit 2，且不得创建 --out、不得写任何产物
        print("错误：--target 不是目录: %s" % args.target, file=sys.stderr)
        return 2
    module = FORM_MODULES[args.form]

    checks = module.run_checks(args.target)
    report = common.build_form_report(
        form=module.FORM, target=args.target, checks=checks,
        advice=module.ADVICE, criteria_notes=module.CRITERIA_NOTES, out_dir=args.out)
    print(common.summary_line(report, args.out))
    return 0  # 报告已写出即 0，无论红绿


if __name__ == "__main__":
    try:  # Windows 控制台缺省 GBK，强制 UTF-8 输出（与仓内工具同口径）
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
