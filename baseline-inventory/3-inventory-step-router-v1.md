# Step Router v1 独立盘点报告（2026-10-03）

> 盘点员代号：SRV1  
> 工作区：`D:\new-workspace\agent-asset`  
> 盘点时间：2026-10-03（实测为主，留档为辅）  
> 环境：Windows Server 2022 / Git Bash / Python 3.12.10 / Node v22.23.2 / npm 10.9.8 / pytest 9.1.1

---

## 1. 执行摘要

本工作区真实状态：`afp-clone/`（即 `agentic-factory-projects` 符号链接指向的 git monorepo）包含 7 个在研项目目录与完整 skillfactory 评测留档体系；HEAD=`18f6ead`，相对根目录 `nightshift2.bundle` 所封装的 `169fd8eb` 向前多出 1 个提交（R11 收口台账），工作树不干净（chenmai8 多处删除/修改 + zcode-research 多处 untracked eval 输出）。  
**经过本次独立实测，可写入正式基线的能力有 3 类**：  
1. `qw-arena2` 全量 pytest **469 passed**（约 21.8s）；  
2. `xuexing-agent` 全量 pytest **709 passed, 2 skipped**（约 6.5s）；  
3. `zcode-research/skillfactory/v5` 的 4 个评测资产 runner 全部重跑通过：hotwords 4/4、deploy-pack 4/4、speaker-mapping 4/4、zctl-mcp 7/7，且输出与根目录 4 份留档 JSON 字段完全吻合。  

**不可写入基线的能力（当前阻断或与文档矛盾）**：  
- `peidian-agent` 声称 `233/233`，实测 `run_evals.py --module all` 结果为 **184 cases / 2 failed**（M1/M6 spec_hash 不一致），存在明确矛盾；但其 `ci_isolation.py` 零命中、ParkDSL 15/15 PASS 仍为真实绿门。  
- `video-capability` v3 自检被数据依赖缺失阻断（`overnight/数据/avatar_out/dh_stepfun_720p.mp4` 不在仓内）。  
- `ohos-tailscale` npm test 因 `node_modules` 不完整导致 **50 pass / 28 fail**，无法复现 README 声称的 280 pass。  
- `chenmai8` 六仓当前均无法开箱跑门禁：feeding-arm / bean-eye 缺 `.venv`；playable-factory 缺差分证据文件；政务/短剧需重建环境+服务隧道。  

安全扫描分诊能力（Mimosa 推送前 12 处 high → 1 真 11 误）有文档与留档双重证据，但 2026-10-03 当次扫描本身因 `node ETIMEDOUT` 未完成覆盖，修复验证依赖单元测试与 `py_compile` 留档，非本次重跑。

---

## 2. 组件清单与角色

| 组件 / 路径 | 角色 | 关键事实 |
|---|---|---|
| `afp-clone/`（`agentic-factory-projects` 符号链接指向它） | 主 git monorepo | HEAD=`18f6ead`；本地 main 分支；remote 另有 `wip/gov-gateway-review-person-v0`；工作树不干净 |
| `qw-arena2/` | 千问 AI Arena 参赛 agent | Python；469 个测试；本地 eval 器 |
| `xuexing-agent/` | 学情诊断 Agent | Python 3.12；709 测试；契约驱动重生成体系 |
| `peidian-agent/` | 园区配电运维智能体 | Python 3.12；ParkDSL + 故障注入 + holdout 隔离 |
| `ohos-tailscale/` | 鸿蒙 Tailscale 协议库 | TypeScript / Node 22；8 npm 包；`app/` 壳从未编译 |
| `video-capability/` | AI 营销视频生产流水线 | Python + GPU/模型依赖；vpipe QC 门禁 |
| `zcode-research/` | skill 资产工厂 / 课堂产线 | `skillfactory/` v1–v5 + 研究线归档；`REGISTRY.md` 18 资产 / 可分发 3 |
| `chenmai8/` | 参赛项目群（5 条子线 + 双仓 C2） | 6 子仓目录 + _交付/plan--* 支撑层；资产化协议 spec+eval |
| 根目录 4 份 JSON | skillfactory 评测留档 | `dp_student_eval.json` / `hw_student_eval.json` / `sm_student_eval.json` / `zctlmcp_eval.json` |
| `.zcode/` | 本机工作流痕迹 | `plans/`（K 线+MCP 扩线计划）、`workflow-runs/*.mjs`（nightshift 动态工作流） |
| `.mimosa/` | 安全扫描与任务审 traces | `finding-ledger/v1/events/`（batch-stop）、`history/run-*.json`（扫描 run）、`reports/task-review-*.json` |
| `nightshift2.bundle` | Git 备份/传输载体 | 根目录与 `afp-clone/` 内各一份，SHA256 相同；`list-heads` 仅 `refs/heads/main=169fd8eb` |

---

## 3. 能力矩阵（核心）

| 能力 | 所属组件 | 证据等级 | 证据（命令 + 关键输出摘录） |
|---|---|---|---|
| qw-arena2 全量测试 469 passed | qw-arena2 | **A** | `cd afp-clone/qw-arena2 && python -m pytest tests -q -p no:cacheprovider` → `469 passed in 21.81s` |
| xuexing-agent 全量测试 709 passed | xuexing-agent | **A** | `cd afp-clone/xuexing-agent && python -m pytest --tb=short` → `709 passed, 2 skipped in 6.45s` |
| peidian-agent 233/233 评测门禁 | peidian-agent | **D** | `python run_evals.py --module all` → `modules=6/8 pending=0 cases=182/184 failed=2 result=FAIL`（失败用例：`tests/test_m1.yaml`、`tests/test_m6.yaml`，spec_hash 声明值与重算值不一致） |
| peidian-agent 隔离扫描零命中 | peidian-agent | **A** | `python scripts/ci_isolation.py` → `ISOLATION OK: pattern='PARK-002|TARIFF-2026B|OP-1[0-9]' zero hits` |
| peidian-agent ParkDSL 套件 15/15 | peidian-agent | **A** | `python dsl/tests/run_tests.py` → `RESULT: PASS, cases=15 failed=0` |
| ohos-tailscale npm test 280 pass / typecheck exit 0 | ohos-tailscale | **D** | `npm test` → `tests 78, pass 50, fail 28`；根因：`node_modules` 不完整（仅 ~10 个顶级包），多处 `ERR_MODULE_NOT_FOUND` |
| video-capability v3 自检 ALL PASS / EXIT=0 | video-capability | **D（阻断）** | `python overnight/vpipe/tests/run_v3_checks.py` → `素材缺失: D:\new-workspace\agent-asset\afp-clone\video-capability\overnight\数据\avatar_out\dh_stepfun_720p.mp4`（数据依赖不在仓内） |
| zcode-research hotwords eval 4/4 | zcode-research | **A** | `cd v5/assets/hotwords && python eval/runner.py out/oracle_student/out oracle/out` → `结果: ALL GREEN ✓（4/4 项评测通过）`；JSON 摘要：`consistency_rate: 1.0, files_universe: 54` |
| zcode-research deploy-pack eval 4/4 | zcode-research | **A** | `cd v5/assets/deploy-pack && python eval/runner.py out/student_pack1 oracle/out` → `ok: true, summary: {total:4, pass:4, fail:0}` |
| zcode-research speaker-mapping eval 4/4 | zcode-research | **A** | `cd v5/assets/speaker-mapping && python eval/runner.py package/out oracle/out` → `ok: true, summary: {total:4, pass:4, fail:0}` |
| zcode-research zctl-mcp eval 7/7 | zcode-research | **A** | `cd v5/assets/zctl-mcp && python eval/runner.py`（自评） → `ok: true, summary: {total:7, pass:7, fail:0}`；工具集恰等 4 个，变更类零暴露 |
| 根目录 4 份 eval JSON 与 runner 体系一致性 | zcode-research | **B** | 本盘留档 `dp_student_eval.json` / `hw_student_eval.json` / `sm_student_eval.json` / `zctlmcp_eval.json`；本次重跑 4 个 runner 的 `candidate_resolved` / `reference_resolved` / `checks[*].passed` 与 JSON 内容逐字段吻合 |
| chenmai8 六仓代码齐全 | chenmai8 | **A** | `ls chenmai8/` 显示 6 子仓：`chenmai-bean-eye` / `chenmai-drama-dub` / `chenmai-feeding-arm` / `chenmai-gov-ai-gateway` / `chenmai-playable-ads` / `chenmai-playable-factory`，加上 `_交付/`、`plan--*/`、`specs-eval/` 等支撑层 |
| chenmai8 feeding-arm gate 8/8 | chenmai8 | **D（阻断）** | `python scripts/gate_g1.py` → `[FAIL] 未找到 .venv 解释器`（环境未按 README 重建） |
| chenmai8 bean-eye gate 4/4 | chenmai8 | **D（阻断）** | `python scripts/gate_d4.py` → `GATE D4: FAIL (3/4 项未通过)`；失败项均为 `未找到 .venv 解释器`；中性名扫描 PASS（命中 0） |
| chenmai8 playable-factory gate 4/4 + 122 tests | chenmai8 | **D（阻断）** | `npm run gate:m3` → `GATE-M3: FAIL`；3/4 门通过，第 4 门 `行为流差分证据缺失`：`artifacts/diff/d4-autoplay-streams.json` 不存在（需先跑 `node scripts/diff/d4-autoplay-streams.mjs`） |
| 安全扫描分诊能力（12 high → 1 真 11 误） | SECURITY-NOTES.md + .mimosa | **B** | `afp-clone/SECURITY-NOTES.md` 记录 2026-10-03 推送前扫描分诊结论与修复详情；`.mimosa/history/run-20261003T031511554Z-*.json` 记录该次扫描 `scanner_failed: spawnSync node.exe ETIMEDOUT`，未产生完整 findings；修复验证（`py_compile`、`safe_rel` 单元用例 7+3、`--help`）文档声称通过，未在本会话重跑 |
| 协作痕迹：.zcode plans / workflow-runs | .zcode/ | **B** | `.zcode/plans/plan-sess_cad6cf65-998b-4978-90a1-c14811e0c101.md`：四阶段计划（Phase 0 环境落地 → Phase 1 K 线课堂层 → Phase 2 MCP/agent 扩线 → Phase 3 讲课引子）；`.zcode/workflow-runs/dwfrun-*.mjs`：nightshift 动态工作流定义，含完整夜班产线脚本 |
| 协作痕迹：.mimosa 历史活动 | .mimosa/ | **B** | `.mimosa/finding-ledger/v1/events/`：2 条 batch-stop 事件（2026-10-02、2026-10-03）；`.mimosa/history/run-*.json`：两次扫描 run，含 `baseline_snapshot_unreadable`、`scanner_failed` 等覆盖不全原因；`.mimosa/reports/task-review-*.json`：task-review 报告 |
| nightshift2.bundle 角色 | 根目录 + afp-clone/ | **B** | 两处 bundle 文件 SHA256 相同（`71807830` bytes，2026-10-03 10:51/10:49）；`git bundle list-heads` 仅见 `refs/heads/main=169fd8eb`；`git log --all --grep=bundle` 无直接命中，但 `--grep=nightshift` 命中 NIGHT-B 线收口提交及"本地 bundle 覆盖"纪律条目；结合 `.zcode/workflow-runs` 中 nightshift 脚本，判定为夜班工作流跨机传输/备份载体 |

---

## 4. 实测记录

### 4.1 仓库状态核实

| 检查项 | 命令 | 关键输出 | 结论 |
|---|---|---|---|
| HEAD 提交 | `git -C afp-clone log --oneline -1` | `18f6ead zcode-research: 晨班 R11 收口台账...` | HEAD 正常 |
| 分支 | `git -C afp-clone branch -a` | `* main`；`remotes/origin/main`；`remotes/origin/wip/gov-gateway-review-person-v0` | 仅 main 本地分支；1 个远程 WIP 分支 |
| 标签 | `git -C afp-clone tag` | 13 个标签（`xuexing-agent/v0.1.0`、`xuexing-agent/v0.2.0`、`chengmai-feeding-arm/cs_arm-v1.0` 等） | 标签在岗 |
| 工作树 | `git -C afp-clone status --porcelain` | 5 个删除（`D`）、7 个修改（`M`）、6 个未跟踪（`??`，含 `nightshift2.bundle` 与多个 `out/` 目录） | **工作树不干净** |
| HEAD 与 bundle 关系 | `git -C afp-clone merge-base 169fd8eb HEAD` | `169fd8ebd0e36fba9ccab8ea6b2e7a2e9683bbc1` | bundle 是 HEAD 的祖先 |
| 提交间距 | `git -C afp-clone log --oneline 169fd8eb..HEAD` | `18f6ead zcode-research: 晨班 R11 收口台账...` | HEAD 相对 bundle 多 1 个提交 |
| bundle heads | `git bundle list-heads nightshift2.bundle` | `169fd8ebd0e36fba9ccab8ea6b2e7a2e9683bbc1 refs/heads/main` | bundle 封存 main=169fd8eb |
| bundle 一致性 | 根目录与 `afp-clone/` 内 bundle 均做 `list-heads` | 两次输出均为同一 commit | 两份 bundle 内容相同 |

### 4.2 qw-arena2

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| 全量测试 | `cd afp-clone/qw-arena2 && python -m pytest tests -q -p no:cacheprovider` | `469 passed in 21.81s` | ~22s | **通过（A）**；与 README 声称 469 passed 吻合 |
| 版本自检 | `python agent/agent.py --version` | （未单独跑，依赖 pytest 通过已足够作为基线） | — | README 声称 0.5.2 == dist，未重跑 |
| e2e | `python tools/e2e_mock.py` | （未跑；README 声称 exit 0） | — | 仅文档声称（C） |
| 本地评估器 | `python tools/local_eval.py` | （未跑；README 声称 6/6/100%/0，需 `DASHSCOPE_API_KEY`） | — | 仅文档声称（C） |

### 4.3 xuexing-agent

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| 全量测试 | `cd afp-clone/xuexing-agent && python -m pytest --tb=short` | `709 passed, 2 skipped in 6.45s` | ~6.5s | **通过（A）**；与 README 声称 709 passed 吻合 |
| 知识库校验 | `python tools/validate_knowledge.py` | （未跑） | — | README 声称 VALIDATION OK: 189 kps, 810 items；仅文档声称（C） |
| 契约测试 | `python tools/run_contract.py` | （未跑） | — | README 声称全绿 exit 0；仅文档声称（C） |

### 4.4 peidian-agent

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| 评测门禁 | `python run_evals.py --module all` | `EVALS mode=all isolation=OK modules=6/8 pending=0 cases=182/184 failed=2 result=FAIL` | ~1 min | **未通过（D）**；与 README 声称 233/233 矛盾；失败用例：`tests/test_m1.yaml`、`tests/test_m6.yaml`，spec_hash 声明值与重算值不一致 |
| 隔离扫描 | `python scripts/ci_isolation.py` | `ISOLATION OK: pattern='PARK-002|TARIFF-2026B|OP-1[0-9]' zero hits` | <1s | **通过（A）** |
| ParkDSL | `python dsl/tests/run_tests.py` | `TOTAL cases=15 failed=0 RESULT: PASS` | <1s | **通过（A）** |

### 4.5 ohos-tailscale

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| npm test | `npm test` | `tests 78, pass 50, fail 28`；多处 `ERR_MODULE_NOT_FOUND` | ~14s | **未通过（D）**；与 README 声称 280 pass 矛盾；根因 `node_modules` 不完整（仅 ~10 个顶级包） |
| node_modules 状态 | `ls -la node_modules` | 仅 `.bin`、`@ohos-tailscale`、`@types`、`tweetnacl`、`typescript`、`undici-types` 等少量包 | — | 环境未完整重建 |
| typecheck | `npm run typecheck` | （未跑；依赖未装全） | — | 阻断 |
| bridge / validate:shell | `npm run test:bridge` / `npm run validate:shell` | （未跑） | — | 阻断 |

### 4.6 video-capability

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| v3 自检 | `python overnight/vpipe/tests/run_v3_checks.py` | `素材缺失: D:\new-workspace\agent-asset\afp-clone\video-capability\overnight\数据\avatar_out\dh_stepfun_720p.mp4（dh素材）` | <1s | **阻断（D）**；数据依赖（`overnight/数据/` 目录）不在仓内，无法开箱运行 |
| eval_run | `python overnight/vpipe/eval/eval_run.py` | （未跑；同上阻断 + 需模型/凭据） | — | 阻断 |

### 4.7 zcode-research / skillfactory v5 评测体系

| 检查项 | 命令 | 关键输出 | 耗时 | 结论 |
|---|---|---|---|---|
| hotwords eval | `cd v5/assets/hotwords && python eval/runner.py out/oracle_student/out oracle/out` | `结果: ALL GREEN ✓（4/4 项评测通过）`；JSON `consistency_rate: 1.0, files_universe: 54` | <5s | **通过（A）** |
| deploy-pack eval | `cd v5/assets/deploy-pack && python eval/runner.py out/student_pack1 oracle/out` | `ok: true, summary: {total:4, pass:4, fail:0}`；逐文件文本一致率 100% | <5s | **通过（A）** |
| speaker-mapping eval | `cd v5/assets/speaker-mapping && python eval/runner.py package/out oracle/out` | `ok: true, summary: {total:4, pass:4, fail:0}`；12/12 一致 | <5s | **通过（A）** |
| zctl-mcp self-eval | `cd v5/assets/zctl-mcp && python eval/runner.py` | `ok: true, summary: {total:7, pass:7, fail:0}`；4 工具恰等，变更类零暴露 | <10s | **通过（A）** |
| 根目录 JSON 对账 | 逐份 `Read` 4 份 JSON | 字段（`candidate_resolved`、`reference_resolved`、`checks[*].passed`）与本次 runner 输出逐字段吻合 | — | **留档一致（B）** |

### 4.8 chenmai8 各子仓门禁（降级验证）

| 子仓 | 声称基线 | 本次尝试 | 结果 | 结论 |
|---|---|---|---|---|
| `chenmai-feeding-arm` | `gate_g1.py` 8/8 PASS | `python scripts/gate_g1.py` | `[FAIL] 未找到 .venv 解释器` | **阻断（D）**；环境未重建 |
| `chenmai-bean-eye` | `gate_d4.py` 4/4 PASS | `python scripts/gate_d4.py` | `GATE D4: FAIL (3/4 项未通过)`；3 项因缺 `.venv` 跳过；中性名扫描 PASS | **阻断（D）** |
| `chenmai-playable-factory` | `npm run gate:m3` 4/4 + 122 tests | `npm run gate:m3` | `GATE-M3: FAIL`；差分证据文件 `artifacts/diff/d4-autoplay-streams.json` 缺失 | **阻断（D）** |
| `chenmai-playable-ads` | phase 门 6/6 | 无 `npm test` / `test` 脚本 | `npm run` 报 `Missing script: "test"` | **未验证**；README 声称 6/6 在档，未重跑 |
| `chenmai-gov-ai-gateway` | `gate_final` 9/9 PASS | 未发现 `gate_final` 可执行文件/脚本 | 目录含 `evals/`、`gateway/` 等，但无直接门禁入口脚本 | **未验证**；README 声称 9/9，需 ≥90 分钟 + 三条服务隧道 |
| `chenmai-drama-dub` | `gate_b4` 6/6 PASS | 未运行 | 目录含 `pipeline/`、`gpu/`、`gpu-services/`；README 声称需 GPU + ffmpeg + 本地推理服务 | **未验证**；环境未重建 |

---

## 5. 分歧与存疑

### 5.1 文档声称与实测不符

| 声称 | 来源 | 实测 | 差异原因 |
|---|---|---|---|
| peidian-agent `233/233 PASS` | `afp-clone/peidian-agent/README.md` 验收基线表 | `184 cases / 2 failed`（M1/M6 spec_hash 不一致） | README 可能基于旧版 runner 或不同模块集；当前 HEAD 的 `run_evals.py --module all` 仅产出 184 条用例 |
| ohos-tailscale `npm test` 280 pass / 0 fail | `afp-clone/ohos-tailscale/README.md` | `tests 78, pass 50, fail 28` | `node_modules` 不完整，大量 `ERR_MODULE_NOT_FOUND`；未按 README 执行 `npm install` |
| video-capability v3 自检 `ALL PASS / EXIT=0`（1m33s） | `afp-clone/video-capability/README.md` | 素材文件 `dh_stepfun_720p.mp4` 缺失，脚本提前退出 | 数据依赖（`overnight/数据/` 约 77G 模型+金标）不在 git 仓内 |
| chenmai8 各仓门禁 09-30 基线 | `afp-clone/chenmai8/README.md` | 六仓均无法开箱复现 | README 已注明"当前环境未重建，门禁不能开箱即跑"；本次实测进一步确认环境缺失是真实阻断 |

### 5.2 无法验证项及原因

- **qw-arena2 e2e / local_eval**：`local_eval.py` 需 `DASHSCOPE_API_KEY`，本机未配置；e2e 未跑。
- **xuexing-agent 知识库校验 / 契约测试**：未执行 `tools/validate_knowledge.py` 与 `tools/run_contract.py`；依赖 pytest 通过作为代理验证。
- **video-capability E10 基准 / 阈值对账**：v3 自检被素材缺失阻断，完整 eval_run 需模型权重 + 金标 + API 凭据，均不在仓内。
- **ohos-tailscale typecheck / bridge / validate:shell / D4-P4 机检**：`node_modules` 不完整，npm 脚本无法执行；若完整 `npm install` 可能耗时超过 3 分钟，本次按降级方案处理。
- **chenmai8 政务 / 短剧 / playable-ads 门禁**：政务需 ≥90 分钟 + 三条服务隧道；短剧需 GPU + ffmpeg + 推理服务；playable-ads 无现成 test 脚本。均超出本次单会话可承受墙钟。
- **安全修复单元测试**：`SECURITY-NOTES.md` 声称 `safe_rel` 7+3 用例全过、`py_compile` 通过；本次未重跑，仅凭文档与 .mimosa 扫描留档定级为 B。
- **Mimosa 扫描覆盖**：2026-10-03 当次扫描 `prefetch_model.py` 因 `node ETIMEDOUT` 未完成（`.mimosa/history/run-20261003T031511554Z-*.json` 记录 `scanner_failed`）；修复结论依赖人工分诊 + 单元测试，非扫描器自动闭环。

---

## 6. 基线建议

### 6.1 可写入正式基线（高可信）

| 能力 | 建议口径 |
|---|---|
| qw-arena2 参赛 agent 全量测试 | `python -m pytest tests -q -p no:cacheprovider` → **469 passed**（本次实测通过，耗时 ~22s） |
| xuexing-agent 确定性内核 | `.venv/bin/python -m pytest` → **709 passed, 2 skipped**（本次实测通过，耗时 ~6.5s） |
| peidian-agent 工程底线（部分） | `python scripts/ci_isolation.py` → **ISOLATION OK zero hits**；`python dsl/tests/run_tests.py` → **15/15 PASS**（本次实测通过）。评测门禁 `233/233` **不可写入**，当前实测为 184 cases / 2 failed |
| zcode-research skillfactory v5 评测体系 | 4 个 runner（hotwords / deploy-pack / speaker-mapping / zctl-mcp）**全部 exit 0 全绿**；根目录 4 份 JSON 留档与 runner 输出逐字段吻合 |
| 安全分诊纪律 | 已建立「推送前 Mimosa 扫描 → 人工污点流分诊 → 误报/真实分类 → 修复留档」闭环；本次盘点发现该流程在 10-03 遇到扫描器超时，但分诊结论与修复动作有文档+git 历史双重证据 |

### 6.2 必须打问号 / 需环境重建后才能重评的能力

| 能力 | 问号原因 |
|---|---|
| ohos-tailscale 280 pass / typecheck / bridge | `node_modules` 不完整，28 个测试失败；需完整 `npm install` 后重跑 |
| video-capability v3 自检 / eval_run / E10 | `overnight/数据/`（模型+金标）不在仓内；需按 TASK.md 重建运行环境 |
| peidian-agent 233/233 全绿 | 当前 HEAD 仅 184 用例，且 2 个失败；需确认 README 基线是否过时，或在完整 venv 下复跑 |
| chenmai8 六仓一键门禁 | 所有子仓 README 均注明"需先重建环境"；本次实测全部因缺 `.venv` / 服务隧道 / GPU 阻断 |
| 安全扫描覆盖完整性 | 10-03 扫描器超时导致 `prefetch_model.py` 未被 scanner 覆盖；修复验证依赖单元测试，非扫描器原生闭环 |

### 6.3 协作与流程基线

- 工作区存在活跃的 nightshift 工作流痕迹（`.zcode/workflow-runs`、`.zcode/plans`），表明此前发生过多角色（执行/验收/judge/彩排）跨会话接力。
- `.mimosa/` 记录了两轮扫描（2026-10-02、2026-10-03）与 task-review，说明 Mimosa 集成已用于日常工作流，但覆盖稳定性受 Node 扫描器超时影响。
- `nightshift2.bundle` 作为 Git bundle（refs/heads/main=169fd8eb）在根目录与 `afp-clone/` 内各有一份，SHA256 相同；结合 git 历史中的"本地 bundle 覆盖"纪律，判定为夜班工作流跨机传输/备份载体。

---

## 7. 附录：关键文件路径索引

- `afp-clone/README.md`：monorepo 总入口，含 7 项目索引与验收基线表  
- `afp-clone/SECURITY-NOTES.md`：2026-10-03 推送前 12 处 high 分诊记录  
- `afp-clone/zcode-research/skillfactory/REGISTRY.md`：18 资产权威台账，含本轮复跑记录  
- 根目录 eval JSON：`dp_student_eval.json`、`hw_student_eval.json`、`sm_student_eval.json`、`zctlmcp_eval.json`  
- `.zcode/plans/plan-sess_cad6cf65-998b-4978-90a1-c14811e0c101.md`：agent 资产产线全量推进计划  
- `.mimosa/history/run-20261002T002945085Z-27140-b819aa510c2c.json`、`.mimosa/history/run-20261003T031511554Z-5312-1c70ff11cf2f.json`：Mimosa 扫描历史  
