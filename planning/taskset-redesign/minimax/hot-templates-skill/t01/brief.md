# hot-templates-skill t01 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t01` |
| 维度 | 能力 |
| nonce | `hot-t01-8a12f7` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，生成抖音口播爆款内容骨架，产物写入 <outdir>（<outdir>/骨架.md 与 <outdir>/structure.json）。材料自含——platform=dy，topic=旧笔记本的续命改装，points 见 data/points.json（恰好 3 条）。模板冻结：3 秒钩子 + 痛点 + 价值点×3 + CTA，各要素的开放槽位字面不得改写。
```

## 2 目标态

6 要素顺序冻结、每要素恰 1 个占位（total_open=6、去重 token=4）、钩子与 CTA 句式逐字、pain_point/cta 无输入填充。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | <outdir> 恰含 骨架.md 与 structure.json，均非空 | find 计数 + 文件大小 | 计数=2，均非空 |
| `A2` | 端态 | 退出码 0，stdout 打印一行 OK 前缀摘要 | echo $? + stdout 首行 | 码 0，首行以 `OK platform=dy` 开头 |
| `S1` | 语义 | hook_3s 文本逐字以「别划走！还在为「旧笔记本的续命改装」反复内耗的人」开头（冻结句式，主题代入尖括号内） | structure.json 元素文本 startswith 断言 | 逐字命中 |
| `S2` | 语义 | cta 文本逐字含「点赞收藏，评论区扣「1」」（冻结扣词） | 元素文本 in 断言 | 逐字命中 |
| `S3` | 语义 | pain_point 与 cta 的 filled_from_input 均为 []（这两要素不含 topic 填充），value_1..3 各恰含一个 point#N | structure.json 逐要素字段比对 | pain_point/cta == []；value_1/2/3 == ["point#1"/"point#2"/"point#3"] |
| `F1` | 结构版式 | 6 个要素 id 顺序恰为 hook_3s、pain_point、value_1、value_2、value_3、cta | structure.json elements[].id 序列比对 | 顺序一致，无增删 |
| `F2` | 结构版式 | 每个要素恰 1 个占位 token（by_element 六项全为 1），total_open == 6 | structure.json placeholder_stats 比对 + 正文正则重计数 | by_element 六项 ==1；total_open == 6 |
| `C1` | 机械自洽 | 每个元素的 placeholder_count 与其 text 正则重计数一致；total_open（出现次数）== 6，而 open_tokens_unique（去重保序）== 4（value_1..3 共用同一 token，去重后计 1） | 正则 `【占位:([^】]*)】` 重计数 vs by_element，并读 open_tokens_unique | 6/6 一致；unique 长度 4 |
| `C2` | 机械自洽 | 骨架.md 首行为 `# 抖音口播稿 · 爆款骨架`，含主题行与尾部「占位符统计」节，统计数字与 structure.json 同源 | 骨架.md 文本比对 + 数字比对 | 逐字一致，数字 == 6 |
| `B1` | 边界纪律 | 未为开放槽位编造内容填充（占位 token 内文保持冻结字面），未把骨架扩写成成文 | 占位 token 文本逐字比对 | 无填充、无扩写 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,re
s=json.load(open('<outdir>/structure.json',encoding='utf-8'))
els={e['id']:e for e in s['elements']}
print('IDS', [e['id'] for e in s['elements']])
print('STATS', s['placeholder_stats'])
print('FILL', {k:els[k]['filled_from_input'] for k in ('hook_3s','pain_point','value_1','value_2','value_3','cta')})
print('HOOK_HEAD', els['hook_3s']['text'][:34])
print('CTA_OK', '点赞收藏，评论区扣「1」' in els['cta']['text'])
print('MD_HEAD', open('<outdir>/骨架.md',encoding='utf-8').readline().rstrip())
PY
```

预期输出：

```text
IDS 6 个顺序冻结 / STATS total_open=6、by_element 六项为 1、open_tokens_unique 长度 4 / FILL pain_point=[] cta=[] / HOOK_HEAD '别划走！还在为「旧笔记本的续命改装」反复内耗的人' / CTA_OK True / MD_HEAD '# 抖音口播稿 · 爆款骨架'
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
