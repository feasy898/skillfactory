# office 重测臂任务（ab2-boundary-missing-required）

处理两份含缺失字段的边界数据：fixtures/请示函/case2.json（主送机关关键缺失、请示事项为空字符串、联系电话/成文日期选填缺失）与 fixtures/会议通知/case2.json（会议名称缺失、会议地点空字符串、会议议题/会议要求/联系人/联系电话选填缺失、含模板外键「备注」）。
命令行契约：--template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>，每次调用生成 文书.docx 与 fields.json。
产物写入 out/<模板>/case2/（两个单元目录，每目录恰含两产物）。
核心行为要求（缺数据不编造、如实记账）：必填缺失以____占位渲染且程序正常结束（退出码 0）；选填缺失留空或省略、不得误记为必填；模板外键记入 unknown_keys 类记账；fields.json 的 missing_required/选填 missing/unknown_keys 名单必须与输入的缺失事实一致；版式不因缺数据而破坏（称谓顶格、落款右对齐）。
实现方式不限。完成后确认两个单元目录与产物齐全。
（注：本任务书为 golden.json ab 任务在「禁止参照物进臂」约束下的忠实改写；输入数据原样来自冻结任务集。）
