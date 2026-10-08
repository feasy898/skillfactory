# hot t02 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. **端态**：两产物齐且非空，时间轴/卖点零改写。
2. **六镜冻结**：shot_1..6 的 meta.time_range 依次=`00:00-00:03`、`00:03-00:10`、`00:10-00:20`、`00:20-00:30`、`00:30-00:40`、`00:40-00:45`；duration_sec=3/7/10/10/10/5；要素 name=分镜N（起-止）。
3. **双列填充**：shot_3..5 的口播列以 `第<X>招，<卖点原文>。【占位:口播补充一句效果】` 形态出现（X∈一/二/三），字幕列含 `字幕要点：<卖点原文>`；卖点必须原文逐字（含「3500K」「磁吸加挂钩」）。
4. **meta 7 键**：每镜 meta 恰含 shot_no/time_range/duration_sec/visual/voiceover/subtitle/beat 七键。
5. **总表与统计**：骨架.md 含表头 `| 序号 | 时间轴 | 画面 | 口播 | 字幕 |`、「分镜总表」节聚合 6 行、「共 45 秒」字样；shot_1 口播含「露营灯选购」、shot_6 口播占位【占位:下期选题】。
6. **占位统计（复审第 6 条口径）**：对 `structure.json` 的 `elements[].text` 逐要素跑占位正则求和，期望 total=**12**（shot_1 1 + shot_2 3 + shot_3..5 各 2 + shot_6 2）；placeholder_stats.total_open 一致；骨架.md 统计节同源（`**12 处**`）。**骨架.md 全文 token 计数不作口径（分镜行在正文与分镜总表各渲染一遍、表格行最多携带 3 个 token：全文 token 实测=37、分布在 25 行——2026-10-09 引擎实测，复审第二轮 R7 更正原记 24；为已知口径陷阱）。**

## 期望（引擎实测 2026-10-09）

element_count=6；elements[].text 占位合计=12（per-element：shot_1 1/shot_2 3/shot_3..6 各 2）；placeholder_stats={total_open:12, total_filled_from_input:4}；points_used=3 条原文、points_unused=[]。

## 判挂点

判挂点统一计分规则（复审第二轮 R1）：加权分按 rubric 公式（10 × Σ(维度分×权重)/Σ权重，0-10 刻度舍 1 位）重算，必须真实跌破通过线。

- 时间轴手工推算错 1 镜（00:20-00:30 边界）→ 正确性错（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.16+0.3+0.3=0.76 → 7.6 < 8.0。
- 口播「第一招」写成「第1招」、卖点改写 → 正确性错（0.4 档）⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.76 → 7.6 < 8.0。
- meta 漏 beat 键 → 完整性错（0.3 档）⟦正确性=1.0,完整性=0.3,可验证性=1.0⟧ → 0.4+0.09+0.3=0.79 → 7.9 < 8.0。

## 机判方法

读 structure.json 逐镜断言 meta 7 键/time_range/duration_sec 与双列文本；骨架.md 断言表头/总表/共 45 秒/统计节。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform video --topic 露营灯选购 --points '["色温选 3500K 左右最显食物本色", "续航按高出实际时长一倍选", "磁吸加挂钩双固定更百搭"]' --outdir <tmp>`，exit 0。真值：elements=6、elements[].text 占位合计=12、stats={12,4}。