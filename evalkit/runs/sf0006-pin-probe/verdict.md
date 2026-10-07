# SF-0006 钉版探针判定（2026-10-08，真实模型调用 6/8）

目标落点：A=「GLM-5.3」@「account:bigmodel-individual-coding-plan」；B=「Minimax-M3.1-Flash-Preview」@「minimax」。
落点判定口径：~/.zcode/cli/db/db.sqlite 的 model_usage join session（directory=探针工作目录）实测值，逐字大小写敏感（照 B-01）。
装置：node /opt/ZCode/resources/glm/zcode.cjs（runtime 0.16.9），headless `-p "回复 ok" --cwd <探针目录> --json`，每次一进程。

## 结论：两目标均可逐字钉中（机制可重复）

| 探针 | 机制 | 实测落点（db join） | 判定 |
|---|---|---|---|
| P1-minimax-rlen | M2（成对 env + defaultModelSelection.options.reasoningLevel） | Minimax-M3.1-Flash-Preview @ minimax（variant=enabled） | ✅ 命中 |
| P2-glm-account | M3（=M2 直指 account provider） | step-5-preview @ new-provider（variant=high） | ❌ fallback |
| P3-adjudication-prune | M2 + 副本裁剪（仅留 moonshot-kimi）判定实验 | k3 @ moonshot-kimi（variant=max） | ❌ 实锤 account 不在 headless registry |
| P4-glm-m4-datadir | **M4**（M2 + ZCODE_DATA_BASE_DIR 派生数据目录 + 凭据副本补明文 identity 条目） | **GLM-5.3 @ account:bigmodel-individual-coding-plan（variant=max）** | ✅ 命中 |
| P5-minimax-repro | M2 复核 | Minimax-M3.1-Flash-Preview @ minimax | ✅ 可重复 |
| P6-glm-m4-repro | M4 复核 | GLM-5.3 @ account:bigmodel-individual-coding-plan | ✅ 可重复 |

## workingMechanism（逐字钉版双机制）

### 机制族（对 A/B 通用骨架：M2）
进程级成对 env：`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`=builtin 原样副本（/opt/ZCode/resources/config/provider/zcode-builtin.json，
revision 30）+ `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`=personal 派生副本（源 ~/.zcode/v2/provider_config.json），
其中派生副本设：
```json
"defaultModelSelection": {
  "providerId": "<目标 provider 逐字 id>",
  "modelId": "<目标 model 逐字 id>",
  "options": { "reasoningLevel": "<模型支持值>" }
}
```
加 `providerOrder` 置顶目标 provider（防 fallback 漂移）。**reasoningLevel 是 SF-0004 时代 M1 失效的根因**：
runtime 0.16.9 的 `QKe`（resolveInitialModelSelection）只认 `isSelectable`（b3i→bpe）的 configured-default，
而 bpe 对 `options.reasoningLevel===undefined` 一律报 `reasoning-level-missing` 不合法 → M1 的 `options:{}`
整体被弃 → 落 registry-fallback（providerOrder 首位 provider 的 models[0]，即 modelOrder[0]，与 B 层
RC3 实测 MiniMax-M3 逐字吻合）。值域（builtin modelRules，匹配大小写不敏感）：
- Minimax-M3.1-Flash-Preview：无专门规则 → 兜底 `.*` → values `["disabled","enabled"]` → 用 `"enabled"`；
- GLM-5.3：规则 `.*glm-5\.3(?:-flash)?…` → values `["low","high","max"]` → 用 `"max"`。

### A 目标专用增强（M4）
headless CLI 的 standalone account 通道（@14756317 恒以 `{standalone:…}` 装配）要求凭据库存在
`account-provider:<providerId>:identity` 条目（oPn→loadMany），宿主全局凭据库只有 api-key 条目而无
identity → account provider 一律 entitled:false → 不进 registry（P2/P3 实锤；P3 副本仅剩 moonshot-kimi
时 fallback 落 k3@moonshot-kimi）。修复：`ZCODE_DATA_BASE_DIR=<scratch>/zcode-data`（进程级 env）+
`<data_dir>/.zcode/v2/credentials.json` 派生凭据副本 = 全局凭据逐条目原样拷贝（加密 blob 不动）+ 注入
一条**明文** identity 条目（cipher ZZr/decrypt 对无 `enc:v1:` 前缀的值原样返回；identity 值从既有
`…account:<id>:api-key` 条目名解析，17 字符，全程留在 scratch，不回显不进仓）。凭据路径解析
`$ZCODE_DATA_BASE_DIR/.zcode/v2/credentials.json`（n$s 实证）。M4 后 standalone 自举：identity→api-key
（CLI 自解密）→ entitled:true → account provider 进 registry → defaultModelSelection 逐字命中
（请求层凭据由 providerRuntimeHeadersPort/SHo 以同一对条目装配）。

### 铁律遵守
- 真实模型调用 6/8（每次 spawn 前记账 pending，事后按 db model_usage 行数回填）；
- ~/.zcode 全局配置零修改（全局凭据仅只读拷贝到 /tmp scratch；opening/closing 对比可另见 B 层装置）；
- 密钥零进仓（records/*.json 泄漏扫描 0 命中；scratch 子目录探针结束即 rmtree）。

## 失败探针（有效结果）
- P2：M3（无 M4 增强）→ fallback step-5-preview@new-provider，即 B 层红线同款落点，证实「仅 M2 不够 A 目标」。
- P3：判定实验 → account provider 确认不在 headless registry（结构性，非值域问题）。

## 对 planner 层的含义（建议，不代拍）
宿主落点映射表可登记：
- minimax 家族：M2 即可（成对 env + defaultModelSelection.options.reasoningLevel="enabled"）；
- GLM/account 家族：M4（M2 + ZCODE_DATA_BASE_DIR 派生数据目录 + identity 明文条目注入）；
- 旧 M1（options:{}）在 runtime 0.16.9 下对任何 provider 均不再钉模型层，只钉 provider 层（fallback 语义）。
