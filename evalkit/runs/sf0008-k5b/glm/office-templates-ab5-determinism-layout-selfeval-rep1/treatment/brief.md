# SF-0008 office 臂任务（ab5-determinism-layout-selfeval）

确定性自评：用完全相同的输入 fixtures/会议通知/case1.json 连续运行生成两遍到同一输出目录 out/会议通知/case1（第二遍覆盖复写第一遍）。
每遍后记录该目录下 文书.docx 与 fields.json 的 sha256 到 run_log.json（标注第几遍），并对两遍产物做逐字节对比，把对比结论（一致/不一致及差异说明）写入 run_log.json。
核心行为要求：同输入连跑两遍产物逐字节一致（fields.json 除 outputs 类路径键外逐字节一致；docx 解析后的段落文本/对齐/缩进/字体/行距完全一致，无当前时间、随机内容等不可复现源）；输出目录恰含两产物。
命令行契约：--template 会议通知 --data <数据json路径> --outdir out/会议通知/case1，每次调用生成 文书.docx 与 fields.json。实现方式不限。
（注：本任务书为 golden.json ab 任务在「禁止参照物进臂」约束下的忠实改写；输入数据原样来自冻结任务集。）
