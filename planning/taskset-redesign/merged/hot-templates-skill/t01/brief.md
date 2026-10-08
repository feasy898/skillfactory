# ht-t01 · wx 满 3 卖点

## 任务

用 hot-templates 技能生成公众号文章爆款骨架：platform=`wx`，topic=`宿舍省电费`，points=`["离开寝室随手断插排", "空调设 26 度配合风扇", "插座改用带开关款"]`（内联 JSON 串），产物写入 `<outdir>`（`骨架.md` + `structure.json`）。

## 判定要点（全部可机判）

1. **成功三判据**：exit 0；stdout 一行 `OK platform=wx topic=宿舍省电费 elements=5 open_placeholders=10 filled_from_input=7 -> <outdir>`（数值部分精确）；两产物存在且非空。
2. **结构**：5 要素 id 顺序=lead_in、thesis_what、thesis_why、thesis_how、golden_ending；三个 thesis 要素 text 分别以「一、是什么」「二、为什么」「三、怎么办」开头。
3. **三抓手填充**：thesis_how text 含三行，格式 `1. 离开寝室随手断插排——【占位:展开：具体做法+一个例子】`、`2. 空调设 26 度配合风扇——…`、`3. 插座改用带开关款——…`（卖点原文入行、价值点槽位零占位）。
4. **filled 语义**：thesis_how 的 filled_from_input=[point#1, point#2, point#3]；lead_in/thesis_what/thesis_why/golden_ending 各含 "topic"；total_filled_from_input=7。
5. **金句**：golden_ending text 含「宿舍省电费这件事，」与「共勉。」。
6. **占位统计**：全产物 `【占位:([^】]*)】` 正则重计 total=10（lead_in 1 + thesis_what 2 + thesis_why 3 + thesis_how 3 + golden_ending 1）；structure.json 的 placeholder_stats 与之一致；骨架.md「占位符统计」节同源。
7. **纯净**：无 `{{`/`}}` 残留；points_unused=[]；points_used=3 条原文。
