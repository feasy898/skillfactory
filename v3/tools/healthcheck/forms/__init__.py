# -*- coding: utf-8 -*-
"""forms — WS9 分形态体检检查模块包（只增不改：旧 5 项 skill 形态检查零改动）。

v3/tools/healthcheck 原有口径只懂 dist skill 包形态（spec.md §3 R2 五项：skill_md_exists →
front_matter_fields → eval_present → eval_smoke → scripts_syntax）。本包按 REGISTRY.md
2026-10-08 ④裁（体检形态豁免注记）的要求，为其余两种/三种非 skill 形态资产补齐同构的
分形态检查，三套口径均写死在各模块 docstring（国际通行/registry 出出处逐条留档）：

- mcp_checks.py     MCP server 形态（对 v5/assets/zctl-mcp/package）
- agent_checks.py   agent 角色包形态（对 v5/assets/acceptor-agent/package）
- tooling_checks.py 工具类技能形态（对 hotwords / deploy-pack / speaker-mapping 的 package/）

入口：仓库根下的 ``healthcheck_forms.py``（与旧 healthcheck.py 并列的独立脚本，
不修改旧文件任何逻辑）。产物 schema 与 skill 形态 report.json 同构（contract.md §5，
tool 字段换为 healthcheck-forms.py，另加 form 字段；评级锚点行「评级：**X**」不变）。
"""

from . import agent_checks, common, mcp_checks, tooling_checks  # noqa: F401

__all__ = ["common", "mcp_checks", "agent_checks", "tooling_checks"]
