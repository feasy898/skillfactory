# ht-t01 rubric（0–10 加权分，通过线 8.0）

加权分 = Σ(维度分 × 权重) / Σ权重。通过 = 加权分 ≥ 8.0。

| 维度 | 权重 | 满分档 | 中档 | 零分档 |
|---|---|---|---|---|
| 正确性（结构+填充） | 0.4 | 5 要素齐且序正；三抓手=3 卖点原文行格式逐字；filled 语义（4×topic+3×point#=7） | 1 处错 0.5 | 要素缺失/顺序错/卖点被改写 |
| 完整性（产物与统计） | 0.3 | 两产物齐非空；占位 10 处重计一致；骨架.md 统计节同源；无 {{}} 残留 | 统计错 1 处 0.5 | 文件缺失 |
| 可验证性（OK 行与台账式自洽） | 0.3 | OK 行精确（elements=5 open_placeholders=10 filled_from_input=7）；points_used=3 原文、points_unused=[]；golden_ending 含「共勉。」 | OK 行数值错 1 个 0.5 | stdout 无 OK 行 |

## design_note（防饱和依据）

- 与旧题差异：旧 ab-003（wx 零卖点）考占位与 [null,null,null]；本题考**满配**下 wx 特有的「topic 记 4 次」语义与 thesis_how 三行格式——旧集 4 平台能力题（ab-001~004）各平台只考了一种卖点形态，wx 满配、video 满配均为空白。
- 裸模型高发失分：thesis_how 三行误把卖点写进【占位】或漏「——」连接符；filled_from_input 只记 point# 不记 4 次 topic（total=3 而非 7）；OK 行数值与实产不符。
