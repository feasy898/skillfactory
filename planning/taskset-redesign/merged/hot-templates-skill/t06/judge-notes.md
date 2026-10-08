# hot t06 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

规整为**位置式**（前 3 个输入项按位进 3 个槽位；空白项的槽落占位；第 4 起保序记 unused）：

1. **槽位分配**：
   - point_block_1 小标题=「无纸化申报随附单证自拍存档」（第 1 项）；
   - point_block_2 含 `【占位:价值点2】`，且**不得**出现「错峰值机攻略」（第 3 项不许前移补位）；
   - point_block_3 小标题=「错峰值机攻略」（第 3 项）。
2. **复述句**：summary_block 三点=`无纸化申报随附单证自拍存档、【占位:价值点2】、错峰值机攻略`。
3. **记账**：points_used=[「无纸化申报随附单证自拍存档」, null, 「错峰值机攻略」]；points_unused=[「候补票改签时限」, 「会员日里程翻倍」]（第 4、5 项保序）；points_input_count=5。
4. **title 数字恒为 3**：title 仍含数字 `3`（模板冻结=价值点槽数，不随实际填充数变 2）。
5. **计数（复审第 6 条口径；复审第 7 条统一值）**：structure.json elements[].text 占位合计=**9**（title 1+hook 1+pb1 1+pb2 2+pb3 1+summary 2+tag 1）；filled_from_input 合计=**8**（point#1 与 point#3 各记 point_block 与 summary_block、topic 类记 title/hook/tag 3 次）；OK 行数值的端态等价物=placeholder_stats={total_open:9, total_filled_from_input:8}；骨架.md 统计节同源（`**9 处**`）；emoji 映射不受影响。

## 期望（引擎实测 2026-10-09）

element_count=7；elements[].text 占位合计=9（per-element：title 1/hook_block 1/point_block_1 1/point_block_2 2/point_block_3 1/summary_block 2/tag_group 1）；stats={9,8}；points_used=[…, null, …]、points_unused=[项4,项5]、points_input_count=5。

## 判挂点

- **收集式错误**（槽=[项1,项3,项4]、unused=[项5]、槽 2 无占位）→ 正确性 0.3 档（口径违反但产物自洽）。
- 槽位/复述句错 1 处 → 正确性 0.4 档；全乱 → 0。
- points_used 无 null 位 / input_count≠5 / title 数字变 2 → 记账错。
- filled_from_input 写 7 或 10 → 统计错（统一期望=8）。

## 机判方法

读 structure.json 断言槽位/复述/记账/统计端态值；骨架.md 断言统计节同源。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform xhs --topic 无纸化通关 --points '["无纸化申报随附单证自拍存档", "   ", "错峰值机攻略", "候补票改签时限", "会员日里程翻倍"]' --outdir <tmp>`，exit 0。
真值：elements[].text 占位合计=9、placeholder_stats={total_open:9, total_filled_from_input:8}、points_used=[…, null, …]、points_unused=[候补票改签时限, 会员日里程翻倍]、points_input_count=5——filled=8 实测坐实，对冲表述删除。