# hot-templates-skill t05 — 题面与判据（边界）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t05` |
| 维度 | 边界 |
| nonce | `hot-t05-1c9e5d` |

## 1 题面（可直接投喂被测臂）

```text
我想要四个平台的爆款骨架：抖音口播、小红书图文、公众号文章、短视频分镜表，主题都是「论文文献管理的最小工具」，卖点用 data/points.json 里这三条。使用 hot-templates 技能，产物分别写入 out/dy、out/xhs、out/wx、out/video 四个目录。
```

## 2 目标态

四个目录各恰含 骨架.md + structure.json；每个 structure.json 的 platform / platform_name / 要素数与所在目录一致，无跨平台串台。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 四次调用退出码均为 0 | echo $? ×4 | 0,0,0,0 |
| `A2` | 端态 | 四个目录各恰含 2 件产物 | find 计数 ×4 | 四个目录各计数 2 |
| `A3` | 端态 | 未产出「一次生成四平台」的合并产物或第 5 个目录 | find <workdir> -name 骨架.md 计数 + 目录列举 | 骨架.md 恰 4 个；out 下恰 4 个子目录 |
| `S1` | 语义 | 每份 structure.json 的 platform 字段与所在目录一致（dy/xhs/wx/video） | json 读 + 与路径比对 | 4/4 一一对应 |
| `S2` | 语义 | platform_name 与 structure_name 逐平台正确（抖音口播稿 / 小红书图文 / 公众号文章 / 短视频分镜表 及各自 structure_name） | json 读比对 | 4/4 正确，无串台 |
| `F1` | 结构版式 | 要素个数逐平台为 6 / 7 / 5 / 6，且 id 序列各自冻结 | structure.json element_count + ids 比对 | dy=6、xhs=7、wx=5、video=6 |
| `F2` | 结构版式 | 骨架.md 首行分别为 `# 抖音口播稿 · 爆款骨架`、`# 小红书图文 · 爆款骨架`、`# 公众号文章 · 爆款骨架`、`# 短视频分镜表 · 爆款骨架` | 各 md 首行比对 | 4/4 逐字命中 |
| `C1` | 机械自洽 | 每份 elements 内不得出现其它平台的要素 id（如 dy 产物里不得有 shot_1、wx 产物里不得有 hook_3s） | 脚本：id 前缀跨平台污染检测 | 4/4 无污染 |
| `C2` | 机械自洽 | 四份产物均无 {{ 或 }} 模板残留；四份的 topic 都逐字等于「论文文献管理的最小工具」 | 正则扫描 + json topic 比对 | 残留 0；topic 4/4 一致 |
| `B1` | 边界纪律 | 遵守「一次一跑」：未把四个平台合成一次调用（引擎无此能力），也未擅自扩写任一平台的成文 | 复核执行轨迹为 4 次调用 + 裁判通读 | 4 次独立调用，无扩写 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,glob,os
exp={'dy':6,'xhs':7,'wx':5,'video':6}
for p in ('dy','xhs','wx','video'):
    s=json.load(open(f'out/{p}/structure.json',encoding='utf-8'))
    print(p, s['platform'], s['platform_name'], s['element_count'], exp[p], s['element_count']==exp[p])
print('MD_COUNT', len(glob.glob('out/*/骨架.md')))
PY
```

预期输出：

```text
四行 platform 与所在目录一致、element_count 分别 6/7/5/6 全 True / MD_COUNT 4
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
