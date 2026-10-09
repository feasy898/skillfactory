# office-templates-skill 评测报告

> 结论先行：本技能在 K-5 回炉重测 round2（EVAL-SPEC v0.2.1 口径，13 任务、每臂 n=3，2026-10-09）盲评三门全过，判定 **accepted（provisional，single_round_signal=true）**；确定性评测第 1 轮通过。round2 为**单轮信号**：同代第二轮（同 `model_pin.judge_model_id` 与 `judge_prompt_version`）确认前，按 EVAL-SPEC v0.2.1 §3.7-1 **禁止对外引用单点 Δ 值**，对外口径限于 verdict、任务数 n=13、每臂重复 rep=3、同代轮次=1、模型钉版、evalbench 版本（见「五、第二轮重测」）。历代评测数字按代分节如实披露于「二、结果」：①开发管线自评、②K5B round1（rejected）、③K-5 裁决（rejected）；跨代数字禁止 Δ 对位或合并披露（§3.7-4）。评测脚本随包附带，本报告的确定性部分任何人可按「四、复现」复跑验证。

## 一、评测方法

两层评测，均在本技能的开发管线中执行（评测管线未随包分发；确定性部分可按「四、复现」用随包脚本复跑）：

**第 1 层：确定性评测（机器判定，无随机、无网络）**

`eval/runner.py` 对 8 个官方样例单元（周报/请示函/会议通知/工作总结 × case1/case2）执行六类检查（contract §5）：单元齐全且产物文件集精确 / docx XML 安全（拒绝 DOCTYPE/ENTITY，防 XXE）/ 版式四要素（spec V2–V5）/ fields.json 自洽（spec S1–S3）/ 台账与 docx 实际内容一致且缺失记账正确（F1/F2/F4）/ 与参照产物字段填充一致率 ≥90%（spec §10）。任一失败 exit 1。红绿双向校验成立：`runner reference/out reference/out` 全过为绿、空目录判红（v0.2 ab5 任务 rubric 第 4 条要求并已实测）。

**第 2 层：有无技能对照盲评（A/B，EVAL-SPEC v0.2 双臂双重复）**

- 任务集 5 个（`eval/golden.json` 的 `ab_tasks`）：ab1 标准四类全量生成、ab2 必填缺失边界、ab3 空列表与字符串型列表边界、ab4 非法输入拒绝、ab5 确定性与交付自评；每任务每臂 **2 次独立重复**（双臂双重复，共 5×2×2=20 份盲评产物）。
- 双臂同模型：基线臂裸做任务；治疗臂先读 `SKILL.md` 及其 references 后按技能方法做同一任务；甲乙匿名落盘、交替呈现，裁判盲评（不知道甲乙哪个来自技能组）。
- 聚合口径：逐任务两重复取 majority 判臂，任务级胜率 = majority 为 treatment 的任务占比；判定按 v0.2 复合验收线（结果表 accepted=true）。

## 二、结果（盲评历代数字按代分节如实披露）

> 三代数字分属不同判分协议与任务集，互相**跨代**，禁止 Δ 对位或合并披露（EVAL-SPEC v0.2.1 §3.7-4）；当前有效判定只有 §五 round2 的 accepted（provisional，single_round_signal=true）。

### 2.1 ①开发管线自评（v0.2 双臂双重复，K5B 提交前自评）

**性质声明：本轮为开发管线内自评，跨代，未获 K-5 采信**；其 accepted=true 仅为自评口径，不构成 K-5 序列判定。

| 轮次 | 任务数 | 基线均分 | 治疗均分 | Δ | 任务级胜率 | 反向任务 | 判定 |
|---|---|---|---|---|---|---|---|
| v0.2 双臂双重复（自评） | 5 | 7.7 | 8.9 | +1.20 | 100%（5/5） | 0 | 达标（accepted=true，自评口径；未获 K-5 采信） |

逐任务两臂均分与 majority（聚合字段 `taskAggs`）：

| 任务 | 基线均分 | 治疗均分 | majority |
|---|---|---|---|
| ab1-standard-four-templates（标准四类全量） | 7.0 | 9.0 | treatment |
| ab2-boundary-missing-required（必填缺失边界） | 8.0 | 9.0 | treatment |
| ab3-empty-and-string-lists（列表边界） | 7.5 | 9.0 | treatment |
| ab4-invalid-input-rejection（非法输入拒绝） | 8.5 | 8.5 | treatment |
| ab5-determinism-layout-selfeval（确定性与交付自评） | 7.5 | 9.0 | treatment |

5 个任务 majority 全为 treatment、无一反向；其中 ab4 两臂同分（8.5），该任务考察的退出码契约较易被裸模型答对，技能优势集中在其余四类任务。盲评聚合原始数据见开发方评测存档（未随包分发）。

### 2.2 ②K5B round1（v0.2 协议、S8-JUDGE-v1、5 题、每臂 n=2）：rejected

盘上留档 `eval/results/benchmark.json`（原样并列保留）：Δ0.725、任务级胜率 40%（2/5）、反向任务 1，v0.2 复合线未同时通过，verdict=**rejected**（evidence_level=provisional）。

### 2.3 ③K-5 裁决（2026-10-08）：rejected

`planning/test-cards-20261008/K5-ruling-20261008.md`：三包维持不批准（rejected×3），office-templates 列为 rejected（Δ+0.73、胜率 40%、反向 1），定为回炉第一优先（资产补强 + n=3 + 增订任务集一并重测）。

### 2.4 确定性评测（第 1 轮通过）

- **开发管线第 1 轮（rep1）留档（存档未随包分发）**：8 样例按 contract §2 命令行全量重生成后 runner 全过（runner_final 留档：ok=true、68 项 checks 全 pass、字段填充一致率 100.0% 66/66）；D1 确定性成立（determinism 留档：四类 case1 的 fields.json 除 outputs 外 0 diff、docx 语义签名逐字节全等 docx_identical_sig=true、字段一致率 4×100%）。
- **分发包复跑（2026-09-30，发包时实跑，命令见「四、复现」）**：8 条生成命令全部 exit=0（Windows x64 / Python 3.12.10 / python-docx 1.2.0）；`python eval/runner.py out reference/out` → `ok=true`、68/68 checks 全 pass、**字段填充一致率 100.0%（66/66，阈值 90%）**、exit 0；绿自检（`runner reference/out reference/out`）exit 0；红检（空目录）exit 1；D1 双跑复验：fields.json 除 outputs 路径外逐字节一致、文书.docx zip 17 条目解压内容 CRC 全等；8 单元新生成产物与 `reference/out` 参照的 fields.json 除 outputs 外逐字段相等。

## 三、局限（诚实声明）

- **合成数据**：盲评任务与黄金集均为合成数据（按典型办公场景构造的数据 JSON 与边界 case，见 `reference/inputs/`），未用真实用户文书；绝对分值不可外推到真实分布，仅说明技能规则在该任务族上的边际贡献。
- 自评轮（§二①）5 任务样本量小，Δ +1.20 幅度中等且含一个两臂同分任务（ab4）；该轮结论取任务级方向一致性（5/5 majority、0 反向）而非单任务分值，且未获 K-5 采信。round2（§五）为 13 任务、n=3。
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

> 本节为 round2 披露（evalkit/runs/office-retest-20261009）。round2 数字（含其内部首轮 fail-closed 值与 D2 复判后终值）的**唯一正确来源为 `eval/results/benchmark-v02-1-office-retest.json`（标注 v0.2.1）**；历代首轮数字（开发管线自评、K5B round1）不在本节亦不作对比基准，按 §二分代披露（K5B round1 留档 `eval/results/benchmark.json` 原样并列保留），与 round2 跨代、禁止 Δ 对位（§3.7-4）。

**数字四随**：任务数 n=13（原始 5 ab + 增订 8 题，任务集冻结 9e7f57c6…）；每臂重复 n=3（78 臂调用，78/78 实测落点钉版 pass）；评测钉版=GLM-5.3@account:bigmodel-individual-coding-plan（max，M4 机制）与 Minimax-M3.1-Flash-Preview@minimax（enabled，M2 机制）双族被测、三族异族互裁（step-router-v1/GLM-5.3/Minimax-M3.1-Flash-Preview，judge_prompt_version=S8-JUDGE-v2-OFXRETEST-1）；评测协议=EVAL-SPEC v0.2.1（§3.3-2 tie-aware）。首轮后按 alpha 裁决（OFFICE-RETEST-RULING-20261009 §D1→D2）完成 t08 锚点澄清与仅 t08 复判一次，下表为**复判后终值**（首轮 fail-closed 值见下文 D2 复判段）。

> **t08 判官面补注（alpha 终裁 C4，2026-10-09）**：t08 判官面已按 D1 锚点澄清修订后投喂——rubric.md sha256=3280f0cd498d86bd7a85bddc9efe39ab39cce7dc0e6647f349a057cc027eaf9e、judge-notes.md=3bceaabc16c51d7f58f54d0d3220d010eb5a92f9aaa6b775e9573a23169ba0bf（与 merged index.json 冻结值一致），D1 修订后现行冻结净荷（99 文件）=c783e2cd66c0170fa6d12323f8ab465c3170ed1af625d0c64a14f811e4191ca8；**投喂面零改动**（task.json/brief.md 与两臂产物未动）。判据面修订仅影响 t08 一个任务的裁判口径，其余 12 题判官面未动。

| 指标 | 值 |
|---|---|
| 均分（treatment / baseline） | 9.28 / 4.69 |
| Δ（单轮信号，禁止对外单点引用，见下注） | +4.59（门 ≥1.0 过） |
| 任务级胜率 | 92.31%（12 胜 / 0 负 / 1 平；门 ≥60% 过，13 题需 ≥8 胜） |
| 反向任务 | 0（门 ≤1 过；swap 独立重算：swap_delta=−4.59 恒等式 |Σ|≤1e-9、swap_reverse=13 镜像） |
| 效率门 | token 比 0.473、耗时比 0.375（≤2.0 过） |
| 按族 matrix | glm 被测 7 题 7 胜 Δ+4.76；minimax 被测 6 题 5 胜 1 平 Δ+4.40 |
| **verdict** | **accepted（provisional）**——D2 复判后 13/13 全部可判且三条件实测值全过；single_round_signal=true（K5B-07），单包进 K-5 重提序列 |
| evidence_level / single_round_signal | provisional / **true**（K5B-07：round1 rejected，两轮不都 accepted → 旗必须为 true） |

> **单点 Δ 披露纪律（alpha 终裁 C2，2026-10-09）**：本表为评测存档完整披露，**Δ+4.59 系单轮信号，不作为头条指标对外呈现**。按 EVAL-SPEC v0.2.1 §3.7-1，同代第二轮（同 `model_pin.judge_model_id` 与 `judge_prompt_version`）确认前，**禁止对外引用任何单点 Δ 值**（含总 Δ、按族 Δ、逐题 Δ）；对外口径限于 **verdict、任务数 n=13、每臂重复 rep=3、同代轮次=1、模型钉版、evalbench 版本**。逐题 Δ 范围（t01–t07 +2.00～+7.25、t08 +7.70）仅作内部登记（round-plan.json `result_summary.delta_range_calibration`），**不外引**。若确需引用区间口径，按 §3.7-1 披露 [Δ_min, Δ_max] 与 n、轮次数。

**D2 复判（2026-10-09，仅 t08 一次）**：D1 锚点澄清（红线封顶=上限 min(公式分,4)、增补 ⟦0,0,0⟧→0.0 锚点、total=维度分机算公式分，alpha 签收）后，按原 staging（P1-P6 映射与 seed 不变、盲态与位置规则不变、面板 step-router-v1+Minimax；判词与会话实际归属见下方更正注记）重判 6 份产物。新增 judge_arith_check：两判官 × 6 产物=12/12 行判官 total≡维度分机算公式分（⟦0,0,0⟧→0.0、⟦0,1,1⟧→min(5.0,4)=4.0、⟦0.25,1,1⟧→6.3 三预登记锚点全部命中，无重发）；§3.4 抽检样本仍 P1（step 匿名复评 0.0 vs 主判 0.0，Δ=0.0 pass）。t08 终分 P1=0.0/P2=10.0/P3=10.0/P4=0.0/P5=10.0/P6=6.9（P6 双裁判档差 step ⟦0.5,1,1⟧=7.5 vs Minimax ⟦0.25,1,1⟧=6.3，|Δ|=1.2 在容差内）。复判留痕 `records/judging/t08-rejudge/d2-rejudge-record.json`；复判装置脚本 bug 两次崩溃，以 budget slot 149–158 与 `judge-work/t08-rejudge/_attempt1-crash-archive/` 如实留痕；崩溃期第 1 轮判词原文未保存（存档 _run1 与 _run2 逐字节相同、均系第 2 轮产物，存档标签有误），修复后第三次执行为落盘复判。首轮（fail-closed rejected：Δ+4.61、12/1/0 误记、t08 unjudgeable）记录另存 `records/judging/first-pass-pre-d2/`，与复判记录并存不覆盖。

> **D2 执行偏差更正注记（alpha 终裁 C3，2026-10-09；装置偏差不改判）**
>
> 经 alpha 终裁复核（`planning/test-cards-20261008/OFFICE-K5-FINAL-RULING-20261009.md` §D2），D2 执行留痕与最初登记存在以下偏差，据实更正（判分数据零改动，本注记为追加披露）：
>
> 1. **实发 3 轮，非单次执行**：D2 期间 t08-rejudge-d2 相关调用实发 3 轮（budget slot 149-151＝第 1 轮、153-155＝第 2 轮、156-158＝第 3 轮即终轮），另有 slot 152 脚本崩溃（KeyError，exit 1）。
> 2. **第 1 轮判词原文未保存**：崩溃存档 `_attempt1-crash-archive/` 的 _run1 与 _run2 经逐文件 md5 实测（22/22 文件）逐字节相同，均系第 2 轮产物——_run1 标签有误，第 1 轮判词未留存。
> 3. **Minimax 判官工作目录两轮间未清空，verdict 字节归属更正**：`d2-rejudge-record.json` 与 `records/judging/t08.json` 登记的 Minimax session（sess_b5987779…，slot 157）为终轮会话，但落盘 verdict.json 三份（终轮目录 + _run1 + _run2）md5 均为 dc5f9ce7…，字节实际出自**第 2 轮 sess_7ac785de（slot 154）**；终轮 transcript 自述「`verdict.json` is already written in the working directory and validates clean — and my independent re-judging landed on exactly the same six totals, so I left it in place rather than overwriting.」——终轮系复核后**沿用**第 2 轮判词文件，非新写。step-router-v1 侧登记与实际一致（终轮 slot 156、resample slot 158，attempt1 即过 arith）。
> 4. 前文原「面板 step-router-v1+Minimax」后所附会话口径已删除：Minimax 终轮未以新判词落盘（见第 3 条），两裁判会话状况以第 1、3 条如实登记为准，不作「全新会话」概括。
>
> **结果不变性证据链（七条，alpha 终裁定性：留痕与披露缺陷，不推翻结论）**：①盲态未破（verdict 只有 P 标签，臂映射仅在 judge-staging）；②污染仅同裁同 brief（BRIEF_SAME 实测）；③Minimax 首轮干净会话 6 总分（0/10/10/0/10/6.3，`records/judging/first-pass-pre-d2/t08.json`）与 D2 verdict 字节完全相同（独立复现）；④step 第 2/3 轮总分逐值一致，§3.4 抽检走 step 通道；⑤t08 treatment 每轮每裁均 10.0、baseline 最高 6.9，恒为 win；⑥重跑由脚本崩溃触发（slot 152 KeyError），非看结果挑选；⑦方向保守（P6 6.3→6.9，t08 Δ+7.90→+7.70）。

**跨代可比（§3.7-4）**：round2（S8-JUDGE-v2-OFXRETEST-1、13 题、n=3）与 round1（S8-JUDGE-v1、5 题、n=2）构成跨代，两轮数字禁止直接 Δ 对位或合并披露。

**t08 分歧性质（D3 更正）**：首轮 §3.4 复评分歧行为——两名异族裁判对被抽基线臂产物的**三维判档完全一致**（均 ⟦0,0,0⟧），分歧纯系 step-router-v1 把红线封顶条款误读为保底赋值（dims 0/0/0 而 total=4.0，公式分应为 0.0），且其匿名复评同一产物自证 0.0；非题面缺陷（treatment 10.0 两裁一致）、非实质判断分歧。属判分锚点缺陷，经 D1 锚点澄清（封顶=上限 min(公式分,4)、增补 ⟦0,0,0⟧→0.0）后由 D2 复判消除。首轮判分留痕另存 `records/judging/first-pass-pre-d2/t08.json`（更早的无 notes 版本存 `records/judging/first-pass-no-notes/`）；复判记录见 `records/judging/t08-rejudge/`。
