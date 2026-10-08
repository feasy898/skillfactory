# SF-0008 盲评判分任务（hot-templates / ab-005）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 确定性：两次生成的 骨架.md 与 structure.json 均逐字节一致（引擎无时间戳、无随机数）
2. 失败路径：非法 platform 退出码为 2 且不创建输出目录；空 topic 退出码为 2、stderr 有报错且不创建输出目录
3. 成功路径不受影响：合法输入仍以退出码 0 结束并写出 骨架.md + structure.json 两份文件，成功行打印 OK 前缀

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json
- P2: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json
- P3: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json
- P4: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json
- P5: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json
- P6: run1__structure.json, run1__骨架.md, run2__structure.json, run2__骨架.md, run_log.json

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
