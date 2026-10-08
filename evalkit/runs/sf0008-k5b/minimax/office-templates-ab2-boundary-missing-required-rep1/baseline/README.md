# SF-0008 office 臂：缺数据边界处理（ab2-boundary-missing-required）

## 运行

```
python3 main.py --template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>
```

每次调用在 `--outdir` 下生成两个产物：`文书.docx`、`fields.json`，退出码 0。
（依赖 `python-docx`，本机可用解释器为 `/usr/bin/python3`。）

本臂的已落盘产物：

```
python3 main.py --template 请示函   --data fixtures/请示函/case2.json   --outdir out/请示函/case2
python3 main.py --template 会议通知 --data fixtures/会议通知/case2.json --outdir out/会议通知/case2
python3 verify_outputs.py    # 独立对拍，checks=43 fails=0
```

## 行为契约（缺数据不编造、如实记账）

| 情形 | 渲染 | 记账 |
| --- | --- | --- |
| 键存在且有值 | 写真值（与输入逐字一致） | `filled` |
| 必填键缺失 / 值为空串 / 值为 null | `____` 占位 | `missing_required` |
| 选填键缺失 / 值为空串 / 值为 null | 正文条目整条省略；落款行留空 | `missing_optional` |
| 模板外键 | 不进正文、不进字段 | `unknown_keys`（含 `unknown_key_details` 记原值） |

键缺失与「键在、值为空串」都判为缺失事实，二者在 `fields[name].present` 上留有区分，
但都不编造值、不误记为必填。

## 版式

标题居中二号小标宋；称谓顶格（无左缩进、无首行缩进），必填缺失时渲染为「字段名：____」显式点出缺哪个字段；
正文首行缩进两字、条目连续编号（一、二、三…，选填条目省略后不跳号）；落款与联系方式右对齐，
选填落款行缺失时留空行以保持落款块形状——缺数据不破坏版式。

## 核验

`verify_outputs.py` 不复用 `main.py` 的中间结果：它从 `fixtures/*.json` 重新推导
必填缺失 / 选填缺失 / 模板外键三张名单，与 `fields.json` 对拍，再直读 docx 段落属性
校验称谓顶格、落款右对齐、`____` 占位确实落到纸面上。