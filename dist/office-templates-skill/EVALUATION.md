# office-templates-skill 评测报告

> 结论先行：同一模型在加载本技能后，中文办公文书生成任务双臂双重复盲评（5 任务）得分从 **7.7 → 8.9（Δ +1.20，任务级胜率 100%，反向任务 0）**，判定**达标**（accepted=true）；确定性评测第 1 轮通过。评测脚本随包附带，本报告的确定性部分任何人可按「四、复现」复跑验证；盲评聚合原始数据见开发方评测存档（未随包分发）。

## 一、评测方法

两层评测，均在本技能的开发管线中执行（评测管线未随包分发；确定性部分可按「四、复现」用随包脚本复跑）：

**第 1 层：确定性评测（机器判定，无随机、无网络）**

`eval/runner.py` 对 8 个官方样例单元（周报/请示函/会议通知/工作总结 × case1/case2）执行六类检查（contract §5）：单元齐全且产物文件集精确 / docx XML 安全（拒绝 DOCTYPE/ENTITY，防 XXE）/ 版式四要素（spec V2–V5）/ fields.json 自洽（spec S1–S3）/ 台账与 docx 实际内容一致且缺失记账正确（F1/F2/F4）/ 与参照产物字段填充一致率 ≥90%（spec §10）。任一失败 exit 1。红绿双向校验成立：`runner reference/out reference/out` 全过为绿、空目录判红（v0.2 ab5 任务 rubric 第 4 条要求并已实测）。

**第 2 层：有无技能对照盲评（A/B，EVAL-SPEC v0.2 双臂双重复）**

- 任务集 5 个（`eval/golden.json` 的 `ab_tasks`）：ab1 标准四类全量生成、ab2 必填缺失边界、ab3 空列表与字符串型列表边界、ab4 非法输入拒绝、ab5 确定性与交付自评；每任务每臂 **2 次独立重复**（双臂双重复，共 5×2×2=20 份盲评产物）。
- 双臂同模型：基线臂裸做任务；治疗臂先读 `SKILL.md` 及其 references 后按技能方法做同一任务；甲乙匿名落盘、交替呈现，裁判盲评（不知道甲乙哪个来自技能组）。
- 聚合口径：逐任务两重复取 majority 判臂，任务级胜率 = majority 为 treatment 的任务占比；判定按 v0.2 复合验收线（结果表 accepted=true）。

## 二、结果

### 2.1 盲评（v0.2 双臂双重复）

| 轮次 | 任务数 | 基线均分 | 治疗均分 | Δ | 任务级胜率 | 反向任务 | 判定 |
|---|---|---|---|---|---|---|---|
| v0.2 双臂双重复 | 5 | 7.7 | 8.9 | **+1.20** | **100%（5/5）** | 0 | **达标**（accepted=true） |

逐任务两臂均分与 majority（聚合字段 `taskAggs`）：

| 任务 | 基线均分 | 治疗均分 | majority |
|---|---|---|---|
| ab1-standard-four-templates（标准四类全量） | 7.0 | 9.0 | treatment |
| ab2-boundary-missing-required（必填缺失边界） | 8.0 | 9.0 | treatment |
| ab3-empty-and-string-lists（列表边界） | 7.5 | 9.0 | treatment |
| ab4-invalid-input-rejection（非法输入拒绝） | 8.5 | 8.5 | treatment |
| ab5-determinism-layout-selfeval（确定性与交付自评） | 7.5 | 9.0 | treatment |

5 个任务 majority 全为 treatment、无一反向；其中 ab4 两臂同分（8.5），该任务考察的退出码契约较易被裸模型答对，技能优势集中在其余四类任务。

### 2.2 确定性评测（第 1 轮通过）

- **开发管线第 1 轮（rep1）留档（存档未随包分发）**：8 样例按 contract §2 命令行全量重生成后 runner 全过（runner_final 留档：ok=true、68 项 checks 全 pass、字段填充一致率 100.0% 66/66）；D1 确定性成立（determinism 留档：四类 case1 的 fields.json 除 outputs 外 0 diff、docx 语义签名逐字节全等 docx_identical_sig=true、字段一致率 4×100%）。
- **分发包复跑（2026-09-30，发包时实跑，命令见「四、复现」）**：8 条生成命令全部 exit=0（Windows x64 / Python 3.12.10 / python-docx 1.2.0）；`python eval/runner.py out reference/out` → `ok=true`、68/68 checks 全 pass、**字段填充一致率 100.0%（66/66，阈值 90%）**、exit 0；绿自检（`runner reference/out reference/out`）exit 0；红检（空目录）exit 1；D1 双跑复验：fields.json 除 outputs 路径外逐字节一致、文书.docx zip 17 条目解压内容 CRC 全等；8 单元新生成产物与 `reference/out` 参照的 fields.json 除 outputs 外逐字段相等。

## 三、局限（诚实声明）

- **合成数据**：盲评任务与黄金集均为合成数据（按典型办公场景构造的数据 JSON 与边界 case，见 `reference/inputs/`），未用真实用户文书；绝对分值不可外推到真实分布，仅说明技能规则在该任务族上的边际贡献。
- 5 任务样本量小，Δ +1.20 幅度中等且含一个两臂同分任务（ab4）；结论取任务级方向一致性（5/5 majority、0 反向）而非单任务分值。
- 裁判为 LLM（盲评），绝对分值可能有偏，但同一裁判同一标准下的组内比较有效。
- 评测在单一环境执行（Windows x64 / Python 3.12.10 / python-docx 1.2.0，与 spec.md 附录 A 一致），跨平台（字体声明渲染、路径分隔符）未验证。
- 盲评逐任务原始评语存开发方评测管线，未随包分发；本报告仅引用其聚合数字。

## 四、复现

```bash
# 在分发包根目录（确定性评测，应 exit 0；runner 必须显式传两参数，见 README 运行目录约定）
for t in 周报 请示函 会议通知 工作总结; do
  for c in case1 case2; do
    python scripts/gen_doc.py --template $t --data reference/inputs/$t/$c.json --outdir out/$t/$c
  done
done
python eval/runner.py out reference/out

# 红绿自校验
python eval/runner.py reference/out reference/out   # 绿：应 exit 0
python eval/runner.py <空目录> reference/out        # 红：应 units_found 失败、exit 1
```

盲评协议（双臂任务指令、rubric、裁判口径）见 `eval/golden.json` 的 `ab_tasks`（5 条）；盲评聚合原始数据见开发方评测存档（未随包分发；含 tasks/baselineMean/treatmentMean/delta/winRate/reverseTasks/accepted 及逐任务 taskAggs）。

## 五、第二轮重测（v0.2.1，2026-10-09，K-5 回炉重测 round2）

> 本节为 round2 披露（evalkit/runs/office-retest-20261009）。首轮（v0.2 双臂双重复 5 任务）数字见上文与
> `eval/results/benchmark.json`（原样并列保留）；round2 新口径并列落盘于
> `eval/results/benchmark-v02-1-office-retest.json`（标注 v0.2.1）。

**数字四随**：任务数 n=13（原始 5 ab + 增订 8 题，任务集冻结 9e7f57c6…）；每臂重复 n=3（78 臂调用，78/78 实测落点钉版 pass）；评测钉版=GLM-5.3@account:bigmodel-individual-coding-plan（max，M4 机制）与 Minimax-M3.1-Flash-Preview@minimax（enabled，M2 机制）双族被测、三族异族互裁（step-router-v1/GLM-5.3/Minimax-M3.1-Flash-Preview，judge_prompt_version=S8-JUDGE-v2-OFXRETEST-1）；评测协议=EVAL-SPEC v0.2.1（§3.3-2 tie-aware）。首轮后按 alpha 裁决（OFFICE-RETEST-RULING-20261009 §D1→D2）完成 t08 锚点澄清与仅 t08 复判一次，下表为**复判后终值**（首轮 fail-closed 值见下文 D2 复判段）。

| 指标 | 值 |
|---|---|
| 均分（treatment / baseline） | 9.28 / 4.69 |
| Δ | **+4.59**（门 ≥1.0 过） |
| 任务级胜率 | **92.31%**（12 胜 / 0 负 / 1 平；门 ≥60% 过，13 题需 ≥8 胜） |
| 反向任务 | **0**（门 ≤1 过；swap 独立重算：swap_delta=−4.59 恒等式 |Σ|≤1e-9、swap_reverse=13 镜像） |
| 效率门 | token 比 0.473、耗时比 0.375（≤2.0 过） |
| 按族 matrix | glm 被测 7 题 7 胜 Δ+4.76；minimax 被测 6 题 5 胜 1 平 Δ+4.40 |
| **verdict** | **accepted（provisional）**——D2 复判后 13/13 全部可判且三条件实测值全过；single_round_signal=true（K5B-07），单包进 K-5 重提序列 |
| evidence_level / single_round_signal | provisional / **true**（K5B-07：round1 rejected，两轮不都 accepted → 旗必须为 true） |

**D2 复判（2026-10-09，仅 t08 一次）**：D1 锚点澄清（红线封顶=上限 min(公式分,4)、增补 ⟦0,0,0⟧→0.0 锚点、total=维度分机算公式分，alpha 签收）后，按原 staging（P1-P6 映射与 seed 不变、盲态与位置规则不变、面板 step-router-v1+Minimax 均新会话）重判 6 份产物。新增 judge_arith_check：两判官 × 6 产物=12/12 行判官 total≡维度分机算公式分（⟦0,0,0⟧→0.0、⟦0,1,1⟧→min(5.0,4)=4.0、⟦0.25,1,1⟧→6.3 三预登记锚点全部命中，无重发）；§3.4 抽检样本仍 P1（step 匿名复评 0.0 vs 主判 0.0，Δ=0.0 pass）。t08 终分 P1=0.0/P2=10.0/P3=10.0/P4=0.0/P5=10.0/P6=6.9（P6 双裁判档差 step ⟦0.5,1,1⟧=7.5 vs Minimax ⟦0.25,1,1⟧=6.3，|Δ|=1.2 在容差内）。复判留痕 `records/judging/t08-rejudge/d2-rejudge-record.json`；复判装置脚本 bug 两次崩溃（判词未落盘）以 budget slot 149–155 与 `judge-work/t08-rejudge/_attempt1-crash-archive/` 如实留痕，修复后第三次执行为落盘复判。首轮（fail-closed rejected：Δ+4.61、12/1/0 误记、t08 unjudgeable）记录另存 `records/judging/first-pass-pre-d2/`，与复判记录并存不覆盖。

**跨代可比（§3.7-4）**：round2（S8-JUDGE-v2-OFXRETEST-1、13 题、n=3）与 round1（S8-JUDGE-v1、5 题、n=2）构成跨代，两轮数字禁止直接 Δ 对位或合并披露。

**t08 分歧性质（D3 更正）**：首轮 §3.4 复评分歧行为——两名异族裁判对被抽基线臂产物的**三维判档完全一致**（均 ⟦0,0,0⟧），分歧纯系 step-router-v1 把红线封顶条款误读为保底赋值（dims 0/0/0 而 total=4.0，公式分应为 0.0），且其匿名复评同一产物自证 0.0；非题面缺陷（treatment 10.0 两裁一致）、非实质判断分歧。属判分锚点缺陷，经 D1 锚点澄清（封顶=上限 min(公式分,4)、增补 ⟦0,0,0⟧→0.0）后由 D2 复判消除。首轮判分留痕另存 `records/judging/first-pass-pre-d2/t08.json`（更早的无 notes 版本存 `records/judging/first-pass-no-notes/`）；复判记录见 `records/judging/t08-rejudge/`。
