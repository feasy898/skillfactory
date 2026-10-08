# K-5 发布申请（更新版 2026-10-03：实物已补迁，全部前置就绪，停在 owner 批准点）

> 撰写：zcode-nightshift ｜ 本文件为申请，**不是批准**。正式发布批准须由 owner 亲自签署 `evidence/publish-approval.md`；任何 agent 不得代签（TASK.md K-5 红线）。

## 1. 结论

| 事项 | 状态 |
|---|---|
| dist 三包实物 | ✅ 已从源机 anolis-gpu-01（/opt/gpumachine/projects/...）补迁，1.1M tar md5=dc0cf866 两端一致 |
| 指纹核验 | ✅ 内嵌仓 SHA 与 REGISTRY L14-16 逐一相符：meeting-minutes-skill=29bd123（26 文件）/ office-templates-skill=1e4ada5（38 文件）/ hot-templates-skill=52187cf（39 文件）；工作区干净 |
| 包内绿自检 | ✅ 三包 `eval/runner.py reference/out reference/out` 全部 exit 0（2026-10-03 复跑） |
| CRLF 修复 | ✅ 12 个 JSON 的 CRLF→LF 全部修复，CR 字节残留 0；修复后三包自检复跑仍全绿（未破坏冻结期望） |
| .mimosa 污染 | ✅ 0（REGISTRY 注 1 口径） |
| requirements.txt | ✅ 三包齐备 |
| 彩排结论 | ✅ K-3 round-1 通过（教学路径为 v5 三资产；dist 包为发布物非教学路径，无彩排阻塞项） |
| 入库方式 | 内嵌 .git 已剥离（指纹上移本文件记档），105 文件以内容入 monorepo |
| **owner 人工批准** | ⏳ **唯一待办**——签署 `evidence/publish-approval.md` 后按 DISTRIBUTION-CHECKLIST 发布 |

## 2. 三包摘要（摘自 REGISTRY L14-L16，2026-09-30 轮）

| 包 | 盲评 | 体检 | 许可 | 用途 |
|---|---|---|---|---|
| meeting-minutes-skill v1.0.0 | Δ+5.25 / 8/8 全胜 / 反向 0，accepted | A（5/5） | MIT | 会议转写稿→决议/待办/风险三段式纪要 docx |
| office-templates-skill v1.0.0 | Δ+1.20 / 5/5 全胜 / 反向 0，accepted（单轮） | A（5/5） | MIT | 周报/请示函/会议通知/工作总结四类中文办公模板 |
| hot-templates-skill v1.0.0 | Δ+6.10 / 5/5 全胜 / 反向 0，accepted | A（5/5） | MIT | 主题+卖点→四平台爆款内容骨架（注：五门复检欠账见 REGISTRY 注 2，以 release-candidate 形态随批） |

## 3. 已知如实披露

- office-templates-skill 盲评为单轮信号（二轮未做）；hot-templates-skill 效率门未测、benchmark.json 未落盘（REGISTRY 注 2）——两包按登记口径随三包一并待批，不隐瞒；
- 发布渠道与 DISTRIBUTION-CHECKLIST 原件在源机盘内未随迁——发布时需按 TASK.md 口径重建清单或从源机补迁（不阻塞批准决定）。

## 4. 发布红线

未获 owner 亲签前不发布；密钥不入仓；本夜全部改动截至本文件均为本地提交。

---

# SF-0008 更新增量（2026-10-08）：三包五门欠账补齐实测——效率门全过、盲评复合线未过，verdict=rejected×3

> 依据：evidence/owner-delegated-signing-20261008.md 第三节 SF-0008（K5B-01..K5B-10）与 owner 2026-10-08 三族并发指令。本节为 K5B-10 规定的**只增更新**，上文历史原文未改。三包 benchmark.json 已按 EVAL-SPEC v0.2 §8.1 九键落盘（本轮新欠账清偿：效率门实测、benchmark.json 落盘、office 二轮、hot 复检轮 n=3）。

## S1. 本轮协议（登记文件：evalkit/runs/sf0008-k5b/round-plan.json + budget.json）

- 被测对象：dist/ 顶层 canonical 三包（零改动，`git status -- dist/*-skill` 无源改动；treatment 挂载为可交付面过滤副本，禁 reference/、eval/ 入臂——A-12 同款口径）
- 臂：82 正式臂进程（mm 8 任务×2臂×n=2=32；office 5×2×2=20；hot 5×2×3=30 复检轮），按族分配 glm=46 / minimax=36，任务级奇偶轮换；两臂 prompt 逐字同；钉版 glm=GLM-5.3@account:bigmodel-individual-coding-plan（M4）、minimax=Minimax-M3.1-Flash-Preview@minimax（M2），82/82 db join 实测逐字命中、零漂移零红线
- 裁判面板（O-7 缺口已解除）：被测 glm → [step-router-v1, Minimax-M3.1-Flash-Preview]；被测 minimax → [step-router-v1, GLM-5.3]；每任务 ≥2 异族裁判、2 族互裁、槽位按任务奇偶轮换；盲态（产物匿名洗牌、路径/臂标脱敏）；step-router-v1 走模型 API 直调（assistant 预填约束输出），glm/minimax 走 headless M4/M2；§3.4 一致性抽检 18/18 任务配对完成、delta 全部 ≤2
- 记账：臂通道台账 84 条（82 done 正式 + 1 冒烟/机制类留痕 + 1 rate_limited 无效尝试不占额度，另有 2 条装置 bug 空转留痕不占额度）；rate_limited 重试实发 0；裁判通道台账 100 条（done 74 / no-verdict 19 / 停批打断 7；含 §3.4 配对修复 12 次与机制验证 2 次，全部逐条落账、无静默剔除）

## S2. 三包本轮结果（本轮=第 2 轮；第 1 轮为存量 ab_summary，均已实读核验）

| 包 | 确定性 | 盲评 v0.2 复合线 | 效率门 (token/耗时比 ≤2.0) | 格式/断言 | verdict（K5B-08） |
|---|---|---|---|---|---|
| meeting-minutes-skill | 绿 0 / 红 1 | Δ+1.93 ✓ ≥1.0，胜率 1/8=12.5% ✗ <60%（7 平 0 负 1 胜），反向 0 ✓ | 0.53 / 0.48 ✓ | 过 / 过 | **rejected**（provisional） |
| office-templates-skill | 绿 0 / 红 1 | Δ+0.73 ✗ <1.0，胜率 2/5=40% ✗ <60%（3 平 1 负 1 胜），反向 1 ✓ | 0.62 / 0.43 ✓ | 过 / 过 | **rejected**（provisional） |
| hot-templates-skill | 绿 0 / 红 1 | Δ+2.42 ✓ ≥1.0，胜率 2/5=40% ✗ <60%（0 平 3 负 2 胜），反向 0 ✓ | 0.74 / 0.63 ✓ | 过 / 过 | **rejected**（provisional） |

**如实结论**：效率门三包全过且 treatment 臂 token/耗时显著更省（约省 26%–57%）；确定性、格式、断言门全过（treatment 侧确定性断言 0 失败，checker 72/82 单元过、10 个 baseline 失败全为预期质量差）。但**盲评 v0.2 复合线三包均未达标**——2026-10-08 的基线臂（无技能的 GLM-5.3 / Minimax-M3.1-Flash-Preview 裸智能体）在冻结任务集上的评分已大幅追平带技能臂，第 1 轮的 Δ 优势（+5.25/+1.20/+6.10）在本轮强基线下收敛为 +1.93/+0.73/+2.42，任务级胜率因大量平局（mm 7/8 平）低于 60%。按 fail-closed 纪律（EVAL-SPEC §3.6、K5B-08），本轮 verdict 均为 **rejected**，disclosure.single_round_signal 全部保持 true，`real-verified` 字样零出现。

## S3. benchmark.json 指纹（K5B-10 要求项）

| 包 | benchmark.json sha256 |
|---|---|
| meeting-minutes-skill | `cb3e7a0d214087d2a724a4f14587f52eef9ba7adfb92145d618710b1c94b7d71` |
| office-templates-skill | `0e2c01e215e08aba15d69b88af96c7164b259130736729b0c83427e17c1df191` |
| hot-templates-skill | `87201abfaface506ed901354ca91a1876211fefc51a69ad545721a7ae058e1ac` |

golden.json sha256 与 REGISTRY 登记逐一相符（K5B-09）：`b3be400a…` / `2fa58b07…` / `19e4b6e1…`（s8_k5b_verify.py 复核 0 fails）。

## S4. 对第 1 节结论的影响

- 第 2 节表中三包「盲评 Δ/胜率」为第 1 轮数字，本轮第 2 轮实测后：**三包的 v0.2 复合线未过，不能以「盲评达标」作为本次发布申请的支撑项**；效率门欠账与 benchmark.json 欠账已清偿（REGISTRY 注 2 所列欠账状态相应更新为「已补齐、本轮盲评未过线」）。
- office「二轮未做」欠账已清偿：disclosure.rounds=2（round1=v3 存量 ab_summary Δ+1.20 accepted；round2=本轮 Δ+0.73 rejected）；两轮非都 accepted → single_round_signal=true 维持。
- hot 复检轮欠账已清偿：n=3 复检（EVAL-SPEC 附录 A）实测 Δ+2.42 / 胜率 40%，复合线未过。
- 是否以「确定性+效率过、盲评两轮分歧」的形态继续推进、或回炉迭代资产/任务适配性后重跑，属 owner 裁量；本申请仍停在 owner 亲签 `evidence/publish-approval.md` 前一步，未获签不发布（第 4 节红线不变）。

