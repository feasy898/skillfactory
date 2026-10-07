# Planner 裁决：SF-0006 B 层 redline_event 与钉版基线迁移（2026-10-08）

## 事件

B 层冒烟（round-report: `evalkit/runs/sf0006-b-smoke/round-report.json`，提交 23d4edc/739e4a7）触发 DT-v1 GLM 红线：宿主默认落点 step-5-preview@new-provider ≠ 契约 GLM-5.3@account:bigmodel-individual-coding-plan。B 层如实判 failed_infra，C 层 not_run（B-06）。

## 裁决

1. **承认 redline_event，接受 failed_infra 为本卡有效结果**；B 层 4 臂产物（minimax 两臂真实完成 mm-01、产物在臂内）仅作装置验证证据，不计分、不引用为基线信号。
2. **SF-0004 的钉版结论在本宿主作废**（环境事实变更：~/.zcode/v2/provider_config.json 2026-10-07 起默认模型选择为空、providerOrder 首选 new-provider；runtime 为 /opt/ZCode 0.16.9 非 Windows npm 版 3.14.4-30）。按 DT-v1，这构成装置基线 bump 情形：evalbench 维持 v6-mvp-0.3 不动（装置代码未变），但**宿主落点映射表**须重建——以新探针实测为准，重建后 CHANGELOG 登记（ADD 条目），不溯改历史记录。
3. **授权钉版适配探针**：预算刚性 ≤8 次真实模型调用（最小 prompt），全部以探针记录留痕（照 sf0004-probes 先例）；只允许进程级 env 派生配置副本机制，**禁止修改 ~/.zcode 全局配置**（B-03 红线继续有效）。找到可逐字钉中 GLM-5.3@account:bigmodel-individual-coding-plan 与 Minimax-M3.1-Flash-Preview@minimax 的机制后，先行单臂验证再申请新一轮冒烟。
4. 探针失败也是有效结果：若本机 runtime 确实无法钉版，如实报告，矩阵族构成问题升级 owner（更换宿主或调整矩阵）。

签署：planner（主代理），2026-10-08。供 owner 审阅。
