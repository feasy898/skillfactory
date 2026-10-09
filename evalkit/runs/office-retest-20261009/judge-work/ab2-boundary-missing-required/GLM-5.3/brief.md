# office 重测盲评判分任务（ab 题：ab2-boundary-missing-required）

你是盲评裁判。以下为本任务的匿名化产物（P1..Pn，顺序随机，来源对你保密）。

## rubric（golden.json 冻结原文，逐条判分）
1. 必填缺失以____占位且程序退出码 0：请示函渲染「____：」顶格称谓与「____」请示事项（文中____出现次数 ≥ missing_required 数），会议通知标题为「关于召开____的通知」
2. fields.json 记账与 spec §9 期望表一致：请示函 missing_required=[主送机关,请示事项]、选填 missing=[联系电话,成文日期]；会议通知 missing_required=[会议名称,会议地点]、unknown_keys=[备注]
3. 选填缺失不误记为必填：联系电话/成文日期等 rendered_as 为留空/省略语义且不出现在 missing_required_names，正文行内留空（如 联系人：李工　　联系电话：）、独立小节省略
4. 落款仍右对齐右空两字（请示函两行、会议通知两行），称谓段仍顶格，版式不因缺数据而破坏
5. runner 对应单元的 boundary_reported 与 fields_match_docx 均 pass，与参照字段填充一致率 ≥90%

评分规则（S8-JUDGE-v2-OFXRETEST-1 / ab 题协议，照 K5B）：
- 对每条 rubric 项独立打分：0=完全不符 / 0.5 / 1=部分符合 / 1.5 / 2=完全符合。
- 每条打分必须附实测证据（引用暂存文件中的具体事实/原文/数字）；无证据的分数无效。证据必须精简（每条 rubric 项 ≤150 字），优先保证 verdict JSON 完整输出。
- ab5 协议注记（planner 裁决 9827318）：第 3、4 条（runner 对拍、红绿自校验）以暂存目录所附 _replay_facts.json（裁判侧臂外机械重放）为计分依据；第 1、2、5 条按产物自含与 run_log 留痕辅助证据正常判。
- 产物总分 total = round(10 × Σ项分 ÷ (2×项数), 1)，区间 [0,10]。
- 你不知道也不得推测产物的来源臂、模型或顺序；只按 rubric 与证据判分。
- verdict.json 结构（紧凑，必须遵守）：{"scores": {"P1": {"total": x.x, "evidence": "≤150 字逐项证据摘要"}}, ...}（每个产品一个键；不要 items 数组、不要其他顶层键）。

## 产物清单
- P1: run_log.json, 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt
- P2: 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt
- P3: 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt
- P4: run_log.json, 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt
- P5: run_log.json, 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt
- P6: 会议通知__case2__fields.json, 会议通知__case2__文书.docx.extract.txt, 请示函__case2__fields.json, 请示函__case2__文书.docx.extract.txt

请阅读同目录各 P* 子目录内的文件后，把 verdict.json 写入当前工作目录（仅输出该文件）。
