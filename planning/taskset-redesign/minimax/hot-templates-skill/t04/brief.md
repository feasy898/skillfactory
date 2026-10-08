# hot-templates-skill t04 — 题面与判据（能力）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t04` |
| 维度 | 能力 |
| nonce | `hot-t04-b70a36` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，生成短视频分镜表爆款内容骨架，产物写入 <outdir>（骨架.md + structure.json）。材料自含——platform=video，topic=高铁商务座的值不值，**没有给任何卖点**（points 为空列表）。模板冻结：6 镜 45 秒分镜表（时间轴/画面/口播/字幕）。卖点槽位全部空缺，请如实保留开放槽位，不要自行编卖点填充。
```

## 2 目标态

6 要素 name/meta 全部冻结；三个卖点镜（shot_3/4/5）的卖点槽位全部落占位；total_open == 18。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 两件产物齐全非空、退出码 0 | find 计数 + echo $? | 计数=2，码 0 |
| `S1` | 语义 | shot_3/4/5 的口播与字幕列均落 【占位:价值点1/2/3】（缺失槽位 token 字面冻结） | structure.json 三个镜的 text 逐字比对 | 三镜各含对应价值点 token；points_used == [null,null,null] |
| `S2` | 语义 | shot_4 文本的 placeholder_count 恰为 4（画面 1 + 口播 2 + 字幕 1），去重后 open token 恰为 3 个 | 正则重计数 + by_element 读取 | placeholder_count == 4；去重 token 数 == 3 |
| `F1` | 结构版式 | 6 个要素 id 为 shot_1..shot_6，name 逐字冻结为「分镜N（起-止）」（如 分镜1（00:00-00:03）、分镜6（00:40-00:45）） | structure.json elements[].name 逐项比对 | 六个 name 全部逐字命中 |
| `F2` | 结构版式 | 每镜 meta 恰 7 键：shot_no / time_range / duration_sec / visual / voiceover / subtitle / beat | meta 键集比对 | 六镜键集全为这 7 项 |
| `F3` | 结构版式 | 时间轴冻结为 00:00-00:03 / 00:03-00:10 / 00:10-00:20 / 00:20-00:30 / 00:30-00:40 / 00:40-00:45（3/7/10/10/10/5 秒）；骨架.md 含表头四列与「共 45 秒」 | meta.time_range / duration_sec 序列比对 + md 文本 | 六段全对；md 含 `| 序号 | 时间轴 | 画面 | 口播 | 字幕 |` 与「共 45 秒」 |
| `C1` | 机械自洽 | placeholder_stats.total_open == 18（零卖点形态的总占位口径） | structure.json 读取 + 正文正则重计数 | 18 |
| `C2` | 机械自洽 | by_element 求和 == total_open；各镜逐个重计数一致 | 脚本求和 + 逐镜正则 | 求和 == 18；6/6 一致 |
| `C3` | 机械自洽 | 骨架.md「占位符统计」节的数字与 structure.json.placeholder_stats 同源 | 两处数字比对 | 均为 18 |
| `B1` | 边界纪律 | 未为三个卖点镜自行编造卖点内容（占位 token 内文保持冻结字面） | token 内文逐字比对 | 无填充 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,re
s=json.load(open('<outdir>/structure.json',encoding='utf-8'))
print('NAMES', [e['name'] for e in s['elements']])
print('META_KEYS', sorted(s['elements'][0]['meta']))
print('TIMES', [e['meta']['time_range'] for e in s['elements']])
print('DURS', [e['meta']['duration_sec'] for e in s['elements']])
e4=s['elements'][3]
toks=re.findall(r'【占位:([^】]*)】', e4['text'])
print('SHOT4_COUNT', len(toks), 'UNIQ', len(dict.fromkeys(toks)), 'TOKENS', toks)
print('TOTAL_OPEN', s['placeholder_stats']['total_open'], 'POINTS_USED', s['points_used'])
PY
```

预期输出：

```text
NAMES 六个冻结名 / META_KEYS 七键 / TIMES 六段冻结 / DURS [3,7,10,10,10,5] / SHOT4_COUNT 4 UNIQ 3 / TOTAL_OPEN 18 / POINTS_USED [None,None,None]
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
