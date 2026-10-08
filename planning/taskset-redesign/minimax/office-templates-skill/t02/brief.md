# office-templates-skill t02 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t02` |
| 维度 | 能力 |
| nonce | `ofc-t02-9a04d8` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/工作总结/case1.json 渲染成工作总结，产物写入 <outdir>（文书.docx + fields.json）。这份数据里的列表字段写法不统一：有的给了字符串，有的给了带空格的数组，还有的直接给了数字。请按技能包规定的取值口径渲染并如实记账。
```

## 2 目标态

三个 list 字段按 F3 宽容口径规整：字符串→单项、数组去空后逐项、非字符串类型 str() 单项。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | 工作回顾为字符串 → 渲染为单项条目，fields value = ["完成三平台评分器回归"] | 台账 value 比对 | 字符串数组，长度 1 |
| `S2` | 语义 | 主要成绩为数组含一个全空白项 → 去空后 2 项 | 台账 value 比对 + 正文条目数 | value 长度 2，正文 2 条 |
| `S3` | 语义 | 存在问题为非字符串数组 [2026, True, {...}] → 每项 str().strip() 后成单项，共 3 项，值分别为 "2026"、"True"、"{'备注': '待与厂商对齐'}" | 台账 value 比对（逐字） | 长度 3，元素全为字符串，非原类型（不得是 int/bool/dict） |
| `S4` | 语义 | 下一步工作打算为数字 4（非列表）→ str().strip() 单项，value = ["4"]，正文条目为「4」而非报错或丢弃 | 台账 value + 正文条目比对 | value == ["4"]，status=filled |
| `C1` | 机械自洽 | 所有 filled 的 list 字段 value 元素全为字符串（str 化），无 int/bool/dict 残留 | 脚本：for v in value: assert isinstance(v,str) | 4/4 字段满足 |
| `C2` | 机械自洽 | fields.summary == {total:7, filled:7, missing:0, missing_required:0, missing_required_names:[], unknown_keys:[]} | json 读 + 自洽断言 | 全部齐全（宽容取值不算缺失） |
| `F1` | 结构版式 | 小节编号为「一、工作回顾」「二、主要成绩」「三、存在问题」「四、下一步工作打算」（第四节为「四」） | 段落文本逐字比对 | 四个节头齐全且编号为 一/二/三/四 |
| `F2` | 结构版式 | 条目编号为全角点「1．2．3．」；落款两行 = 「度量研究院」+「2026年9月30日」（日期为裸日期、无标签） | 末两非空段文本逐字比对 | 第二行为「2026年9月30日」而非「成文日期：…」 |
| `B1` | 边界纪律 | 未把数字 4 当成「4 条计划」自行扩写，未把 True 渲染成「是」、未把 dict 渲染成 JSON 串 | 正文逐字比对 | 正文为 str() 结果的字面值 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
from docx import Document
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
v={x['name']:x['value'] for x in f['fields']}
for k in ('工作回顾','主要成绩','存在问题','下一步工作打算'): print(k, v[k])
print('ALL_STR', all(isinstance(i,str) for k in ('工作回顾','主要成绩','存在问题','下一步工作打算') for i in v[k]))
ps=[p.text for p in Document('<outdir>/文书.docx').paragraphs]
print('SECS', [p for p in ps if p[:2] in ('一、','二、','三、','四、')])
print('SIG', [p for p in ps if p.strip()][-2:])
PY
```

预期输出：

```text
四字段 value 均为字符串数组 / ALL_STR True / SECS 四节含「四、下一步工作打算」/ SIG ['度量研究院','2026年9月30日']
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
