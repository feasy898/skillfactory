# ht-t04 · dy 冻结句式逐字 + stdout 契约

## 任务

用 hot-templates 技能生成抖音口播骨架：platform=`dy`，topic=`二手书循环`，points=`["教材按学期末集中回收", "封面破损评级再定价", "跨界换书市集引流"]`，产物写入 `<outdir>`。

## 判定要点（全部可机判）

1. **OK 行契约**（SKILL 使用步骤 3）：stdout 恰一行匹配
   `^OK platform=dy topic=二手书循环 elements=6 open_placeholders=6 filled_from_input=4 -> \S+$`
   （filled_from_input=4 已实测校准：hook_3s 记 topic 1 次 + value_1..3 各记 point#N；pain_point/cta 为空）
2. **钩子逐字冻结**：hook_3s 的 text 逐字等于
   `别划走！还在为「二手书循环」反复内耗的人，这条视频就是给你准备的——【占位:可替换为你的原创钩子强句，一句制造好奇或冲突】`
3. **CTA 冻结**：cta 的 text 含 `点赞收藏，评论区扣「1」` 且含 `【占位:配套资料/下期选题】`。
4. **价值点槽位**：value_1..3 的 text 形态为 `第<X>招：<卖点原文>。【占位:一句话展开：怎么做/效果/案例】`（X∈一/二/三，实测校准）；三槽位无【占位:价值点N】。
5. **结构**：6 要素 id 顺序=hook_3s、pain_point、value_1、value_2、value_3、cta；structure.json 顶层恰 11 键（template_version="1.0"/platform/platform_name/structure_name/topic/points_input_count/points_used/points_unused/element_count/elements/placeholder_stats）；platform_name=`抖音口播稿`。
6. **统计同源**：占位正则重计 total=6（每要素恰 1 token）；placeholder_stats.by_element 求和=6；骨架.md 统计节 `- 未填占位符（待人工/AI 补写）：**6 处**`。
