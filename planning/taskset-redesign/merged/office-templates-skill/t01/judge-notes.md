# office t01 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

数据中「温馨提示」为模板外键（F6）：不进文书、按字典序记入 summary.unknown_keys，正常生成不报错（该说明为判官判据，被测指令不含）。

1. **夹心空白项剔除**：「本周工作内容」3 项中第 2 项为 `"   "` → 文书「一、本周工作内容」节恰 2 条目（`1．完成店庆档期主题陈列改造`、`2．复盘会员日核销数据并输出简报`），无空条目；fields.json value 数组=strip 后 2 项。
2. **字符串单项化**：「下周工作计划」为字符串 `"启动冬季书单选品"` → 单条目、value=`["启动冬季书单选品"]`（F3）。
3. **尾部空白项剔除**：「问题与需协调事项」`["收银终端老化，需要报修", ""]` → 恰 1 条目；该选填小节因尚有 1 个非空项**不省略**。
4. **值 strip**：部门 `" 拾贝书店 "` → 标题=`拾贝书店工作周报`（strip 后代入）、fields.json 部门 value=`拾贝书店`。
5. **F6**：`summary.unknown_keys == ["温馨提示"]`；文书正文不出现「温馨提示」内容。
6. **互洽**：fields.json 的 summary 计数 filled=7/total=7/missing=0；delivery-report.json 三空数组 + title 与 fields.json.title 逐字相等；文书.docx 实际条目数与台账 value 一致。

## 期望（引擎实测 2026-10-09）

title=`拾贝书店工作周报`；summary={total:7, filled:7, missing:0, missing_required_names:[], unknown_keys:["温馨提示"]}；末段=「报送日期：2026-10-12」。

## 判挂点

- 空白项被渲染为空条目或编号跳跃（1、3）→ 完整性降档。
- 标题写成「 拾贝书店 工作周报」（未 strip）→ 正确性错。
- delivery-report.json 乱填缺失字段名（编造缺失）→ 可验证性 0。

## 机判方法

python-docx 断言条目数与文本；json 断言 fields.json 与 delivery-report.json；三方数字互洽断言。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/office-templates-skill/scripts/gen_doc.py --template 周报 --data shibei_week42.json --outdir <tmp>`，exit 0。真值见上「期望」。