# SF-0008 盲评判分任务（office-templates / ab1-standard-four-templates）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（冻结原文，逐条判分）
1. 四个单元目录 package/out/<模板>/case1/ 均恰含 文书.docx 与 fields.json，python eval/runner.py package/out oracle/out 的 units_found/products_exact 全部 pass
2. 版式四要素对四类全部成立（spec V2–V5）：标题居中黑体二号且与 fields.json.title 相等；请示函/会议通知称谓顶格；正文存在 firstLineChars=200 的仿宋三号 28 磅固定行距段；落款右对齐右空两字
3. A4 页面版心按 GB/T 9704（上3.7/下3.5/左2.8/右2.6 cm，容差 0.05 cm），标题文案符合四条公式（如 关于{请示事由}的请示）
4. 四份 fields.json 顶层与 summary 键集合恰为 spec §6 所列，filled/missing 计数与明细自洽，且四类 case1 均 filled=total/total（周报 7/7、请示函 8/8、会议通知 11/11、工作总结 7/7）
5. 与参照的字段填充一致率 ≥90%（runner 的 field_fill_agreement_ge_90pct pass，自校验口径 oracle vs oracle 为 100%）

评分规则（S8-JUDGE-v1）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt, 周报__case1__fields.json, 周报__case1__文书.docx.extract.txt, 工作总结__case1__fields.json, 工作总结__case1__文书.docx.extract.txt, 请示函__case1__fields.json, 请示函__case1__文书.docx.extract.txt
- P2: 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt, 周报__case1__fields.json, 周报__case1__文书.docx.extract.txt, 工作总结__case1__fields.json, 工作总结__case1__文书.docx.extract.txt, 请示函__case1__fields.json, 请示函__case1__文书.docx.extract.txt
- P3: 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt, 周报__case1__fields.json, 周报__case1__文书.docx.extract.txt, 工作总结__case1__fields.json, 工作总结__case1__文书.docx.extract.txt, 请示函__case1__fields.json, 请示函__case1__文书.docx.extract.txt
- P4: 会议通知__case1__fields.json, 会议通知__case1__文书.docx.extract.txt, 周报__case1__fields.json, 周报__case1__文书.docx.extract.txt, 工作总结__case1__fields.json, 工作总结__case1__文书.docx.extract.txt, 请示函__case1__fields.json, 请示函__case1__文书.docx.extract.txt

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
