# ht-t06 rubric（0–10 加权分，通过线 8.0）

加权分 = Σ(维度分 × 权重) / Σ权重。通过 = 加权分 ≥ 8.0。

| 维度 | 权重 | 满分档 | 中档 | 零分档 |
|---|---|---|---|---|
| 正确性（位置式槽位） | 0.4 | 槽1=项1、槽2=占位价值点2（无项 3 文本）、槽3=项3；复述句三点形态正确 | 「收集式」错误（槽=[项1,项3,项4]、unused=[项5]）0.3 | 槽位/复述全乱 |
| 完整性（记账与计数） | 0.3 | points_used 含 null 位、unused=第4/5 项保序、input_count=5、title 数字=3、open=9（实测校准） | 记账错 1 处 0.5 | 文件缺失 |
| 可验证性（同源与纯净） | 0.3 | OK 行精确（elements=7 open_placeholders=9 filled_from_input=8，实测校准）；stats 与骨架.md 同源；无 {{}} | OK 行数值错 1 个 0.5 | stdout 无 OK 行 |

filled_from_input 期望总数：point#1（point_block_1）+ point#3（point_block_3）+ summary_block（topic+point#1+point#3=3）+ hook_block/title/tag_group（topic 类 3）= 8？——以引擎实跑为准：判官按「OK 行数值与 structure.json 自洽」断言（filled 数与 filled_from_input 明细一致即得分，不预设具体整数，防设计者对实现细节记忆偏差引入误判）；但槽位/复述句/记账三处的期望值按 brief 精确断言。

## design_note（防饱和依据）

- 与旧题差异：旧 ab-002 是 5 条**全非空**截断（考 unused 保序）；本题在同样 5 条里埋夹心空白，把「位置式 vs 收集式」两种合理直觉放进同一输入——只有严格按 normalize_points 口径（先按位进槽）才得到正确槽位。判据在槽 2/槽 3 内容、复述句形态、points_used 的 null 位三处同时显形。
- 这是「读文档可得、凭直觉必错」的典型边界构造：SKILL.md 输入格式节明文「非空卖点 strip 后入槽；缺失或空白串的**槽位**落占位」——「槽位」二字已定性，但裸模型极少逐字抠这个语义。
