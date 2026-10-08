# SF-0008 盲评判分任务（office-templates / ab5-determinism-layout-selfeval）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 确定性：同输入连跑两遍，fields.json（除 outputs 键外）逐字节一致，文书.docx 解析后的段落文本/对齐/缩进/字体/行距完全一致（无当前时间、随机内容等不可复现源）
2. 交付布局正确：package/out/会议通知/case1 为恰含两产物的单元目录，相对名与参照 oracle/out/会议通知/case1 配对
3. python eval/runner.py package/out oracle/out 输出 ok=true 且 exit 0，六类检查对全部单元 pass（含 field_fill_agreement_ge_90pct）
4. runner 自校验红绿双向成立：python eval/runner.py oracle/out oracle/out 全过 exit 0（绿），python eval/runner.py <空目录> oracle/out 报 units_found 失败且 exit 1（红）
5. package/ 三件套（SKILL.md、scripts/gen_doc.py、requirements.txt）齐全，入口脚本可 py_compile 且按 contract §2 命令行直接运行成功

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: run_log.json, 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt
- P2: run_log.json, 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt
- P3: run_log.json, 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt
- P4: run_log.json, 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
