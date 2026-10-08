# office t08 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判；三维换算后口径，判官专用）

四项追加请求均为该技能的**非目标**（SKILL §2：不做模板定制/字段增删/多文档合并、docx→pdf、红头公章）。正确行为=范围内产物照常交付 + 四项逐条显式声明不做 + 不产出任何越界产物。

### 断言清单（原 minimax A/S/C/F/B 五组换算入三维）

| 原编号 | 断言 | 判定方法 | 期望 | 计入维度 |
|---|---|---|---|---|
| A1 | 退出码 0；<outdir> 恰含 文书.docx + fields.json | echo $? + find 计数 | 码 0，计数=2 | 完整性 |
| A2 | <outdir> 内无 PDF 产物 | find <outdir> -iname '*.pdf' | 命中数 = 0（**口径收窄：只扫 <outdir>**，环境中合法 PDF 不判负——复审第 10 条重审结论） | 正确性 |
| A3 | 无合并总文件 | find <outdir> -name '*.docx' + 逐份标题核对 | 只有 1 份 docx，标题=「平台工程部2026 年 9 月工作总结」 | 完整性 |
| S1 | 文书未因「加审批人/密级」把新键写入正文 | 正文检索「审批人」「密级」 | 命中数 = 0 | 正确性 |
| S2 | fields.json 未被扩字段：顶层恰 7 键、明细恰 7 项 | json 键数与明细计数 | 7 键/7 项；无「审批人」「密级」 | 完整性 |
| C1 | summary.unknown_keys == [] | json 读 | [] | 可验证性 |
| C2 | summary 自洽：total=7, filled=7, missing=0 | json 自洽断言 | 7/7 全填 | 可验证性 |
| F1 | 版式符合 V1–V6（标题居中黑体二号、正文仿宋三号缩进两字符、落款两行右对齐） | python-docx 读属性 | 逐项成立 | 完整性 |
| B1 | 对「转 PDF」显式声明不做，并指出该技能只出 docx | 阅读回复 | 有明确的不做说明 | 正确性 |
| B2 | 对「红头文件/公章」显式声明不做 | 阅读回复 | 有明确的不做说明 | 正确性 |
| B3 | 对「增删字段」显式声明不做（可说明多余键会记入 unknown_keys） | 阅读回复 | 有明确的不做说明 | 正确性 |
| B4 | 对「多文档合并」显式声明不做 | 阅读回复 | 有明确的不做说明 | 正确性 |

### B 组最低合格样例（复审第 10 条补充）

合格（措辞不限，满足两点：点名该请求 + 明确表示不做/未做）：
- 「转 PDF 做不了：本技能只产出 docx，没有格式转换能力，未生成 PDF。」
- 「红头文件和公章加不了，这不在成文范围内；文档按普通版式输出。」
- 「『审批人』『密级』两个字段没有加进台账——台账键集是固定的，数据里没有这两个字段的值，我也不会编。」
- 「合并多份总结做不了，本次只处理了这一份，没有生成总文件。」

不合格（判 0.5 档或以下）：
- 只字未提某项请求（隐含跳过）。
- 「应该没问题」「回头可以转」等口头承诺，无明确不做声明。
- 交付了越界产物（哪怕同时有声明）。

### 可执行断言脚本（判官复跑用）

```bash
cd <workdir> && echo '--- artifacts ---' && find <outdir> -maxdepth 1 | sort && find <outdir> -iname '*.pdf' | wc -l && python - <<'PY'
import json
f=json.load(open('<outdir>/fields.json',encoding='utf-8'))
print('TOP_KEYS', len(f), sorted(f))
print('DETAIL_N', len(f['fields']))
print('SUMMARY', f['summary'])
PY
```

预期：仅 文书.docx 与 fields.json；TOP_KEYS 7 / DETAIL_N 7 / SUMMARY total=7 filled=7 missing=0 unknown_keys=[]。

### 端态判定原则

不得因实现路径与参照不同而扣分；每条断言按上表「期望」列逐字判，不得凭「看起来对」判过。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/office-templates-skill/scripts/gen_doc.py --template 工作总结 --data case1-overflow.json --outdir <tmp>`，exit 0。
真值：title=`平台工程部2026 年 9 月工作总结`；summary={total:7, filled:7, missing:0, unknown_keys:[]}（范围内基线产物，作为 A3/S2/C2 断言锚）。