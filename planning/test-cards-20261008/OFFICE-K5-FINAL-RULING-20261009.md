# office 单包 K-5 重提终裁（alpha，2026-10-09）

## 终裁

office-templates K-5 重提状态确认为 **accepted（provisional，single_round_signal=true）**，列 K-5 重提序列第 1 位，单包不与 mm/hot 捆绑。三门数值由本裁决内从原始 per-run 分数独立复算，与盘上一致，fail-closed 口径未放宽。
但披露件存在 3 处实质缺陷 + 3 处轻缺陷（C1-C6），落盘并经 alpha 复核前，状态记为「已确认、待披露更正、未呈 owner」。

## D2 执行偏差（alpha 定性：留痕与披露缺陷，不推翻结论）

(a) D2 实发 3 轮调用（slot 149-151/153-155/156-158），非「只复判一次」；第 1 轮判词原文未保存；_attempt1-crash-archive 的 _run1 与 _run2 md5 相同，均系第 2 轮产物。
(b) Minimax 判官工作目录两轮间未清空：终轮 sess_b5987779 transcript 自述「verdict.json is already written … I left it in place」；落盘 verdict 三份 md5 均 dc5f9ce7…，字节出自第 2 轮 sess_7ac785de；EVALUATION.md:89「均新会话」与 d2-rejudge-record 归属记录不实。

不推翻结论的七条依据：①盲态未破（verdict 只有 P 标签，臂映射仅在 judge-staging）；②污染仅同裁同 brief（BRIEF_SAME 实测）；③Minimax 首轮干净会话 6 总分与 D2 完全相同（独立复现）；④step 第 2/3 轮总分逐值一致，§3.4 抽检走 step 通道；⑤t08 treatment 每轮每裁均 10.0、baseline 最高 6.9，恒为 win；⑥重跑由脚本崩溃触发（slot 152 KeyError），非看结果挑选；⑦方向保守（P6 6.3→6.9，t08 Δ+7.90→+7.70）。

## C1-C6 更正清单（零模型更正卡）

C1 重写 EVALUATION.md 结论先行与 §二：头条只写 round2 accepted（provisional，single_round_signal=true）；按代分节如实披露①开发管线自评 +1.20（K5B 前自评、跨代、未获 K-5 采信）②K5B round1 rejected（Δ0.725/胜率 40%/反向 1）③K-5 2026-10-08 裁决 rejected；禁止跨代 Δ 对位（§3.7-4）；:72 指向更正。
C2 §5 Δ+4.59 去单点头条呈现，注明单轮信号、同代第二轮确认前禁止外引单点 Δ（§3.7-1）；对外口径限于 verdict/n/rep/轮次/钉版/evalbench 版本；内部登记逐题 Δ 范围不外引。
C3 四处追加更正注记（EVALUATION.md:89、d2-rejudge-record.json、t08.json、budget.json closing_note）：D2 实发 3 轮、首轮判词未存档、存档标签有误、Minimax verdict 字节出自 sess_7ac785de、删「均新会话」；同时登记结果不变性七条证据链，定性装置偏差不改判。
C4 四随补注：t08 判官面已按 D1 修订（rubric 3280f0cd…/judge-notes 3bceaabc…/现行冻结 c783e2cd…），投喂面零改动。
C5 「六产物完全收敛」改「P1-P5 两裁判一致，P6 7.5 对 6.3（|Δ|=1.2 容差内）」。
C6 D1 签收与本终裁落盘于 merged/ 之外（本目录），避免改动冻结净荷哈希；REVISION-LOG 引用。

## mm/hot 开测前置（四项缺一不可）

① D5 三处缺口照 D1 流程修订（mm/t08 补⟦0.5,0,1⟧→5.0；hot/t08 补⟦0,0,1⟧→2.0；hot/t07 两档预登记+澄清 rubric:9 边界），附对照表经 alpha 签收；mm/t06、t07 零改动结论认可。
② EVAL-SPEC v0.2.2（D4 ①-⑤）落盘。
③ 修订后重算三口径冻结哈希，开工冻结校验 exit 0，office 子树逐文件 sha256 不变证明。
④ 预算台账预登记。
全套装置教训沿用（judge-notes 首批嵌入、step 无 prefill、n=3 tie-aware、抽检、从严登记、judge_arith_check 首轮即生效、封顶上限语义）+ D2 五条新纪律（唯一新工作目录、判词按 slot 先写后处理、mock 三分支干跑、判词归属记实际会话、崩溃重跑事前登记）。各自独立成轮独立提交 K-5，可并行。

## 对 owner 的交付建议

office 是 K-5 重提序列第 1 个、目前唯一 accepted 的包（provisional、单轮信号）。建议 owner 视对外宣传需要决定是否另做同钉版同 judge_prompt_version 的同代确认轮；确认前对外只说「通过」，不引用单点 Δ。

## 纪律重申

alpha 本签署只是 owner 委托的 K-5 裁决代行，**不构成发布授权**。dist 仍停在 owner 批准点。任何发布、上架、分发、对外宣传动作必须 owner 亲签，任何 agent 不得据本裁决自动发布。C1-C6 未落盘或复核发现影响门值的新失实，office 退回本裁决前状态重新裁决。
