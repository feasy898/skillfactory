# ab2-boundary-missing-required（baseline 臂）

处理两份含缺失字段的边界数据，渲染公文并如实记账缺失事实。

## 命令行契约

```bash
python3 gen_doc.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>
```

每次调用在 `--outdir` 下生成且仅生成两个产物：

| 产物 | 说明 |
| --- | --- |
| `文书.docx` | 按模板版式渲染的公文 |
| `fields.json` | 字段记账：必填缺失 / 选填缺失 / 模板外键 / 逐字段渲染去向 |

一键重跑本臂全部产物：

```bash
./run_all.sh      # 渲染 out/请示函/case2/ 与 out/会议通知/case2/
python3 verify.py # 34 项自检断言
```

## 核心行为

| 情形 | 判定 | 渲染 | 记账 |
| --- | --- | --- | --- |
| 必填字段缺失（键不存在，或值为空串 / 纯空白） | `filled=false` | 以 `____` 占位 | `missing_required` |
| 选填字段缺失 | `filled=false` | 该行整行省略 | `missing_optional` |
| 选填字段有值 | `filled=true` | 正常渲染 | 不记缺失 |
| 模板外键（数据有、模板无） | — | **不渲染进正文** | `unknown_keys` + `unknown_key_values` |

任何情形下程序都正常结束（退出码 0），不推断、不编造、不填默认值。
选填缺失不计入 `missing_required`；模板外键值不泄漏进正文。

## 版式

标题居中 / 称谓顶格（无首行缩进）/ 正文首行缩进 2 字符 / 落款右对齐。
缩进同时写出 `w:firstLineChars`（Word 按字符精确缩进）与 `w:firstLine`
（twips，供只读 `w:firstLine` 的解析器判定），因此缺数据也不会破坏版式。

## 本臂两份输入的缺失事实

**fixtures/请示函/case2.json**

- 必填缺失：`主送机关`（键不存在）、`请示事项`（空字符串）
- 选填缺失：`成文日期`、`联系电话`（键不存在）；`联系人` 有值，正常渲染

**fixtures/会议通知/case2.json**

- 必填缺失：`会议名称`（键不存在）、`会议地点`（空字符串）
- 选填缺失：`会议议题`、`会议要求`、`联系人`、`联系电话`（键不存在）
- 模板外键：`备注`（记入 `unknown_keys`，不渲染）

## 实现说明

`gen_doc.py` 仅依赖 Python 标准库（`zipfile` + OOXML 直写），不依赖
python-docx，保证在任何 Python 3 环境下都可运行——本机 `python3` 指向的
venv 并未安装 python-docx。相同输入产出字节一致的包（zip 时间戳固定）。

## 文件

```
gen_doc.py     渲染器与 CLI（--template/--data/--outdir）
run_all.sh     一键渲染两个单元目录
verify.py      自检：产物齐全 / 退出码 0 / 占位 / 记账 / 版式
fixtures/      输入数据（原样，未改动）
out/<模板>/case2/   产物：文书.docx + fields.json
```