# MiniMax-M3.1-Flash 独立盘点报告（2026-10-03）

> 盘点员代号 **MM-F**。本报告完全独立作业，未读取 `baseline-inventory/` 下其他盘点员的文件。
> 全部结论只写我本次亲手跑过的命令与读过的文件；未跑的一律标注证据等级并说明原因。

---

## 1. 执行摘要

这是一个**「一人软件工厂」的多项目 AI agent 产线 monorepo**，核心资产不是产品、而是**「规格（SPEC）+ 确定性评测（EVAL）+ 门禁」的方法论本身**：每个项目把「什么是好的」冻结成可执行评测，验收靠跑测试而不是靠人读文档。本次实测结论分化明显——**5 个项目里有 3 个的数字与声称完全吻合**（qw-arena2 469/469、xuexing-agent 709 passed + 2 skipped、ohos-tailscale 280/280 + typecheck exit 0），**skillfactory 的 v5 评测体系经我重跑 4 个资产全部自评通过、且红路正确 fail-closed（exit 1）、连归档的「学员产物」都能复评通过，是本次最扎实的一块**；但 **peidian-agent 声称 233/233 实测只有 182/184 且 result=FAIL**（两个模块 spec_hash 漂移导致整模块中止），**ohos-tailscale 的 bridge 门禁声称 13/13 实测 11/13**，**video-capability 因 77G 模型与金标素材刻意不入仓而无法在本机复现其 "ALL PASS"**（runner 自行 exit 2 = 环境问题，未执行任何断言）。仓库工程纪律扎实：477 次提交、安全密钥零入库有 `ci_isolation.py` 门在岗、评测红路 fail-closed 真实有效；但**文档声称的「全绿」有明显乐观成分，且当前工作树有 9 个符号链接在 Windows 上无法物化**（`core.symlinks=false`），这是接手者会立刻撞到的第一个坑。

---

## 2. 组件清单与角色

| 组件 | 路径 | 角色 | 本次状态 |
|---|---|---|---|
| monorepo | `afp-clone/`（根目录 `agentic-factory-projects` 符号链接指向它） | 7 个在研项目合并仓，477 commits | HEAD=`18f6ead`，工作树有 9 个 symlink 型脏条目 |
| 参赛选购 agent | `qw-arena2/` | 千问 AI Arena 参赛，469 测试 | ✅ 全绿 |
| 学情诊断 | `xuexing-agent/` | 确定性内核 + LLM 壳，契约驱动重生成 | ✅ 全绿 |
| 配电运维 agent | `peidian-agent/` | 受控行动网关 + 两票制 + 仿真评测 | ❌ 182/184 FAIL |
| 鸿蒙 tailscale | `ohos-tailscale/` | 纯 TS 协议库 8 包 + ArkTS 壳 | ✅ 主门全绿，bridge 门 11/13 |
| 视频流水线 | `video-capability/` | 生成→QC 门禁→judge 盲测 | ⚠️ 无法复现（素材不在仓） |
| skill 资产工厂 | `zcode-research/` | v5 产线 + REGISTRY 总台账 + 4 资产 eval | ✅ 评测体系实测可用 |
| 参赛项目群 | `chenmai8/` | 6 子仓 + 交付支撑层 | ⚠️ 代码在，门禁需重建 venv |
| 安全留档 | `SECURITY-NOTES.md` + `.mimosa/`（根与仓内各一份） | 推送前扫描分诊记录 | ✅ 修复已验证在位 |
| 外部资产 | `nightshift2.bundle`（根 + 仓内各一份，SHA256 相同） | 推送传输载体 | ✅ 完整历史，落后 HEAD 一个提交 |

---

## 3. 能力矩阵（核心）

| 能力 | 所属组件 | 等级 | 证据 |
|---|---|---|---|
| qw-arena2 全量测试 469 passed | qw-arena2 | **A** | `python -m pytest tests -q` → `469 passed in 22.14s` |
| qw-arena2 版本自检 0.5.2 | qw-arena2 | **A** | `python agent/agent.py --version` → `0.5.2` |
| qw-arena2 e2e mock 全链 | qw-arena2 | **A** | `python tools/e2e_mock.py` → `exit_code: 0`、`"passed": true`、1.11s |
| xuexing-agent 全量 709 passed / 2 skipped | xuexing-agent | **A** | `python -m pytest` → `709 passed, 2 skipped in 8.93s` |
| xuexing 知识库校验（189 kps / 810 items） | xuexing-agent | **A** | `tools/validate_knowledge.py` → `VALIDATION OK: 189 kps, 810 items ... 810/810 dual-agent-verified` |
| xuexing 契约测试全绿 | xuexing-agent | **A** | `tools/run_contract.py` → 进度点 100%，exit 0 |
| xuexing 凭据零入库 | xuexing-agent | **A** | `git ls-files \| grep -i '\.env$'` → 空 |
| ohos-tailscale 全仓 280 pass / 0 fail | ohos-tailscale | **A** | `npm test` → `# pass 280 # fail 0`（15.2s，需先 `npm install`） |
| ohos-tailscale 类型检查 exit 0 | ohos-tailscale | **A** | `npm run typecheck` → `tsc --noEmit`，EXIT=0 |
| ohos-tailscale ArkTS 静态机检 54/54 | ohos-tailscale | **A** | `npm run validate:shell` → `summary: 54 passed, 0 failed` |
| **ohos bridge 集成 13/13** | ohos-tailscale | **D** | `npm run test:bridge` → `# pass 11 # fail 2`（详见 §5） |
| **peidian 评测门禁 233/233** | peidian-agent | **D** | `python run_evals.py --module all` → `cases=182/184 failed=2 result=FAIL` |
| peidian 隔离扫描 zero hits | peidian-agent | **A** | `scripts/ci_isolation.py` → `ISOLATION OK: ... zero hits`，EXIT=0 |
| peidian ParkDSL 15/15 | peidian-agent | **A** | `dsl/tests/run_tests.py` → `TOTAL cases=15 failed=0 RESULT: PASS` |
| **video-capability v3 自检 ALL PASS** | video-capability | **C** | `run_v3_checks.py` → exit 2「素材缺失」，README:14 明确「运行时依赖不在仓内」 |
| video-capability QC 代码可加载 | video-capability | **A** | `import qc_orch_v2` → OK；`--help` 正常输出 |
| skillfactory deploy-pack 自评 4/4 | zcode-research | **A** | `runner.py <oracle/out> <oracle/out>` → `ok=true, total=4, passed=4, text_agreement_rate=1.0` |
| skillfactory speaker-mapping 自评 4/4 | zcode-research | **A** | 同上 → `ok=true, total=4, pass=4` |
| skillfactory hotwords 自评 4/4 ALL GREEN | zcode-research | **A** | 同上 → `结果: ALL GREEN ✓（4/4）`，54/54 文件一致率 1.0 |
| skillfactory zctl-mcp 自评 7/7 | zcode-research | **A** | 零参数自评 → `ok=true, total=7, pass=7, fail=0` |
| **评测红路 fail-closed** | zcode-research | **A** | 指向不存在产物 → `结果: FAILED ✗（0/4）`，EXIT=1 |
| 归档「学员产物」可复评 | zcode-research/deploy-pack | **A** | `runner.py out/student_pack1 oracle/out/pack-canonical` → EXIT=0 |
| 根目录 4 份 eval JSON 留档 | 工作区根 | **B** | JSON 内 `candidate_resolved` 绝对路径指向本工作区；hw 为 stdout 全量捕获（含前置 `[PASS]` 行 + 尾部 JSON） |
| 安全修复 safe_rel 防路径穿越 | video-capability | **A** | 实测 6 个恶意路径全拒（`../evil`/`/etc/passwd`/`C:/win`/`a/../../b`/空/`..`），2 个正常路径全过 |
| 安全修复 https 守卫防 SSRF | video-capability | **A** | `prefetch_model.py:44-45` 非 https 抛 ValueError |
| 12 处 high 分诊（1 真 11 误报） | afp-clone | **B** | `SECURITY-NOTES.md` 全文；`~/.mimosa/security-scans/` 归档最新只到 2026-09-29，未含该次扫描产物 |
| chenmai8 六子仓代码在库 | chenmai8 | **A** | 6 目录均在，文件数 134/6242/233/161/19748/215 |
| **chenmai8 各仓一键门禁** | chenmai8 | **D** | `python scripts/gate_g1.py` → `未找到 .venv 解释器` EXIT=1 |
| chenmai8 门禁需重建环境的文档说明 | chenmai8 | **C** | `README.md:32,41` 自述「当前环境未重建，门禁不能开箱即跑」——诚实，但意味着数字未复现 |
| bundle 完整历史可验证 | 工作区根 | **A** | `git bundle verify` → `is okay` + `records a complete history` |
| Mimosa 扫描报告结构化留档 | .mimosa | **B** | reports/history/finding-ledger 三层齐全，schema `mimosa-task-review/v2` |

---

## 4. 实测记录

### 4.1 仓库真实状态

```bash
git -C afp-clone rev-parse HEAD      # 18f6ead098c95794034a4d6bab6c576746cfcbe0
git -C afp-clone status --porcelain   # 17 行
git rev-list --count HEAD            # 477
```

- **分支**：`main`（当前）+ `origin/main` + `origin/wip/gov-gateway-review-person-v0`（README:59 说的未并入评审线，确实在）。
- **标签** 12 个：`xuexing-agent/v0.1.0`、`v0.2.0`、`classroom-v0.1`、`chengmai-feeding-arm/*`（8 个）、`chengmai-playable-factory/clean-room-v0`。与 README:58 相符。
- **7 个项目目录全部齐全**，chenmai8 六个子目录也齐全。
- **工作树不干净：17 项**。逐条查 `git ls-files -s` 后确认，9 个「已跟踪脏条目」**全部是 mode `120000` 的符号链接**（`D` 或 `T`），根因是 `core.symlinks=false`（Windows 检出默认）——不是内容被改。例：`chenmai-drama-dub/_regen2` 磁盘上目录存在，git 却报 D。
- 另 8 项是未跟踪产物：`nightshift2.bundle`、`deploy-pack/out/`、`hotwords/out/`、`hotwords/store.json`、`speaker-mapping/out/`、`deploy-pack/oracle/out/validate.json`、`deploy-pack/package/NUL`。

### 4.2 bundle 与 HEAD 的关系（**修正了背景线索**）

```bash
git bundle list-heads nightshift2.bundle
# 169fd8ebd0e36fba9ccab8ea6b2e7a2e9683bbc1 refs/heads/main
git bundle verify ../nightshift2.bundle
# ../nightshift2.bundle is okay / The bundle records a complete history.
git merge-base --is-ancestor 169fd8eb HEAD   # exit 0
git diff --stat 169fd8eb HEAD                # 1 file changed, 1 insertion(+)
```

**`169fd8eb` 不是 HEAD，而是 HEAD 的父提交**（HEAD=`18f6ead`，2026-10-03 11:04:36 提交，晚 16 分钟）。两份 bundle SHA256 完全相同（`f04b6c5d…7882c2`），差的内容仅 `zcode-research/worklog.md` 一行。

### 4.3 逐项目实测

| 项目 | 命令 | 结果 | 耗时 | 与声称吻合 |
|---|---|---|---|---|
| qw-arena2 | `python -m pytest tests -q` | **469 passed** | 22.1s | ✅ 精确一致 |
| qw-arena2 | `python agent/agent.py --version` | `0.5.2` | — | ✅ |
| qw-arena2 | `python tools/e2e_mock.py` | `exit_code:0, passed:true` | 1.6s | ✅ |
| xuexing | `python -m pytest` | **709 passed, 2 skipped** | 8.9s | ✅ 精确一致 |
| xuexing | `tools/validate_knowledge.py` | `VALIDATION OK: 189 kps, 810 items` | 0.5s | ✅ |
| xuexing | `tools/run_contract.py` | 100% exit 0 | 9.2s | ✅ |
| peidian | `python run_evals.py --module all` | **182/184 failed=2 FAIL** | 49.5s | ❌ **不一致** |
| peidian | `scripts/ci_isolation.py` | `ISOLATION OK` | — | ✅ |
| peidian | `dsl/tests/run_tests.py` | 15/15 PASS | — | ✅ |
| ohos | `npm install` | added 12 packages | 7.6s | 前置 |
| ohos | `npm test` | **280 pass / 0 fail** | 15.2s | ✅ 精确一致 |
| ohos | `npm run typecheck` | EXIT=0 | 7.8s | ✅ |
| ohos | `npm run validate:shell` | 54 passed | — | ✅ |
| ohos | `npm run test:bridge` | **11 pass / 2 fail** | — | ❌ **不一致** |
| video | `run_v3_checks.py` | **exit 2**「素材缺失」 | 0.4s | ⚠️ 无法验证 |
| chenmai8 | `chenmai-feeding-arm/scripts/gate_g1.py` | **exit 1**「未找到 .venv」 | — | ❌ 环境未重建 |

**关于 video-capability 的降级说明**：`run_v3_checks.py:70-79` 先查 ffmpeg（本机有 6.1.1），再查 `overnight/数据/avatar_out/dh_stepfun_720p.mp4` 与 `overnight/数据/golden/clips`——`overnight/数据` 目录**根本不存在**（`git ls-files overnight/ | grep -c 数据` = 0，即从未入 git）。这与 `README.md:14` 的自述一致（模型 77G、金标 40 条均不在仓内）。**runner 的 A–E 全部断言一条都没执行**，所以我不对其 "ALL PASS" 作任何肯定或否定判断。降级验证：`qc_orch_v2` 可 import、`--help` 正常、`thresholds.yaml` 在位（9898 字节）。

### 4.4 skillfactory 评测证据链

**评测对象**：runner 比对的是「产物根目录」——`run_all.py` 产出的 `out/`（含 `manifest.json` + 各步骤快照），参照物是 `oracle/out`。它**评的是产物一致性，不是源码单测**。hotwords 的四项检查（`runner.py:14-18`）= 脚本序列一致 / 重复添加被拒 / funasr 导出格式 / 与参照产物 100% 一致。

**四 runner 自评**（全部 exit 0）：

| 资产 | 命令 | 结果 |
|---|---|---|
| deploy-pack | `runner.py <oracle/out> <oracle/out>` | `ok=true, checks=4/4, text_agreement_rate=1.0` |
| speaker-mapping | 同上 | `ok=true, total=4, pass=4` |
| hotwords | 同上 | `ALL GREEN ✓（4/4）`，`files_matched 54/54, consistency_rate 1.0` |
| zctl-mcp | 零参数自评 | `ok=true, total=7, pass=7, fail=0` |

**红路验证**（fail-closed 是本产线最关键的设计）：`runner.py /tmp/definitely-missing-MM-F <oracle/out>` → `结果: FAILED ✗（0/4）`，**EXIT=1**。评测器不会因为找不到产物就放行。

**与根目录留档的对应**：四份 JSON 的数字与我重跑结果**逐项吻合**（4/4、4/4、4/4、7/7）。JSON 内的 `candidate_resolved` 绝对路径正是本工作区路径，且指向那些**未跟踪的 out/ 目录**——这证明留档就是在本机、对着这些产物跑出来的。我进一步**复评了归档的学员产物** `deploy-pack/out/student_pack1`（对应 `dp_student_eval.json` 的 candidate），结果 **exit 0**，说明留档可复现而不只是 oracle 自说自话。

**一处格式差异**：`hw_student_eval.json` **不是纯 JSON**——它是 stdout 全量捕获（4 行 `[PASS] …` 日志 + 分隔线 + 尾部 JSON 块）。用 `json.load()` 直接解析会抛 `Expecting value: line 1 column 2`。另三份是纯 JSON。任何下游工具按 JSON 解析这四份文件会在第二份上炸。

### 4.5 安全能力

**修复在位且有效**（我实测了函数行为，不只是读代码）：

```
prefetch_model.py:53  def safe_rel(dest, rel)   ← 新增
prefetch_model.py:58  拒绝 isabs / 盘符 / ".." / 空段
prefetch_model.py:63  realpath 包含性断言（commonpath）
prefetch_model.py:44  parsed.scheme != "https" → raise  ← SSRF 守卫
```

实测：`../evil`、`/etc/passwd`、`C:/win`、`a/../../b`、空串、`..` **6 个恶意路径全部 ValueError 拒绝**；`model.safetensors`、`sub/dir/f.bin` **2 个正常路径正确放行**。

**分诊能力的证据与局限**：`SECURITY-NOTES.md` 记录了 12 处 high 的逐条污点流核对（1 真 11 误报），方法论是「不信模式匹配结论」。但我核查了 `~/.mimosa/security-scans/`（7 个 project 目录、80 个文件），**最新一次扫描产物停在 2026-09-29，并不存在 2026-10-03 那次 12 处分诊对应的扫描归档**——该次结论目前只有 `SECURITY-NOTES.md` 文字留档，机器可核验的原始 findings 不在工作区。

**另需注意**：根与仓内 `.mimosa/` 里的所有报告 `run_status` 均为 **`inconclusive`**，非 pass。最新一次（2026-10-03T03:15:11Z）的失败原因明确记录为 `scanner_failed: spawnSync node.exe ETIMEDOUT`，且**恰好就发生在 prefetch_model.py 这个被修复的文件上**——即：Mimosa 自身在这次会话里扫描失败，修复是靠人工污点流分析而非扫描器判定做出的。coverage 也自陈 `status: partial`、`scanned_files: 0`。

### 4.6 协作痕迹

- `.zcode/plans/plan-sess_cad6cf65-….md`：一份完整的四阶段推进计划（K 线课堂层 / K-5 发布闭环 / MCP 扩线 / 课程设计），写明「停在你的人工批准点」「发布不可代签」「红路永远 exit 1」「验收不信任自报」。
- `.zcode/workflow-drafts/` 下有三份 `盘点*.dwf.ts`（GLM-5.3-Flash / MiniMax-M3.1-Flash / Step-Router-V1）——**即本次三盘点员的编排脚本**。按红线要求我未读取其内容。
- `.zcode/workflow-runs/` 5 个 `.mjs` 运行记录 + `afp-clone/.zcode/workflow-runs/` 1 个；`.mimosa/hook-state/` 里有 `dwfrun-…-actor_1_1` 命名的会话状态，说明动态工作流确实在此工作区跑过。
- `zcode-research/worklog.md:24` 记录了 2026-10-03 晨班 R11 的完整闭环，是理解当前仓库状态最关键的一条线索。

---

## 5. 分歧与存疑

### 5.1 【D】peidian-agent 233/233 不成立 —— 实测 182/184 FAIL

```
EVALS mode=all isolation=OK modules=6/8 pending=0 cases=182/184 failed=2 skipped=0 result=FAIL
```

两处失败**都是 `SPEC_DRIFT`（规格漂移），不是业务逻辑失败**：

```
tests/test_m1.yaml: 声明=0b5be472…  重算=673df3dd…
tests/test_m6.yaml: 声明=f90a3d34…  重算=78c16232…
```

`run_evals.py:819-825` 的 `compute_spec_hash()` 按 `spec_ref` 顺序拼接**文件原始字节**取 sha256。漂移导致 **m1 与 m6 两个模块在执行任何用例前就整体中止**（modules=6/8），因此：

- 233 是 YAML 里的用例总数（我逐文件点过：49+30+30+30+19+27+21+27 = **233**，与声称一致）；
- 但 233 − 30(m1) − 21(m6) = **182 实跑 + 2 条漂移记录 = 184**。
- **即：51 个用例根本没被执行。**

**根因排查（已排除 Windows 因素）**：`core.autocrlf=false`、`file` 命令显示规格文件均为 LF 纯文本，**不是 CRLF 检出漂移**。我用 `git show` 直接取 HEAD 的 blob 重算，发现**在声称 233/233 PASS 的那个提交 `6cdabbb` 上就已经是 MISMATCH**（673df3dd…）——即**该声称在其自己声明的提交上就不成立**，不是本次环境造成的。我另外试了「把 `specs/ADDENDUM.md` 换成 `specs-v2/ADDENDUM.md`」等变体，也都对不上声明值。

**这是本次盘点最重要的发现**：README/TASK/worklog 共 10 余处反复记载「233/233 PASS exit 0（本轮实跑）」，但当前 HEAD 上该门禁是红的。修复动作应是重算并回写 m1/m6 的 `spec_hash`（`tests/CHANGELOG.md` 已有此类回写的先例），**属于改测试资产，不是我盘点员的权限范围**。

### 5.2 【D】ohos-tailscale bridge 13/13 不成立 —— 实测 11/13

失败的是 `app/bridge/test/disco-netcheck.test.ts` 的第 8、10 个用例，都是 IPv4-mapped 地址断言：

```
assert.deepEqual(result?.ip, new Uint8Array([156, 238, 240, 81]))
  actual: Uint8Array(4) [203, 0, 113, 10]
```

**这是测试自身的期望值写错，不是被测代码错**：同一用例里 `bus.bind({natPublic: '203.0.113.10:41037'})`，而 `MockStunServer.handleInbound()` 回显 `pkt.from`（`mock-udp-bus.ts:190`），所以返回 `203.0.113.10` 才是自洽的；断言却写死了 `156.238.240.81`。因为全部输入都是硬编码常量，**与平台无关，在 Linux 上同样会失败**。

**额外发现（安全卫生）**：`156.238.240.81` 是本机 hk-gateway 的**真实生产出口 IP**（见 `D:\AGENTS.md` 机器表）。它被硬编码进了公开仓库的测试文件，直接违反该仓 `README.md:49` 自己定的「网络地址卫生」纪律。`git log -S` 显示它由 `360bc87` 引入，此后未改。

### 5.3 【C】video-capability ALL PASS 无法验证

素材（77G 模型 / 金标 40 条）刻意不入仓，runner 自检 exit 2。我只验证到「代码可加载、依赖在位」，**对其 5 项检查的通过与否不作任何判断**。这是环境限制，不是矛盾——但基线里不能写「已验证」。

### 5.4 【C】chenmai8 门禁全部未复现

六子仓代码在库（文件数 134/6242/233/161/19748/215），但 `gate_g1.py` 直接 exit 1 找不到 `.venv`。README:41 诚实声明了这一点，**但表中 8/8、9/9、6/6 等基线数字本次一条都未能复现**。

### 5.5 【B/C】安全分诊的机器证据缺口

12 处分诊的结论只有文字留档；`~/.mimosa/security-scans/` 无对应归档；工作区内所有 mimosa 报告 `run_status=inconclusive` 且最新一次 `scanned_files: 0`（node 进程 ETIMEDOUT）。**修复本身我实测有效（A 级），但「扫描→分诊」这条自动链路本次未成功运行过。**

### 5.6 其他观察

- `deploy-pack/package/NUL` 是一个 **Windows 保留名文件**（Linux `>NUL` 重定向事故产物，169fd8eb 的父提交 `100a9c2` 声称已清除，但**该文件此刻仍在磁盘上且仍未跟踪**——清理未真正完成或被回滚，值得复查）。
- `xuexing-agent` 根目录有个 `%TEMP%joint_gate_out.txt`（Windows 重定向事故产物，README:「已知问题 5」自己承认，可删）。
- 根目录 `agentic-factory-projects` 是指向 `afp-clone` 的符号链接——在 `core.symlinks=false` 环境下这是个易碎点。

---

## 6. 基线建议

### 可写入正式基线（A 级，本次实测复现）

1. **qw-arena2：469 passed + 版本 0.5.2 + e2e mock exit 0** —— 22 秒跑完，可作快速回归。
2. **xuexing-agent：709 passed / 2 skipped + 知识库 VALIDATION OK + 契约全绿 + 凭据零入库** —— 9 秒跑完，三件套齐全。
3. **ohos-tailscale：npm install(5s) + npm test 280/280 + typecheck exit 0 + validate:shell 54/54** —— 注意必须先 `npm install`，否则 78 个测试文件里 28 个因 `@ohos-tailscale/common` 未链接而 `ERR_MODULE_NOT_FOUND`。
4. **peidian 副门：ci_isolation zero hits + ParkDSL 15/15**。
5. **skillfactory v5 评测体系可用**：4 资产自评全绿（4/4、4/4、4/4、7/7）、**红路 fail-closed 有效（exit 1）**、归档学员产物可复评 exit 0。**这是本工作区方法论价值最高的资产**——评测器本身可信。
6. **prefetch_model.py 安全修复在位且有效**（6 恶意全拒 / 2 正常全过 / https 守卫）。
7. **nightshift2.bundle 是完整历史且可验证**。

### 必须打问号 / 需修复后才能入基线

1. **peidian 233/233 —— 建议标为「当前 FAIL」**。接手者若照 README 跑会得到红色结果并浪费排查时间。修复=重算回写 m1/m6 的 `spec_hash`。
2. **ohos bridge 13/13 —— 建议标为 11/13**。修复=把两处断言的 `156.238.240.81` 改为 `203.0.113.10`（同时清除仓内真实生产 IP）。
3. **video-capability —— 标为「本机不可验证」**，须写明前置条件（77G 模型 + 金标 + ffmpeg），不得标绿。
4. **chenmai8 六子仓门禁 —— 标为「需重建环境」**，README 已如实声明；基线里应保留 09-30 数字但注明未复现。
5. **12 处 high 分诊的自动扫描链路** —— 修复有效（A），但扫描器本次 `inconclusive`，不宜声称「扫描能力已验证」。
6. **工作树洁净度** —— 9 个 symlink 在 Windows 上无法物化，基线检查脚本不应把 `git status` 非空直接判为「有人改了代码」。
7. **四份根目录 eval JSON 格式不齐** —— `hw_student_eval.json` 非纯 JSON，下游解析会炸，建议统一格式或加说明。

### 一句话给决策者

**这个工作区的「评测方法论」是真的、可用、可复现（skillfactory 四资产自评全绿 + 红路正确失败），「项目数字」则有三处需要打折：peidian 门禁当前是红的、ohos bridge 差 2 个用例、video 与 chenmai8 因环境未重建而无法复现。README 的「全绿」基调比实测乐观，接手前应按上表修正。**

---

*盘点员 MM-F（minimax/Minimax-M3.1-Flash-Preview）｜2026-10-03｜全程只读原始资产，未 commit / push / 改删任何既有文件；唯一写入为本报告。ohos-tailscale 执行了 `npm install`（写入 node_modules，任务书允许），未修改任何被跟踪文件。*
