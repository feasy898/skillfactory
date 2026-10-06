# evalkit CHANGELOG（bench 自身迭代留档 · PLAN §3.8 三分类）

> 格式：removed（附饱和证据）/ fixed（附缺陷类型 + 复现命令）/ added。
> 跨版本 Δ 禁止并列（EVAL-SPEC §4.4-2；装置侧由 aggregate.py AG-7 拒绝门执行）。

## v6-mvp-0.3 · 2026-10-04（SF-0005 · worker-glm-bd）

### added

**ADD-1｜版本 bump：WS4 dev 题池落池触发（SYNTHESIS 20261004-sf0005ws4 R-C5/R-C8）**
- 题号：SF-0005（卡面修订第 1 条，planner-glm 2026-10-04 07:2x 依据 ensemble 裁决 R-C5）
- 变更：`evaluators/aggregate.py` `--evalbench-version` 默认 `v6-mvp-0.2` → `v6-mvp-0.3`；
  新增 dev 题池 `packs/ws4-dev/`（8 题：mm-01/02、hot-01/02/03、ofc-01/02/03，nonce 化
  +三层用例 4正/2近负/2对抗，3 题 origin=public-variant）+ 判分器件
  `harness/ws4_gen.py / ws4_judge.py / ws4_d3_gate.py / ws4_pool_state.py`
  （L2 主判=task_outcome_* 全 8×≤8 条；L1 子轨=dist 原版 runner 桥接只登记不判分）
  + `bench/devpool-r1/pool-state.json`（D1-D4 SOP 痕迹，signoff 全 WAITING_OWNER）
- 类型：added（新增题池触发版本 bump；非修尺子——既有判分器零语义变更）
- 判定人：planner-glm（卡面修订授权仅 aggregate.py+本文件两处既有文件改动，R-C8）
- 复现命令：`python -c "import argparse" && grep -n 'v6-mvp-0.3' evaluators/aggregate.py`；
  跨版本拒绝门回归：`python evaluators/aggregate.py --run-dir runs/r1-probe --pack packs/sm-mapping-01
  --out "$TEMP/ag7-redtest-matrix-v03.json" --delta-from runs/r1-probe/matrix.json` → exit 1
  （v6-mvp-0.1 旧 matrix 对 0.3 拒绝并列）
- 已知残留（登记待 planner 裁）：`harness/run_all.py:51` 透传参数 default 仍钉 v6-mvp-0.2
  （SF-0006 开工门 GP-4 前需一行同步或由卡 B 编排器显式传参）；README.md:78 为历史叙述不改。
  （→ 已收口：2026-10-06 INTENT §6 遗留小项①升格执行，见本节 FIX-C2。）

### removed

- 无（本版无退役题；WS4 题池为新增，饱和退役机制待基线轮后启用）。

### added（遗留小项③④升格执行 · 2026-10-06）

**ADD-2｜M1 成对 env 契约文档化入装置 + B 支宿主复测留档（INTENT §6 遗留小项④③）**
- 题号：SF-0004 报告 §11.3「配置文档化另开卡」+ §11.1「B 支宿主复测门 3」（planner 2026-10-06 升格）
- 变更：`README.md` 新增「模型钉版 M1：env 覆盖成对契约」节（成对变量、单给即抛错的
  `resolveNodeProviderRuntimePaths` 硬前置、personal 副本两处差异、A 支实测落点与复原、
  `defaultModelSelection=null` 结构性原因双宿主实测、覆盖面=仅 minimax 族/headless 单通道、
  B0c 复测结论）；新探针 `planning/reports/sf0004-probes/b0c_retest_host.py` +
  证据 `p-b0-catalog-host-retest.json`、`p-b0c-listmodels-host-evidence.json`
  （原 b0c_catalog.py / p-b0-catalog.json 留档不改）
- 类型：added（文档+复测探针，零判分器改动）
- 判定人：planner 升格（INTENT §6.6 → 2026-10-06 执行）
- 复现命令：`python planning/reports/sf0004-probes/b0c_retest_host.py` → exit 0，
  available=false / untested_catalog_unavailable（本机第二台宿主：zcode workflow 宿主会话
  ListModels 实调 model_catalog_unavailable，B1 维持 not_run，0 模型调用）

### fixed（卡面+装置一行同步 · 升卡收口 2026-10-06 · 非装置版本变更，版本号保持 0.3）

**FIX-C1｜验收卡版本锚随装置 bump 漂红（B5/F4 恒红的卡侧根因）**
- 题号：SF-0003 遗留红收口（verify_sf0003 31/34 时代红 B5/F4/D2；升卡授权=装置协议
  freeze/DECLARED 声明面，改前留档见 runs/sf0003/verify-upgrade-pre.json）
- 旧文本：`harness/verify_sf0003.py` B5/F4 断言锚 `v6-mvp-0.2` 字面；B5 pos 侧 prev 基准
  用 0.2 时代静态文件 `runs/sf0003/ag7-prev-same.json`（evalbench_version=v6-mvp-0.2）
- 新文本：卡面锚改 `CUR_VERSION`（v6-mvp-0.3，与 `evaluators/aggregate.py:70` 装置声明面
  同步）；B5 prev 基准改由 verify 运行时按卡面锚自生成（静态文件随跑刷新并注记升卡）；
  D2 卡时点门诚实降级 historical（点态已由 5654f83 commit 落盘，改以 ac18867 基线↔HEAD
  git 史断言：开工前行 sha==d0 证据 c861cf0d…、package/ 子树 numstat 恰 1 1）
- 缺陷类型：卡面锚定缺陷（验收卡时态≠装置时态）——非判分器语义变更，装置钉版 re-freeze
  仅 verify_sf0003.py 一行指纹更新（F5 变更集仍恰等 DECLARED 声明清单）
- 判定人：planner 升卡协议（2026-10-06，B5/F4 装置版本演进 0.2→0.3 卡未随）
- 复现命令：`python harness/verify_sf0003.py`（升卡前红 B5/D2/F4=31/34，升卡后 34 门全绿；
  基线留档 runs/sf0003/verify-upgrade-pre.json，终态 runs/sf0003/verify-post-split6.json）

**FIX-C2｜run_all.py 版本透传钉旧值（ADD-1 已知残留收口，INTENT §6 遗留小项①）**
- 题号：INTENT §6.6 遗留工程小项①（验收发现升格，planner 2026-10-06）；承接本节 ADD-1 已知残留行
- 旧文本：`harness/run_all.py:51` `ap.add_argument("--evalbench-version", default="v6-mvp-0.2", …)`
- 新文本：default 改 `"v6-mvp-0.3"`（help 注明声明面=aggregate.py default、本行 2026-10-06 一行同步）；
  一键复跑 `run_all.py` 不再透传旧版号给 aggregate.py
- 缺陷类型：口径残留缺陷（编排器透传面与装置声明面漂移；非判分器语义变更——
  run_all.py 侧无判分逻辑，且显式传参路径本就可用）
- 判定人：planner 升格（INTENT §6.6 → 2026-10-06 执行）
- 复现命令：`python harness/run_all.py --help`（usage 含 `--evalbench-version`）+
  `grep -n 'v6-mvp-0.3' harness/run_all.py` 恰 1 处 default；改前留档
  runs/sf0003/verify-pre-x4.json（34 门全绿）+ keyfiles-pre-x4.sha256

**FIX-C3｜freeze glob 单层不覆盖嵌套 wrapper（INTENT §6 遗留小项②）**
- 题号：INTENT §6.6 遗留工程小项②（验收发现升格，planner 2026-10-06）
- 旧文本：`harness/freeze_device.py` `KEY_GLOBS=["packs/*/checks/run_check.py", …]` +
  `glob.glob(...)` 单层——`packs/ws4-dev/<题>/checks/run_check.py` 两层深的 8 个嵌套
  wrapper 判分面全部漏冻（改它们不触发装置 verify 红）
- 新文本：KEY_GLOBS 改 `**` 递归形态 + `glob.glob(..., recursive=True)`；钉版面 20→28 文件
  （+8 = packs/ws4-dev 8 题嵌套 wrapper；收集面差分实测恰好 +8、零丢失）；verify_sf0003.py
  DECLARED 声明面同步（DECLARED_CHANGED +freeze_device、DECLARED_NEW +8，F5 恰等语义不变）
- 缺陷类型：装置钉版覆盖缺陷（EI-23 冻结面漏嵌套层；修冻结面本身，不改任何判分阈值）
- 判定人：planner 升格（INTENT §6.6 → 2026-10-06 执行；升格授权=装置协议 freeze/DECLARED 声明面）
- 复现命令：`python harness/freeze_device.py freeze && python harness/freeze_device.py verify`
  （28 个关键文件全对）；改前钉版面留档 runs/sf0003/keyfiles-pre-x4.sha256（20 条），
  升格前基线 runs/sf0003/verify-pre-x4.json（34 门全绿）

---

## v6-mvp-0.2 · 2026-10-03（SF-0003 · worker-glm-m4）

### fixed（3 条）

**FIX-1｜口径（O-6 条款执行：版本 bump + 旧基线作废）**
- 题号：O-6（PLAN §8；EVAL-SPEC §4.1 钉版与 headless 实测不符）
- 旧文本：`ap.add_argument("--evalbench-version", default="v6-mvp-0.1")`（evaluators/aggregate.py）；
  harness/run_all.py 无该参数透传——一键复跑永远落旧版号
- 新文本：`ap.add_argument("--evalbench-version", default="v6-mvp-0.2")`；
  run_all.py 增加 `--evalbench-version` 透传至 aggregate.py；全树旧版号清零
  （`grep -rn 'v6-mvp-0.1' evaluators harness packs nc README.md` = 0 行，本文件历史节除外）
- 缺陷类型：口径缺陷（装置）——模型落点 GLM-5.3 ≠ 文档声称 GLM-5.3-Flash，
  触发 O-6 后半句「bump evalbench 版本、旧基线作废」；r1-probe 全部数字标 citable:false
  （见 runs/r1-probe/INVALIDATED.md）；baseline/ 为空 → 作废走分支 B
  （runs/sf0003-baseline-void.json，voided_count=0）
- 判定人：planner-glm（2026-10-03，SF-0001 验收拍板）；实测证据 SF-0001 报告 §4.1
- 复现命令：`python -c "import json;print(json.load(open('runs/r1-probe/matrix.json',encoding='utf-8'))['evalbench_version'])"` → v6-mvp-0.1；
  `python evaluators/aggregate.py --run-dir runs/r1-probe --pack packs/sm-mapping-01 --delta-from runs/r1-probe/matrix.json`
  → AG-7 跨版本拒绝 exit 1（本卡 B5 双向实测）

**FIX-2｜装置（任务包黄金输入目录名与参照基线生成形态不一致 → 检查 4 双臂恒红）**
- 题号：SF-0001 §4.2 缺陷②（修法 A，planner 拍板采纳）
- 旧文本：`packs/sm-mapping-01/inputs/`（黄金输入目录名）；brief 旧运行条款
  「所有 24 个文件必须在 `out/` 目录作为 cwd、以相对路径写出」——臂树与参照基线
  （oracle/ 下以 `--transcript fixtures/…` 生成）不同形态，两处路径回显恒差
- 新文本：目录改名 `inputs/` → `fixtures/`（6 文件 sha256 保内容不变）；
  brief 改为「以臂根为 cwd、`--transcript "fixtures/…"`、`--out "out/…"`」；
  装置 4 处适配（make_arms.py / pack_checks.py×3 / process_track.py / README 目录表）；
  EI-20 conformance 改 inputs/fixtures 双名兼容；偏离留痕 packs/sm-mapping-01/PACK-DEVIATIONS.md
- 缺陷类型：装置缺陷（题面/尺子，非模型非资产）——PLAN §3.6 头号判例同构；
  9 个映射产物实际 9/9 逐字节相同，红的是尺子
- 判定人：planner-glm（2026-10-03 拍板修法 A）；根因链 SF-0001 报告 §4.2
- 复现命令：0 模型 replay（本卡 E 组）：
  `python evaluators/artifact_track.py --pack packs/sm-mapping-01 --product-root runs/sf0003-replay/out --reference <ASSET>/oracle/out`
  → 4/4 PASS，检查 4 reference_agreement_100pct 首次转绿（E1）；负控 E3/E4 证明门未放水

**FIX-3｜资产（SKILL.md INFO 行文档与工具实际输出不一致，D5 类）**
- 题号：SF-0001 §4.3 缺陷③
- 旧文本：``| `INFO: 写出 …（共 N 行，替换 X 处，未映射 Y 种）` | 汇总信息 | — |``
  （v5/assets/speaker-mapping/package/SKILL.md:54）
- 新文本：``| `INFO: 写出 out/<file>（共 N 行，替换标签 X 处，未映射标签 Y 种）` | 汇总信息 | — |``
  （补「标签」二字 ×2 + 体现 `--out` 路径回显；与工具实测 stderr 逐段同构）
- 缺陷类型：资产文档缺陷（D5 类）——文档错一字，brief 与 SKILL.md 两条独立路径同时带偏
- 判定人：planner-glm（2026-10-03 开卡裁定）；实测对照 SF-0001 报告 §4.3 + 本卡 D4
  （harness/doc_consistency.py 实跑工具取 stderr 与文档模板占位符归一比对，含变异自检）
- 复现命令：`python harness/doc_consistency.py --asset <ASSET>/package` → exit 0；
  删「标签」二字重跑 → exit 1（阳性对照，MT-2）

### added

- AG-7 跨版本拒绝门最小实现（aggregate.py `--delta-from`）：混版本输入 exit≠0 报「版本」
  不出数，同版本接受且 delta_vs_prev 显式 null（否定式测试双向，B5）。
- harness/doc_consistency.py 常设门：实跑资产工具取 stderr INFO 行 ↔ SKILL.md 文档模板
  占位符归一比对（D4，含变异自检）。
- harness/verify_sf0003.py：SF-0003 验收汇总器（A1–F6 逐条机跑，exit 0 当且仅当全绿；
  逐条命令仍是唯一真值源，G4）。
- packs/sm-mapping-01/PACK-DEVIATIONS.md：本包对 PLAN §3.3 通用格式（inputs/ 字面）的
  显式偏离留痕 + 建议回写条款文本（供 planner 决定）。

### removed

- 无（本版无退役题；bench 题池饱和退役机制属 WS4+，见 PLAN §3.7/§3.8）。

---

## v6-mvp-0.1 · 2026-10-03（SF-0001 · worker-minimax-r7）

- 初版（历史版本号，仅作留档）：eval harness MVP 落盘；该轮产出物性质=「管线验证信号」。
  **O-6 裁定后本版本全部数字 citable:false（见 runs/r1-probe/INVALIDATED.md）。**
