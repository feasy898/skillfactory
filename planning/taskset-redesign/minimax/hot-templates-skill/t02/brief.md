# hot-templates-skill t02 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t02` |
| 维度 | 能力 |
| nonce | `hot-t02-3d6b90` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，生成小红书图文爆款内容骨架，产物写入 <outdir>（骨架.md + structure.json）。材料自含——platform=xhs，topic=小户型厨房的收纳动线，points 见 data/points.json（共 4 条）。模板冻结：标题带数字 + emoji 规则 + 正文分块 + 标签组。请按包内规定的标签口径与截断口径如实产出。
```

## 2 目标态

7 要素冻结；标签组按正则恰 6 个 # 标签且首标签由主题派生；标题数字恒为 3；4 卖点取前 3、第 4 条入 points_unused。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全非空、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | 标签组文本逐字 = 「#小户型厨房的收纳动线 #干货分享 #方法论 #自我提升 【占位:2个垂直领域标签，如：#时间管理 #精力管理】」 | structure.json tag_group.text 逐字比对 | 逐字命中（首标签为主题派生，已去 # 与空白） |
| `S2` | 语义 | 标题文本中的数字恒为 3（模板冻结为价值点数 3），即便输入给了 4 条卖点也不得变成 4 | 正则提取 title.text 里的数字 | 恰含数字 3，且不含数字 4 |
| `S3` | 语义 | 截断：points_used 恰为前 3 条原文；points_unused 恰含第 4 条原文，保序不乱 | structure.json points_used / points_unused 比对 | used 长度 3、unused 长度 1；points_input_count == 4 |
| `F1` | 结构版式 | 7 个要素 id 顺序恰为 title、hook_block、point_block_1..3、summary_block、tag_group | elements[].id 序列比对 | 顺序一致，无增删 |
| `F2` | 结构版式 | 标签计数口径：按正则 `#[^\s#]+` 在 tag_group.text 上计数恰为 6（4 个字面标签 + 占位 token 内 2 个示例标签） | re.findall(r'#[^\s#]+', text) 计数 | 6；末个 token 因正则不排除右括号而形如「#精力管理】」（口径说明，不另设考点）；不得按「3-8 个」的宽口径判过 |
| `F3` | 结构版式 | emoji 映射冻结：title=🔥、hook_block=✅、point_block_*=💡、summary_block=📌、tag_group=🏷️（meta.emoji 逐项比对） | structure.json meta.emoji 逐要素比对 | 五项全对 |
| `C1` | 机械自洽 | title / hook_block / summary_block 的 filled_from_input 含 topic；summary_block 另含 point#1..3 | structure.json 逐要素比对 | 三要素含 topic；summary 含 4 项 |
| `C2` | 机械自洽 | placeholder_stats.by_element 求和 == total_open（满 3 卖点应为 7），且与骨架.md「占位符统计」节数字一致 | json 求和 + md 数字比对 | total_open == 7；两处数字相同 |
| `B1` | 边界纪律 | 未自行给标签组增删标签以「凑到 3-8 个」的直觉区间；未把第 4 条卖点塞进正文块 | 标签计数 + points_used 比对 | 计数恰 6、正文仅前 3 条 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,re
s=json.load(open('<outdir>/structure.json',encoding='utf-8'))
els={e['id']:e for e in s['elements']}
tg=els['tag_group']['text']
print('TAGS', re.findall(r'#[^\s#]+', tg))
print('TAG_COUNT', len(re.findall(r'#[^\s#]+', tg)))
print('TITLE', els['title']['text'])
print('NUM_IN_TITLE', re.findall(r'\d', els['title']['text']))
print('INPUT/USED/UNUSED', s['points_input_count'], s['points_used'], s['points_unused'])
print('EMOJI', {e['id']: e['meta'].get('emoji') for e in s['elements']})
print('TOTAL_OPEN', s['placeholder_stats']['total_open'])
PY
```

预期输出：

```text
TAGS 6 个（前 5 个为 #小户型厨房的收纳动线/#干货分享/#方法论/#自我提升/#时间管理，第 6 个带尾部 】）/ TAG_COUNT 6 / NUM_IN_TITLE ['3'] / INPUT 4、USED 3 条、UNUSED 1 条 / EMOJI 五项冻结 / TOTAL_OPEN 7
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
