# office-templates-skill t04 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t04` |
| 维度 | 能力 |
| nonce | `ofc-t04-b87a29` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/周报/case2.json 渲染成周报，产物写入 <outdir>（文书.docx + fields.json）。这份数据里有几个键不在周报模板的字段表内。请如实处理它们，并在交付时告诉我这些键的情况。
```

## 2 目标态

unknown_keys 按字典序恰为 ["密级","备注","审批人"]；三键不出现于 fields 明细与 filled/missing；不影响文书。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | summary.unknown_keys 逐字 == ["备注", "审批人", "密级"]（字典序 = Python sorted() 的码位序，非输入顺序：备 U+5907 < 审 U+5BA1 < 密 U+5BC6） | json 读并做 == 比对 | 顺序为 备注→审批人→密级 |
| `S2` | 语义 | 三个外键的值（内部 / 此键不在模板字段内 / 魏娥）未被渲染进文书任何段落 | 正文全文包含检索三个外键值 | 三处命中数均为 0 |
| `C1` | 机械自洽 | 外键不出现在 fields 明细、filled_fields、missing_fields 任何位置 | 脚本：外键集合 ∩ (明细名 ∪ filled ∪ missing) == 空集 | 交集为空 |
| `C2` | 机械自洽 | summary 自洽：total=7, filled=7, missing=0（外键不计入 total，明细仍恰 7 项） | json 读 + 自洽断言 | filled+missing=total=7 |
| `F1` | 结构版式 | 文书结构不受外键影响：小节一/二/三齐全（问题与需协调事项有值故不省略） | 段落遍历 | 三个节头齐全；节序 一→二→三 |
| `B1` | 边界纪律 | 交付回复中主动提示存在未被模板消费的键（SKILL 工作流第 4 步） | 裁判通读回复 | 点名 3 个外键或明确说明有未消费键 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
names=[x['name'] for x in f['fields']]
extra={'密级','备注','审批人'}
print('UNKNOWN', f['summary']['unknown_keys'])
print('LEAK_INTO_LEDGER', sorted(extra & (set(names)|set(f['filled_fields'])|set(f['missing_fields']))))
full='\n'.join(p.text for p in Document('<outdir>/文书.docx').paragraphs)
print('VALUES_IN_DOC', {v: full.count(v) for v in ('内部','此键不在模板字段内')})
PY
```

预期输出：

```text
UNKNOWN ['密级','备注','审批人'] / LEAK_INTO_LEDGER [] / VALUES_IN_DOC 计数均 0
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
