# SF-0006 钉版探针 · 静态侦察（0 次模型调用，2026-10-08）

对象：/opt/ZCode/resources/glm/zcode.cjs（runtime 0.16.9，14.8MB minified bundle）+ 宿主全局配置（只读）。

## 链条（bundle 内偏移为 char index）

1. 成对 env 强制（@1067378）：`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` 与 `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`
   必须同时提供，单变量启动抛错（resolveNodeProviderRuntimePaths）。
2. headless 启动读 defaultModelSelection（@14127508 段）：`configuredDefaultModelSelection = await
   NodeModelSelectionConfigRepository.read()` ← personal 配置的 `config.defaultModelSelection`。
3. headless 初始模型选择（@13877077 p9a；@13874671 T$o 调用）：
   `I = resume ? T?.selection : runtimeConfig.modelSelection ?? T?.selection`，其中
   `T = QKe({configuredDefault, registry})`。本机 setting.json 无 modelSelection 键（实测），
   新会话非 resume → 走 QKe。
4. QKe（resolveInitialModelSelection @577644）：
   - configuredDefault 且 `b3i(registry, sel)`（isSelectable）→ `source:"configured-default"`，逐字用之；
   - 否则 fallback `registry-fallback`：providerOrder 首个非 hidden provider 的 models[0]，
     由 v3i 补 `options.reasoningLevel = values.at(-1)`。
5. b3i → bpe（validateModelSelectionOptions @575763）：**`options.reasoningLevel === undefined` 直接
   `ok:false, code:"reasoning-level-missing"`**；值不在 `optionSpecs.reasoningLevel.values` 亦 false。

## 对 B 层 RC3 的解释（M1 为何 provider 层生效、模型层落 MiniMax-M3）

M1 派生副本 `defaultModelSelection={providerId:"minimax", modelId:"Minimax-M3.1-Flash-Preview", options:{}}`
→ bpe 报 reasoning-level-missing → 落 registry-fallback。personal 副本 providerOrder 置顶 minimax →
registry minimax.models 顺序 = 宿主 modelOrder（模板 builtinModelIds 8 个 + personal M3.1 按 modelOrder 排，
M3.1 在末位，ype @559166）→ models[0]=MiniMax-M3，v3i 补 values.at(-1)。db 实测（sess_9dfb6c3e /
sess_9aa98deb）model_id=MiniMax-M3, variant=enabled —— 与链条逐字吻合。

## reasoningLevel 值域（builtin /opt/ZCode/resources/config/provider/zcode-builtin.json，revision 30）

匹配大小写不敏感（vWt 第三参 true，@544959）：
- `modelMatch ".*"` 兜底 → values `["disabled","enabled"]`。minimax 模板（builtinModelIds 8 个
  MiniMax 模型）与 Minimax-M3.1-Flash-Preview 无专门规则 → 落兜底，**用 "enabled"**。
  （db 侧印证：M1 fallback 落 MiniMax-M3 variant=enabled = 同兜底 values.at(-1)。）
- `modelMatch ".*glm-5\.3(?:-flash)?(?:[.\-:/\[].*)?"` → values `["low","high","max"]`。
  GLM-5.3 @ account:bigmodel-individual-coding-plan（builtinProviderModelRules 注册，enabled:true）
  **用 "max"**。（db 侧印证：全库 GLM-5.3@account:bigmodel variant=max 7480 条为众数。）

## 机制假设（待实测证伪）

M2/M3 = M1 成对 env 骨架 + `defaultModelSelection.options.reasoningLevel` 填入模型支持值：
- B 目标：`{"providerId":"minimax","modelId":"Minimax-M3.1-Flash-Preview","options":{"reasoningLevel":"enabled"}}`
- A 目标：`{"providerId":"account:bigmodel-individual-coding-plan","modelId":"GLM-5.3","options":{"reasoningLevel":"max"}}`

A 目标附加风险（如实登记）：account provider access.type=zhipu-account，entitled/states 由 account
通道注入（FHo @14127508 段校验 current 为 boolean）；本 workflow 会话 db 实测同 provider 可用
（provider_id 逐字一致），但 headless CLI 走 standalone account 通道未经实测，P2 验证。

其余前提（实测确认）：宿主注入 env 在 worker 会话存在（须显式覆盖）；~/.zcode/config.json 不存在；
~/.zcode/v2/setting.json 无 modelSelection；两份 builtin（/opt/ZCode 与 runtime active 副本）revision 同为 30。
