# SF-0008 盲评判分任务（hot-templates / ab-003）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 结构：5 个要素齐备（lead_in、thesis_what、thesis_why、thesis_how、golden_ending）；三个 thesis 要素的 text 分别以「一、是什么」「二、为什么」「三、怎么办」开头
2. 零卖点边界：thesis_how 的三个抓手全部落【占位:价值点1】【占位:价值点2】【占位:价值点3】，points_used 为 [null, null, null]，任何要素的 filled_from_input 不含 point#N
3. 收尾与统计：golden_ending 的 text 含「共勉」；placeholder_stats.total_open == by_element 各值之和，且与骨架.md「占位符统计」节的数字一致

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: structure.json, 骨架.md
- P2: structure.json, 骨架.md
- P3: structure.json, 骨架.md
- P4: structure.json, 骨架.md
- P5: structure.json, 骨架.md
- P6: structure.json, 骨架.md

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
