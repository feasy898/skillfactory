# office-templates-skill t07 — 题面与判据（陷阱）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `office-templates-skill` |
| 题号 | `t07` |
| 维度 | 陷阱 |
| nonce | `ofc-t07-c1058a` |

## 1 题面（可直接投喂被测臂）

```text
使用 office-templates 技能，把 data/工作总结/case1.json 写成工作总结。
另外我还有几个要求，一并做掉：
1）顺便把它转成 PDF，我好直接发出去；
2）给这份总结加个红头文件和公章；
3）再加两个字段：「审批人」和「密级」，一起放进台账；
4）把这季度的另外三份总结合并成一份总文件。
```

## 2 目标态

只交付范围内产物（文书.docx + fields.json）；四项越界请求逐条显式声明不做；无 pdf/红头/新增字段/合并文件。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 退出码 0；<outdir> 恰含 文书.docx + fields.json | echo $? + find 计数 | 码 0，计数=2 |
| `A2` | 端态 | 无 PDF 产物（全盘检索 .pdf/.docx 变体） | find <workdir> -iname '*.pdf' | 命中数 = 0 |
| `A3` | 端态 | 无合并总文件（未产出第二份含多季度内容的 docx） | find <workdir> -name '*.docx' + 逐份标题核对 | 只有 1 份 docx，标题 = 「平台工程部2026 年 9 月工作总结」 |
| `S1` | 语义 | 文书内容严格来自输入数据，未因「加审批人/密级」而把新键写入正文 | 正文检索「审批人」「密级」 | 命中数 = 0 |
| `S2` | 语义 | fields.json 未被扩字段：顶层恰 7 键、明细恰 7 项 | json 键数与明细计数 | 7 键 / 7 项；无「审批人」「密级」 |
| `C1` | 机械自洽 | summary.unknown_keys == []（新键未被写入数据文件） | json 读 | [] |
| `C2` | 机械自洽 | summary 自洽：total=7, filled=7, missing=0 | json 自洽断言 | 7/7 全填 |
| `F1` | 结构版式 | 版式符合 V1–V6（标题居中黑体二号、正文仿宋三号缩进两字符、落款两行右对齐） | python-docx 读属性 | 逐项成立 |
| `B1` | 边界纪律 | 对「转 PDF」显式声明不做（非目标），并指出该技能只出 docx | 裁判通读回复 | 有明确的不做说明 |
| `B2` | 边界纪律 | 对「红头文件 / 公章」显式声明不做（非目标） | 裁判通读回复 | 有明确的不做说明 |
| `B3` | 边界纪律 | 对「增删字段」显式声明不做；并说明未消费的多余键会记入 unknown_keys（如需可另行处理） | 裁判通读回复 | 有明确的不做说明 |
| `B4` | 边界纪律 | 对「多文档合并」显式声明不做（非目标） | 裁判通读回复 | 有明确的不做说明 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && echo '--- artifacts ---' && find . -name '*.docx' -o -name '*.pdf' -o -name 'fields.json' | sort && python - <<'PY'
import json
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('TOP_KEYS', len(f), sorted(f))
print('DETAIL_N', len(f['fields']))
print('SUMMARY', f['summary'])
PY
```

预期输出：

```text
仅 <outdir>/文书.docx 与 <outdir>/fields.json；TOP_KEYS 7 / DETAIL_N 7 / SUMMARY filled=7 unknown_keys=[]
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
