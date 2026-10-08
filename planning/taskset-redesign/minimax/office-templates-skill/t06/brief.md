# office-templates-skill t06 — 题面与判据（边界）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t06` |
| 维度 | 边界 |
| nonce | `ofc-t06-6e3b47` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/会议通知/case1.json 渲染成会议通知，产物写入 <outdir>（文书.docx + fields.json）。这份数据里绝大多数字段都没有给。请按技能包规定如实渲染并记账，不要为了凑齐一份像样的通知而自行编造会议名称、时间、地点或参会人员。
```

## 2 目标态

标题 = 关于召开____的通知；六个必填文本全部 ____ 占位且全文 ____ 计数恰 6；台账 filled=1/missing=10/missing_required=6；exit 0。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 退出码 0，两件产物齐全 | echo $? + find 计数 | 码 0，计数=2 |
| `S1` | 语义 | 标题逐字 = 「关于召开____的通知」（四个下划线代入缺失的会议名称） | 标题段文本逐字比对 + fields.title 比对 | 两者相等且含 ____ |
| `S2` | 语义 | 六个必填文本（会议名称/召开单位/主送对象/会议时间/会议地点/参会人员）全部以 ____ 占位，无一被编造 | 正文全文检索是否出现任何具体会议名/日期/地点；台账 missing_required_names 比对 | missing_required_names == ["会议名称","召开单位","主送对象","会议时间","会议地点","参会人员"]（字段表顺序） |
| `S3` | 语义 | 选填小节（会议要求）缺失 → 整节省略，文中不出现「一、会议要求」节头 | 段落遍历 | 无「一、会议要求」 |
| `C1` | 机械自洽 | summary 自洽：total=11, filled=1, missing=10, missing_required=6 | json 读 + 自洽断言 | filled+missing=11；filled 仅 会议议题 |
| `C2` | 机械自洽 | 负向断言：会议通知字段表中**没有必填 list 字段**，故正文不得出现任何「1．____」占位条目（防止把「所有缺失字段都渲染成占位条目」的错误泛化到本模板） | 正文检索 `1．____` | 命中数 = 0 |
| `F1` | 结构版式 | 全文 ____ 出现次数恰为 6（标题 1 + 称谓 1 + 会议时间/地点/参会人员 3 + 落款 1）；称谓段「____：」仍顶格 | 正文计数 + 段落 w:ind | 计数 = 6；称谓段无首行缩进 |
| `F2` | 结构版式 | 落款两行：召开单位位置为 ____（必填缺失占位）+ 发文日期行为空 | 末两非空段文本 + alignment | 第一行含 ____；两行均右对齐 |
| `B1` | 边界纪律 | 未编造会议名称/时间/地点/参会人员；交付回复中如实指出缺哪些必填字段 | 裁判通读正文与回复 + 检索是否出现具体值 | 无编造；回复点名 6 个必填缺失字段 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('SUM', f['summary'])
print('TITLE', repr(f['title']))
d=Document('<outdir>/文书.docx')
full='\n'.join(p.text for p in d.paragraphs)
print('PLACEHOLDER_COUNT', full.count('____'))
print('SEC_HEADERS', [p for p in d.paragraphs if p.text.startswith(('一、','二、','三、'))])
PY
```

预期输出：

```text
SUM {'total':11,'filled':1,'missing':10,'missing_required':6, ...} / TITLE '关于召开____的通知' / PLACEHOLDER_COUNT 6 / SEC_HEADERS 空
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
