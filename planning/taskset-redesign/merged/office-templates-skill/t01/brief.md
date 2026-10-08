# ot-t02 · 列表规整组合 + 交付核对报告

## 任务

把 `task.json.input.data` 保存为 `shibei_week42.json`（顶层对象，含模板外键「温馨提示」），用 office-templates 技能以模板「周报」生成到 `<outdir>/`（`文书.docx` + `fields.json`）。

**另要求**（交付前核对，工作流第 4 步）：读 `fields.json` 后，在 `<outdir>/delivery-report.json` 落盘一份交付核对报告，顶层恰 4 键：

```json
{
  "missing_required_names": [],
  "missing_optional": [],
  "unknown_keys": [],
  "title": "（与 fields.json.title 一致）"
}
```

内容必须与 fields.json 实际记账一致（本题为全填场景，三个数组应为空——如实落盘，缺数据不编造的反面是**有数据不漏记**）。

## 判定要点（全部可机判）

1. **夹心空白项剔除**：「本周工作内容」3 项中第 2 项为 `"   "` → 文书「一、本周工作内容」节恰 2 条目（`1．完成店庆档期主题陈列改造`、`2．复盘会员日核销数据并输出简报`），无空条目；fields.json value 数组=strip 后 2 项。
2. **字符串单项化**：「下周工作计划」为字符串 `"启动冬季书单选品"` → 单条目、value=`["启动冬季书单选品"]`（F3）。
3. **尾部空白项剔除**：「问题与需协调事项」`["收银终端老化，需要报修", ""]` → 恰 1 条目；该选填小节因尚有 1 个非空项**不省略**。
4. **值 strip**：部门 `" 拾贝书店 "` → 标题=`拾贝书店工作周报`（strip 后代入）、fields.json 部门 value=`拾贝书店`。
5. **F6**：`summary.unknown_keys == ["温馨提示"]`；文书正文不出现「温馨提示」内容。
6. **互洽**：fields.json 的 summary 计数 filled=7/total=7/missing=0；delivery-report.json 三空数组 + title 与 fields.json.title 逐字相等；文书.docx 实际条目数与台账 value 一致。

## 判挂点

- 空白项被渲染为空条目或编号跳跃（1、3）→ 完整性降档。
- 标题写成「 拾贝书店 工作周报」（未 strip）→ 正确性错。
- delivery-report.json 乱填缺失字段名（编造缺失）→ 可验证性 0。
