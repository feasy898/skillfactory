# SF-0008 盲评判分任务（hot-templates / ab-001）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 结构：structure.json 含全部 6 个要素且 id 顺序为 hook_3s、pain_point、value_1、value_2、value_3、cta，其中钩子（hook_3s）与 CTA（cta）的 text 均非空
2. 填充：3 条卖点分别出现在 value_1/value_2/value_3 的 text 中且 filled_from_input 含 point#1、point#2、point#3；points_used 为 3 条原文；value 槽位无【占位:价值点N】
3. 自洽：每个 element 的 placeholder_count 与 text 中【占位:…】正则重计数一致；placeholder_stats.by_element 求和 == total_open；骨架.md 主题行含「通勤时间管理」且尾部有「占位符统计」节
4. 纯净：两份产物中均无 {{ 或 }} 模板残留

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
