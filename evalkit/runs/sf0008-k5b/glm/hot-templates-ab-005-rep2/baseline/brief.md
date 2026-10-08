使用 hot-templates 技能完成两项工程性验收（不要求产出常规骨架交付目录）：① 用完全相同的输入（platform=dy，topic=确定性复跑主题，points=["要点甲", "要点乙", "要点丙"]）连续生成两次到两个不同输出目录，逐字节比对两份 骨架.md 与 structure.json；② 分别用非法 platform（如 bilibili）与空 topic（空白串）各触发一次生成，观察退出码、stderr 与输出目录是否被创建。
把本次任务中每一次生成调用的记录（输入参数、退出码、stderr 摘要、产生的文件清单）写入 run_log.json，与产物同级放在工作目录下。

