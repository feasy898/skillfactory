# hot t04 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. **钩子逐字冻结**：hook_3s 的 text 逐字等于
   `别划走！还在为「二手书循环」反复内耗的人，这条视频就是给你准备的——【占位:可替换为你的原创钩子强句，一句制造好奇或冲突】`
2. **CTA 冻结**：cta 的 text 含 `点赞收藏，评论区扣「1」` 且含 `【占位:配套资料/下期选题】`。
3. **价值点槽位**：value_1..3 的 text 形态为 `第<X>招：<卖点原文>。【占位:一句话展开：怎么做/效果/案例】`（X∈一/二/三，实测校准）；三槽位无【占位:价值点N】。
4. **结构**：6 要素 id 顺序=hook_3s、pain_point、value_1、value_2、value_3、cta；structure.json 顶层恰 11 键（template_version="1.0"/platform/platform_name/structure_name/topic/points_input_count/points_used/points_unused/element_count/elements/placeholder_stats）；platform_name=`抖音口播稿`。
5. **统计同源（复审第 6 条口径）**：structure.json elements[].text 占位合计=**6**（每要素恰 1 token）；placeholder_stats.by_element 求和=6、total_filled_from_input=4（hook_3s 记 topic 1 次 + value_1..3 各记 point#N；pain_point/cta 为空）；骨架.md 统计节 `- 未填占位符（待人工/AI 补写）：**6 处**`。
6. **复审第 14 条**：stdout OK 行不再作为判分项；「生成方式正确」的证据由端态承担——钩子逐字 + OK 行数值等价物（placeholder_stats 端态值）+ 统计节格式三处联合。手写骨架在钩子逐字与统计节格式两处仍必露馅。

## 期望（引擎实测 2026-10-09）

element_count=6；elements[].text 占位合计=6（每要素 1）；stats={6,4}；points_used=3 条原文、points_input_count=3、points_unused=[]。

## 判挂点

判挂点统一计分规则（复审第二轮 R1）：加权分按 rubric 公式（10 × Σ(维度分×权重)/Σ权重，0-10 刻度舍 1 位）重算，必须真实跌破通过线。

- 句式差 1 字符（引号/破折号）→ 正确性降档（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.16+0.3+0.3=0.76 → 7.6 < 8.0；句式重写或卖点改写 → 正确性零档 ⟦正确性=0,完整性=1.0,可验证性=1.0⟧ → 0.60 → 7.0 < 8.0。
- structure.json 键缺失或统计错 → 完整性错（0.3 档）⟦正确性=1.0,完整性=0.3,可验证性=1.0⟧ → 0.4+0.09+0.3=0.79 → 7.9 < 8.0。

## 机判方法

读 structure.json 逐要素逐字断言 + 顶层键清点 + stats 断言；骨架.md 统计节断言。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform dy --topic 二手书循环 --points '["教材按学期末集中回收", "封面破损评级再定价", "跨界换书市集引流"]' --outdir <tmp>`，exit 0。真值：elements=6、占位合计=6、stats={6,4}。