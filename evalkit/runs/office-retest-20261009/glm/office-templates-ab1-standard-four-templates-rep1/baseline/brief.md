# office 重测臂任务（ab1-standard-four-templates）

把 fixtures/ 目录下四类模板的 case1 数据 JSON（周报、请示函、会议通知、工作总结各一份，字段全部齐全）分别生成为公文产物。
命令行契约：--template <周报|请示函|会议通知|工作总结> --data <数据json路径> --outdir <输出目录>，每次调用在该目录下生成 文书.docx 与 fields.json 两个产物。
产物写入 out/<模板>/case1/（四类各一个单元目录，每目录恰含 文书.docx 与 fields.json）。
风格要求：GB/T 9704 公文风格（A4 版面）。缺数据不编造：必填缺失以____占位、选填缺失留空或省略，并在 fields.json 中如实记账。
fields.json 顶层需含 title、fields 明细（每个字段：名称、是否必填、状态、值/渲染方式）与 summary（filled/missing/total 计数）。
实现方式不限（可自行编写脚本后调用）。完成后确认四个单元目录与产物齐全。
（注：本任务书为 golden.json ab 任务在「禁止参照物进臂」约束下的忠实改写；输入数据原样来自冻结任务集。）
