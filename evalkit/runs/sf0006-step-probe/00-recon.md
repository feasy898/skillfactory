# SF-0006 step 族钉版探针 · 静态侦察（0 次模型调用，2026-10-08）

目标落点：「step-router-v1」@「new-provider」。照 sf0006-pin-probe/ 的 M2 先例做变体。
装置：node /opt/ZCode/resources/glm/zcode.cjs（runtime 0.16.9），headless `-p "回复 ok" --cwd <探针目录> --json`。

## 1. provider/model 确切拼写（宿主 ~/.zcode/v2/provider_config.json 只读实测）

- providerOrder：`["new-provider","minimax","new-provider-2","moonshot-kimi","new-provider-3"]`；
- `new-provider`：access.type=`api-key`（stepfun，baseUrl https://api.stepfun.com/step_plan/v1，
  api.type=`openai-chat-completions`），personalModelIds=`["step-5-preview","step-router-v1"]`，
  modelOrder=`["step-5-preview","step-router-v1"]`。
- 拼写逐字确认：provider id=`new-provider`，model id=`step-router-v1`（小写、连字符、v1 结尾）。
- **M2 先例侧证 registry 在位**：sf0006-pin-probe P2（M3 直指 account 失败）fallback 恰落
  `step-5-preview @ new-provider（variant=high）`——说明 new-provider 在 headless registry 中
  entitled 可用（api-key 通道，非 zhipu-account，无需 M4 identity 注入）。

## 2. reasoningLevel 值域（三层合并推演，bundle 实证）

- builtin /opt/ZCode/resources/config/provider/zcode-builtin.json（revision 30）modelRules 共 84 条；
  匹配 `step-router-v1` 的仅兜底 `.*` 一条 → `optionSpecs.reasoningLevel.values=["disabled","enabled"]`
  （与任务卡「ListModels 档位 disabled/enabled」吻合）。
- personal modelConfigRules.providerModelRules 中 (new-provider, step-router-v1) 精确规则：
  `enabled:true, properties.contextWindow=256000, optionSpecs.maxOutputTokens.max=32000`，
  **未声明 reasoningLevel 键**。
- 合并语义（bundle /opt/ZCode/resources/glm/zcode.cjs）：
  - 规则序 `dA.composeEffective`（@543475 段）：`[...builtin.rules(), ...personal.rules().filter(精确规则)]`，
    builtin 在前 personal 在后；
  - `dA.resolve`：依序 `n=n.overlay(s.config)`，overlay 叠加非整体替换；
  - `uA.overlay`（ModelConfig，@543475）：`optionSpecs: this.overlayConfig(this.optionSpecs, t.optionSpecs)`；
  - `uAe.overlay`（ModelOptionSpecs，@542859）：`reasoningLevel: this.overlayConfig(this.reasoningLevel, t.reasoningLevel)`；
  - `Bx.overlayConfig`（@533261）：`n===void 0 ? t : ...` —— **personal 未声明 → builtin 值域存活**。
- 结论：step-router-v1 生效值域=`["disabled","enabled"]` → M2 变体填 `"enabled"`（=values.at(-1)，
  与 registry-fallback 补档语义一致）。

## 3. 校验链（bundle 实证，@575763 bpe）

```js
function bpe(e,t){let n=t.options?.reasoningLevel,o=e.config.optionSpecs.reasoningLevel;
 return n===void 0?{ok:!1,code:"reasoning-level-missing",...}
 :o.values.includes(n)?{ok:!0}:{ok:!1,code:"reasoning-level-not-supported",...}}
```

- `options:{}` → missing（SF-0004 时代 M1 失效根因）；`reasoningLevel:"enabled"` ∈ values → ok。
- isSelectable 失败 → QKe 落 registry-fallback：providerOrder 首个非 hidden provider 的 models[0]
  + values.at(-1) → 对本族即 `step-5-preview @ new-provider（variant=high，因 step-5-preview
  personal 值域=["low","medium","high"]）`。**该落点即 S1 的判别信号**：db 落 step-router-v1=命中；
  落 step-5-preview=校验未过。

## 4. 「router 特殊路由字段」排查结论（静态）

- defaultModelSelection schema（@644336 段 `Pu`）与请求装配对 step-router-v1 无任何 model 映射/
  子模型字段需求：api.type=openai-chat-completions，model_id 直传上游；db model_usage 记 CLI 所用
  model_id，无别名层。
- builtin 兜底规则 reasoningLevel 带 `"map":"{}"`（GLM 族规则同样携带），非 step 族特有，不构成
  额外路由字段。
- 结论：M2 变体（成对 env + defaultModelSelection.options.reasoningLevel="enabled" +
  providerOrder 置顶）无需求适；若 S1 意外落 step-5-preview，再从 db 落点+CLI 输出反推。

## 5. 预算与纪律

- 真实模型调用 ≤6（任务卡刚性；spawn 前记账 pending，事后按 db model_usage 行数回填；
  无模型调用的失败探针不消耗预算）。
- ~/.zcode 全局配置零修改：builtin 原样副本 + personal 只读派生副本均落 /tmp scratch，
  记录落盘前剥离 apiKey 字段；探针结束 rmtree scratch。
- 落点判定：~/.zcode/cli/db/db.sqlite 的 model_usage join session（directory=探针工作目录），
  逐字大小写敏感。
