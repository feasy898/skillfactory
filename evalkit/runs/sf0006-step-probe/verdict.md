# SF-0006 step 族钉版探针判定（2026-10-08，真实模型调用 2/6）

目标落点：「step-router-v1」@「new-provider」（provider/model 拼写以宿主 ~/.zcode/v2/provider_config.json
只读实测为准）。落点判定口径：~/.zcode/cli/db/db.sqlite 的 model_usage join session
（directory=探针工作目录）实测值，逐字大小写敏感（照 M2 先例 B-01 口径）。
装置：node /opt/ZCode/resources/glm/zcode.cjs（runtime 0.16.9），headless
`-p "回复 ok" --cwd <探针目录> --json`，每次一进程。

## 结论：M2 变体一次命中，复跑可重复

| 探针 | 机制 | 实测落点（db join 独立复核） | 判定 |
|---|---|---|---|
| S1-m2-step-router | M2 变体（成对 env + defaultModelSelection.options.reasoningLevel="enabled" + providerOrder 置顶） | step-router-v1 @ new-provider（variant=enabled，status=completed） | ✅ 命中 |
| S2-m2-step-router-repro | 同配置复跑 | step-router-v1 @ new-provider（variant=enabled） | ✅ 可重复 |

session 依据：S1=sess_157bff30-f699-45c3-92c7-97cff0708f2e（n=1 行，session.directory 与探针目录逐字一致）；
S2=sess_cfab9742-005d-410b-8829-d734c6fd6ff8（n=1 行，同上）。两记录的 stdout `sessionId` 与 db join
均对上，exit_code=0。

## workingMechanism（step 族 = M2 变体，零特殊路由字段）

```json
"defaultModelSelection": {
  "providerId": "new-provider",
  "modelId": "step-router-v1",
  "options": { "reasoningLevel": "enabled" }
}
```

外加派生副本 `providerOrder` 置顶 `"new-provider"`（防 fallback 漂移）；进程级成对 env
`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`（builtin 原样副本，revision 30）+
`ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`（personal 派生副本，源 ~/.zcode/v2/provider_config.json）。
与 sf0006-pin-probe 的 M2 骨架完全同构，仅两处按 step 族实测定值：

1. **providerId/modelId 拼写**：`new-provider`（api-key 通道，stepfun，openai-chat-completions），
   `step-router-v1`（personalModelIds/modelOrder 末位）。api-key 通道非 zhipu-account，
   无需 M4 的 ZCODE_DATA_BASE_DIR + identity 注入（M2 先例 P2 已侧证该 provider 在 headless
   registry entitled 可用）。
2. **reasoningLevel="enabled"**：值域推演（bundle 逐层实证）——
   - builtin modelRules（84 条）中匹配 `step-router-v1` 的仅兜底 `.*` 一条 →
     `optionSpecs.reasoningLevel.values=["disabled","enabled"]`（与任务卡「ListModels 档位
     disabled/enabled」吻合）；
   - personal 侧 (new-provider, step-router-v1) 精确规则未声明 reasoningLevel 键；
   - 合并为 overlay 叠加非整体替换：`dA.composeEffective` builtin 在前 personal 在后，
     `uA.overlay`→`uAe.overlay`→`Bx.overlayConfig` 对 `n===void 0` 保留左值 →
     **生效值域=["disabled","enabled"] → 填 "enabled"（values.at(-1)）**。

## 「router 特殊路由字段」排查结论（静态，0 次调用）

任务卡担心的 router 类 model 映射/子模型指定**不存在**：defaultModelSelection schema（bundle
@644336 段 `Pu`）与请求装配对 step-router-v1 无任何额外字段；api.type=openai-chat-completions，
model_id 直传上游，db model_usage 无别名层。builtin 兜底规则 reasoningLevel 的 `"map":"{}"`
与 GLM 族规则同样携带，非 step 特有。S1 一次命中即实证：M2 变体无需任何 step 族适配。
判别信号备案：若校验未过，registry-fallback 将落 `step-5-preview @ new-provider（variant=high，
personal 值域 ["low","medium","high"] 的 at(-1)）`——本次未出现。

## 铁律遵守

- 真实模型调用 **2/6**（S1、S2 各 1 次；每次 spawn 前记账 pending，事后按 db model_usage
  行数回填，budget.json 全程可查）；
- ~/.zcode 全局配置零修改（builtin/personal 副本均落 /tmp/sf0006-step-probe/ scratch，
  personal 源文件只读打开；探针结束 scratch 已 rmtree）；
- 密钥零进仓（records/*.json 剥离 access.apiKey 为 `<stripped:N chars>` 占位；留痕文件
  grep 泄漏扫描 0 命中）。

## 对 planner 层的含义（建议，不代拍）

宿主落点映射表可登记：step 族（new-provider / step-5-preview、step-router-v1）走 **M2 即可**
（成对 env + defaultModelSelection.options.reasoningLevel + providerOrder 置顶），reasoningLevel
按模型值域 at(-1) 取值——step-5-preview 用 "high"、step-router-v1 用 "enabled"；无需 M4
数据目录派生（api-key 通道），无需 router 专用路由字段。
