# MCP 形态体检报告（分形态 Healthcheck）

- 目标包：`/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/zctl-mcp/package`
- 生成时间：2026-10-08T11:23:21+0800（healthcheck-forms.py 1.0.0 (mcp 形态)）
- 评级：**A**（A=0 失败 / B=1 失败 / C=≥2 失败）
- 汇总：5 项检查，5 通过 / 0 失败

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| mcp_server_parsable | ✅ PASS | mcp-server.mjs 通过 node --check 语法解析（node v22.16.0） |
| server_info_identity | ✅ PASS | initialize 实测 serverInfo name=zctl-mcp version=1.0.0 protocolVersion=2024-11-05 与冻结基线一致 |
| tools_decl_match_impl | ✅ PASS | 三方一致：4 个工具 ['zctl_reset_status', 'zctl_offpeak_availability', 'zctl_offpeak_status', 'zctl_help']（tools/list 实测 = 源码 TOOLS 声明 = 冻结基线，required/描述关键词逐项过，分派分支齐备） |
| no_mutation_exposure | ✅ PASS | 暴露面干净：4 个工具全部只读声明、无禁暴露工具名、源码无变更类 zctl 接线（核对口径：冻结基线 forbidden_tool_names=['zctl_reset_use', 'zctl_offpeak_take', 'zctl_offpeak_settle']；模式 zctl 变更类接线 "reset","use"/zctl 变更类接线 "offpeak","take"/zctl 变更类接线 "settle"/独立参数元素 "--yes"（变更确认旗标）） |
| install_md_complete | ✅ PASS | INSTALL.md 四要素齐备：Node 版本要求 / mcpServers 配置片段 / eval/runner.py 自检入口 / 变更类安全说明 |

## 检查口径出处

- MCP 官方规范 modelcontextprotocol.io（revision 2024-11-05）：JSON-RPC 2.0 换行分隔、initialize 应答 serverInfo{name,version}、tools/list、tools/call 错误码 -32602/-32601/-32700。
- registry 冻结基线：v5/assets/zctl-mcp/oracle/expected_tools.json（serverInfo / 4 只读工具 / inputSchema_required / description_contains / forbidden_tool_names）。
- 安全口径：上游 zctl 纪律——变更类命令默认 dry-run 须 --yes；MCP 侧不提供变更类入口（v5/assets/zctl-mcp/spec.md R1、package/INSTALL.md 安全说明）。

## 建议

评级 A：无失败项，mcp 形态口径全绿。
