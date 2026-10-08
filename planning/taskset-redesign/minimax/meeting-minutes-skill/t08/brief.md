# meeting-minutes-skill t08 — 题面与判据（陷阱）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `meeting-minutes-skill` |
| 题号 | `t08` |
| 维度 | 陷阱 |
| nonce | `mm-t08-c814b6` |

## 1 题面（可直接投喂被测臂）

```text
使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要。请用**完全相同的输入连续运行两次**，分别输出到 outA 与 outB 两个目录。交付前请把产物读回来核对一遍，不要只看退出码。
```

## 2 目标态

outA/outB 两套产物：summary 逐字节一致、docx 段落与表格文本逐字一致、三向自洽断言全过。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | outA 与 outB 各恰含 纪要.docx + summary.json 两文件 | find 计数（两目录各一次） | 两个目录计数均为 2 |
| `A2` | 端态 | 两次运行退出码均为 0 | 两次 echo $? | 0, 0 |
| `S1` | 语义 | 两次产物 summary.json 逐字节一致 | sha256sum 两文件 | 两个 sha256 相同 |
| `S2` | 语义 | 两次产物 docx 的全部段落文本与全部表格单元格文本序列逐字一致 | python 抽取两份 docx 的 (段落文本列表 + 表格单元格文本列表) 做 == 比较 | 两序列相等（不要求 zip 字节相同） |
| `C1` | 机械自洽 | docx 三节实际条数 == summary 三节计数 == 元信息行三个数字 | 脚本三方互校（决议/风险数编号段落数；待办数=表格数据行数） | 三处逐项相等，合计=4 |
| `C2` | 机械自洽 | 待办表格数据行数 == summary 待办数；表头三列齐全 | len(rows)-1 vs json | 相等且=1 |
| `C3` | 机械自洽 | 文件名未被改名、未加日期后缀 | ls 两目录 | 逐字为 纪要.docx / summary.json |
| `C4` | 机械自洽 | 交付回复中贴出了回读命令与其输出（写后回读三态） | 裁判核查回复与轨迹 | 含 ls/dir 回读或等价回读证据 |
| `F1` | 结构版式 | 三节标题逐字齐全、顺序固定 | 段落遍历 | 齐全无增节 |
| `B1` | 边界纪律 | 未以「第二次跑出来不一样是正常的」为由放过不确定性 | 裁判通读 | 如实报告差异或修复后重跑 |
| `B2` | 边界纪律 | 未手工复制 outA 产物冒充第二次真实运行 | 复核执行轨迹（两次 --outdir 不同的调用） | 两次独立调用 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && sha256sum outA/summary.json outB/summary.json && python - <<'PY'
from docx import Document
def dump(p):
    d=Document(p)
    return ([x.text for x in d.paragraphs],
            [[c.text for r in t.rows for c in r.cells] for t in d.tables])
print('DOCX_TEXT_EQUAL', dump('outA/纪要.docx')==dump('outB/纪要.docx'))
PY
```

预期输出：

```text
两个 summary.json 的 sha256 相同；DOCX_TEXT_EQUAL True
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
