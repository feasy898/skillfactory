# ab2-boundary-missing-required（baseline 臂）

边界数据：输入缺必填/缺选填/含模板外键，渲染器必须「缺数据不编造、如实记账」。

## 运行

依赖 `python-docx`（本机装在 `/home/pan-ding/venvs/shenbao`，版本 1.2.0）：

```bash
PY=/home/pan-ding/venvs/shenbao/bin/python

$PY gen_doc.py --template 请示函   --data fixtures/请示函/case2.json   --outdir out
$PY gen_doc.py --template 会议通知 --data fixtures/会议通知/case2.json --outdir out
$PY verify.py        # 自检，退出码 0 = 全通过
```

每次调用产出 `<outdir>/<模板>/<用例名>/{文书.docx, fields.json}`；两次调用均以退出码 0 正常结束。

## 记账口径

| 情形 | 文书 | fields.json |
| --- | --- | --- |
| 必填键缺失 / 值为空串 | 该处以 `____` 占位 | 进 `missing_required`，`detail` 标注 `key_absent` / `empty_value` |
| 选填键缺失 / 值为空串 | 整行省略，绝不出占位、绝不冒充必填 | 进 `missing_optional` |
| 模板外键 | 不写入正文 | 进 `unknown_keys`，`detail` 标注 `not_in_template_schema` |

## 字段口径

- **请示函** — 必填：主送机关、请示事由、请示缘由、请示事项、请示单位；选填：联系人、联系电话、成文日期。
- **会议通知** — 必填：召开单位、主送对象、会议名称、会议时间、会议地点、参会人员；选填：会议议题、会议要求、联系人、联系电话、发文日期。

## case2 实测结果

| 模板 | missing_required | missing_optional | unknown_keys |
| --- | --- | --- | --- |
| 请示函 | 主送机关（键缺失）、请示事项（空串） | 联系电话、成文日期 | — |
| 会议通知 | 会议名称（键缺失）、会议地点（空串） | 会议议题、会议要求、联系人、联系电话 | 备注 |

## 版式

A4，页边距上 3.7 / 下 3.5 / 左 2.8 / 右 2.6 cm；标题居中加粗二号，正文三号仿宋、固定行距 30 磅。

- 称谓段顶格（左对齐、`first_line_indent = 0`）；
- 正文首行缩进两字符；
- 落款块右对齐、位于文末，单位为末行（日期选填有值时排在单位之上）。

`.render/` 下留有 LibreOffice 转出的 PDF 与 PNG 页面快照，供版式目视复核。
