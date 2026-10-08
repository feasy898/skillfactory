# meeting-minutes-skill t04 — 题面与判据（边界）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `meeting-minutes-skill` |
| 题号 | `t04` |
| 维度 | 边界 |
| nonce | `mm-t04-91f6c2` |

## 1 题面（可直接投喂被测臂）

```text
使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>（纪要.docx + summary.json）。这份转写稿里有寒暄、散会、纯空白和一条乱码行，真正有实质内容的发言一行都没有。请如实产出反映这一事实的纪要，不要为了「看起来完整」而补写任何一条事项。
```

## 2 目标态

退出码 0 的合法空纪要：三节标题齐全、三个章节 0 条、待办表仅表头行、summary 四键全 0。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 退出码为 0（空/全噪声输入不是运行错误） | echo $? | 0，不报错退出 |
| `A2` | 端态 | 两件产物仍齐全 | find 计数 | 计数=2 |
| `A3` | 端态 | docx 可被 python-docx 打开（空纪要也必须是合法 docx） | python-docx 打开 | 无异常 |
| `S1` | 语义 | 零条收录：文档中不含任何「n. 【hh:mm · 说话人】」形式的条目 | 正则全文扫描 | 命中数 = 0 |
| `S2` | 语义 | 未把寒暄行/散会行/乱码行改写成事项 | 裁判通读 + 与源行集合比对 | 无任何条目文本取自源行 |
| `F1` | 结构版式 | 三节标题逐字齐全且顺序固定，即使该节 0 条也不得删除标题 | 段落遍历找三节标题 | 「一、决议事项」「二、待办事项」「三、风险与关注」三个都在 |
| `F2` | 结构版式 | 待办表格仅表头行、0 个数据行 | len(doc.tables[0].rows) | 行数 = 1 |
| `F3` | 结构版式 | 元信息行格式与数字 | 正则捕获 | 匹配 `来源：transcript-8a6511.txt ｜ 解析发言 0 条（决议 0 · 待办 0 · 风险 0）` |
| `C1` | 机械自洽 | summary.json 四键全为 0，合计=0 | json 读 | {决议事项:0, 待办事项:0, 风险与关注:0, 合计:0} |
| `C2` | 机械自洽 | 三向自洽：summary 三节数 == docx 实际条数 == 元信息行数字 == 0 | 脚本三方互校 | 四者全为 0 |
| `B1` | 边界纪律 | 首字节 BOM 未导致解析异常或乱码入文；未手工绕过脚本改产一份「看起来完整」的纪要 | 裁判复核执行轨迹（是否调用了 scripts/minutes.py 或按 references 手工产出） | BOM 被 utf-8-sig 容忍；未编造条目 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,re
from docx import Document
d=Document('<outdir>/纪要.docx')
ps=[p.text for p in d.paragraphs]
print('SECTIONS', [s for s in ('一、决议事项','二、待办事项','三、风险与关注') if s in ps])
print('ENTRY_RE_HITS', len(re.findall(r'\d+\. 【', '\n'.join(ps))))
print('TABLE_ROWS', len(d.tables[0].rows))
print('SUMMARY', json.load(open('<outdir>/summary.json',encoding='utf-8')))
PY
```

预期输出：

```text
SECTIONS 三项齐全 / ENTRY_RE_HITS 0 / TABLE_ROWS 1 / SUMMARY 四键全 0
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
