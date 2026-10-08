# hot-templates-skill t03 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t03` |
| 维度 | 能力 |
| nonce | `hot-t03-5f24c8` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，生成公众号文章爆款内容骨架，产物写入 <outdir>（骨架.md + structure.json）。材料自含——platform=wx，topic=把周报写成三句话，points 见 data/points.json（恰好 3 条）。模板冻结：引子 + 三段论（是什么/为什么/怎么办）+ 金句收尾。
```

## 2 目标态

5 要素冻结；thesis_how 三行结构逐字；三抓手同居 thesis_how；总填充 7（topic 记 4 次 + point 记 3 次）；金句结构逐字。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全非空、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | thesis_how 文本首行逐字「三、怎么办」，次行逐字「落到操作层面，给你三个抓手：」，其后三行形如 `N. <卖点>——【占位:展开：具体做法+一个例子】`（N 为半角数字 + 空格） | 按 \n 切分后逐行比对 | 共 5 行；三行序号为 1. 2. 3. |
| `S2` | 语义 | golden_ending 文本结构逐字：`「把周报写成三句话这件事，【占位:金句主体——句式建议：真正的…不是靠…，而是靠…】」` + 换行 + `共勉。` | 逐字比对 | 逐字命中，两行结构 |
| `S3` | 语义 | 三个卖点全部同居 thesis_how 的三抓手，不得被拆到 thesis_what / thesis_why | 三个卖点文本的全文出现位置断言 | 每条只在 thesis_how 出现一次；其余两要素不含卖点原文 |
| `F1` | 结构版式 | 5 个要素 id 顺序恰为 lead_in、thesis_what、thesis_why、thesis_how、golden_ending | elements[].id 序列比对 | 顺序一致 |
| `F2` | 结构版式 | 三个 thesis 要素的文本分别以「一、是什么」「二、为什么」「三、怎么办」开头 | startswith 断言 | 三处全中 |
| `C1` | 机械自洽 | placeholder_stats.total_filled_from_input == 7（topic 在 4 个要素各记一次 + point#1..3 各一次） | structure.json 逐要素 filled_from_input 汇总求和 | 7 |
| `C2` | 机械自洽 | topic 填充恰出现在 4 个要素（lead_in / thesis_what / thesis_why / golden_ending），不出现在 thesis_how | 脚本：含 'topic' 的要素 id 集合比对 | 集合恰为那 4 个 |
| `B1` | 边界纪律 | 未把「三抓手」扩写成正文段落（骨架只给结构 + 开放槽位） | 文本比对 | 无扩写、无编造案例 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json
s=json.load(open('<outdir>/structure.json',encoding='utf-8'))
els={e['id']:e for e in s['elements']}
print('IDS', [e['id'] for e in s['elements']])
print('HOW', els['thesis_how']['text'].split('\n'))
print('ENDING', els['golden_ending']['text'].split('\n'))
print('STATS', s['placeholder_stats']['total_filled_from_input'], s['placeholder_stats']['total_open'])
print('TOPIC_IN', [e['id'] for e in s['elements'] if 'topic' in e['filled_from_input']])
PY
```

预期输出：

```text
IDS 5 个 / HOW 五行（首两行为冻结文案，后三行为 `N. 卖点——【占位:…】`）/ ENDING 两行 / 填充总数 7、total_open 10 / TOPIC_IN 四要素
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
