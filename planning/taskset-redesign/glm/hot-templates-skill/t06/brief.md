# ht-t06 · 夹心空白卖点：位置式规整

## 任务

用 hot-templates 技能生成小红书图文骨架：platform=`xhs`，topic=`无纸化通关`，points=`["无纸化申报随附单证自拍存档", "   ", "错峰值机攻略", "候补票改签时限", "会员日里程翻倍"]`（第 2 项为纯空白串），产物写入 `<outdir>`。

## 判定要点（全部可机判）

规整为**位置式**（前 3 个输入项按位进 3 个槽位；空白项的槽落占位；第 4 起保序记 unused）：

1. **槽位分配**：
   - point_block_1 小标题=「无纸化申报随附单证自拍存档」（第 1 项）；
   - point_block_2 含 `【占位:价值点2】`，且**不得**出现「错峰值机攻略」（第 3 项不许前移补位）；
   - point_block_3 小标题=「错峰值机攻略」（第 3 项）；
2. **复述句**：summary_block 三点=`无纸化申报随附单证自拍存档、【占位:价值点2】、错峰值机攻略`。
3. **记账**：points_used=[「无纸化申报随附单证自拍存档」, null, 「错峰值机攻略」]；points_unused=[「候补票改签时限」, 「会员日里程翻倍」]（第 4、5 项保序）；points_input_count=5；filled_from_input：point#1 与 point#3（point_block_1/3 与 summary_block）。
4. **title 数字恒为 3**：title 仍含数字 `3`（模板冻结=价值点槽数，不随实际填充数变 2）。
5. **计数**：OK 行 `open_placeholders=9 filled_from_input=8`（实测校准：缺 1 槽在 point_block_2 正文与 summary_block 复述各多 1 个【占位:价值点2】→ 7+2=9；filled 由满配 10 减去 point#2 的 2 处记录 → 8）；占位正则重计一致；emoji 映射不受影响。
