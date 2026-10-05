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

### removed

- 无（本版无退役题；WS4 题池为新增，饱和退役机制待基线轮后启用）。

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
