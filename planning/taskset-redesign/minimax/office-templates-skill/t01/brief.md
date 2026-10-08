# office-templates-skill t01 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t01` |
| 维度 | 能力 |
| nonce | `ofc-t01-3e7b52` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/周报/case1.json 渲染成周报，产物写入 <outdir>（文书.docx + fields.json）。这份数据的字段值带着多余的前后空白与制表符。请按技能包规定的取值口径渲染，并把台账里的 value 一并处理干净。
```

## 2 目标态

文书正文不含任何首尾空白；台账 value 为 strip 后的值；全空白列表项被丢弃且不导致字段判缺失。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | <outdir> 恰含 文书.docx 与 fields.json，退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | 标题段逐字 = 「智造事业部工作周报」（无前后空白、无全角空格残留） | doc.paragraphs[0].text | 智造事业部工作周报 |
| `S2` | 语义 | 基本信息行逐字 = 「填报人：张浩　　周期：2026-10-05 至 2026-10-11」（两个全角空格分隔；值两端无空白） | 段落文本逐字比对（注意分隔符是两个全角空格 U+3000） | 逐字相同 |
| `S3` | 语义 | 列表项入文已 strip：本周工作内容恰 2 条（第三条全空白项被丢弃），条目前后无空白 | 抽取小节条目段落文本并 strip 后比对 + 断言原文无首尾空白 | 2 条；条目标题为「完成三批次评分器回归」「复核 12 份标注台账」 |
| `C1` | 机械自洽 | fields.json 每个 filled 项的 value 均等于 strip 后的输入值（文本为字符串、list 为数组） | 脚本比对 fields.filled 项与输入 JSON 的 strip 值 | 7/7 相等 |
| `C2` | 机械自洽 | fields.summary == {total:7, filled:7, missing:0, missing_required:0, missing_required_names:[], unknown_keys:[]}；filled+missing=total | json 读 + 自洽断言 | 全部齐全，无字段因空白被判缺失 |
| `F1` | 结构版式 | 标题居中黑体 22pt；正文首行缩进两字符（firstLineChars=200）、仿宋 16pt、28 磅固定行距 | python-docx 读 alignment / run.font / w:firstLineChars | 逐项成立 |
| `F2` | 结构版式 | 落款行逐字 = 「报送日期：2026-10-11」，右对齐且右缩进两字 | 末个非空段文本 + alignment + right_indent | 逐字相同，值不带尾随空格 |
| `B1` | 边界纪律 | 未因数据带空白就自行「美化」标点（如把全角空格改成两个半角空格或加逗号） | 正文逐字比对 | 未改写任何字符 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
d=Document('<outdir>/文书.docx')
ps=[p.text for p in d.paragraphs]
print('TITLE', repr(ps[0]))
print('INFO', repr(ps[1]))
print('SIG', repr([p for p in ps if p.strip()][-1]))
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('SUMMARY', f['summary'])
print('VALUES', {x['name']:x['value'] for x in f['fields']})
PY
```

预期输出：

```text
TITLE '智造事业部工作周报' / INFO '填报人：张浩　　周期：2026-10-05 至 2026-10-11' / SUMMARY total=7 filled=7 missing=0 / VALUES 全部 strip
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
