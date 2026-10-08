# office-templates-skill t05 — 题面与判据（边界）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t05` |
| 维度 | 边界 |
| nonce | `ofc-t05-2df916` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/工作总结/case1.json 渲染成工作总结，产物写入 <outdir>（文书.docx + fields.json）。这份数据里有些字段是空字符串、有些是只有空白的数组、有些列表里的每一项都是空白。请按技能包规定判断哪些字段算缺失、缺失了怎么渲染，并在交付时把缺哪些字段说清楚。
```

## 2 目标态

3 个必填字段（总结主体/工作回顾/主要成绩）判缺失并按 F1/F4 渲染；2 个选填字段判缺失走省略或留空；exit 0；台账如实记账。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 退出码为 0（必填缺失不是运行错误），两件产物齐全 | echo $? + find 计数 | 码 0，计数=2 |
| `S1` | 语义 | 总结主体为空白串「   」→ 判缺失，标题代入占位符，逐字 = 「____2026 年 9 月工作总结」 | 标题段文本逐字比对 + fields.title 比对 | 两者相等且恰含一处 ____ |
| `S2` | 语义 | 工作回顾为空白串形态的必填列表 → 判缺失、value=null、rendered_as=「以____占位条目」 | 台账明细三项（status/value/rendered_as）比对 | missing / null / 以____占位条目 |
| `S3` | 语义 | 主要成绩为三项全空白数组（三项分别为空格串、制表符、空串）→ 判缺失，不得判为「有 3 个空条目」的 filled | 台账明细比对 | missing / null / 以____占位条目 |
| `C1` | 机械自洽 | summary 自洽：total=7, filled=2, missing=5, missing_required=3 | json 读 + 自洽断言 | filled+missing=7；filled 仅 总结时段 与 下一步工作打算 |
| `C2` | 机械自洽 | missing_required_names 逐字 == ["总结主体","工作回顾","主要成绩"]，顺序等于字段表顺序而非字典序 | 脚本比对字段表顺序 | 顺序为 总结主体 → 工作回顾 → 主要成绩 |
| `F1` | 结构版式 | 两个必填列表缺失 → 各渲染一个占位条目「1．____」（小节标题保留） | 正文检索 `1．____` 计数 | 命中数 = 2，分别落在「一、工作回顾」「二、主要成绩」节下 |
| `F2` | 结构版式 | 选填小节「存在问题」缺失 → 整节省略（文中无该节头），其后一节编号仍为「四、」 | 段落遍历 + 节头逐字比对 | 无「三、存在问题」；有「四、下一步工作打算」 |
| `B1` | 边界纪律 | 交付回复中点名缺失的必填字段；未因数据「几乎全空」而拒绝成文或编造总结内容 | 裁判通读回复 + 正文检索具体实体 | 点名 3 个必填缺失；正文无编造条目 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('SUM', f['summary'])
print('DETAIL', {x['name']: (x['status'], x['value'], x.get('rendered_as')) for x in f['fields']})
full='\n'.join(p.text for p in Document('<outdir>/文书.docx').paragraphs)
print('PLACEHOLDER_ITEM_HITS', full.count('1．____'))
print('SECTIONS', [l for l in full.split('\n') if l[:2] in ('一、','二、','三、','四、')])
PY
```

预期输出：

```text
SUM {'total':7,'filled':2,'missing':5,'missing_required':3,'missing_required_names':['总结主体','工作回顾','主要成绩'],'unknown_keys':[]} / PLACEHOLDER_ITEM_HITS 2 / SECTIONS 无「三、存在问题」
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
