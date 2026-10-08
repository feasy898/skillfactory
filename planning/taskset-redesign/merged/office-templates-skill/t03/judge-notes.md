# office t03 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

### A. 请示函-empty（`{}`，8 字段全缺）

1. exit 0、两产物齐。
2. 标题=`关于____的请示`；称谓段=`____：`；请示缘由、请示事项段均含 `____`；落款单位行=`____`、成文日期行为空。全文 `____` 恰出现 **5 次**（5 个必填 text 字段各 1 处）。
3. fields.json：missing=8/8、missing_required=[请示事由, 主送机关, 请示缘由, 请示事项, 请示单位]（按字段表顺序）、5 个必填 rendered_as=「以____占位」、3 个选填（联系人/联系电话/成文日期）rendered_as=「留空（渲染为空字符串）」。

### B. 工作总结-blank（键全在、值全空白）

1. exit 0、两产物齐。空白判定=strip 后为空：`"  "`、`""`、`"　"`（全角空格）、`[]`、`[" "]`（全空白数组）**全部判缺失**——键存在不等于有值。
2. 标题=`________工作总结`（总结主体与总结时段两个占位连排，恰 8 个下划线）。
3. 工作回顾/主要成绩/下一步工作打算（必填列表缺失）→ 各渲染占位条目 `1．____`；存在问题（选填）→「存在问题」小节**整节省略**（字符串 `"  "` 经 F3 单项化+去空白后为空数组→选填列表缺失）；成文日期（选填）→ 落款日期行为空段。
4. fields.json：missing=7/7、missing_required=[总结主体, 总结时段, 工作回顾, 主要成绩, 下一步工作打算]、3 个必填列表 rendered_as=「以____占位条目」、存在问题 rendered_as=「省略该条目/小节」、成文日期 rendered_as=「留空（渲染为空字符串）」。

## 期望（引擎实测 2026-10-09）

A：title=`关于____的请示`、summary={total:8, filled:0, missing:8, missing_required:5}、rendered_as 实测与上述逐字一致、末三非空段=`____`/`联系人：　　联系电话：`/`____`。
B：title=`________工作总结`、summary={total:7, filled:0, missing:7, missing_required:5}、存在问题=「省略该条目/小节」、成文日期=「留空（渲染为空字符串）」。

## 判挂点

- 任一份数据被当作错误处理（非 0 退出、拒产、报错中断）→ 直接不通过。
- `{}` 场景只渲染部分占位或标题兜底成「请示函」→ 正确性错。
- `[" "]` 被当作有值渲染空条目 → 空白判缺失守。
- rendered_as 措辞与 spec 语义不符（如写成「缺失」）→ 可验证性降档。

## 机判方法

python-docx 断言两份产物（____ 计数/标题/节保留）；json 断言两份 fields.json 的 summary 与 rendered_as 逐字。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/office-templates-skill/scripts/gen_doc.py --template 请示函 --data qingshi_empty.json --outdir <tmp>` 与 `--template 工作总结 --data zongjie_blank.json --outdir <tmp>`，均 exit 0。真值见上「期望」。