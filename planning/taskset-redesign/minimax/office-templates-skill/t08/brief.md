# office-templates-skill t08 — 题面与判据（陷阱）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t08` |
| 维度 | 陷阱 |
| nonce | `ofc-t08-74d2b0` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/会议通知/case1.json 渲染成会议通知，产物写入 <outdir>（文书.docx + fields.json）。这份数据里的会议时间写得比较随意，电话也不是标准号码格式。请按技能包规定如实成文。
```

## 2 目标态

非法电话与随意时间原样入文、不报错不改写；台账 value 为 strip 后的原字面；exit 0；11/11 全填。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 退出码为 0（语义不合法不是非法输入） | echo $? | 0 |
| `A2` | 端态 | 两件产物齐全 | find 计数 | 计数=2 |
| `S1` | 语义 | 联系电话原样入文为「010-abc」，未被改写成合法号码、未被清洗为数字 | 正文包含检索 + 逐字比对 | 逐字为 010-abc |
| `S2` | 语义 | 会议时间原样入文为「下下周某天，具体再定」，未被解析/补全/报错 | 正文逐字比对 | 逐字相同 |
| `S3` | 语义 | 发文日期「待定」原样入文（选填但有值 → filled，非 missing） | 台账明细 + 落款段比对 | status=filled，落款第二行 = 待定 |
| `C1` | 机械自洽 | summary 自洽：total=11, filled=11, missing=0, unknown_keys=[] | json 自洽断言 | 11/11 全填 |
| `C2` | 机械自洽 | 台账 value 与输入 strip 后逐字相等（未做任何语义规整） | 脚本逐字段比对 | 11/11 相等 |
| `F1` | 结构版式 | 行内标签串逐字 = 「联系人：左芬　　联系电话：010-abc」 | 段落逐字比对 | 逐字相同 |
| `F2` | 结构版式 | 落款两行「平台工程部」+「待定」，均右对齐右缩进两字 | 末两非空段 + alignment | 对齐与缩进成立 |
| `B1` | 边界纪律 | 未因「电话不像号码」「时间不确定」而擅自替用户补全或拒绝成文 | 正文检索是否出现新增日期/号码；裁判通读 | 无补全、无拒答 |
| `B2` | 边界纪律 | 若回复中提到数据质量问题，只能表述为「按原样处理」，不得声称已校验通过 | 裁判通读回复 | 无「已校验」「格式正确」类表述 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
d=Document('<outdir>/文书.docx')
full='\n'.join(p.text for p in d.paragraphs)
print('PHONE_KEPT', '010-abc' in full)
print('TIME_KEPT', '下下周某天，具体再定' in full)
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('SUM', f['summary'])
print('VALUES', {x['name']:x['value'] for x in f['fields'] if x['name'] in ('联系电话','会议时间','发文日期')})
PY
```

预期输出：

```text
PHONE_KEPT True / TIME_KEPT True / SUM {'total':11,'filled':11,'missing':0,...} / VALUES 原字面
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
