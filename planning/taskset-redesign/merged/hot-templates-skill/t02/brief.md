# ht-t02 · video 满 3 卖点

## 任务

用 hot-templates 技能生成短视频分镜表骨架：platform=`video`，topic=`露营灯选购`，points=`["色温选 3500K 左右最显食物本色", "续航按高出实际时长一倍选", "磁吸加挂钩双固定更百搭"]`，产物写入 `<outdir>`（`骨架.md` + `structure.json`）。

## 判定要点（全部可机判）

1. **成功三判据**：exit 0；OK 行 `OK platform=video topic=露营灯选购 elements=6 open_placeholders=12 filled_from_input=4 -> <outdir>`（数值精确）；两产物齐。
2. **六镜冻结**：shot_1..6 的 meta.time_range 依次=`00:00-00:03`、`00:03-00:10`、`00:10-00:20`、`00:20-00:30`、`00:30-00:40`、`00:40-00:45`；duration_sec=3/7/10/10/10/5；要素 name=分镜N（起-止）。
3. **双列填充**：shot_3..5 的口播列以 `第<X>招，<卖点原文>。【占位:口播补充一句效果】` 形态出现（X∈一/二/三，即第一招/第二招/第三招），字幕列含 `字幕要点：<卖点原文>`；卖点必须原文逐字（含「3500K」「磁吸加挂钩」）。
4. **meta 7 键**：每镜 meta 恰含 shot_no/time_range/duration_sec/visual/voiceover/subtitle/beat 七键。
5. **总表与统计**：骨架.md 含表头 `| 序号 | 时间轴 | 画面 | 口播 | 字幕 |`、「分镜总表」节聚合 6 行、「共 45 秒」字样；占位正则重计 total=12；shot_1 口播含「露营灯选购」、shot_6 口播占位【占位:下期选题】。
