# hot-templates-skill t06 — 题面与判据（陷阱）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t06` |
| 维度 | 陷阱 |
| nonce | `hot-t06-42fb8a` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，生成抖音口播爆款内容骨架，产物写入 <outdir>（骨架.md + structure.json）。材料自含——platform=dy，topic=家庭备餐的十分钟流程，points 见 data/points.json（3 条，其中第 2 条只有空白字符）。请如实处理这条空白卖点，不要跳过它把后面的卖点往前挪，也不要替它编内容。
```

## 2 目标态

第 2 槽落 【占位:价值点2】且 points_used[1] 为 null；第 3 条卖点仍入第 3 槽（保序）；points_input_count == 3。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全非空、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | value_2 文本恰含 【占位:价值点2】（空白串按缺失处理，不是空字符串、也不是被跳过） | structure.json value_2.text 包含断言 | 含「【占位:价值点2】」 |
| `S2` | 语义 | 保序：value_1 = 第 1 条卖点、value_3 = 第 3 条卖点（第三条不得被挤进第 2 槽） | value_1/value_3 文本逐字比对 | value_1 含「第一件事先把台面清空」；value_3 含「第三件事当天做完不留隔夜」 |
| `S3` | 语义 | points_used 恰为 [第1条, null, 第3条]（缺失位为 JSON null 而非空串或被删除） | structure.json points_used 逐位比对 | 长度 3，中间为 null |
| `F1` | 结构版式 | value_2 的 filled_from_input 为 []（未填充槽位不记 point#2） | structure.json 逐要素比对 | []；value_1/3 为 ["point#1"]/["point#3"] |
| `C1` | 机械自洽 | points_input_count == 3（输入条数，与规整后的 3 槽是两个概念，不得写成 2） | structure.json 读取 | 3 |
| `C2` | 机械自洽 | total_open == 7（6 个冻结 token + 第 2 槽多出的 价值点2），by_element 中 value_2 == 2 | json 读取 + 正文正则重计数 | 7；value_2 为 2，其余五要素为 1 |
| `B1` | 边界纪律 | 未替空白卖点编造内容；未把空白卖点静默丢弃导致槽位前移 | value_2 文本逐字比对 | 占位 token 保持冻结字面，无编造、无前移 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,re
s=json.load(open('<outdir>/structure.json',encoding='utf-8'))
els={e['id']:e for e in s['elements']}
print('INPUT_COUNT', s['points_input_count'])
print('USED', s['points_used'])
print('V1', els['value_1']['text'][:28])
print('V2', els['value_2']['text'])
print('V3', els['value_3']['text'][:30])
print('FILL', {k: els[k]['filled_from_input'] for k in ('value_1','value_2','value_3')})
print('TOTAL_OPEN', s['placeholder_stats']['total_open'], 'BY_EL', s['placeholder_stats']['by_element'])
PY
```

预期输出：

```text
INPUT_COUNT 3 / USED [第1条, None, 第3条] / V2 含【占位:价值点2】/ FILL value_2=[] / TOTAL_OPEN 7、by_element.value_2=2
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
