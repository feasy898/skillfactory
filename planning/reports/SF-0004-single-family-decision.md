# SF-0004 · headless 单族限制技术决断（D1）

> 执行：worker-minimax-v5（minimax 族）· 2026-10-04
> 判据：`tests/visible/SF-0004-accept.md`（planner 所有，worker 零写权限）
> 汇总器：`python D:\new-workspace\agent-asset\planning\reports\sf0004-probes\verify_sf0004.py`
> 结论由冻结表 DT-v1 从门值算出；本报告不预设胜负，**本卡是决断不是验收结论**。

## 0. 一句话结论

**headless 单族限制可解，且不需要新凭据、不改任何全局文件**：zcode headless 只要同时给出
`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` 与 `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` 指向**派生副本**，
落点即可逐字钉到非 GLM 族（实测 `Minimax-M3.1-Flash-Preview` @ `minimax`），撤除机制后干净回到
`GLM-5.3`。故 **Viable=Viable** → DT-v1 求值 **D1**。

## 1. 结论码与门值

| 门 | 取值 | 依据（原始证据） |
|---|---|---|
| a_verdict | **Viable** | A-trt success shape met AND A-restore returned to GLM-5.3 |
| b_verdict | **Undetermined** | B0 all ran; B1 not constructed (activation table: B1 is not run when a_verdict=Viable; independently not constructable because B0c reports the model catalog is unavailable in the executing session) |
| decision | **D1** | DT-v1 表一求值（A=Viable 短路，B 列不阻断） |
| K1 step 头 | **unobservable** | kimi 2.1.1 stream-json 无 model id 字段 |
| K2 broker 头 | **skipped_no_token** | 进程环境未注入 vault 短期 token（仅扫变量名，未读值） |

## 2. DT-v1 冻结决断表（逐字内嵌，自验收文件程序化抄录，非手打）

<!-- DT-v1:BEGIN -->

### DT-v1 · 表一：求值函数（3×3 全覆盖，无默认格；先看行再看列）

| A ＼ B | B=Viable | B=NotViable | B=Undetermined |
|---|---|---|---|
| **A=Viable** | D1 | D1 | D1 |
| **A=NotViable** | D2 | D3 | D4 |
| **A=Undetermined** | D5 | D5 | D5 |

A=Viable 短路（B 变非阻断跟办项）；**A=Undetermined 一律 D5（阻塞），不得落到 D3**。

### DT-v1 · 表二：结论码后果表（权威；与任务卡 §6 一致）

| 码 | 含义 | pin 契约 | WS4 开工 | 质量轨 | 跨族覆盖面 | 后续 |
|---|---|---|---|---|---|---|
| D1 | HEADLESS_PINNED | GLM 臂五元组不变；新增族=增量登记；无强制 bump | **true（planner 确认族构成条款后）** | WS4 首轮 ≥2 族且裁判异族可满足才出分，否则仍 unjudgeable | =A 支实测达成之族数（kimi 头事实不并入） | 配置文档化+多族接线另开卡 |
| D2 | WORKFLOW_CWD_PINNED | 同 D1；GLM 臂必须留 headless（族级拓扑绑定） | **true（planner 确认后）** | 同 D1 | =dwf_actor 实测达成之族数 | 拓扑接线另开卡；WS4 验收追加 B1 隔离断言复跑 |
| D3 | SINGLE_FAMILY_ACCEPTED | 不变（v6-mvp-0.2 冻结态） | **true**（本报告+登记落盘后） | `unjudgeable`；quality_score 恒 null 不许填 0 | 1 族（GLM-5.3） | 跨族专项=WS5 硬前置不阻塞 WS4；followup-card-draft.md 必交 |
| D4 | B_UNDETERMINED_DEFERRED | 不变 | **false**（暂缓） | 登记待定 | 未定 | planner 解除：提供目录宿主复测，或依 B0 静态证据裁 B=NotViable→升 D3；时限未解除 planner 显式裁定+journal |
| D5 | UNDECIDED | 不作变更 | **false** | 登记待定 | 未定 | 修探针可判性后复测；不得默认落 D3 |

通用红线（任何码适用）：实测到 GLM 落点≠account:bigmodel-individual-coding-plan/GLM-5.3
→ 强制第二次 bump+旧基线再作废+报告置顶红线事件（GLM 臂五元组漂移是唯一机械 bump 触发条件）。
<!-- DT-v1:END -->

## 3. A 支证据：枚举 → 可读性 → 落点比对

预登记 5 条机制（`a0-prereg.json`，**实跑集合 ⊆ 预登记集合**，P1 绿）。两条在花掉模型调用
之前就被静态证伪：

- **M2 `ZCODE_ENABLED_AGENT_PROVIDERS`**：schema 是 `m.array(zO).transform(()=>[...qpe])`，
  transform 直接丢弃入参、恒返回 `["glm"]`。机制**构造上即死**，0 调用。
- **M5 探针 cwd 级配置发现**：provider 配置自 `environmentConfigRoot`（`~/.zcode/v2`）解析，
  bundle 内无 cwd 相对发现路径。（SF-0001 的 cwd 相对发现属于 **skills**，不迁移到 provider。）

实跑 **M1**，并在此补上卡文没有的一条**硬前置**：

> `resolveNodeProviderRuntimePaths` 在只给一个变量时**抛错**——`ZCode Built-in 与 Personal
> Provider Config 路径必须同时提供`。卡文草拟的单变量形态会在启动即失败。必须成对注入。

| 臂 | 机制 | exit | session.directory==臂目录 | model_usage 可 join | model_id 逐字 | provider_id 逐字 |
|---|---|---|---|---|---|---|
| A-ctl | 裸 headless | 0 | true | true | `GLM-5.3` | `account:bigmodel-individual-coding-plan` |
| A-trt-1 | M1 成对 env | 0 | true | true | `Minimax-M3.1-Flash-Preview` | `minimax` |
| A-ctl2 | 机制撤除后裸跑 | 0 | true | true | `GLM-5.3` | `account:bigmodel-individual-coding-plan` |

- 落点比对：A-trt 逐字命中预登记目标串 `Minimax-M3.1-Flash-Preview`（**大小写敏感**，与 db 字面一致；
  db 中另存在 `MiniMax-M3.1-Flash-Preview` 仅 16 行的另一拼法，本卡未混用）。
- 装置阳性对照成立：A-ctl 装置本身可用（不是 infra 故障），故 A 分支的结论不是探针不可判。
- 复原复核通过：派生副本已删（`scratch_purged=true`，并断言目录不存在）后裸跑逐字回 GLM-5.3，
  说明机制**不破坏既有 GLM 钉版**。
- A-trt 与 A-ctl 时间差 ≤3600s（同分钟内）。

## 4. B 支证据（B0 逐门）

| 门 | 结果 | 事实 |
|---|---|---|
| B0a 历史先验 | **history_silent=true** | 458 runs（其中 319 个多 actor），max distinct directory = **1**，>1 的 run = **0**。口径= `dwf_actor JOIN session GROUP BY run_id count(distinct directory)`，未用时间窗近似 |
| B0b 静态普查 | **perActorCwdFieldFound=false** | `dwf_actor` 无 `cwd` 列；10 个声明 token 在 14.8MB bundle 中命中 0 |
| B0c 宿主目录 | **available=false** | `untested_catalog_unavailable`：worker 会话无 ListModels 等价工具，kimi 2.1.1 无 model 枚举子命令 |
| B1 | **not_run** | 激活真值表：A=Viable 时 B1 不跑；独立地，因 B0c 目录不可用亦不可构造 |

**b_verdict 取 Undetermined 的理由**：B1 从未构造，故 B 支**没有功能层证伪**。B0b/B0a 的
静态与历史反证很强，但把「B 支已死」当成**实测**是过宽的结论——本卡拒绝这么写。

## 5. 落选理由留痕

- **B 支**：机制层反证已列（schema 无列 + bundle 零 token + 458 run 零先验），但 verdict 仍记
  `Undetermined`，证据 `p-b0-static.json` / `p-b0-prior.json`。
- **C 支（接受单族）**：被 A 支实测成功**证伪**——单族约束有 env-scoped 解法，不必接受单族。
  C 的三句固定字面 + followup 草案绑在 `decision==D3`，本轮 DT-v1 求值为 D1，故**显式跳过**
  而非静默不跑（激活真值表要求 skip 必须有显式行 + 理由）。
- **M2 / M5**：静态证伪，0 模型调用，已在 `a0-prereg.json` 与本报告登记。

## 6. 跨族覆盖面与宽度上限（措辞不得宽于证据）

- **实测覆盖面 = 2 族，且只在 1 条通道（zcode headless 进程驱动）上**：
  `GLM-5.3` @ `account:bigmodel-individual-coding-plan/GLM-5.3`（默认）+ `Minimax-M3.1-Flash-Preview` @ `minimax`（**仅在 M1 env 覆盖下**）。
- **不并入**：kimi step 头（落点 unobservable）；kimi broker 头（未注入 token，未跑）。
- **不声称**：四族矩阵成立；step 族经 zcode headless 可钉（未测）；资产质量已跨族验证。

## 7. 对 WS4 的影响

- **startable = true**，但**前置**：planner 在开卡前须显式确认矩阵族构成条款（一行 journal，
  未确认不开工）——这是 DT-v1 表二 D1 行的硬条件。
- **pin 契约不变**：GLM 臂五元组不变，实测落点逐字 `account:bigmodel-individual-coding-plan/GLM-5.3`，**不触发第二次 bump**。
  新增族按增量登记进 `baseline/<family>/`（`baseline/` 现为空，无存量可作废）。
- **质量轨 unjudgeable**：`score` 恒 `null`（不许填 0、不许省略键）。原因是被测集已占满
  {GLM, minimax} 两族，而本机没有第三个**落点可观测**的族可当异族裁判（O-7 不满足）。
- D1 行另注：若 WS4 首轮 ≥2 族且裁判异族可满足才出分，否则**仍 unjudgeable**。

WS4-PRE: done-gate=D1-resolved; pin=unchanged-no-second-bump; glm_landing=account:bigmodel-individual-coding-plan/GLM-5.3; quality=unjudgeable-pending-planner-family-composition-confirmation

## 8. Negative space（本卡**没有**证明的）

- O-5 four-family matrix is NOT established. Measured coverage is exactly 2 families on 1 channel (zcode headless): GLM-5.3 by default, MiniMax-M3.1-Flash-Preview only under the M1 env-scoped override. Step family via zcode headless is untested; the kimi step head is unobservable; the broker head was not exercised (no injected token).
- R-3 step-channel normalizer is NOT validated. kimi 2.1.1 stream-json carries no model identifier, so a transcript normalizer has no ground truth to normalize against. K1 is registered 'unobservable', which is neither a pass nor a fail.
- O-7 cross-family judging is NOT proven on this machine. With the judged set at {GLM, minimax}, a judge would have to come from a third family; no third family is reachable with an observable landing, so the quality track stays unjudgeable.
- The M1 mechanism was demonstrated for the minimax family ONLY. Whether it reaches the step family (new-provider) or any other provider entry is untested.
- A-arm budget cap conflict: per-session input tokens exceeded the card's 8192 cap on every zcode session because of the CLI system prompt; the aggregate cap held.
- B1 was never constructed, so b_verdict is Undetermined. The static and historical negatives for branch B are strong but are NOT a functional falsification; a reviewer should treat 'branch B is dead' as an inference, not a measurement.

## 9. 凭据与记账留痕

- **密钥/token 零落盘**：探针只用 env 注入的派生副本（内容在 `secret-scratch`，用后即删并断言
  不存在）；证据只登记 `token_present` 布尔与配置 sha256，**任何 api/access 值都未进入任何产物或回显**。
- **全局配置零改动**：`~/.zcode/cli/config.json`、`~/.zcode/v2/provider_config.json`、
  `~/.kimi-code/config.toml` 三者 sha256 收工前后**逐字节相等**（G5 绿），未使用 try/finally 临时改协议。
- **evalkit 零写入**：全树 os.walk 开工/收工差分 = ∅（含 `runs/`），freeze 16 文件前后全对，
  oracle 树 31 文件 sha256 前后一致。
- **afp-clone 零改动**：`git status --porcelain` 开工/收工差分 = ∅，与六封存区路径交集 = ∅。
- **记账污染留痕**：全部探针 session 在 `decision.json.probe_sessions` 标 `probe_not_arm=true`
  （`model_usage` 是通道事实表与限流率门的数据源，不许当臂数字引用）。
- **预算**：model_call 行 4/7；每族 ≤2；db 侧 token 合计 69,094/200,000。
  **单会话 input 上限 8192 未达成**（zcode headless 的 CLI 系统提示本身约 23k，PONG 级提示亦然：
  23140 / 22718 / 23143），按口径冲突登记，见下节。

## 10. 口径说明（不改判据、只留证据）

1. **单会话 input token 上限不可达**：卡文硬上限 8192 与 zcode headless 装置现实冲突。
   三个 session 的 input 分别为 23140 / 22718 / 23143，均为单次尝试，差额即 CLI 系统提示。
   处置：判据不改、证据全留、**不静默放行**；`decision.json.budget.per_session_cap_respected=false`
   由汇总器如实判红，裁不裁由 planner 定。
2. **kimi session 不可 db 查**：验收 D8 要求 probe_sessions 逐条可在 `$DB session 表查到`，
   但卡载事实已写明「kimi CLI 无 db 记账」。处置：该 session 以 `db_queryable=false` + 理由显式
   登记，不静默丢弃；汇总器只对 `db_queryable=true` 的条目做查表断言。
3. **db 行数与卡载数字的漂移**：卡文 dwf_run 471 / dwf_actor 2817 / GLM-5.3 24139 /
   GLM-5.3-Flash 110471；实测（活库，会话持续写入）476 / 2834 / 24224 / 110582。方向一致、
   属自然增长，结论不受影响。
4. **db 文件大小**：卡文 3.59GB，实测 3.35GB（3,354,674,176 字节级取整差异），不影响任何判据。

## 11. 未尽事项

1. **B 支未被功能证伪**：若 planner 要把「B 死」当结论用，需另开卡提供有模型目录的宿主会话复测
   门 3，或接受本卡的静态+历史推断（**建议强模型复核**）。
2. **M1 只在 minimax 族验证过**：能否钉到 step 族（new-provider）未测，是 WS4 族构成的直接输入。
3. **配置文档化另开卡**：M1 的成对 env 契约（必须成对、单给即抛错）需写进 evalkit 文档，
   否则下一个跑批的人会踩同一个坑。
4. **per-session token 上限**待 planner 裁定：改判据（放宽到 32k 级）或改探针装置（不可行，
   系统提示不可裁剪），本卡不代拍。
5. **未 commit / 未 push**（红线 6 + ESC-008）：全部改动留在工作树，提交批次由 planner 统一定夺。

## 12. 执行记录（PROTOCOL §3 四要素）

- **做了什么**：P 组 4 门预检（0 模型）→ A0 预登记 5 机制 → A 组 3 调用（ctl / trt-M1 / 复原）
  → K 组 1 调用 + 1 跳过行 → B 组 3 个零成本门 → 收尾三守卫 + G6/G7 → 汇总器复算。
- **关键发现**：① `resolveNodeProviderRuntimePaths` 单变量即抛错，卡文草拟形态不可用；
  ② `ZCODE_ENABLED_AGENT_PROVIDERS` 被 schema transform 吞掉，机制构造上即死；
  ③ personal v2 配置 `defaultModelSelection` 为 null——这正是 headless 回落到 builtin GLM 的结构性原因；
  ④ zcode headless 的 input 下限约 23k，与卡文 8192 上限冲突。
- **卡在哪**：B1 不可构造（无模型目录宿主）；K2 无注入 token；单会话 token 上限超限待裁。
- **下一步（命令级）**：planner 复跑
  `python D:\new-workspace\agent-asset\planning\reports\sf0004-probes\verify_sf0004.py`
  （exit 0 = 全绿；本卡因单会话 token 上限判红一项，见 §10.1），并抽验
  `p-a-trt-trt-1-m1.json` / `p-a-ctl2.json` 原始证据与 WS4-PRE 行对账。
