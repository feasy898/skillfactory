# forms — WS9 分形态体检（MCP / agent / tooling）

旧口径（`package/healthcheck.py`，5 项）只懂 dist skill 包形态。按 `REGISTRY.md`
2026-10-08 **④裁体检形态豁免注记**的要求，本目录补齐三套分形态检查，对 v5 五件资产
补检并逐报告留档；**旧文件零改动**（只增不改），旧 5 项 skill 形态检查继续走原入口。

## 用法（与旧 healthcheck.py 并列的独立入口）

```
python v3/tools/healthcheck/healthcheck_forms.py --form mcp     --target v5/assets/zctl-mcp/package         --out <报告目录>
python v3/tools/healthcheck/healthcheck_forms.py --form agent   --target v5/assets/acceptor-agent/package     --out <报告目录>
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/hotwords/package           --out <报告目录>
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/deploy-pack/package        --out <报告目录>
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/speaker-mapping/package    --out <报告目录>
```

退出码：`0` = 报告已写出（红绿都 0，只报告不设门）；`2` = 参数缺失 / 未知形态 /
`--target` 不是目录（不写任何产物）。

## 模块清单与检查项（口径出处写死在各模块 docstring）

| 模块 | 形态 / 对象 | 检查项（顺序冻结） | 口径出处（摘要） |
|---|---|---|---|
| `forms/mcp_checks.py` | MCP server / `zctl-mcp/package` | `mcp_server_parsable` `server_info_identity` `tools_decl_match_impl` `no_mutation_exposure` `install_md_complete` | MCP 官方规范（modelcontextprotocol.io，revision 2024-11-05：JSON-RPC 2.0、initialize serverInfo、tools/list）；registry 冻结基线 `v5/assets/zctl-mcp/oracle/expected_tools.json`；上游 zctl 变更类 dry-run 须 `--yes` 纪律 |
| `forms/agent_checks.py` | agent 角色包 / `acceptor-agent/package` | `agent_md_sections` `schema_fields_exact` `example_valid` `no_promise_wording` | 子代理定义通行三段式（职责/输出契约/禁令）与 JSON Schema enum 习惯；registry 冻结基线 `v5/assets/acceptor-agent/oracle/expectations.json`；spec.md R1–R4 角色纪律 |
| `forms/tooling_checks.py` | 工具类技能 / `hotwords`、`deploy-pack`、`speaker-mapping` 的 `package/` | `cli_executable` `eval_runner_red_green` `skill_md_fields_relaxed` | skill front-matter 通行必填两要素（name/description，解析同 R4）；确定性评测红绿纪律（本仓 spec.md R6/R8：绿 0 / 红 fail-closed 1）；REGISTRY ④裁工具类放宽口径（豁免注记逐报告留档） |
| `forms/common.py` | 共享件 | — | 报告组装按 R9/R10 同构；评级 R8 同规则；摘要截断 R6 同口径 |
| `../healthcheck_forms.py` | 入口 | — | 退出码 R11 同口径（0 报告已写出 / 2 参数或目标无效） |

## 产物 schema（与 skill 形态同构 + form 字段）

`report.json`：`tool`（`healthcheck-forms.py 1.0.0 (<form> 形态)`）、`form`、`target`、
`generated_at`（唯一非确定性字段）、`summary{total,pass,fail}`、`rating`（A=0 败 / B=1 败 /
C=≥2 败）、`checks[{name,pass,detail}]`。`REPORT.md` 机器锚点行 `评级：**X**` 不变，另附
「检查口径出处」节（各模块 `CRITERIA_NOTES` 逐条落盘）。

## 自证留档（forms/out/，评级留档）

`forms/out/{zctl-mcp,acceptor-agent,hotwords,deploy-pack,speaker-mapping}/` 存五件实跑
产物（report.json + REPORT.md）。复现（仓库根 `skillfactory` 下）：

```
python v3/tools/healthcheck/healthcheck_forms.py --form mcp     --target v5/assets/zctl-mcp/package      --out v3/tools/healthcheck/forms/out/zctl-mcp
python v3/tools/healthcheck/healthcheck_forms.py --form agent   --target v5/assets/acceptor-agent/package --out v3/tools/healthcheck/forms/out/acceptor-agent
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/hotwords/package       --out v3/tools/healthcheck/forms/out/hotwords
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/deploy-pack/package    --out v3/tools/healthcheck/forms/out/deploy-pack
python v3/tools/healthcheck/healthcheck_forms.py --form tooling --target v5/assets/speaker-mapping/package --out v3/tools/healthcheck/forms/out/speaker-mapping
```

## 边界（不做的事）

- 只报告不设门：红绿都 exit 0，是否拦截由调用方决定（与旧口径一致）。
- 不做完整 YAML / JSON Schema 第三方库解析：front-matter 行级解析（R4 同口径），
  verdict schema 语义校验按基线口径内置实现，零第三方依赖、零模型调用、零网络。
- MCP stdio 探针为单次确定性调用（每 target 一次 node 子进程，不重试掩蔽）；
  环境无 node 时如实记红（MCP 形态运行时要求 Node ≥18），不降级放行。
- 旧 5 项 skill 形态检查、`oracle/`、`fixtures/`、`eval/runner.py` 一律未动。
