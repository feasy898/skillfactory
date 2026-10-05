# r1-probe 轮作废标记（O-6 条款执行 · SF-0003）

> 依据：PLAN §8 O-6【已裁定】——zcode headless 实测模型落点 = **GLM-5.3**
> （`account:bigmodel-individual-coding-plan/GLM-5.3`，两臂 model_usage 一致；
> 非 EVAL-SPEC §4.1 钉版的 GLM-5.3-Flash，且 headless 无 `--model` 选项）。
> 触发条款后半句：**bump evalbench 版本（v6-mvp-0.1 → v6-mvp-0.2）、旧基线作废**。

## 处置

- **本轮（runs/r1-probe/）全部数字：citable: false，不得引用。**
  matrix.json、报告 §2 步 2 表、任何 token/墙钟数字——包括本就已按
  「管线验证信号」口径封存的表述在内——在 v6-mvp-0.2 口径下一律不得与新轮并列或对比。
- baseline/ 无 r1-probe 基线文件（该轮从未写入 baseline/），作废动作走分支 B
  显式零记录：见 `runs/sf0003-baseline-void.json`（voided_count=0）。
- 后续轮次对照请使用 evalbench v6-mvp-0.2 口径（`aggregate.py --evalbench-version`），
  跨版本并列会被 AG-7 拒绝门拦下（exit≠0，不出数）。

留痕：SF-0003 · worker-glm-m4 · 2026-10-03 · 复现与证据链：SF-0001 报告 §4.1
（D:\new-workspace\agent-asset\planning\reports\SF-0001-ws1-report.md）。
