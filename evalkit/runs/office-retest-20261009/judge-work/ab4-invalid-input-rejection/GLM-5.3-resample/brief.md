# office 重测盲评判分任务（ab 题：ab4-invalid-input-rejection）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（golden.json 冻结原文，逐条判分）
1. 四组非法输入退出码均为 2（不是崩溃/其他码），stderr 打印中文错误信息，且与参照 oracle 的退出码逐组一致
2. 四组非法输入均零产物残留：不创建 outdir、不写 文书.docx 或 fields.json（find 计数=0），不产半成品
3. 合法对照组退出码 0 且两产物齐全，证明拒绝逻辑未误伤正常输入
4. SKILL.md 错误处理节逐条列出四种非法输入与退出码表（contract §4.7），与实测行为一致
5. 被测不得把必填缺失当作错误（spec C3/F7）：含缺失的 case2 输入必须 exit 0 并产出，与负路径行为形成对照

评分规则（S8-JUDGE-v2-OFXRETEST-1 / ab 题协议，照 K5B）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- ab5 协议注记（planner 裁决 9827318）：第 3、4 条（runner 对拍、红绿自校验）以暂存目录所附 _replay_facts.json（裁判侧臂外机械重放）为计分依据；第 1、2、5 条按产物自含与 run_log 留痕辅助证据正常判。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- Q1: run_log.json, 周报__case1__fields.json, 周报__case1__文书.docx.extract.txt

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
