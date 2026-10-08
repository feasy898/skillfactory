# hot t03 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. **strip 规整**：points_used[0]==`三档承重分装更护肩`（strip 后）；point_block_1 小标题=strip 后卖点；topic 入 title/summary_block 时为首尾空白 strip 后的 `#通勤背包选购`（`#` 保留——只有标签派生才去 #）。
2. **标题**：title text 含 `🔥` 且含数字 `3`（=模板冻结的价值点槽数）；meta.emoji=🔥。
3. **emoji 映射**：hook_block=✅、point_block_1..3=💡、summary_block=📌、tag_group=🏷️（meta.emoji 逐键断言）。
4. **首标签派生**：tag_group text 含 `#通勤背包选购`（clean_tag=`re.sub(r"[\s#]+","",topic)` 去掉 # 与全部空白后前置 #）；字面 4 标签 `#通勤背包选购 #干货分享 #方法论 #自我提升` 齐全；正则 `#[^\s#]+` 对 tag_group text 计数=6（含占位 token 内 2 个示例标签）。
5. **summary_block 三点复述**：`#通勤背包选购的核心就三点：三档承重分装更护肩、YKK 拉链六年质保、背部独立鞋仓。`（3 卖点 strip 后原文）+【占位:一句互动引导，如：你最想先试哪个？评论区聊聊】。
6. **计数（复审第 6 条口径）**：structure.json elements[].text 占位合计=**7**（7 要素各 1）；placeholder_stats={total_open:7, total_filled_from_input:10}（10=title/hook_block/tag_group 各记 topic 类 1 次 + summary_block 记 topic+point#×3 共 4 次 + point_block_1..3 各记 point#N）；points_used=3 条 strip 后原文；points_unused=[]；无 {{}} 残留。骨架.md 统计节同源（`**7 处**`）。

## 期望（引擎实测 2026-10-09）

element_count=7；elements[].text 占位合计=7；stats={7,10}；points_used=[三档承重分装更护肩, YKK 拉链六年质保, 背部独立鞋仓]；topic 入 structure.json=`#通勤背包选购`。

## 判挂点

判挂点统一计分规则（复审第二轮 R1）：加权分按 rubric 公式（10 × Σ(维度分×权重)/Σ权重，0-10 刻度舍 1 位）重算，必须真实跌破通过线。

- 把 `#通勤背包选购` 再 strip 成「通勤背包选购」进 title（多剥了 #）→ 正确性错（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.16+0.3+0.3=0.76 → 7.6 < 8.0。
- 首标签留内部空格或多余 # → 派生错（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.76 → 7.6 < 8.0。
- 标签计数写 4 或 8 → 计数口径错（0.3 档）⟦正确性=1.0,完整性=0.3,可验证性=1.0⟧ → 0.4+0.09+0.3=0.79 → 7.9 < 8.0。

## 机判方法

读 structure.json 断言 strip/派生/emoji/标签计数/统计；骨架.md 断言统计节同源。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform xhs --topic ' #通勤背包选购 ' --points '["  三档承重分装更护肩  ", "YKK 拉链六年质保", "背部独立鞋仓"]' --outdir <tmp>`，exit 0。真值：elements=7、占位合计=7、stats={7,10}、points_used 全 strip。