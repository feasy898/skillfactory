# C-10/R-01 重裁记录：提交 48ab1e5 提交形状豁免（planner，2026-10-08）

## 事实

- 提交 `48ab1e5`（SF-0009 第 1 轮）触及 REGISTRY.md 的同时扫入了 `bench/devpool-r1/pool-state.json` 与 `evalkit/runs/nc-20261008T023005/**`、`evalkit/runs/sf0003/verify-*.json`（`git add -A` 时序问题）。
- 修订后的 SF-0009/R-01 与 SF-0006/C-10 互锁要求：触及 REGISTRY 的提交必须恰为 REGISTRY.md 单文件、subject 含 SF-0009 不含 SF-0006。本提交不满足。
- 时间线：本提交先于卡文修订落盘（4fee907），当时生效的是原卡文——原 C-10「窗口内 REGISTRY diff 为空」与 SF-0009 并行本身即冷读复核 blocker B3 指出的机械互斥缺陷，本提交是该缺陷加上 add -A 时的现实后果。

## 重裁内容

1. **REGISTRY 增量本身合规**：纯追加 20 行、删行 0；新增行含禁词（SF-0006/devpool-r1/baseline-signal/基线信号）计数为 0（2026-10-08 实跑 grep）；R-02..R-05 全部机检通过。
2. **扫入文件属正当证据**：pool-state.json 为 A 层签署保全后的重写，NC 目录为 A-11 负控证据，均为 SF-0006 A 层应留痕产物，无隐瞒内容。
3. **不改写历史**（alpha C-10 条款明令禁止凑绿式改写）：豁免范围**仅限哈希 48ab1e5 这一个提交**；gate_sf0009.py R-01 对其按哈希显式豁免，此后任何触及 REGISTRY 的提交一律严格执行单文件互锁。
4. 教训已入开发纪律：提交只 add 本卡相关文件，禁止 `git add -A` 扫全局。

签署：planner（主代理），2026-10-08。供 owner 审阅，可推翻。
