# SF-0008 盲评判分任务（office-templates / ab3-empty-and-string-lists）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 空列表按必填缺失渲染占位条目：周报「一、本周工作内容」节含「1．____」，工作总结「主要成绩」节含「1．____」，fields.json rendered_as 为占位条目语义
2. 字符串型列表单项化正确：工作总结 case2 的 工作回顾="完成评测平台月度巡检" 渲染为单项条目且 fields.json value=["完成评测平台月度巡检"]
3. 选填小节整节省略：周报 case2 文书中不出现「问题与需协调事项」节头、工作总结 case2 不出现「存在问题」节，但 fields.json 仍记 missing（required=false）
4. 缺失记账与 spec §9 一致：周报 missing_required=[部门,周期,本周工作内容]（标题为「____工作周报」），工作总结 missing_required=[总结主体,主要成绩]（标题为「____2026年9月工作总结」）
5. 小节编号与条目编号规范（一、二、三、与 1．2．3．），落款右对齐不因空日期/缺主体破坏（工作总结空成文日期行为空段，末个非空段仍右对齐）

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: 周报__case2__fields.json, 周报__case2__文书.docx.extract.txt, 工作总结__case2__fields.json, 工作总结__case2__文书.docx.extract.txt
- P2: 周报__case2__fields.json, 周报__case2__文书.docx.extract.txt, 工作总结__case2__fields.json, 工作总结__case2__文书.docx.extract.txt
- P3: 周报__case2__fields.json, 周报__case2__文书.docx.extract.txt, 工作总结__case2__fields.json, 工作总结__case2__文书.docx.extract.txt
- P4: 周报__case2__fields.json, 周报__case2__文书.docx.extract.txt, 工作总结__case2__fields.json, 工作总结__case2__文书.docx.extract.txt

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
