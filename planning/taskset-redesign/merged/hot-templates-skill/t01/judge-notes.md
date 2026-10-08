# hot t01 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. **端态三判据**：两产物（`骨架.md` + `structure.json`）存在且非空、内容与输入一致（topic/卖点零改写）。
2. **结构**：5 要素 id 顺序=lead_in、thesis_what、thesis_why、thesis_how、golden_ending；三个 thesis 要素 text 分别以「一、是什么」「二、为什么」「三、怎么办」开头。
3. **三抓手填充**：thesis_how text 含三行，格式 `1. 离开寝室随手断插排——【占位:展开：具体做法+一个例子】`、`2. 空调设 26 度配合风扇——…`、`3. 插座改用带开关款——…`（卖点原文入行、价值点槽位零占位）。
4. **filled 语义**：thesis_how 的 filled_from_input=[point#1, point#2, point#3]；lead_in/thesis_what/thesis_why/golden_ending 各含 "topic"；total_filled_from_input=7。
5. **金句**：golden_ending text 含「宿舍省电费这件事，」与「共勉。」。
6. **占位统计（复审第 6 条口径）**：对 `structure.json` 的 `elements[].text` 逐要素跑 `【占位:([^】]*)】` 正则求和，期望 total=**10**（lead_in 1 + thesis_what 2 + thesis_why 3 + thesis_how 3 + golden_ending 1）；structure.json 的 placeholder_stats.total_open 与之一致；骨架.md「占位符统计」节同源（`- 未填占位符（待人工/AI 补写）：**10 处**`）。骨架.md 正文的 token 出现次数不作为统计口径。
7. **纯净与记账**：无 `{{`/`}}` 残留；points_unused=[]；points_used=3 条原文。

## 期望（引擎实测 2026-10-09）

element_count=5；elements[].text 占位合计=10（per-element：lead_in 1/thesis_what 2/thesis_why 3/thesis_how 3/golden_ending 1）；placeholder_stats={total_open:10, total_filled_from_input:7}；points_used=3 条原文、points_input_count=3、points_unused=[]。**注意：stdout OK 行不再作为判分项（复审第 14 条），仅作辅助线索。**

## 判挂点

判挂点统一计分规则（复审第二轮 R1）：加权分按 rubric 公式（10 × Σ(维度分×权重)/Σ权重，0-10 刻度舍 1 位）重算，必须真实跌破通过线。

- thesis_how 三行误把卖点写进【占位】或漏「——」连接符 → 正确性错（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.16+0.3+0.3=0.76 → 7.6 < 8.0。
- filled_from_input 只记 point# 不记 4 次 topic（total=3 而非 7）→ 端态统计错 ⟦正确性=1.0,完整性=1.0,可验证性=0.3⟧ → 0.4+0.3+0.09=0.79 → 7.9 < 8.0。
- 要素缺失/顺序错/卖点被改写 → 正确性零档 ⟦正确性=0,完整性=1.0,可验证性=1.0⟧ → 0+0.3+0.3=0.60 → 6.0 < 8.0。

## 机判方法

读 structure.json 断言（要素序/逐要素 text/placeholder_stats/points_*），读 骨架.md 断言统计节同源。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform wx --topic 宿舍省电费 --points '["离开寝室随手断插排", "空调设 26 度配合风扇", "插座改用带开关款"]' --outdir <tmp>`，exit 0。真值：elements=5、elements[].text 占位合计=10、stats={10,7}。