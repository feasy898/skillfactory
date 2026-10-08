# Planner 裁决：ofc D3 作用域迁移 + WS3 对拍 harness 建设授权（2026-10-08）

## 事实

1. ofc 三题金标候选（35+6=41 份）与受托模型盲注 verdict 已注入（提交 0f1f7d2/01a83e6/eb8d6f0），但 `ws4_d3_gate` 对 ofc 硬编码 `WAITING_WS3` 作用域，真实对拍被状态机短路（exit 3）。
2. WS3 原口径对拍不可执行：office-eval-suite 无逐条答案判定器（spec.md:107 明文 semantic 交由未来裁判模型）、无逐条参照产物（157 checks 中 47 semantic、纯机械条目仅 2/34）。

## 裁决

1. **ofc D3 作用域迁移**：ofc-01/02/03 的 D3 从「WAITING_WS3」迁移至 SF-0006 委托链下执行——依据：owner 2026-10-08 常设指示已把人工门委托给受托签署模型，WS3 所需的人工金标出具能力已在链内（mm/hot 先例），WS3-scoped 的历史理由消失。装置面改动（ws4_d3_gate/ws4_pool_state 的 ofc 作用域解除，以金标存在+本裁决文件为放行条件）走冻结协议，pool-state 的状态字段由工具派生，不手改。
2. **WS3 对拍 harness 建设**：按 owner 三族并发指令，semantic 面由裁判模型执行（GLM-5.3-Flash / step-router-v1 / Minimax-M3.1-Flash-Preview，异族抽取 ≥2 互裁、盲态、位置轮换）；逐条参照产物用三族生成（34 条 × 3 族，或按域抽样裁剪，预算另批）。checker（157 checks 机械面）与裁判面合并得出每条 checker 结论，对 34 条金标（全 true）算准确率/召回，≥95% 达标。原「零模型」约束对本卡解除（owner 指令优先）。
3. 两条路径失败均为有效结果，如实留痕；不放宽 ≥95% 达标线。

签署：planner（主代理），2026-10-08。供 owner 审阅。
