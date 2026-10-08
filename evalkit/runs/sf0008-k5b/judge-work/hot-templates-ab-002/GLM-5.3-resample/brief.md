# SF-0008 盲评判分任务（hot-templates / ab-002）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 结构：7 个要素齐备（title、hook_block、point_block_1..3、summary_block、tag_group）；title 的 text 含 🔥 且含数字 3
2. emoji 规则：meta.emoji 按映射表冻结——hook_block=✅、point_block_*=💡、summary_block=📌、tag_group=🏷️
3. 截断策略：仅前 3 条卖点进正文干货块（filled_from_input 含 point#1..3），第 4、5 条原文完整且保序记入 points_unused，points_used 恰为前 3 条
4. 标签组：tag_group 的 text 含 3-8 个 # 话题标签，且首标签由主题派生（#租房避坑指南，已去空白与 #）

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- Q1: structure.json, 骨架.md

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
