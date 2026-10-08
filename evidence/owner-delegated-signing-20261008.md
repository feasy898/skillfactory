# owner 委托签署纪要（2026-10-08）

> **授权链**：owner 于 2026-10-08 给出常设指示——凡需要人类签署/裁定的事项，由 Opus/alpha（`new-provider-2/alpha`）或 Kimi K3（`moonshot-kimi/k3`）之一代为审阅并回答，其回答即代表 owner 的选择；主代理负责先把人类意图完整解释给受托模型，并将结果以本文件落盘留痕。
> **本次受托模型**：new-provider-2/alpha（Opus），经动态工作流 `dwfrun-2cb01171` 完成；alpha 在临时副本中实跑核验后出具以下决定（第一节为其原文，未删改）。
> **签署人栏口径**：`owner 委托 alpha 代行`（delegated-signing-model），不冒称人工亲签；涉及人工标注的事项（D3 金标）不因本签署视为已人工完成。
> **签署时仓库状态**：HEAD = `cfad437aa2208bcc1d4fbad5faf1dc298ed6413e`（签署落盘提交前的基线）。
> **K-5 状态**：**未批准**。`evidence/publish-approval.md` 不存在，且在按第②项补齐欠账、重新提交并获得新签署之前不得存在。
> **修订记录**：2026-10-08 冷读复核（GLM-5.3 代行 kimi，kimi 渠道故障）提出 3 blocker + 6 improvement，由 alpha 全部修订（23 处，只收紧不放宽），本文件第三节已按修订文本更新；门槛脚本同步见 SF-0006 卡末注记。

---

## 一、四项签署决定（alpha 原文）

### ① devpool 题池 D1 签署

**决定**：签署全部 8 题的 D1（来源→题面）：mm-01、mm-02、hot-01、hot-02、hot-03、ofc-01、ofc-02、ofc-03。其中 mm 2 题和 hot 3 题共 5 道，满足 SF-0006 基线轮兜底门（mm/hot ≥5）。ofc 3 题只签 D1，D3 仍归 WS3。sc1（来源合法）判为成立。

**理由**：本次逐题读了 8 题的 brief.md 和 fixtures：实体全部是 nonce 化的虚构项目名和常见人名；ofc-02 的「联系电话」值为 null，没有真实个人信息。3 道 public-variant 题只引用法律、法规、公文条例和国标的条目号或文种定义，题面全部自写，没有整段复制原文，符合 INTENT §4-10 的版权口径。本次实测：用 python 核对 56 个包文件 sha256，全部与 pool-state 登记一致；在临时副本中跑 8 题 `gen_oracle.py --selftest`，结果全部 exit 0、SELFTEST PASS，sc2–sc4 复核成立；资产名 grep 零命中。

**附加条件**：(1) 本签只覆盖 D1。D3 要求人工金标对拍 ≥95%，必须由人做真实标注。代理不得自造金标，所以 mm/hot 的 D3 仍为 WAITING_OWNER，ofc 的 D3 仍为 WAITING_WS3。(2) 阻塞性发现：evalkit/harness/ws4_judge.py:37 的 DIST_ROOT=`<仓库上级>/afp-clone/zcode-research/skillfactory/dist`，这是拆仓前的布局，当前机器上不存在（/home/pan-ding/workspace/skill工厂/ 下只有 skillfactory）。L1 子轨因此报 bridge_error，按 fail-closed 判分器一律 exit 1。我在临时副本里先不链接跑了一遍，8 题 selftest 全部 exit 1；把这条路径链接到仓内 dist/ 后才全绿。SF-0006 开跑前必须修正这条路径并留痕，否则基线轮全红。(3) oracle/ 产物没有入仓（pool-state.json 登记的 outputs_sha256 对应文件不在盘上），可以用 gen_oracle 同种子逐字节复现（selftest 的 DET 项通过）。(4) 质量意见，不阻塞：hot 线 fixtures 的主题和卖点语义不搭（例如 hot-01 主题「宿舍收纳」配「四象限法排任务优先级」），会降低「模拟真实任务」的逼真度，建议下一版题池修正生成器配对。(5) 公开规范变体题的「公开发布」状态依据的是 source_ref 的陈述；我没有联网逐条核实原文页面。

【复核调和注记（alpha，2026-10-08，不改上文原文）】①附加条件(1)写的是「必须由人做真实标注，代理不得自造金标」，而 SF-0006/P2、A-08 由受托签署模型出具金标，两者字面冲突，调和如下：(i) 该禁项针对的是开发方或被测链路自产自判，以及任何冒称人工的标注。受托签署模型在 owner 常设授权链内出具标注，对 checker 输出盲态，且独立于开发方，属授权链内行为，不属禁项。(ii) 该标注不是人工标注。①(1)与 PLAN §3.8 的人工标注要求在字面上仍未满足，D3 证据等级降格为「受托模型金标（非人工）」；pool-state（d3_record.annotator_kind）、round-report 及一切引用都要如实写明，不得写成人工金标或人工 D3 已过。(iii) 人工标注可得后，须另开卡重做对拍；分歧以人工为准，并按 A-09 留痕。本注记只收紧、不放宽：mm/hot 的 D3 在受托标注对拍达标并签署之前，仍为 WAITING_OWNER。

### ② K-5 dist 三包发布批准

**决定**：不按现状批准，先补欠账、后重新提交签署，三包都不放行（hot-templates 也不例外）。发布形态倾向：dist/build/standard 合规变体（skills-ref 通过、已剔除 reference/），不发布顶层原始包。具体发布渠道、时机和收费由 owner 决定，本签不代决。

**理由**：SKILL-SPEC-v0.1 §4（standard/SKILL-SPEC-v0.1.md:268）规定五门全部通过才可进分发，「任一门不过，禁止发布」。但 REGISTRY 披露 1 写明「全批效率门未测」，三包盲评都是每臂 2 次重复；全仓 find 也找不到任何 benchmark.json（§4:276 要求落盘）。按 fail-closed 纪律（INTENT §3-7），未测的门只能算红，「接受披露放行」与之冲突；INTENT §2.4 意图 3 也要求先迭代到合成极限，再进入真实人类使用。

**附加条件**：重新提交前须补齐：(a) 三包效率门实测（token 比率和耗时比率 ≤2.0），盲评重复达标，eval/results/benchmark.json 和验收单落盘；office-templates 补第二轮盲评。【勘误】本条原引用「每臂 ≥3 次」，经核对 v2/standard/EVAL-SPEC-v0.2.md 附录 A，v0.2 已改为「标准 n=2，禁止 n=1；边界带/复检轮 n=3」，该引用不成立；决定本身仍成立，依据是 v0.2 同样要求而至今未满足的效率门与 benchmark.json 两项。(b) 修复 dist/build 变体中的悬空引用：变体已剔除 reference/，但 SKILL.md（meeting-minutes:61、hot-templates:80）和 EVALUATION.md「四、复现」仍让用户跑 `eval/runner.py <out> reference/out`，并声称「任何人可复跑验证」。这与实物不符，属于诚实性缺陷，必须二选一：改写说明，或随包附上非答案性质的输入样例。(c) REGISTRY「对外必须随附的披露口径」1–5 条要写进发布形态的 EVALUATION.md；现在的变体缺少 single_round_signal、效率门未测、real-verified ✗ 等字样。(d) dist-compliance-tickets.md 引用的 dist/build/build-summary.json 在盘上不存在，需要补出或更正引用。本次已实跑：在临时副本跑 `python tests/run_checks.py`，PASS 28/28、exit 0；三包 canonical `eval/runner.py reference/out reference/out` 绿 exit 0，空目录红 exit 1。补齐后需要新的签署，本签不构成预先批准。

### ③ canonical 源包 reference/ 目录处置

**决定**：选「留证据」：三包 canonical 源包的 reference/ 原样不动，只记账。决定不删除；「迁正」暂缓，等下次源包升版时随版本一起做。

**理由**：仓内仍有地方依赖 reference/：evalkit/harness/ws4_judge.py:429 的 devpool L1 子轨直接读 dist/\<pkg\>/reference/out，canonical runner 的自检也用 reference/out 作参照。删除会让题池判分器全部 fail-closed 变红，并丢失证据，所以不能删。②已定发布形态为 build 合规变体，而 build.py 已把 reference/ 排除出所有变体（HY-5），答案不会随分发面暴露。reference/ 本身是包内开发可见的样例，不属于 holdout，现阶段迁正只会给冻结中的 harness 增加改动风险。

**附加条件**：(1) 记账：REGISTRY 追加一条，说明 reference/ 为 oracle 性质参照物，canonical 顶层原始包禁止直接对外分发，只能经 build.py 变体出包。(2) 将来迁正时必须同步修改 ws4_judge.py 的 ref_root、build.py、canonical SKILL.md 的命令说明和相关测试，并重跑 run_checks.py 和 devpool selftest，以退出码为证。(3) 本选择与②联动：如果 owner 改为发布顶层原始包，本项需要重裁。

### ④ zctl-mcp / acceptor-agent 体检形态豁免

**决定**：批准形态豁免，记档为「体检不适用（形态不符），不作为质量污点」。v5 的 hotwords、deploy-pack、speaker-mapping 三件按同一先例一并豁免（REGISTRY 注 1 记的 C 级改注为形态错配）。豁免只去掉污点标签，不等于体检 A：五件状态保持「内部就绪」，不进 dist；WS9 分形态体检器建成后必须用对应形态的体检器补检。

**理由**：REGISTRY 注 1（L166）和注 A1（L194）都写明 v3 healthcheck 按 dist skill 包形态设计，拿它量 MCP server 包和 agent 角色包不适用；B 表 mcp-office-pack 已有「体检器 5 项不适用」的先例。本次在临时副本实跑两件的 eval/runner.py：绿（自评）exit 0，红（空目录）exit 1，用法错 exit 2，确定性门成立。豁免是显式记档、写明不适用，不是静默放行；而且不放宽进入 dist 的条件，所以不违反 fail-closed。如果要求按 skill 体检表整改，就是为了凑表去改 MCP/agent 的形态，违背 INTENT §4-4「符合国际通行标准」。

**附加条件**：(1) 事实更正：REGISTRY L191–192 记的 zctl-mcp 和 acceptor-agent 是「未体检」，并不是 C 级；C 级（2/5）是 v5 另外三件的记录。记档时按台账原文写。(2) WS9 的分形态体检器应包含 MCP 协议合规检查（对 zctl-mcp）和 agent 定义格式检查（对 acceptor-agent），建成后必须复检并在 REGISTRY 追加结果。(3) 两件的盲评只有 n=2（注 A2），加厚欠账不因本豁免消除；zctl-mcp 的真机端到端调用欠账也照旧保留。

---

## 二、D1 签署登记（已落盘 bench/devpool-r1/pool-state.json）

8 题 `d1_record.signoff` 已写入：签署人=`owner 委托 alpha 代行`，日期=2026-10-08，被签对象sha256=各题 brief.md sha256（单字段格式，沿用 SF-0005 报告 §5 第 3 步；runner_contract.json / gen_oracle.py / checks/ 等装置面文件按 alpha 勘误不列入 D1 签署对象，改由 freeze_device 钉版管辖。【复核更正】签署时 evalkit/harness/keyfiles.sha256 只覆盖 8 份 checks/run_check.py，gen_oracle.py 与 runner_contract.json 并未钉版，由 SF-0006 A-04 修订条款收口；题面四类文件的签署基准以本落盘提交 c5b4ca0 中 pool-state.json 的 pack_files_sha256 为准）。落盘时实算 8 题 × 7 个包文件共 56 个 sha256 与 pool-state 原登记**全部一致**（alpha 实测 + 本次落盘复算双确认）。

| 题号 | brief.md sha256 | 题型 |
|---|---|---|
| mm-01 | `80ff3b1c5dd7e6d7621e79de7855f7e23e0f69d3706f25d5f76d97f1f2ae7cfa` | positive（自建） |
| mm-02 | `eecf24f3afe9364746ff9c8e3db7f44cf5528b854bdf596a2ad6e8462b95dd65` | near-negative（公开变体） |
| hot-01 | `000ccae8ec3875a44e36aa253dfd629323cc63dfe3c0f2b76c5fefbb48f9fda7` | positive（公开变体） |
| hot-02 | `1f3fbb26f166485f0aa367e55535ec9d2676da145e5db091244444b985a5b420` | positive（自建） |
| hot-03 | `e8e6b8145c5e9fb2751a3719fe880ca0846dd125f0d808433d1d99a4c406a64d` | near-negative（自建） |
| ofc-01 | `39abc11962e2ba3ad6511496071ac5fc1c05d22f9ac71f402435d4c0ceb69cb3` | positive（自建） |
| ofc-02 | `4f99385ce80951d027e17d9b0b11988a178b6f82adc1b3ddf1fe5c8e8588512f` | adversarial（公开变体） |
| ofc-03 | `28fbfe16f1002455febd5326450326de4aca3dad9c06c1578d0e2b1ce499c919` | adversarial（自建） |

mm/hot 5 题 D3 维持 WAITING_OWNER——待受托模型按 SF-0006 P2 流程出具金标标注（annotator_kind=`delegated-signing-model`，如实不得冒称人工）后落盘；ofc 3 题 D3 维持 WAITING_WS3。

---

## 三、测试卡（alpha 开出并依冷读复核修订，2026-10-08）

### SF-0006 —— WS4 基线轮：devpool-r1 mm/hot 5 题 × 两族（GLM-5.3 默认臂 + Minimax-M3.1-Flash-Preview M1 钉版臂）× 两臂 × n=2，分三层（A 零模型装置层 → B 冒烟 4 臂 → C 基线 40 臂），每层可独立失败并如实留痕

**开跑前置**

- P1【签署代理人出具，主代理落盘】①的 D1 签署记录写入 bench/devpool-r1/pool-state.json：8 题 d1_record.signoff 三字段均非 null；签署人=「owner 委托 alpha 代行」，日期=2026-10-08；被签对象sha256=该题 brief.md 的 sha256（沿用 SF-0005 报告 §5 第 3 步的单字段格式）。题面四类文件（brief.md、rubric.md、task.json、fixtures/*）的签署基准 sha256，唯一来源是签署落盘提交 c5b4ca0 中 bench/devpool-r1/pool-state.json 的 pack_files_sha256，读取方式为 `git show c5b4ca0:bench/devpool-r1/pool-state.json`。该快照与签署基线 cfad437 逐键相等，签署时 alpha 实测与落盘复算双确认。不另附独立清单，也不以工作树 pool-state.json 为准，因为 ws4_pool_state.py:137–148 重跑时会按现盘重算该字段。【对①的勘误，如实说明】我在①写的是「7 个包文件」，但本次实读 evalkit/packs/ws4-dev/mm-01/runner_contract.json，里面是旧机 Windows 绝对路径（D:\new-workspace\agent-asset\afp-clone\...）。A-01 修好路径后这个文件必然要重生成，它和 gen_oracle.py、checks/run_check.py 一样属于装置面，不再算 D1 签署对象，改由 freeze_device 钉版管。签署时 keyfiles.sha256 只覆盖 8 份 checks/run_check.py，gen_oracle.py 与 runner_contract.json 的钉版由 A-04 收口。
- P2【D3 金标；标注由签署代理人出具，样本准备、注入和对拍由开发方执行】我判定 D3 是本卡出分的硬前置。依据三条：本轮质量轨不可判（SF-0004 报告 §7），产物轨 checker 是唯一计分来源；PLAN §3.8 要求「先修尺子再加题，人工必须过 D1 和 D3」；TESTS BQ-11 规定「缺则该题不入池」。【与①附加条件(1)的调和】①(1)禁止的「代理自造金标」，指开发方或被测链路自产自判，以及任何冒称人工的标注。受托签署模型在 owner 常设授权链内出具标注，对 checker 输出盲态，且独立于开发方，因此不属该禁项。但这种标注不是人工标注，PLAN §3.8 与①(1)的人工要求在字面上仍未满足，所以 D3 证据等级降格，记为「受托模型金标（非人工）」：pool-state 的 d3_record 须带 annotator_kind="delegated-signing-model"；round-report 与一切引用都要如实写明，不得写成人工金标或人工 D3 已过（由 C-10 机判）。人工标注可得后，须另开卡重做对拍；分歧以人工为准，并按 A-09 留痕。流程分四步。(a) 开发方为 mm-01/mm-02/hot-01/hot-02/hot-03 每题准备 ≥10 份候选产物，来源须混合：oracle 输出、ws4_gen CORRUPTIONS 损坏库、开发方手工构造的边界变体（双向都要有：应过和应不过）、B 层冒烟臂的真实产物。每份产物带 source 字段，不附任何判定。(b) 签署代理人只读 brief.md、fixtures 和产物本身，逐份出具 expected_pass；全程不看 checker 输出。(c) 开发方把标注写入 bench/devpool-r1/goldens/\<task\>/\<sample\>/verdict.json，字段为 {expected_pass, annotator:"owner 委托 alpha 代行", annotator_kind:"delegated-signing-model", product_sha256, source}；product_sha256 = evalkit/harness/oracle_gate.py 的 hash_tree(\<sample\>/product)["tree_sha256"]，与 A-08 同算法。annotator_kind 必须如实写明这是受托模型标注，不得冒称人工。(d) 开发方跑 `python evalkit/harness/ws4_d3_gate.py --task <id> --real`。全部 exit 0 后，签署代理人再出具 d3_record.signoff，其被签对象sha256 = hash_tree(bench/devpool-r1/goldens/\<task\>)["tree_sha256"]，由主代理落盘。对拍出现分歧时，不得静默改标注或改阈值，必须按 A-09 留痕处理。
- P3【开发方】运行环境：python 必须能 import docx。本次实测宿主 system python3 报 `ModuleNotFoundError: No module named 'docx'`，需要建 venv 并安装 python-docx。另实测 /usr/bin/zcode 和 ~/.zcode/cli/db/db.sqlite 都在位；宿主能否真实调用模型本次未测，由 B 层实测判定。
- P4【planner/主代理】矩阵族构成已确认：INTENT.md §2.5 记 2026-10-04「WS4 跑批矩阵门解除：GLM-5.3 默认臂 + Minimax-M3.1-Flash-Preview 钉版臂；step 族不入首轮」，这满足 SF-0004 报告 §7 D1 行的硬条件。开工时在 round-report.json 记 base_commit，即开工时的 `git rev-parse HEAD`，本次实读为 cfad437aa2208bcc1d4fbad5faf1dc298ed6413e，以实际开工值为准。
- P5【主代理】模型调用预算上限：B 层 ≤4 个臂进程，C 层 ≤40 个臂进程；每臂仅限 rate_limited 退避重试 1 次（PLAN §5.6）。超出预算须先经 planner 批准；超额的臂进程不计入结果。
- P6【开发方，C 层开跑前】多题 × 单族聚合工具：现行 evalkit/evaluators/aggregate.py 是单 run_dir、单 pack 的 MVP（aggregate.py:96 将 delta_vs_none 写死为 None，且没有混族拒绝出口），不能满足 C-01/C-05。须在 C 层开跑前改造 aggregate.py 或新增聚合工具（下称 \<聚合工具\>，路径登记进 round-report.json 的 aggregator 字段），满足四项：按族各出一份 matrix，覆盖 5 题；按 PLAN §3.2 计算 delta_vs_none；delta_vs_prev 保持显式 null；输入含两族单元时非零退出，且不落盘任何 matrix 文件（AG-6）。改造按 A-04 装置协议执行：改前留档；re-freeze，且 keyfiles 覆盖 \<聚合工具\>；CHANGELOG 登记；verify_sf0003 不回退。红先证据为改造前对两族混合输入的退出码。未满足则 C 层 status==not_run（B-06 口径），不得用手工汇总代替。

**验收条款**

- A-01｜修复拆仓残留路径：ws4_judge.py 的 DIST_ROOT 按 SF_ROOT/仓根自动探测模式改为指向本仓 dist/（照 5972cf0 先例）；evalkit/ 下全部 Python 文件（含注释与字符串、含未跟踪文件、含本卡新增编排器）不得再出现 afp-clone 子串；evalkit/ 之外的仓内可执行文件只允许出现已登记的历史存量（原样不改写、不被本卡任何命令调用），出现任何新增即红；上列需改动的文件属钉版面者，改动走 A-04 协议｜判定：(1) 与门槛脚本 planning/test-cards-20261008/gate_sf0006a.py（commit 97467b8）同口径：遍历 evalkit/**/*.py（仅跳过 \_\_pycache\_\_，含未跟踪文件），按子串口径计，注释与字符串同计；`grep -rIl --include='*.py' --exclude-dir=__pycache__ 'afp-clone' evalkit` 须 exit 1（零命中）。(2) `git grep --untracked -l 'afp-clone' -- '*.py' '*.sh' '*.ps1' '*.js' '*.mjs' '*.ts' ':!evalkit'` 列出的文件集合须 ⊆ 已登记历史存量 {planning/reports/sf0004-probes/build_ledger.py、close_guards.py、gen_deliverables.py、snap_open.py（SF-0004 探针留档）；v5/assets/speaker-mapping/out/fix_student.py（历史产物）；planning/test-cards-20261008/gate_*.py（门槛脚本以该字面量做扫描）}。(3) `git diff --quiet <base_commit> -- planning/reports/sf0004-probes v5/assets/speaker-mapping/out` 须 exit 0（存量不改写）。(4) `grep -rIlE 'sf0004-probes|speaker-mapping/out' evalkit --include='*.py'` 须 exit 1（存量不被调用）。红先证据：签署落盘提交 c5b4ca0 中 evalkit 内 4 个文件命中，分别为 ws4_judge.py:37 的 `DIST_ROOT = os.path.join(WORKSPACE, "afp-clone", ...)`、run_all.py:23 的 `ASSET = os.path.join(WORKSPACE, "afp-clone", ...)`（原 5 文件清单漏扫）、verify_sf0003.py（注释与门标签）、packs/sm-mapping-01/checks/run_check.py:27（注释）；evalkit 外命中恰为上列存量（2026-10-08 alpha 复核实读）
- A-02｜8 题生成器红绿自检在真实仓布局下全绿（BQ-8/9/10 加 fixtures 漂移守卫）｜判定：在仓根执行 `for t in mm-01 mm-02 hot-01 hot-02 hot-03 ofc-01 ofc-02 ofc-03; do python evalkit/packs/ws4-dev/$t/gen_oracle.py --selftest; done`，8 次都 exit 0，且末行均为 `SELFTEST PASS`。红先证据：mm-01 exit 1（l1 bridge_error 找不到 afp-clone 路径）；链接后 8/8 exit 0
- A-03｜8 份 runner_contract.json 重生成，指向本仓真实路径｜判定：python 断言，对 8 包逐一检查：os.path.isdir(ref_root_verbatim) 为 True，os.path.isfile(runner_path) 为 True，selfcheck_exit==0，redpath_exit==1，且文件内容不含子串 `D:\\`。全部为真时 exit 0
- A-04｜装置钉版协议：改动前留档，改动后 re-freeze；CHANGELOG 登记 fixed 条目；SF-0003 门不回退；钉版面扩至 ws4-dev 8 题的 gen_oracle.py 与 runner_contract.json。纪要第二节所称「改由 freeze_device 钉版管辖」在签署时并不成立：keyfiles.sha256 只含 8 份 checks/run_check.py。钉版面在 B、C 层跑批期间不得漂移｜判定：`python evalkit/harness/freeze_device.py verify --evalkit evalkit` 须 exit 0；`grep -cE 'packs/ws4-dev/[^/]+/gen_oracle\.py' evalkit/harness/keyfiles.sha256` 须 ==8，`grep -cE 'packs/ws4-dev/[^/]+/runner_contract\.json' evalkit/harness/keyfiles.sha256` 须 ==8；`grep -c 'ws4_judge.py' evalkit/CHANGELOG.md` 须比 base_commit 版本（`git show <base_commit>:evalkit/CHANGELOG.md`）增加 ≥1；`python evalkit/harness/verify_sf0003.py` 须 exit 0，且输出含「全绿（N 门」、N≥34（钉版面扩容引起的声明面同步按 ce7b1b2 先例执行，并在 CHANGELOG 登记；门数只许增不许减）；B 层与 C 层收工时各再执行一次 freeze verify，须 exit 0。基线：freeze verify exit 0（28 文件全对），verify_sf0003 exit 0（34 门全绿）；红先证据：两条 keyfiles grep 现状均为 0（2026-10-08 alpha 实跑）
- A-05｜签署与就绪保全：重跑 ws4_pool_state.py 不得把已落盘的 d1/d3 signoff 冲成 null，也不得把已派生的 ready/counts.ready 冲回 false/0。签署时代码 ws4_pool_state.py:33 的 SIGNOFF_NULL 会无条件覆盖 signoff，ready=False 与 counts.ready=0 为字面量（工作树实读 :154、:170），均须修｜判定：先读取 pool-state 8 题的 d1_record.signoff、d3_record.signoff、ready 与 counts.ready；执行 `python evalkit/harness/ws4_pool_state.py`，须 exit 0；再读取一次；python 断言：8 题 d1、d3 signoff 前后逐字段相等，d1 签署人非 null；8 题 ready 与 counts.ready 前后相等。本断言执行两次：A 层执行一次（此时 d3 未签、ready 全为 false）；A-10 落盘 d3 signoff 并完成 ready 派生之后再执行一次。两次均须成立
- A-06｜D1 签署对象与现物一致：题面没有在签署后被改｜判定：python 断言，唯一对拍基准为签署落盘提交快照 `git show c5b4ca0:bench/devpool-r1/pool-state.json` 的 pack_files_sha256（与 cfad437 逐键相等），不得读取工作树 pool-state.json（ws4_pool_state.py:137–148 重跑时按现盘重算，对拍工作树即自证）。对 8 题逐一检查：(1) 现盘 brief.md 原字节 sha256 == 工作树 d1_record.signoff.被签对象sha256 == 快照 pack_files_sha256["brief.md"]；(2) rubric.md、task.json 与快照中全部 fixtures/ 键，现盘原字节 sha256 逐一等于快照值；(3) 现盘 fixtures/ 下递归文件集合 == 快照中 fixtures/ 键集合（不得增删）。共 32 个题面文件。gen_oracle.py、checks/run_check.py、runner_contract.json 属装置面，不在本条，归 A-04。实算（2026-10-08 alpha 复核）：32 个文件与 c5b4ca0 快照全部一致，fixtures 集合无增删
- A-07｜D3 金标对拍：mm/hot 5 题全部达标，ofc 3 题维持 WAITING_WS3｜判定：5 题分别执行 `python evalkit/harness/ws4_d3_gate.py --task <id> --real`，均须 exit 0，且输出 JSON 中 d3_gate.mismatches==[]、accuracy≥0.95；ofc-01/02/03 同一命令须 exit 3。基线：mm-01、hot-01、ofc-01 均 exit 3（金标未注入，fail-closed 拦住）
- A-08｜金标样本构成足以否证 checker，不是自环复读｜判定：python 断言。哈希算法统一用 evalkit/harness/oracle_gate.py:52 的 hash_tree(\<目录\>)["tree_sha256"]：相对路径排序；文本扩展名按 CRLF→LF 归一后、二进制按原字节逐文件求 sha256；按「路径\0文件哈希\0」顺序累入（oracle_gate.py:31–65）。复核方 import 同一函数复算，不得另写。每题须满足：样本数 ≥10；expected_pass=true 和 false 的各 ≥4；annotator=="owner 委托 alpha 代行" 且 annotator_kind=="delegated-signing-model"；product_sha256 == hash_tree(\<样本\>/product)["tree_sha256"]，且该树 file_count ≥1；expected_pass=true 的样本中，产物树哈希 ≠ 同种子 oracle 输出树哈希的 ≥2 份（oracle 输出由 `gen_oracle.py --out <scratch>` 生成后用 hash_tree 计算）；expected_pass=false 的样本中，source 不以 `corruption:` 开头的 ≥2 份
- A-09｜标注先于对拍，且标注不可静默翻改｜判定：`git merge-base --is-ancestor <首次引入 goldens verdict.json 的提交> <首次写入 d3 real 结果的提交>` 须 exit 0。对每个 verdict.json 执行 `git log --format=%H -- <path> | wc -l`，结果须 ==1；若 >1，该样本路径必须出现在 bench/devpool-r1/goldens/RELABEL.md 中，并带旧值、新值、理由
- A-10｜READY 翻绿口径与机制：ready 只能由 ws4_pool_state.py 从盘上记录派生，派生条件为 D1 已签 ∧ D3 真实对拍达标 ∧ D3 已签；禁止手改 pool-state.json；mm/hot ready 数 ≥5。责任：开发方实现派生逻辑（装置改动走 A-04 协议）；签署代理人出具 d3_record.signoff，主代理落盘；翻绿由落盘后重跑 ws4_pool_state.py 产生；d3_record 须带 annotator_kind="delegated-signing-model"｜判定：d3 signoff 落盘后，先执行 `python evalkit/harness/ws4_pool_state.py`，须 exit 0；再 python 读取 pool-state.json 断言：每题 ready == (d1_record.signoff.签署人非 null ∧ 该题 A-07 命令 exit 0 ∧ d3_record.signoff 三字段非 null ∧ line∈{mm,hot})；counts.ready == ready 为 true 的题数，且 ≥5；ofc 三题 ready==false；mm/hot 各题 d3_record.annotator_kind=="delegated-signing-model"，d3_record.signoff.签署人=="owner 委托 alpha 代行"，被签对象sha256 == oracle_gate.hash_tree(bench/devpool-r1/goldens/\<task\>)["tree_sha256"]；随后紧接再执行一次 A-05 判定，须成立
- A-11｜负控与分类器阳性对照仍然成立｜判定：`python evalkit/nc/run_nc.py --out <scratch>` 须 exit 0 且输出含「成立（9/9）」；`python evalkit/evaluators/classify.py --selftest` 须 exit 0。基线均为 exit 0
- A-12｜建臂与隔离（零模型）：treatment 臂挂载 dist/build/standard/\<meeting-minutes|hot-templates\> 合规变体；baseline 臂只有输入；任何臂都不得带参照物｜判定：对每个题 × 重复：`python evalkit/harness/make_arms.py --pack <pack> --run-id <id> --asset-skill dist/build/standard/<name>` 须 exit 0；`python evalkit/harness/isolation_probe.py <baseline 臂>` 须 exit 0；`find <treatment 臂> -type d \( -name reference -o -name oracle \)` 输出须为空；`python evalkit/harness/pack_checks.py --pack <pack> --arms <b> --arms <t> --model-pin <pin>` 须 exit 0
- A-13｜nonce 矩阵（EI-8）：同一重复内两臂、两族的输入相同；跨重复的输入不同｜判定：python 断言，树哈希一律用 oracle_gate.hash_tree(\<目录\>)["tree_sha256"]（与 A-08 同算法），各树 file_count ≥1。rep1 各臂输入的 fixtures 树哈希 == 包内 evalkit/packs/ws4-dev/\<task\>/fixtures 树哈希（nonce A，canonical 种子）。rep2 的输入由 `gen_oracle.py --nonce-set B --out <scratch>` 生成，其 fixtures 树哈希须 ≠ rep1，且 rep2 各臂输入树哈希 == 该生成树哈希。同一 rep 内 4 个臂（2 族 × 2 臂）的输入树哈希两两相等
- A-14｜oracle 树放在所有臂目录之外，开跑前登记哈希基线｜判定：每题每 rep 执行 `python evalkit/harness/oracle_gate.py hash --root <oracle 根> --record <runs/<id>/oracle/<task>-<rep>.json>` 须 exit 0；oracle 根路径不得是任何臂目录的子路径（os.path.commonpath 断言）
- B-01｜冒烟层：mm-01 × {glm, minimax} × {baseline, treatment} × n=1，共 4 臂，钉版落点逐字核对（大小写敏感）｜判定：4 份 records/model_pin.json 都齐五键（model_id、provider_base_url、cli_runtime、date、reasoning_variant），且用 model_usage join 出的实际落点核对：glm 臂必须 ==「GLM-5.3」@「account:bigmodel-individual-coding-plan」，minimax 臂必须 ==「Minimax-M3.1-Flash-Preview」@「minimax」。GLM 臂一旦漂移，round-report.json 写 redline_event=true，B/C 层停跑（SF-0004 DT-v1 通用红线）
- B-02｜EI-0：每个臂都能和遥测 join 上｜判定：每臂 records/telemetry.json 含 session_id；db 中该 session 的 directory 等于臂目录绝对路径；model_usage 中该 session 至少 1 行。python 断言全部为真
- B-03｜M1 成对 env 契约，全局配置零改动｜判定：minimax 臂的启动记录中，ZCODE_BUILTIN_PROVIDER_CONFIG_FILE 与 ZCODE_PERSONAL_PROVIDER_CONFIG_FILE 两个变量同时存在（只记变量名，不记值）；跑完后派生副本路径 `test ! -e` 须为真；~/.zcode/cli/config.json 与 ~/.zcode/v2/provider_config.json 的 sha256 在本卡开工前和收工后逐字节相等，并记入 round-report.json
- B-04｜跑完后参照区未被触碰｜判定：`python evalkit/harness/oracle_gate.py verify --root <oracle 根> --record <A-14 记录>` 对所有已跑题 × rep 都须 exit 0
- B-05｜密钥零落盘｜判定：`grep -rEn 'ghp_|github_pat_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-' evalkit/runs/<run-id>` 须 exit 1（零命中）
- B-06｜模型层失败时如实留痕：A 层判定独立有效；B 层失败则 C 层不开跑｜判定：round-report.json 中 layers.A/B/C.status ∈ {passed, failed_infra, failed_device, not_run}。B 层非 passed 时须同时满足：每臂都有 classify 三桶归类和 reason；C 层 status==not_run；`ls evalkit/runs/<run-id>/C` 不存在或为空
- C-01｜基线层覆盖完整：5 题 × 2 族 × 2 臂 × 2 rep = 40 个单元｜判定：按族各一份 matrix（matrix-glm.json、matrix-minimax.json），python 断言：rows 恰为 5 题；每族 20 个单元；每个单元齐六键（process_pass、artifact_pass、quality_score、tokens、wall_ms、infra_error）；臂进程总数 ≤40 加上已登记的重试次数
- C-02｜产物轨可复算｜判定：对每个非 infra 单元，用落盘产物重跑 `python evalkit/packs/ws4-dev/<task>/checks/run_check.py <产物根> --input-basis <该 rep 输入>`，(exit==0) 须等于单元中的 artifact_pass；复算脚本全部一致时 exit 0
- C-03｜过程轨在位，且无 oracle 读取｜判定：每个单元 process_pass 非 null；`python evalkit/evaluators/process_track.py --arm-dir <臂> --oracle-root <oracle 根>` 的记录中禁止面（EI-14）命中数 ==0；有命中的单元必须在 matrix 中标红，不得删除
- C-04｜质量轨按实标注 unjudgeable，不出分｜判定：python 断言：每个单元都有 quality_score 键且值为 null（不是 0），并带 unjudgeable 标记（SF-0004 报告 §7：异族裁判不可满足）
- C-05｜delta 字段口径（PLAN §3.2，AG-4/6/7）｜判定：每份 matrix 中，delta_vs_none 等于由单元独立复算的值，误差 <1e-9；复算口径为每题 treatment 通过率 − baseline 通过率，再对题取均值，复算脚本不得 import \<聚合工具\>。delta_vs_prev 为 null（不是 0）；layer=="dev"；evalbench_version=="v6-mvp-0.3"，或已 bump 且 CHANGELOG 有对应条目；单份 matrix 内只有一个族。把两族数据喂给同一次 \<聚合工具\>（P6 中登记于 round-report.json 的 aggregator 字段）须非零退出，且不落盘任何 matrix 文件（AG-6 拒绝）
- C-06｜infra 披露与单族作废规则（PLAN §5.5，EI-19）｜判定：round-report.json 记录每族 infra_error 比例。比例 >20% 的族：citable=false，reason 写「装置不稳」。某一族整列崩溃时：该族标 unjudgeable，另一族照常出数；`grep -c '整轮无效' round-report.json` 须 ==0。infra 剔除的单元逐条列在 infra_errors 中（禁止静默剔除）
- C-07｜效率数据落盘（本卡只记录，不判门）｜判定：非 infra 单元的 tokens、wall_ms 均非 null，且 tokens 来自 model_usage join；round-report.json 中每族有 token_ratio 与 wall_ratio（treatment/baseline），数值可由单元复算
- C-08｜D4 难度带分拣落盘｜判定：5 题的 pool-state d4_record.band 非 null，取值 ∈ {rotation, iteration, attribution, out_of_band}，band_reason 写明各族的 treatment 通过率；分拣与 PLAN §3.2 阈值（>90%、60–90%、<60%）一致，用 python 复算校验
- C-09｜C 层跑完后 oracle 哈希不变｜判定：对全部 10 个题 × rep 执行 `oracle_gate.py verify`，均须 exit 0
- C-10｜结论措辞、台账纪律与证据等级：本轮只出基线信号，不出验收结论；本卡不写 REGISTRY.md，窗口内 REGISTRY 变更只许来自 SF-0009 的单文件独立提交；D3 金标按受托模型标注如实降格披露｜判定：round-report.json 中 verdict_type=="baseline-signal"；只有 A-07 全部 exit 0 且 C-06 两族 infra ≤20% 时，citable 才可为 true；`grep -cE 'accepted|验收结论' round-report.json` 须 ==0；round-report.json 含 d3_annotator_kind=="delegated-signing-model" 且含字符串「D3 金标为受托模型标注，非人工」；`grep -cE '人工金标(对拍)?(通过|达标)|人工 ?D3 ?(已|通过|达标)' round-report.json` 须 ==0。REGISTRY 窗口断言：对 `git log --format=%H <base_commit>..HEAD -- REGISTRY.md` 列出的每个提交 c，`git log -1 --format=%s c` 须含「SF-0009」且不含「SF-0006」；`git show --name-only --format= c` 的输出须恰为 REGISTRY.md 一行；`git diff <base_commit>..HEAD -- REGISTRY.md | grep '^+[^+]' | grep -cE 'SF-0006|devpool-r1|baseline-signal|基线信号'` 须 ==0。窗口内出现任何不满足上述条件的 REGISTRY 提交即判红，须经 planner 重裁，不得改写历史提交凑绿
- C-11｜落盘往返（EI-21）｜判定：python 遍历 evalkit/runs/\<run-id\>/**/*.json 与 pool-state.json：json.load 全部成功，严格按 UTF-8 解码，且 CR 字节数 ==0
- C-12｜分层提交与公开仓安全｜判定：A、B、C 每层各有 ≥1 个提交；提交前执行 `git diff --cached | grep -E 'ghp_|github_pat_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-'` 须 exit 1；`git diff --cached --name-only | xargs -r du -m | awk '$1>50'` 输出须为空

**不在范围**：ofc-01/02/03 的 D3 与跑分（归 WS3）；质量轨打分与跨族裁判（SF-0004：异族裁判当前不可满足，维持 unjudgeable）；三臂/A_old 对照与 delta_vs_prev 数值（首轮基线轮）；任何验收结论、准入判定与 REGISTRY.md 更新；step 族、kimi 通道、MiniMax-M3 入矩阵（INTENT §6-4 未决）；holdout 题跑分（\<HOLDOUT\> 不得触碰）；修改 dist/v5 原版 runner、判分阈值或 golden；K-5 发布及其欠账（见 SF-0007/SF-0008）；canonical reference/ 的迁移或删除（③已裁定留证据）。

【门槛脚本同步注记（alpha 复核，2026-10-08）】planning/test-cards-20261008/ 下的门槛脚本须随本次卡文修订同步，门槛口径不得宽于卡面；同步之前，相应条款的门槛 PASS 不作为过门依据。(1) gate_sf0006a.py A-06 现在读取的是 A-05 重跑 ws4_pool_state.py 之后的工作树 pool-state.json，而 ws4_pool_state.py:137–148 会按现盘重算 pack_files_sha256，所以对 rubric.md/task.json/fixtures 构成自证假绿。须改为对拍 `git show c5b4ca0:bench/devpool-r1/pool-state.json`，补 fixtures 文件集合无增删的断言，并只比对四类题面文件。(2) A-01 须补 evalkit 外白名单、存量不改写、存量不被调用三项断言。(3) A-04 须补 keyfiles 覆盖计数（gen_oracle.py 8 条、runner_contract.json 8 条），并把 `"34" in stdout` 收紧为「全绿（N 门」且 N≥34。(4) A-05 须补 d3 signoff 与 ready/counts.ready 的前后相等断言。(5) gate_sf0007.py 的 K5A-04 按修订后的第 1–5 条口径同步。【主代理执行记录】(1)–(5) 已于 2026-10-08 同步落盘（gate_sf0006a.py A-01b/A-04/A-05/A-06、gate_sf0007.py K5A-04）。

### SF-0007（拟，编号以 planner 登记为准）—— ② 衍生零模型执行项：dist/build 发布形态修补（悬空 reference/ 引用、披露口径、build-summary 引用），不发布

**开跑前置**

- 【签署代理人出具，主代理落盘】②的签署文件（不按现状批准，倾向以 dist/build/standard 合规变体为发布形态）已入库，路径记入本卡 base 记录
- 【开发方】记录 base_commit；环境中装有 python-docx 与 skills-ref（本次实测 ~/.local/bin/skills-ref 在位）
- 【开发方】只能通过 dist/build.py 的声明变换修改变体文档；canonical 源包零改动（dist-compliance-tickets.md 修复方式条款）

**验收条款**

- K5A-01｜9 个变体产物（3 包 × standard/claude-code/learner）的 *.md 中，每个 `reference/...` 路径引用都必须在该变体目录内真实存在｜判定：python 扫描 dist/build/\<变体\>/\<包\>/**/*.md，抽取 `reference/[\w./\-\一-\龥]*` 路径逐一 os.path.exists；悬空数 ==0 时 exit 0。红先证据：9/9 产物都有悬空引用（standard 下 hot 11 处、mm 6 处、office 4 处，例如 meeting-minutes SKILL.md:61 的 `eval/runner.py <被测out> reference/out`）
- K5A-02｜WS2 全部门不回退（AC/BP/HY，含 BP-6 变换面外 sha256 等于源、BP-7 双跑一致、HY-1/HY-2 卫生项）｜判定：`cd dist && python tests/run_checks.py` 须 exit 0，且输出含「PASS 28 / FAIL 0」。基线：28/28 exit 0
- K5A-03｜canonical 三包零改动｜判定：`git diff --stat <base_commit>..HEAD -- dist/meeting-minutes-skill dist/office-templates-skill dist/hot-templates-skill` 输出须为空
- K5A-04｜REGISTRY「对外必须随附的披露口径」第 1–5 条全部写进各变体 EVALUATION.md（②附加条件(c)）｜判定：9 份变体 EVALUATION.md 中，第 1 条：`grep -c 'synthetic-passed'`、`grep -c 'real-verified ✗'`、`grep -c '效率门'` 均 ≥1；第 5 条：`grep -c '\.mimosa'` ≥1。office 的 3 份另需第 2 条 `grep -c 'single_round_signal'` ≥1；mm 的 3 份另需第 3 条 `grep -c 'majority'` ≥1 且 `grep -cE '勘误|修正'` ≥1；hot 的 3 份另需第 4 条 `grep -c 'release-candidate'` ≥1 且 `grep -c '复检'` ≥1。另外 `find dist/build -name .mimosa` 输出须为空（第 5 条工序实况）。红先证据：standard 变体 EVALUATION.md 中 grep single_round/synthetic-passed/效率 零命中；9 份 `.mimosa` 零命中；hot 的 3 份「复检」「release-candidate」零命中（2026-10-08 alpha 复核实读）。基线：mm 的 3 份第 3 条已在位（standard/meeting-minutes/EVALUATION.md:44「判定字段勘误…majority」），本断言起防回退作用
- K5A-05｜变体中不得出现参照物或 oracle｜判定：`find dist/build -type d \( -name reference -o -name oracle \)` 输出须为空
- K5A-06｜build-summary.json 的引用必须闭合｜判定：二者之一：(a) `python -c "import json;d=json.load(open('dist/build/build-summary.json',encoding='utf-8'))"` exit 0，且内容覆盖 3 包 × 3 变体；(b) `grep -c 'build-summary.json' dist/dist-compliance-tickets.md` ==0。实读：该文件不存在，tickets 第 26 行仍引用它
- K5A-07｜未经新签署，不得出现发布批准文件｜判定：`test ! -e evidence/publish-approval.md` 须 exit 0

**不在范围**：任何发布、上架、推送到分发渠道的动作（渠道与时机归 owner）；效率门、盲评加厚、benchmark.json（见 SF-0008）；canonical 源包 reference/ 的处置（③已裁定留证据）；修改任何 eval/runner.py 或 golden.json。

### SF-0008（拟，编号以 planner 登记为准）—— ② 衍生模型执行项：K-5 三包五门欠账补齐（效率门实测、benchmark.json 落盘、office 二轮、hot 复检轮），完成后重新提交签署

**开跑前置**

- 【签署代理人出具勘误，主代理落盘到②签署文件】②理由中「三包盲评每臂 2 次低于 §3.3 要求的 ≥3」经核对 v2/standard/EVAL-SPEC-v0.2.md 附录 A 不成立（v0.2 已改「标准 n=2，禁止 n=1；边界带/复检轮 n=3」）。②的决定仍然有效，依据是 v0.2 同样要求、而至今未满足的两项：效率门（§8.1 acceptance.gates.efficiency）和 benchmark.json 落盘（全仓 find 零命中）。（该勘误已并入本纪要第一节②附加条件首段）
- 【开发方】SF-0006 的 A 层和 B 层 status==passed：管道、遥测 join 和 M1 钉版都已实证；否则本卡不开跑
- 【planner】裁判配置须满足 O-7 建议默认值：裁判族与被测族无交集、≥2 族互裁、位置轮换。按 SF-0004 报告 §8，本机当前可观测落点只有 GLM 与 minimax 两族。若被测族为 GLM，可用裁判只剩 minimax 一族，≥2 族互裁可能无法满足；满足不了时，盲评门按 fail-closed 记为不可判，不得放宽口径
- 【planner】批准模型调用预算：三包 × 任务数 × 2 臂 × n（mm/office 为 2，hot 复检为 3）× 轮数，加上裁判调用
- 【开发方】ab 任务源保持冻结：mm 用 v2/evalbench-v02/meeting-minutes 的 8 任务集（dist golden.json 只有 3 个 ab_tasks，本次实读）；office 与 hot 各用自身 golden.json 的 5 个 ab_tasks

**验收条款**

- K5B-01｜三包各自落盘 dist/\<pkg\>/eval/results/benchmark.json，结构符合 EVAL-SPEC v0.2 §8.1｜判定：python 对 3 个文件做 json.load，并断言顶层九键齐全：asset、evalbench、model_pin、tasks、judge_consistency、infra_errors、aggregate、acceptance、disclosure；model_pin 中 judge_model_id 与 judge_prompt_version 非空
- K5B-02｜任务数与重复数达标｜判定：python 断言：每包 len(tasks)≥5；每个任务每臂 len(runs) 对 mm/office ≥2、对 hot ≥3（复检轮 n=3，EVAL-SPEC 附录 A）
- K5B-03｜效率门实测：token 比率 ≤2.0 且耗时比率 ≤2.0｜判定：由 tasks[].arms.*.runs 复算：均值 tokens(treatment)/均值 tokens(baseline) ≤2.0，均值 duration_s 的比率同样 ≤2.0；复算得到的布尔值须 == acceptance.gates.efficiency；每个 run 的 tokens 都能回溯到 model_usage session join，记录中带 session_id
- K5B-04｜裁判跨族、盲态；无合格裁判时不放行｜判定：python 断言 model_pin.judge_model_id 中不含被测模型族标识（例如被测为 GLM-5.3 时不含 'GLM'）；凡判定为不可判的任务，task_verdict=="unjudgeable" 且 acceptance.gates.blind_v02==false，不得为 true
- K5B-05｜聚合可审计（BG-1、AG-1）｜判定：独立脚本从 tasks 复算 delta、task_win_rate、reverse_tasks，结果须等于 aggregate 与 blind_detail；把两臂标签互换后重算，须满足 winRate→1−winRate、delta 变号、reverse_tasks 不变；断言全部为真时 exit 0
  - 【勘误注记（SF-0010，2026-10-08，依据 K-5 alpha 裁决 `planning/test-cards-20261008/K5-ruling-20261008.md` 附带发现；原文不动，仅追加）】swap 后 (T′,B′)=(原B,原T) 须对原始 per-run 分数独立调用 §3.3-2/3（EVAL-SPEC v0.2.1 tie-aware 口径）重算 delta′/winRate′/reverse_tasks′，**禁止 verdict 标签互换式伪复算**：win/loss 翻标签在含平局/部分平局的轮次产出假 winRate 与假 reverse_tasks（本案实证：s8_aggregate.py 旧 swap 块产出 swap_reverse_tasks=6/3/4；从原始 run 独立重算的真实反向=0/0/0）。其中 reverse_tasks 是资产方向不变量（本条款「reverse_tasks 不变」之锚点）：反向计数按 §3.6 完整口径（tie-aware 任务级判定＋平局任务不进反向计数），镜像均分反向（平局任务均分不对称＋win 镜像必落败）属伪象，只可作附加披露，不得计入 reverse_tasks。断言脚本与留档：`evalkit/runs/sf0008-k5b/s8_swap_recheck.py` → `evalkit/runs/sf0008-k5b/records/s8-swap-recheck.json`（exit 0）。
- K5B-06｜裁判一致性抽检落盘（EVAL-SPEC §3.4）｜判定：python 断言 judge_consistency 每个任务 ≥1 条；分差（delta）>2 的条目，其 action ∈ {re-judged, unjudgeable}
- K5B-07｜office 二轮信号如实标注｜判定：office 的 disclosure.rounds≥2；只有两轮都 accepted 且 Δ 同号时，single_round_signal 才可为 false，否则必须为 true（python 断言）
- K5B-08｜verdict 与门一致，不夸大证据等级｜判定：acceptance.verdict=="accepted" 当且仅当 deterministic、blind_v02、efficiency、format、assertion 五门全为 true；evidence_level ∈ {synthetic-passed, provisional}（本卡不做真实复验，不得写 real-verified）
- K5B-09｜确定性门复跑不回退，golden 冻结｜判定：三包各执行 `python eval/runner.py reference/out reference/out` 须 exit 0，空目录红路 `python eval/runner.py <空目录> reference/out` 须 exit 1（基线：三包绿 0、红 1）；eval/golden.json 的 sha256 须等于 REGISTRY.md:71/75/79 的登记值（实算一致：b3be400a…、2fa58b07…、19e4b6e1…）
- K5B-10｜重新提交签署，不自批｜判定：`git diff <base_commit>..HEAD -- evidence/publish-approval-REQUEST.md` 只有新增行，且新增内容包含 3 个 benchmark.json 的 sha256；`test ! -e evidence/publish-approval.md` 须 exit 0

**不在范围**：发布动作、渠道、收费（owner 保留）；真实数据复验（L3，切真实人类的决策权在 owner）；修改 ab 任务集、rubric、runner 或阈值；devpool 基线轮（SF-0006）；引入旗舰模型充当被测臂（INTENT §4-5）。

### SF-0009（拟，编号以 planner 登记为准）—— ③④ 裁定回写：REGISTRY 追加 reference/ 留证据登记与 5 件工具/MCP/agent 的体检形态豁免注记（零模型、只追加）

**开跑前置**

- 【签署代理人出具，主代理落盘】③（留证据）和④（形态豁免，v5 五件一并裁定）的签署文件已入库（即本文件），路径记入本卡 base 记录
- 【开发方】记录 base_commit。③的锚定值（本次实读）：reference/ 的 git tree id 为 mm `0c4c1c91dc1e1ce0a5f15af39896f49d3db317d7`、office `99ead1a5887201f8faec07aee6918fc3752e89e2`、hot `7debb3aabdaa0d891fa309159e76880c772f369f`（HEAD cfad437），三包 reference/ 共 60 个受控文件
- 【开发方】REGISTRY.md 的追加单独成提交：该提交只改 REGISTRY.md 一个文件，subject 含「SF-0009」且不含「SF-0006」；新增行不得含 SF-0006、devpool-r1、baseline-signal、基线信号字样。理由：SF-0006 窗口与本卡并行，SF-0006/C-10 以此区分 REGISTRY 变更的归属，替代原「REGISTRY diff 为空」断言；本卡违反即同时打红 SF-0006/C-10

**验收条款**

- R-01｜REGISTRY.md 只追加，不改历史｜判定：`git diff <base_commit>..HEAD -- REGISTRY.md | grep -c '^-[^-]'` 须 ==0，新增行数须 ≥1；对 `git log --format=%H <base_commit>..HEAD -- REGISTRY.md` 的每个提交 c：`git show --name-only --format= c` 须恰为 REGISTRY.md 一行，subject 须含「SF-0009」且不含「SF-0006」（与 SF-0006/C-10 窗口断言互锁）
- R-02｜③登记内容在位：reference/ 是 oracle 性质参照物，canonical 顶层原始包禁止直接对外分发，只能经 build.py 变体出包｜判定：在 REGISTRY 新增行中 `grep -c 'reference/'` ≥1、`grep -c '禁止直接对外分发'` ≥1，并包含本签署文件路径字符串
- R-03｜③留证据即原样不动｜判定：`git rev-parse HEAD:dist/meeting-minutes-skill/reference`、`git rev-parse HEAD:dist/office-templates-skill/reference`、`git rev-parse HEAD:dist/hot-templates-skill/reference` 依次等于前置中的三个 tree id；`git status --porcelain -- dist/*/reference` 输出须为空
- R-04｜④豁免注记覆盖五件，并如实更正形态描述｜判定：REGISTRY 新增行中，zctl-mcp、acceptor-agent、hotwords、deploy-pack、speaker-mapping 五个名称各出现 ≥1 次；`grep -c '形态豁免'` ≥1；zctl-mcp 与 acceptor-agent 所在新增行含「未体检」，且不含「C 级」或「C（」
- R-05｜豁免不升级状态：五件不进 dist，新增行不宣称可分发｜判定：`ls dist` 的目录集合与 base 相同；新增行中同时含五件名称之一和「可分发」的行数 ==0；`git diff --stat <base_commit>..HEAD -- v3/tools/healthcheck` 输出须为空（体检器不改）
- R-06｜豁免对象的确定性门仍然成立｜判定：在 v5/assets/zctl-mcp 与 v5/assets/acceptor-agent 的临时副本中：`python eval/runner.py` 须 exit 0；`python eval/runner.py <空目录> oracle` 须 exit 1；`python eval/runner.py x` 须 exit 2。基线：两者均为 0/1/2

**不在范围**：WS9 分形态体检器建设（豁免是过渡登记，WS9 建成后须复检，另行开卡）；reference/ 迁正（留待源包升版时再裁定）；zctl-mcp/acceptor-agent 的盲评加厚与真机端到端欠账；改动 REGISTRY 任何既有行。

---

## 四、执行状态与下一步

| 卡 | 状态 | 说明 |
|---|---|---|
| SF-0006 | **A 层进行中（按修订卡施工）** | A-01..A-06、A-11..A-14 零模型条款先行（A-04 新增钉版面扩容、A-05 新增 ready 保全）；A-07..A-10 等 P2 金标注入（受托模型标注，证据降格为「受托模型金标（非人工）」） |
| SF-0007 | 可开工（零模型） | 只经 build.py 声明变换修变体文档；canonical 零改动；披露口径按 K5A-04 修订覆盖第 1–5 条 |
| SF-0008 | 等 SF-0006 A+B 层 passed | 需真实模型调用；裁判配置若不满足 O-7 按 fail-closed 记不可判；窗口内不得写 REGISTRY（C-10 归属断言） |
| SF-0009 | 可开工（零模型） | REGISTRY 只追加注记；追加须单独成提交（subject 含 SF-0009，与 C-10 互锁） |
| K-5 发布 | **未批准** | 补齐 SF-0007/SF-0008 后重新提交签署；publish-approval.md 不得先行存在 |
