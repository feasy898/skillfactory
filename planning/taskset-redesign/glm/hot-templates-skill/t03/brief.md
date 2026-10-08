# ht-t03 · xhs 满配：strip、标签派生与计数口径

## 任务

用 hot-templates 技能生成小红书图文骨架：platform=`xhs`，topic=「 #通勤背包选购 」（首尾各一个空格、含 `#`），points=`["  三档承重分装更护肩  ", "YKK 拉链六年质保", "背部独立鞋仓"]`（第 1 条首尾空白），产物写入 `<outdir>`。

## 判定要点（全部可机判）

1. **strip 规整**：points_used[0]==`三档承重分装更护肩`（strip 后）；point_block_1 小标题=strip 后卖点；topic 入 title/summary_block 时为首尾空白 strip 后的 `#通勤背包选购`（`#` 保留——只有标签派生才去 #）。
2. **标题**：title text 含 `🔥` 且含数字 `3`（=模板冻结的价值点槽数）；meta.emoji=🔥。
3. **emoji 映射**：hook_block=✅、point_block_1..3=💡、summary_block=📌、tag_group=🏷️（meta.emoji 逐键断言）。
4. **首标签派生**：tag_group text 含 `#通勤背包选购`（clean_tag=`re.sub(r"[\s#]+","",topic)` 去掉 # 与全部空白后前置 #）；字面 4 标签 `#通勤背包选购 #干货分享 #方法论 #自我提升` 齐全；正则 `#[^\s#]+` 计数=6（含占位 token 内 2 个示例标签）。
5. **summary_block 三点复述**：`#通勤背包选购的核心就三点：三档承重分装更护肩、YKK 拉链六年质保、背部独立鞋仓。`（3 卖点 strip 后原文）+【占位:一句互动引导，如：你最想先试哪个？评论区聊聊】。
6. **计数**：OK 行 `elements=7 open_placeholders=7 filled_from_input=10`（10 已实测校准：title/hook_block/tag_group 各记 topic 类 1 次 + summary_block 记 topic+point#×3 共 4 次 + point_block_1..3 各记 point#N——即 filled 明细总数）；points_used=3 条 strip 后原文；points_unused=[]；占位正则重计 total=7；无 {{}} 残留。
