# SF-0003 · evalkit 修复包交付报告（O-6 落地 + 修法 A + SKILL.md INFO 行）

> 任务：SF-0003（`projects/skillfactory/tasks/review/SF-0003-evalkit-fixpack.by-worker-glm-m4.md`）
> 执行：worker-glm-m4（glm 族），2026-10-03 21:30–23:59
> 验收文件：`D:\workspace\local-plane\projects\skillfactory\tests\visible\SF-0003-accept.md`
> 汇总器：`python harness/verify_sf0003.py` → **34/34 门全绿，exit 0**
> （逐门四字段 `{id, command, exit_code, ts, evidence_sha256}` 全量落盘：`evalkit/runs/sf0003/verify-sf0003.json`；
> 逐条命令仍是唯一真值源，本报告与汇总器都是它的索引）
> 硬约束遵守：0 模型（未跑任何臂）；runner.py 零改动；oracle 全树前后哈希一致；不 commit 不 push；
> 封存区零触碰；holdout 零读；密钥零落盘。

---

## 一、做了什么（按执行序）

### S0 前置自检（A 组）
`freeze_device.py verify` 绿（S0 时点 14 文件旧指纹全对）→ `oracle_gate.py hash` 存档
`runs/sf0003/oracle-before.json`（tree_sha256=`e3086e10…ceeacc`，31 文件，与常量一致）→
runner.py `git diff --exit-code` 空 → git porcelain 存 S0 基线快照
`runs/sf0003/porcelain-before.json`（19 条，见下「既有噪音」节）。

### S1 O-6 落地（B 组）
1. **版本 bump**：`evaluators/aggregate.py` 默认 `--evalbench-version` v6-mvp-0.1→**v6-mvp-0.2**；
   `harness/run_all.py` 加同名透传参数（一键复跑不再落旧版号）。全树旧版号清零
   （`grep -rn 'v6-mvp-0.1' evaluators harness packs nc README.md` = 0 行）。
2. **作废二分支 → 分支 B**：`baseline/` 实测为空（无任何 `<family>/<version>.json`），
   落 `runs/sf0003-baseline-void.json`（voided_count=0+理由+目录清单；聚合器可读旧版号基线数==0）。
3. **`runs/r1-probe/INVALIDATED.md`**：O-6 / citable: false / 不得引用 三个字样齐。
4. **AG-7 跨版本拒绝门（最小实现）**：`aggregate.py --delta-from <上一轮 matrix.json>`。
   实测双向：混版本（prev=v6-mvp-0.1 vs 本轮 v6-mvp-0.2）→ **exit 1**、报错含「版本」、零输出文件；
   同版本（合成输入 `runs/sf0003/ag7-prev-same.json`）→ exit 0、`delta_vs_prev={pack: null}` 显式 null。
5. **`evalkit/CHANGELOG.md`**（新建）：v6-mvp-0.2 节 3 条 fixed（五字段齐+复现命令引用）+ added 4 条。
6. **PLAN §8 O-6 行回改**（本卡唯一授权 PLAN 改动）：状态【保留】→**【已裁定】2026-10-03**，
   处置列写明落点全串 `account:bigmodel-individual-coding-plan/GLM-5.3`、bump、作废、citable:false、
   AG-7 拦截；§8 计数行同步（已裁定 4→5、保留 11→10——该行与 O-6 行同表，属同处回改的连带同步）。
7. **evalkit README 已知限制节**：模型钉版条目同步为「O-6 已裁定」态（含落点全串；无「待 planner 裁定」）。

### S2 修法 A（C 组）
1. `packs/sm-mapping-01/inputs/` → **`fixtures/`** 原子改名（6 文件；改名前逐文件 sha256 存
   `runs/sf0003/inputs-pre-rename-sha256.json`，改名后逐一相等=保内容；附带验证 6 文件与
   `oracle/fixtures/` 同名文件逐字节相同）。
2. **brief.md 改写**：运行条款改为「以臂根为 cwd、`--transcript "fixtures/…"`、`--out "out/…"`」；
   删除旧条款（`inputs/` 目录、「`out/` 目录作为 cwd」绝迹）；硬性要求 1 去掉工具命名建议
   （不含 map_speakers/SKILL.md/资产名字样，EI-7）；INFO 行示例同步为新模板
   （brief 原文带的旧 INFO 句正是缺陷③带偏 baseline 臂的路径之一，SF-0001 §4.3）。
3. **装置 4 处适配**：`make_arms.py`（目录检查+建树+树形说明）、`pack_checks.py`
   （EI-7 扫描面/EI-9 臂树/EI-20 六件清单改 **inputs/fixtures 双名兼容**：一名即可、双名并存判红、
   fixtures 优先——`'"inputs"'` 字面全装置仅存于此处合法别名表）、`process_track.py`
   （引引面正则加 `fixtures/` 形态）、README 目录表。rubric.md 的两处输入目录引用同步。
4. **`packs/sm-mapping-01/PACK-DEVIATIONS.md`**（新建）：偏离项/依据（PLAN §3.1 L1 同形态前提）/
   适用范围（仅本包）/建议回写 PLAN §3.3 的条款文本。
5. **重建臂树**（run-id `sf0003-fix`）：make_arms exit 0 → 隔离探针 baseline 零命中 exit 0、
   treatment 命中 2（`.zcode/skills/` 下 SKILL.md+map_speakers.py，**设计内阳性对照**，README 口径）→
   pack_checks 三断言全过（EI-20 认 fixtures，`input_dir_name: "fixtures"`）。

### S3 SKILL.md INFO 行（D 组，资产树唯一破例点）
1. **D0**：开工时 `SKILL.md:54` 行 sha256=`c861cf0da1a8…`，文本与 SF-0001 报告 §4.3 所记旧文
   逐字一致 → 判定「未改，本卡修」（证据 `runs/sf0003/d0-line54-pre.json`）。
   **行尾事实勘误：该文件实为 LF（0/74 CRLF），任务卡/验收 D3 写「现为 CRLF」与实测不符；
   本卡按「保持原行尾、不引入混行」处理（保留 LF），D3 按行尾单一性+与开工态一致判定。**
2. **D1**：字节级替换一行：旧 `` INFO: 写出 …（共 N 行，替换 X 处，未映射 Y 种） `` →
   新 `` INFO: 写出 out/<file>（共 N 行，替换标签 X 处，未映射标签 Y 种） ``（新文本恰 1、旧文本 0）。
3. **D2**：`git diff --numstat` 恰 `1 1 <path>`；ASSET 子树 porcelain 对 S0 基线快照的
   **新增条目恰等于该文件一行**（差分口径，见「既有噪音」节）。
4. **D4**：新建常设门 `harness/doc_consistency.py`——scratch 临时目录实跑资产工具取 stderr INFO 行，
   与 SKILL.md 模板做占位符归一（剥 `[prog]` 前缀/`\`→`/` 对称归一/数字与文件占位）后逐段同构比对；
   `--selfcheck` 变异自检：删两处「标签」→ 比对必红（MT-2 阳性对照）→ 字节复原（sha256 校验）→ 复跑回绿。
   实测：比对 PASS + 变异自检 PASS，exit 0。实测附带发现：**package 版工具不自动建 out/ 父目录**
   （oracle 版会建），已作为注释留痕在 doc_consistency.py。
5. **D5**：产线根 grep 旧文本：speaker-mapping 包内 0；dist/build 0；唯一命中
   `skillfactory/planning/reports/SF-0001-ws1-report.md`（历史报告引用旧文本作证据，登记不修）。

### S4 0 模型 replay（E 组，本卡核心证据）
`runs/sf0003-replay/` scratch 树（fixtures 来自任务包；生成器=原版 `oracle/map_speakers.py` 的
scratch 副本；cwd=scratch 根）按 brief 新条款复刻全量 **12 条命令**（9 映射 + 3 发现，
参数形态 `--transcript "fixtures/…"` `--out "out/…"`，命令原文全量落盘
`runs/sf0003-replay/replay-commands.json`）：

- **24 产物+stderr 与 `oracle/out/` 逐字节一致：24/24，差异 0**（`runs/sf0003-replay/diff.json`）。
- `artifact_track.py --product-root runs/sf0003-replay/out --reference $ASSET/oracle/out` →
  **exit 0，4/4 PASS——检查 4 `reference_agreement_100pct` 首次转绿**（r1-probe 两臂恒红的尺子已修好）。
- **E2 决策表**：逐字节一致 → 归一规则数=0 收工（无需 normalization.json）。
- **E3 NC-A**（`nc-sf0003-e3/` 独立副本，输入目录名 fixtures→fixturesX 重跑）：检查 4 **红** ✓。
- **E4 NC-B**（好产物副本翻转 1 字节重跑）：检查 4 **红**（check1 同时红，符合预期）✓。
  → 双负控证明转绿不是放水。
- **E5 回显语义（必答）**：**归一回显**。工具对 `--out`/`--transcript` 的回显经
  `str(Path(argv))` 按 OS 分隔符归一——传入 `/` 形态在 Windows 回显为 `\` 形态
  （证据：replay 产物 `discover__normal.json` 的 `transcript=="fixtures\\normal.txt"`、
  INFO 行 `写出 out\\normal__m_full.txt`，与基线逐字节一致）。

### S5 回归+钉版闭环（F 组）
run_check 绿路 exit 0 / 空目录红路 exit 1（双向）；`nc/run_nc.py` **9/9** exit 0（负控未退化）；
oracle 前后 `verify` unchanged=true（tree_sha256 仍=`e3086e10…`，31 文件）；
`aggregate.py` 写-读往返：必填键齐、`delta_vs_prev==null`、版本 v6-mvp-0.2；
**freeze 三段式**：改后 verify 红（漂移清单恰=声明集：changed 5 + new 2）→
`python harness/freeze_device.py freeze --evalkit D:\new-workspace\agent-asset\evalkit`
（子命令先经 `-h` 的 usage 输出确认：`usage: freeze_device.py [...] {freeze,verify}`）→
re-freeze 后 verify 绿（16 关键文件）。**keyfiles 变更条目集合恰等本卡声明清单**：
- changed（5）：evaluators/aggregate.py、evaluators/process_track.py、harness/make_arms.py、
  harness/pack_checks.py、harness/run_all.py
- new（2）：harness/doc_consistency.py、harness/verify_sf0003.py
v6 未升格（F6）。

---

## 二、证据摘录（关键命令与输出）

| 门 | 命令 | 输出/退出码 |
|---|---|---|
| E1 | `artifact_track … --product-root runs/sf0003-replay/out --reference …/oracle/out` | exit 0；`PASS replacement_line_by_line / PASS unmapped_warnings / PASS discover_stats / PASS reference_agreement_100pct` |
| E1 比对 | 24 文件 sha256 对账 | `24 files; identical: 24; diffs: []` |
| B5 负向 | `aggregate.py … --delta-from runs/r1-probe/matrix.json` | exit 1；`AG-7 跨版本拒绝：上一轮 evalbench 版本 v6-mvp-0.1 与本轮 v6-mvp-0.2 不同…已拒绝出数`；无输出文件 |
| B5 正向 | 同上 `--delta-from runs/sf0003/ag7-prev-same.json` | exit 0；`delta_vs_prev: {'sm-mapping-01': None}` |
| F5 一段 | `freeze_device.py verify`（re-freeze 前） | exit 1；`changed×5 + new_file×2` 恰等声明集 |
| F5 三段 | `freeze …` → `verify` | `已冻结 16 个关键文件` → `装置钉版一致：16 个关键文件 sha256 全对` exit 0 |
| F3 | `oracle_gate.py verify --record runs/sf0003/oracle-before.json` | `"unchanged": true`，31/31 |
| F2 | `nc/run_nc.py` | exit 0，`负控全红 + 正常臂不误报: 成立（9/9）` |
| D4 | `doc_consistency.py --asset …/package --selfcheck` | `比对: PASS` + `变异自检: PASS`，exit 0 |
| G4 | `harness/verify_sf0003.py` | **34 门全绿，exit 0**；JSON 落 `runs/sf0003/verify-sf0003.json` |

---

## 三、自测逐条（A1–F6 → 34 门）

全部门行含 `{id, command, exit_code, ts, evidence_sha256}` 四字段，机械可复核：
`python harness/verify_sf0003.py`（planner 验收亲复跑入口），或直接读
`evalkit/runs/sf0003/verify-sf0003.json`。当前快照：**34/34 PASS，failed=[]**。
本报告「二、证据摘录」列出关键十条的原文级输出。

### 验收字面与实测的三处口径说明（不改判据，全部留证据）

1. **A4/D2 差分口径**：afp-clone 工作树存在**先于本平面**的噪音——chenmai8（封存区）8 条
   D/T 条目为 HEAD 中 symlink（mode 120000，指向原宿主绝对路径 `/d/workspace/澄迈8项目/…`）
   在 Windows checkout 上的物化差异；另有 10-01 评测轮遗留 untracked（含
   `speaker-mapping/out/`、deploy-pack/hotwords out/ 等）。A4/D2 的设计目的=「本卡改动面收死」，
   故按 **S0 基线快照差分**实现（`runs/sf0003/porcelain-before.json`，raw sha256=
   `2392656e…41583c`）：本卡新增条目 ∩ 六封存区 = ∅（A4 绿）；ASSET 子树新增 = 恰 SKILL.md 一行（D2 绿）。
   既有噪音一项未动、一项未清（不属本卡授权面）。
2. **E1 显式 --reference**：验收 E1 字面命令未带 `--reference`，而 run_check/runner 的契约是
   0 参=自校验、2 参=对照、1 参=用法错误（exit 2）——单 root 无法触发检查 4。故 E1 按与
   `run_all.py` 相同的形态显式传 `--reference $ASSET/oracle/out`（同判据同尺子，fail-closed 不降）。
3. **B6/B7 路径**：验收写 `evalkit/CHANGELOG.md`、`evalkit/README.md`，按工作区相对路径理解为
   `$EK/CHANGELOG.md`、`$EK/README.md`（$EK=agent-asset/evalkit）。

### 事实勘误两则（实测数据在案）

- SKILL.md 行尾：实测 LF（0/74 CRLF），非卡文所写 CRLF；本卡保留原 LF（见 D0 证据文件）。
- 任务卡「装置代码 4 处硬编码 inputs」勘察精确（make_arms 81-82,100；pack_checks 73,100-101,132；
  process_track 103），按此最小面改动即全绿。

---

## 四、未尽事项 / 给下一棒

1. **WS4 首跑回溯条款待用**：检查 4 现已可绿；WS4 基线轮若仍红按 PLAN §5.5 决策表归因，
   不得归一凑绿（验收文末处置规则原文保留）。
2. **PLAN §3.3 回写待 planner 裁定**：建议条款文本已写在 PACK-DEVIATIONS.md。
3. **commit/push 未做**（红线 6）：本卡全部改动留在工作树——evalkit/ 侧（不进 git 的装置区）
   + afp-clone 内恰 1 行（SKILL.md）+ planning/ 三文件（PLAN.md、TESTS.md 未动，PLAN 已改、
   本报告新增）。提交批次与 ESC-008 衔接由 planner 验收后统一定夺。
4. **evalkit 根目录遗留空目录**（`·`、`步0`、`绿路（零参数自校验）`、runs 下 `echo ##########`
   等，疑似前轮 shell 事故产物）：零字节、零影响、不在本卡授权清理面，原样保留并在此登记。
5. **package 版 map_speakers.py 不自动建 out/ 父目录**（oracle 版会建）：行为差异已在
   doc_consistency.py 留注释；是否算资产缺陷由 planner 判断（SKILL.md 第 3 步示例隐含 cwd=含 out 的目录）。
6. r1-probe 全部数字 **citable: false**（O-6 作废标记在案），任何新引用须先过 AG-7 口径。

> 修题留档（G3）：三条 fixed 的五字段全文见 `evalkit/CHANGELOG.md` v6-mvp-0.2 节
> （题号/旧文本/新文本/缺陷类型/判定人+日期齐，旧新文本逐字引用）。
