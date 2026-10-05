# 任务：按版式规范生成一份工作周报文书

## 输入

- `fixtures/input.json`：`{"template": "周报", "title": <标题>, "fields": [{"name", "required", "kind", "value"}, ...]}`，
  全部字段均已给值（`value` 均非 null）。

## 输出（写到 `out/` 目录）

**1. `out/文书.docx`（Word 文档）**，版式逐条执行：

- 第一段 = 标题（内容取输入 `title`），**居中对齐**；
- 正文每字段一段，段文本为 `字段名:值`（冒号用中文全角`：`），**每段首行缩进两字符（约 24 磅）**；
- 最后两段为落款：第一段 = `填报人` 的值，第二段 = `报送日期` 的值，两段均**右对齐**（只写值本身，不带字段名）；
- `填报人`、`报送日期` 两个字段不进正文段（它们只出现在落款）。

**2. `out/fields.json`**：

```json
{
  "template": "周报",
  "title": <输入 title>,
  "filled_fields": [<已填字段名数组>],
  "missing_fields": [],
  "fields": [{"name", "required", "kind", "status", "value"}, ...]
}
```

- `status` 取 `"filled"`（本任务全部字段已给值）；`filled_fields` 与 `fields` 中 `status=="filled"` 的字段名集合一致；`missing_fields` 为空数组。

## 判定要点（判定即按此执行）

- docx 可正常打开，内部无 `<!DOCTYPE`/`<!ENTITY` 声明；
- 标题居中、落款右对齐、正文段首行缩进落在 20–28 磅档；
- **每个字段值在 docx 正文中逐字出现**（一个字符都不能变）；
- fields.json 记账与输入字段清单完全一致（多了少了都判不合格）。

## 环境

- 可用 Python（python-docx 已安装）生成 docx；无需联网。
