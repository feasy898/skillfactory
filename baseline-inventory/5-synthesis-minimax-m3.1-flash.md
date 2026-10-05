# MiniMax-M3.1-Flash 交叉审校总结（2026-10-03）

> 审校员代号 **X-MMF**（minimax/Minimax-M3.1-Flash-Preview）。与另两名交叉审校员并行作业，互不共享上下文。
> 输入：`1-inventory-glm5.3-flash.md`（GLM-F，下称 **GLM**）、`2-inventory-minimax-m3.1-flash.md`（MM-F）、`3-inventory-step-router-v1.md`（SRV1）。
> **所有裁定均由我本会话亲自执行命令得出**，命令与关键输出随文附上。凡我未跑的，一律标「未跑」。
> 红线遵守：未修改/删除任何既有文件；未 `git commit` / `git push`；未外发数据。唯一新建文件为本报告 + 系统临时目录下的 `X-MMF-*` 产物（`X-MMF-specarch.py`、`X-MMF-peidian.log`、`X-MMF-nulrepo/`、`X-MMF-nultest/`、`X-MMF-status.txt`）。仲裁后工作树脏项仍为 17 项，与开工前一致（`git status --porcelain | wc -l` = 17）。

---

## 0. 一句话结论

三方在**所有实质判断上都是一致的**——19 条候选分歧里，**只有 1 条是真分歧**（bridge 11/13 的根因归属），**6 条是统计口径差异而非矛盾**，**3 条是计数错误**。我另外挖出 **2 件三方都没看见的事**：一个真实基础设施 IP 以字节数组形式残留在公开仓里（而清洗说明声称已清），以及 `NUL` 保留名文件对 git 工具链的破坏性机制——这解释了为什么「Windows 兼容清理」提交只清了索引、没清磁盘。

---

## 1. 高置信共识（可进正式基线）

证据等级取三方交集。凡我亲自复跑的，附我的命令与输出。

| # | 结论 | 几方一致 | 证据等级（交集） | 我的独立复验 |
|---|---|---|---|---|
| C1 | monorepo HEAD=`18f6ead098c9579…`（2026-10-03 11:04:36），`git rev-list --count HEAD`=**477** | **3/3** | **A** | `git log -1 --format='%H %ci %s'` → `18f6ead… 2026-10-03 11:04:36 +0800 zcode-research: 晨班 R11 收口台账…`；`git rev-list --count HEAD` → `477` |
| C2 | `qw-arena2` 全量单测 **469 passed**，exit 0 | **3/3** | **A** | `cd qw-arena2 && python -m pytest tests -q -p no:cacheprovider` → `469 passed in 17.63s`，`EXIT=0` |
| C3 | `xuexing-agent` 全量单测 **709 passed, 2 skipped**，exit 0 | **3/3** | **A** | `cd xuexing-agent && python -m pytest` → `709 passed, 2 skipped in 4.82s`，`EXIT=0` |
| C4 | `peidian-agent` 评测门禁 **当前为红**：`cases=182/184 failed=2 result=FAIL`，exit 1；两处失败是 m1/m6 的 SPEC_DRIFT，51 个用例未执行 | **3/3** | **A** | `cd peidian-agent && python run_evals.py --module all` → `EVALS mode=all isolation=OK modules=6/8 pending=0 cases=182/184 failed=2 skipped=0 result=FAIL`，`EXIT=1`（日志 `X-MMF-peidian.log`） |
| C5 | `video-capability` v3 自检 **本机不可执行**：exit 2「素材缺失」，A–E 断言一条未跑 | **3/3** | **A** | `cd video-capability && python overnight/vpipe/tests/run_v3_checks.py` → `素材缺失: …overnight\数据\avatar_out\dh_stepfun_720p.mp4（dh素材）`，`EXIT=2`；`git ls-files -- "overnight/数据" | wc -l` → `0`；脚本 `run_v3_checks.py:7` 自述 `0=全部通过 1=有失败 2=环境问题（ffmpeg/素材缺失，未执行）` |
| C6 | `chenmai8` 门禁 **fail-closed 拒跑**（环境未重建），README 已如实声明 | **3/3** | **A**（行为）/ C（基线数字） | `cd chenmai-feeding-arm && python scripts/gate_g1.py` → `[FAIL] 未找到 .venv 解释器…`，`EXIT=1` |
| C7 | `nightshift2.bundle` = 自包含完整历史，唯一 ref `refs/heads/main=169fd8eb`，是 **HEAD 的直接父提交**（差 1 个提交、1 行文件） | **3/3** | **A** | `git bundle verify ../nightshift2.bundle` → `is okay` + `records a complete history`；`git bundle list-heads` → `169fd8eb… refs/heads/main`；`git merge-base --is-ancestor 169fd8eb HEAD` → exit 0；`git log --oneline 169fd8eb..HEAD` → 仅 `18f6ead`；`git diff --stat 169fd8eb HEAD` → `zcode-research/worklog.md \| 1 +` |
| C8 | 根目录 + `afp-clone/` 两份 bundle **逐字节相同** | **3/3** | **A** | `sha256sum nightshift2.bundle afp-clone/nightshift2.bundle` → 两者均 `f04b6c5db190d0129dbce49db0dc0287dafbae0e45dae0ab5c63df29fb7882c2` |
| C9 | skillfactory v5 评测体系 **活着**：runner 可复现、绿路 exit 0 | **3/3** | **A** | `cd v5/assets/speaker-mapping && python eval/runner.py out/student_run1 oracle/out` → 12/12 一致，`GREEN_EXIT=0` |
| C10 | 评测器 **红路 fail-closed** 真实有效（篡改/缺失 → exit 1） | **2/3**（GLM、MM-F 实测；SRV1 未跑红路） | **A** | `python eval/runner.py C:/…/X-MMF-missing-dir oracle/out` → 12 项全报「被测侧 缺少 …」，`RED_EXIT=1` |
| C11 | `ohos-tailscale` **`npm test` 280/280 需先 `npm install`** | **2/3** + 我（SRV1 测的是未安装态，见 §2 D3） | **A** | `cd ohos-tailscale && npm test` → `# tests 280 # pass 280 # fail 0`，`NPMTEST_EXIT=0`（5.5s） |
| C12 | `ohos-tailscale` `typecheck` exit 0；`validate:shell` **54 passed / 0 failed** | **2/3** + 我（SRV1 未装依赖未跑） | **A** | `npm run typecheck` → `EXIT=0`；`npm run validate:shell` → `summary: 54 passed, 0 failed` |
| C13 | `ohos-tailscale` `test:bridge` **11/13**（2 失败），与 README 声称的 13/13 矛盾 | **2/3** + 我（SRV1 未跑） | **A** | `npm run test:bridge` → `# tests 13 # pass 11 # fail 2`，`BRIDGE_EXIT=1`；失败用例 = `not ok 8 STUN 探测全链路…`（`disco-netcheck.test.ts:62`）与 `not ok 10 disco Ping→Pong…`（`disco-netcheck.test.ts:99`） |
| C14 | 「12 处 high 分诊」的**机器可核验原始报告不在盘内**；`SECURITY-NOTES.md:3` 是唯一留档 | **3/3** | **A**（缺失本身）／B（分诊结论） | 见 §2 D4 全量命令 |
| C15 | 工作区 Mimosa 留档 run **全部 `inconclusive` / `findings.total=0` / `coverage.status=partial`** | **2/3**（GLM、MM-F；SRV1 计数为 2 实为 4） | **A** | 4 份 `history/run-*.json` 逐份解析：`run-20261002T002945085Z`(root)、`run-20261003T031511554Z`(root)、`run-20261002T122651043Z`(仓内)、`run-20261002T161732254Z`(仓内) — 四份 `runStatus` 均为 `inconclusive` |
| C16 | `prefetch_model.py` 安全修复**在位且行为有效**（路径穿越拒、https 守卫） | **2/3**（GLM、MM-F；SRV1 未跑） | **A** | 逐项 import 调用：7 个恶意路径（`../evil` `/etc/passwd` `C:/win` `a/../../b` `''` `..` `../../etc/shadow`）**7/7 ValueError 拒绝**，2 个正常路径正确放行 |
| C17 | `peidian` 副门绿：`ci_isolation.py` 零命中、`dsl/tests/run_tests.py` 15/15 | **2/3** 直接实测（MM-F、SRV1；GLM 仅从门禁输出读到 `isolation=OK`，未单独跑这两条） | **A** | `python scripts/ci_isolation.py` → `ISOLATION OK: pattern='PARK-002|TARIFF-2026B|OP-1[0-9]' zero hits in golden, scenarios, src, tests, ontology, regulations, tools, skills, prompts, assets`，`EXIT=0`；`python dsl/tests/run_tests.py` → `TOTAL cases=15 failed=0 / RESULT: PASS`，`EXIT=0` |
| C18 | `chenmai8` 六子仓代码在库，README 自述门禁不能开箱跑 | **3/3** | **A**（在库）／C（基线数字） | 六目录齐；文件数见 §3 |
| C19 | GitHub 远端**当前不可达**，远端推送状态无人核实过 | **3/3** | **A**（不可达）／—（远端实况） | `git ls-remote origin` → `fatal: unable to access 'https://github.com/feasy898/…': Failed to connect to github.com:443 over proxy 100.64.0.3 after 21013 ms: Could not connect to server` |
| C20 | 「全绿」基调比实测乐观——须按项目分档写基线 | **3/3** | — | 三方独立得出同一结论，措辞不同 |

---

## 2. 分歧仲裁记录

19 条候选中：**真分歧 1 条、口径差异 6 条、计数错误 3 条、文档/实测矛盾但三方结论一致 9 条**（矛盾项已在 C1–C20 落位，此处只记仲裁过程与口径校正）。

### 2.1 真分歧（唯一一条）：`test:bridge` 11/13 的根因归属

| 项 | 内容 |
|---|---|
| **分歧** | GLM：根因 = 10-01 公开脱敏 `git filter-repo` 清洗副作用（`PUBLIC-SCRUB-NOTE.md §2` 自述清洗覆盖「测试夹具（NAT 仿真地址）」），属脱敏副作用而非代码劣化。MM-F：根因 = 测试自身期望值写错——同一用例 `bus.bind({natPublic:'203.0.113.10:41037'})` 而断言写死 `[156,238,240,81]`，输入全为硬编码常量，**与平台无关，Linux 上同样失败**。 |
| **裁定** | **两方都对，分工不同：MM-F 说的是「缺陷是什么」，GLM 说的是「缺陷怎么来的」。合并后的准确表述是——10-01 的 filter-repo 公开清洗把测试夹具的**字符串形态** `156.238.240.81` 替换成了 `203.0.113.10`，但**漏掉了字节数组形态** `new Uint8Array([156, 238, 240, 81])`，于是「输入侧被洗、期望值侧没被洗」，制造了这条不对称的断言语义。被测代码没错，错的是断言；制造这个错的是清洗脚本。**平台无关——MM-F 这条判断成立。** |
| **我的实测证据** | ① 字节数组残留在**两处**，GLM 与 MM-F 都只找到断言那一处：<br>`git grep -n "156, 238, 240, 81" -- .` →<br>`ohos-tailscale/app/bridge/test/disco-netcheck.test.ts:79: assert.deepEqual(result?.ip, new Uint8Array([156, 238, 240, 81]), '映射地址=公网 IPv4 原始字节');`<br>`ohos-tailscale/app/bridge/test/disco-netcheck.test.ts:125: mapIp16FromV4(new Uint8Array([156, 238, 240, 81])),`<br>② 而**点分十进制形态全仓零命中**：`git grep -n "156\.238" -- .` → 空（exit 0）。这正解释了清洗为何被自以为完成——纯文本 grep 查不出来。<br>③ 清洗说明的承诺被证伪：`PUBLIC-SCRUB-NOTE.md §3` 写「测试夹具中的地址已随上表一并示例化（`app/bridge/test/`、…）」，而 §2 映射表只登记了字符串形态。<br>④ 自洽性佐证：同文件 `:65` 输入侧 `natPublic: '203.0.113.10:41037'`；`docs/oracle/protocol-notes.md:200` 明写「`IPv4: yes, 203.0.113.10:41037` 中的公网地址正是 hk-gateway 的公网 IP」。<br>⑤ 失败详情（我实跑）：`actual: Uint8Array(4) [203, 0, 113, 10]` vs expected `[156,238,240,81]`。 |
| **对基线的处置** | 写 **11/13**，并把根因写成「公开清洗漏洗字节数组形态」——不是「代码劣化」。修复动作有两项且必须同时做：改断言值 **+** 清掉残留真实 IP（见 §4-B2）。 |
| **附：悬而未决** | MM-F 称 `git log -S` 显示该 IP 由 `360bc87` 引入、此后未改——**成立**（我复跑 `git log --all -S "156, 238, 240, 81" -- ohos-tailscale/` 与 `git log -S "203.0.113.10:41037"` 均只命中 `360bc87`，该提交也是此文件的 add 提交，author=committer=2026-10-01 04:38:28）。但 **`360bc87` 本身是否就是被 filter-repo 重写后的提交，无法判定**：`.git/filter-repo/` 目录不存在（无 commit-map / ref-map 残留），且该提交 author 与 committer 时间戳完全相同、不带重写特征。→ **悬而未决**，但不影响裁定：当前字节内容本身就是判据。 |

### 2.2 口径差异（不是矛盾）

**D1 — peidian「182/184」vs「184 cases / 2 failed」**
- 分歧表象：GLM/MM-F 写 `cases=182/184 failed=2`；SRV1 写「184 cases / 2 failed」并补一句「当前 HEAD 的 `run_evals.py --module all` 仅产出 184 条用例」。
- **裁定：三方跑的是同一条命令、同一行输出，无实质分歧；SRV1 的措辞把「总数」当成了「产出数」，且漏了 233 这个真正的分母。**规范口径如下（我逐文件点过用例数验证）：

  | 口径 | 值 | 含义 |
  |---|---|---|
  | YAML 声明用例总数（m0–m7 八模块） | **233** = 49+30+30+30+19+27+21+27 | README 声称的「233/233」的分母 |
  | 实际执行 | **182** | 6 个模块（m0/m2/m3/m4/m5/m7）实跑全过 |
  | 门禁记账分母 | **184** = 182 + 2 | 2 = m1/m6 的模块级 SPEC_DRIFT 记录 |
  | **从未执行** | **51** = 30(m1) + 21(m6) | 漂移导致两模块在跑任何用例前整体中止（`modules=6/8`） |

  我的验证：`for f in tests/test_m*.yaml` 逐份解析用例数 → `m0=49 m1=30 m2=30 m3=30 m4=19 m5=27 m6=21 m7=27 m8=7 m9=8`（m0–m7 合计 233；m8/m9 不在 `--module all` 范围内）。
- **给合并总文者的写法**：「README 声称 233/233；实测 6/8 模块执行、182 用例通过、m1/m6 因 spec_hash 漂移整体中止、51 用例未执行，门禁 exit 1。SRV1 的『184 条用例』应改写为『记账分母 184』。」

**D2 — `safe_rel` 「7 恶意/3 正常」vs「6 恶意/2 正常」**
- **裁定：样本集不同，不是分歧。**我实测 7/7 恶意全拒（含 MM-F 未列的 `../../etc/shadow`）、2/2 正常放行。两方的结论方向完全一致。基线写法建议统一为「恶意路径变体全拒、正常相对路径放行」，不写死数字。

**D3 — `ohos-tailscale`「280/280」vs「78 tests / 50 pass / 28 fail」**
- **裁定：纯环境态差异，同一份代码，不是矛盾。**机制我已验证：`package.json` 声明 `workspaces: ["packages/*"]`，`npm install` 会在 `node_modules/@ohos-tailscale/` 下建 8 个指向 `packages/*` 的符号链接（`ls -la` 确认 8 条 `lrwxrwxrwx`，mtime 均为 2026-10-03 13:04 = MM-F 那次安装）。缺了这 8 个链接，`import '@ohos-tailscale/common'` 全部 `ERR_MODULE_NOT_FOUND` → 恰好 28 个失败。
- SRV1 测的是未安装态，GLM **也测过未安装态并得到完全相同的 78/50/28**，MM-F 只测了安装后。所以这不是「1 打 2」，而是 **2/3 测了未安装态（数字一致）+ 1/3 测了安装后**。
- **我无法复现未安装态**（拆掉 `node_modules` 属红线），故 78/50/28 采信 GLM 与 SRV1 的一致观察。
- **基线写法**：`npm test` 的 280/280 **必须带前置 `npm install`**；78/50/28 是「未装依赖」态，**不得记为代码缺陷**。

**D4 — Mimosa 留档 run 的条数与字段**
- GLM：4 个 run（`inconclusive` / `findings.total=0`），并给出「root 最新 run coverage.baseline `captured_files: 2851`」。MM-F：工作区内所有报告 `run_status=inconclusive`，最新一次 `scanned_files: 0`。SRV1：「两次扫描 run（2026-10-02、2026-10-03）」。
- **裁定：GLM 的 4 与字段全对，SRV1 的 2 是漏读了 `afp-clone/.mimosa/`（该目录下另有 2 个 10-02 的 run），MM-F 的表述正确但未给条数。** GLM 与 MM-F 读的其实是不同对象，不矛盾——我逐份解析：
  - `.mimosa/history/run-20261003T031511554Z-5312-…json`：`runStatus=inconclusive`、`findings={"total":0}`、`coverage={"status":"partial","reasonCounts":{"scanner_failed":1,"project_check_failed":1}}`、`evidenceBoundary="static_only"`、`rulesVersion="unavailable"`；
  - `.mimosa/reports/task-review-…-20261003T031511554Z-5312-….json`：`"captured_files": 2851`、`"scanned_files": 0`、`run_status: inconclusive`、`status: partial`。
  - 即 **GLM 引的 2851 出自 report 文件、MM-F 引的 0 出自同一 report，两者都对**。
- **补验（三方都没查的）**：`~/.mimosa/` 下除 `security-scans/` 外还有 `security-scan-jobs/`，11 个 job 文件，**最新 mtime 2026-09-29 12:20**。`find ~/.mimosa/security-scans -type f -printf '%T+ %p\n' | sort -r | head -1` → `2026-09-30+02:48:50 … project-5e38758eef22c3b4a5d713cd/scan-2026-09-29T18-48-50.950Z-…/report.md`。**结论：12-high 那次扫描在两个归档根里都不存在。**

**D5 — `nightshift2.bundle` 的角色定性**
- GLM：夜班/晨班收口时点的完整历史快照——**推送前置物兼离线传输载体**，兼灾备种子（非增量备份，无 basis；不含 R11 最后一笔）。SRV1：夜班工作流跨机传输/备份载体。MM-F：推送传输载体。
- **裁定：三方一致，措辞深浅不同，无需仲裁。**但须标明等级：*关系*（169fd8eb = HEAD 父提交、双份一致、自包含）是 **A**；*角色*是**推断**，理由是三方都连不上 GitHub，无任何一方的远端实况证据。基线里应写「A 级事实 + 推断角色」两层，不要把推断混进 A 级。

**D6 — bundle 头 `169fd8eb` 是不是 HEAD**
- GLM 与 MM-F 都做了 `merge-base --is-ancestor` / `diff --stat`；SRV1 也做了 `merge-base`。**三方一致 + 我复核：是父提交，差 1 个提交。**MM-F 报告里「修正了背景线索」的措辞暗示这是它独家纠正的，实际非独家。

### 2.3 计数错误（实测裁定）

**E1 — 标签数：GLM 与 SRV1 都说 13，MM-F 说 12 → 裁定 MM-F 正确。**
```
$ git tag | wc -l
12
$ git tag | sort
chengmai-feeding-arm/{cs_arm,cs_mouth,cs_orchestra,cs_schema,cs_schema-v1.1,cs_sim,cs_voice,e2e-mock}-v1.0   ← 8 个
chengmai-playable-factory/clean-room-v0
classroom-v0.1
xuexing-agent/v0.1.0
xuexing-agent/v0.2.0
```
附注：MM-F 称「与 README:58 相符」略强——`README.md:58` 只按模式列举（`xuexing-agent/v0.1.0`、`v0.2.0`、`chengmai-feeding-arm/*`、`chengmai-playable-factory/clean-room-v0` = 11 个），**`classroom-v0.1` 未被 README 覆盖**，是文档漏项。

**E2 — 工作树脏项构成：GLM 与 MM-F 都说「9 条符号链接」，SRV1 拆成「5 D / 7 M / 6 ??」→ 裁定 10 条符号链接、17 条脏项、三方计数皆有小误。**
```
$ git -c core.quotepath=false status --porcelain      # 共 17 行
 D chenmai8/_reviews/可玩的小游戏广告
 T chenmai8/_reviews/短剧多国出海/repo
 D chenmai8/chenmai-drama-dub/_regen2
 D chenmai8/chenmai-playable-ads/_regen
 D chenmai8/chenmai-playable-ads/packages/engine-bridge/_regen
 T chenmai8/plan--可玩的小游戏广告/可玩的小游戏广告/repo
 T chenmai8/plan--政务AI脱敏网关/具身助餐机器人/repo
 D chenmai8/plan--政务AI脱敏网关/咖啡豆质检
 T chenmai8/plan--政务AI脱敏网关/政务AI脱敏网关/repo
 T chenmai8/plan--政务AI脱敏网关/短剧多国出海/repo
?? nightshift2.bundle
?? zcode-research/skillfactory/v5/assets/deploy-pack/oracle/out/validate.json
?? zcode-research/skillfactory/v5/assets/deploy-pack/out/
?? zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL
?? zcode-research/skillfactory/v5/assets/hotwords/out/
?? zcode-research/skillfactory/v5/assets/hotwords/store.json
?? zcode-research/skillfactory/v5/assets/speaker-mapping/out/
```
- 逐条查 mode：**10 条全部是 `120000` 符号链接**（`git ls-files -s`），且磁盘上 10 条**全部实际存在为普通目录**（`stat -c '%F'` → `directory`）。根因 `git config core.symlinks` = `false`。
- **GLM、MM-F 少算 1 条（9→10）；SRV1 的三项拆分里两项错（应为 5 D / 5 T / 7 ??）。**
- 结论定性三方一致且**成立**：这是 Windows 检出伪差，**不是内容被改**；基线检查脚本不得把 `git status` 非空直接判为「有人改了代码」（MM-F 这条建议正确，应保留）。
- 未跟踪 7 项中，`deploy-pack/out/`、`hotwords/out/`、`speaker-mapping/out/`、`hotwords/store.json`、`deploy-pack/oracle/out/validate.json` 是评测产物；`nightshift2.bundle` 是传输副本；`deploy-pack/package/NUL` 是**残留缺陷**（见 D7）。

**E3 — MM-F 报告内部小误**：「另 **8** 项是未跟踪产物」但只列了 7 项。实测未跟踪恰为 **7** 项。合并时以实测为准。

### 2.4 「12 处 high」扫描证据链 —— 三方一致，我补一层

- 三方一致：原始扫描报告不在盘内。GLM 从 `.mimosa/` 两级 + `~/.mimosa/security-scans/` 两侧查；MM-F 查 `~/.mimosa/security-scans/`（7 个 project 目录、80 个文件）；SRV1 引用 `.mimosa/history/run-20261003T031511554Z-*.json` 的 `scanner_failed`。**我加查了 `~/.mimosa/security-scan-jobs/`（11 个 job，最新 2026-09-29 12:20）——同样没有 10-03 的产物。裁定成立：三方一致。**
- 留档的正面证据：`SECURITY-NOTES.md:3` = `> 2026-10-03，zcode-nightshift。触发：Mimosa git-push 前扫描报 12 处 high。`——**B 级文字留档，无机器可核验底稿。**
- **hook 活性：三方口径不同，我给出可核验的裁定。**
  - GLM 声称「本会话一次 Bash 重定向被 `Mimosa 拒绝了…` hook 拦截」——**我未能复现拦截**，不采信为硬证据。
  - 我改用状态文件证明 hook **在本会话实时工作**：`afp-clone/.mimosa/hook-state/sess_dwf-dwfrun-fc74f056-…-actor_1_1.json`（**我自己的会话 id**）mtime = `2026-10-03 13:31:05`，内容 `{"touched":[],"bashMutation":true,…}`——`bashMutation: true` 说明 hook 正在观测我的 Bash 调用。同一目录下另有 3 个并行盘点/审校会话的 hook-state，mtime 分别 13:02:54 / 13:21:46 / 13:34:12。
  - `afp-clone/.mimosa/hook-status/` 有 3 份 `mimosa-hook-status/v1` 记录，其中两份精确对应两份盘点报告的落盘：`sessionId=…dwfrun-1095ea25…` → `file=D:\new-workspace\agent-asset\baseline-inventory\2-inventory-minimax-m3.1-flash.md`，`sessionId=…dwfrun-56c4fa86…` → `file=…\1-inventory-glm5.3-flash.md`，均 `outcome:"clear" / coverage:"complete" / findingCount:0`。
  - **裁定：hook 现行活跃（A 级，状态文件实证）；「hook 会误伤只读操作」为 GLM 独家观察，我未复现，标 B。**

### 2.5 悬而未决

1. **`spec_hash` 声明值 `0b5be472…` / `f90a3d34…` 究竟对应哪一刻的字节**——注册漂移发生在某次**未提交的工作树**时刻，库内无任何证据可还原。GLM 与 MM-F 都已声明不可还原，我确认**不可还原**。
2. **`360bc87` 是否为 filter-repo 重写产物**——无 `.git/filter-repo/commit-map` 残留，author=committer 时间戳无重写特征，无法判定（见 §2.1 附注）。
3. **GitHub 远端到底有没有这 10 个提交**——网络不可达，任何一方都无法核实（见 §4 补验）。
4. **12 处 high 的原始条目**——报告不在盘内，永久不可核验。

---

## 3. 复跑确认的分歧项（我补做的独立实测）

| 断言 | 出处 | 我的复验 | 结果 |
|---|---|---|---|
| peidian 门禁 182/184 | GLM、MM-F、SRV1 | `python run_evals.py --module all` | **逐位复现**，exit 1 |
| ohos bridge 11/13 | GLM、MM-F | `npm run test:bridge` | **逐位复现**，exit 1 |
| ohos npm test 280/280 | GLM、MM-F | `npm test` | **逐位复现**，exit 0 |
| video exit 2 | 三方 | `run_v3_checks.py` | **逐位复现** |
| chenmai-feeding-arm gate_g1 exit 1 | 三方 | 同命令 | **逐位复现** |
| skillfactory 红路 exit 1 / 绿路 exit 0 | GLM、MM-F | 同命令 | **逐位复现** |

**特别记录：peidian 门禁并发未污染本次结果。**我的运行时刻 `runtime/eval_results.json` 的 `generated_at=2026-10-03T05:44:06Z`（=本地 13:44），为单写者；GLM 报告的 m7「任务已存在」×2 干扰**未在我这里出现**。机制上 GLM 的说法成立：`peidian-agent/src/m2_information/__init__.py:170` 有 `raise ValueError(f"任务已存在: {task_id}")`，且 `runtime/` 下有共享状态目录 `m2_eval/ m3_eval/ m7_eval/ runs/`（`peidian-agent/.gitignore:2` 忽略 `runtime/`，所以并发跑不会脏工作树，但**会互相污染结果**）。

---

## 4. 共同盲区与补验结果

### 4.1 三方都没覆盖的盲区（我全部当场补验）

**B1 — Windows 保留名 `NUL` 对 git 工具链的破坏性机制（最重要，三方零覆盖）**
GLM 只在 reflog 里读到 `100a9c2` 提交信息声称已清理；MM-F 发现文件还在、怀疑「清理未真正完成或被回滚」；SRV1 未提及。谁都没问**为什么清不掉**。
- 我的补验（先在系统临时目录建一次性仓库复现机制，**未触碰工作区**）：
```
$ cd /tmp/X-MMF-nulrepo && git init -q . && echo "content123" > NUL && git add -A
error: short read while indexing NUL
error: NUL: failed to insert into database
fatal: adding files failed
$ git rm NUL
git rm exit=128          # 文件仍在磁盘上，status 仍显示 ?? NUL
```
- 工作区实证：
```
$ git show --name-status 100a9c2        # 提交标题「清除 deploy-pack/package/NUL」
D  zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL     # 索引侧确已删除（54 行）
$ sha256sum <disk>                       # aab92ecee3ac6f44a1df0112449af485fd0ca7aba7b63cfe751f2096ef2d5b7a
$ git show 100a9c2^:<path> | sha256sum   # aab92ece…（逐字节相同）
$ ls -la <path>                          # 1698 B，mtime 2026-10-02 00:15
$ git check-ignore -v <path>             # exit 1（未被忽略）
$ git status --porcelain -- <path>       # ??（永久脏项）
```
- **裁定：`100a9c2` 的「Windows 兼容清理」只完成了索引侧，磁盘侧从未清掉，且此后会一直以 `??` 出现在 `git status` 里。**这不是回滚（MM-F 的第二个猜测可排除），是**保留名让 git 无法按路径读写该文件**。
- **基线必须写**：接手者若看到 `?? .../package/NUL`，那是**已知残留**不是新污染；处置需用非 git 路径（如 PowerShell `Remove-Item -LiteralPath '\\?\D:\...\NUL'`），我未执行删除（红线）。

**B2 — 公开仓里真实基础设施 IP 的字节数组残留（重要，三方零覆盖）**
MM-F 发现了 IP 硬编码，但把它当成「测试写错」；**没人去核对 10-01 的公开清洗到底覆没覆盖它**。
- 补验见 §2.1：`git grep "156\.238" -- .` 全仓零命中，而 `git grep "156, 238, 240, 81" -- .` 命中 2 处。`156.238.240.81` = hk-gateway 出口 IP（`D:\AGENTS.md` 机器表），`docs/oracle/protocol-notes.md:200` 亦自证 `203.0.113.10`「正是 hk-gateway 的公网 IP」。
- **裁定：这是本次唯一一条带外溢影响的安全发现**——不是测试红了的问题，是**真实基础设施 IP 残留在对外公开的仓库中，且清洗说明 `PUBLIC-SCRUB-NOTE.md §3` 明确声称已清**。必须与 §2.1 的断言修复同批处理。
- 报告口径建议：不给它单独开「漏洞」章节（它不是可利用漏洞），但要作为**「公开清洗的覆盖面审计缺口」**写进基线的待办项，并点名 `disco-netcheck.test.ts:79,125`。

**B3 — `npm run typecheck:bridge` 三方都没跑**
`package.json` 的 5 个脚本里，三方合计只跑了 4 个。
- 补验：`npm run typecheck:bridge` → `tsc --noEmit -p app/bridge`，**`EXIT=0`**。补上后 ohos 的脚本覆盖率为 5/5。

**B4 — `~/.mimosa/security-scan-jobs/` 三方都没查**（GLM、MM-F 只查了 `security-scans/`）——补验见 §2.4 D4，结论不变（无 10-03 归档）。

**B5 — README 自身的标签清单漏项**——`README.md:58` 未列 `classroom-v0.1`（见 E1）。三方都只做了「README 与实测是否相符」的核对，没人核对 README 的**枚举完整性**。

**B6 — `node_modules` 是审校过程新产生的未跟踪-已忽略产物**——`git check-ignore -v ohos-tailscale/node_modules` → `ohos-tailscale/.gitignore:2:node_modules/`。它不脏工作树，但**改变了 ohos 的可复现态**（78/50/28 态已不可复现）。基线若要留档，必须写明「280/280 是安装后态，且安装态现已在盘」。

### 4.2 补验小结表

| 盲区 | 补验命令（我跑的） | 结果 |
|---|---|---|
| `NUL` 为何清不掉 | `git init` 临时仓复现 + `sha256sum` 对比 + `git check-ignore` | 保留名致 git 读不到该文件；索引清、磁盘未清 |
| 真实 IP 是否被清洗覆盖 | `git grep "156\.238" / "156, 238, 240, 81"` | 字符串形态已清、字节数组形态残留 2 处 |
| `typecheck:bridge` | `npm run typecheck:bridge` | exit 0（5/5 覆盖） |
| `security-scan-jobs` 归档 | `find ~/.mimosa/security-scan-jobs -type f` | 11 个 job，最新 2026-09-29 |
| README 标签枚举完整性 | `git tag \| sort` vs `README.md:58` | 12 个，README 漏 `classroom-v0.1` |
| node_modules 归属 | `git check-ignore -v ohos-tailscale/node_modules` | 被 `.gitignore:2` 忽略，不脏工作树 |

---

## 5. 确认的独家发现

### 5.1 成立，收进基线

| # | 独家发现 | 原发现方 | 我的复核 | 裁定 |
|---|---|---|---|---|
| U1 | `hw_student_eval.json` **不是纯 JSON**（stdout 全量捕获，含 `[PASS]` 前置行），下游 `json.load()` 会炸；另三份是纯 JSON | MM-F | `python -c "json.load(...)"` 逐份 → `dp/sm/zctlmcp → pure JSON OK`；`hw_student_eval.json → FAIL: JSONDecodeError Expecting value: line 1 column 2 (char 1)`；`head -c 300` 首行即 `[PASS] script_sequence_consistent: 10 步序列…` | **成立，A 级。** 写进基线「格式不齐」项 |
| U2 | `chenmai8` 六子仓文件数 **134 / 6242 / 233 / 161 / 19748 / 215** | MM-F | `find chenmai8/<d> -type f \| wc -l` 六次 → **六个数字逐位吻合** | **成立，A 级，精度罕见** |
| U3 | `xuexing-agent/%TEMP%joint_gate_out.txt` 是 Windows 重定向事故产物（405 B，未清理） | MM-F | `ls -la xuexing-agent/ \| grep -i TEMP` → `-rw-r--r-- 405 Oct 2 00:15 %TEMP%joint_gate_out.txt` | **成立，A 级**。与 U6 的 `NUL` 同类，应一并列为「已知可删残留」 |
| U4 | `qwen-arena2` **打包 e2e 不可执行**：`e2e_mock_packaged.py` exit 1，因 `dist/` 不在库 | GLM | `python tools/e2e_mock_packaged.py` → `[e2e-packaged] 被测产物不存在：…qw-arena2\dist\agent\agent.py（先运行 tools/package.py）`，`EXIT=1` | **成立，A 级。** 补齐了「G0-3 前半过、后半不可跑」的完整图景 |
| U5 | peidian 门禁 **不支持并发实跑**，首跑 m7 出现「任务已存在」×2，错峰后消失 | GLM | 未复现竞态本身，但**机制证实**：`src/m2_information/__init__.py:170 raise ValueError(f"任务已存在: {task_id}")` + `runtime/{m2_eval,m3_eval,m7_eval,runs}` 共享状态目录；且 `runtime/` 被 `.gitignore:2` 忽略，故并发不脏工作树但污染结果 | **成立，机制 A 级、并发现象 B 级。** 这条是**多 agent 盘点协作规约**的直接依据，必须保留 |
| U6 | `156.238.240.81`（hk-gateway 真实出口 IP）被硬编码进测试，违反该仓自订的「网络地址卫生」纪律；`git log -S` 溯源至 `360bc87` | MM-F | 见 §2.1：`git log --all -S "156, 238, 240, 81"` → 仅 `360bc87`；`D:\AGENTS.md` 机器表载明该 IP 为 hk-gateway 出口 | **成立且**需修正 MM-F 的定位——不是「测试里写错了一个 IP」，而是**公开清洗漏洗 + 真实 IP 残留**（见 B2）。MM-F 未意识到点分形态已被清掉 |
| U7 | `chenmai-bean-eye` gate_d4 = **FAIL (3/4)**，仅「中性名扫描零命中」PASS（扫 124 个跟踪文本文件 / 23 条模式） | SRV1 | `python scripts/gate_d4.py` → `GATE D4: FAIL (3/4 项未通过)` + `[PASS] ④ 中性名扫描零命中: 命中 0；扫描 124 个 git 跟踪文本文件…模式 23 条`，`EXIT=1` | **成立，A 级。** SRV1 独家，是 chenmai8 里唯一给出内部结构的 |
| U8 | `chenmai-playable-factory` `gate:m3` FAIL，第 4 门缺 `artifacts/diff/d4-autoplay-streams.json` | SRV1 | `ls artifacts/diff/` → `No such file or directory`；`npm run gate:m3` → `GATE-M3: FAIL（存在 FAIL 门项，墙钟 14.9s）`，`EXIT=1`；`[4/4] 中性名扫描 PASS（215 个入库文件 × 5 词，命中 0）` | **成立，A 级。** 关键：这是 chenmai8 里**唯一不因缺 `.venv` 而失败的**阻断项，补足了「环境未重建」这个统一解释的例外 |
| U9 | `chenmai-playable-ads` 无 `test` 脚本（`package.json` scripts 为空对象） | SRV1 | `json.load(package.json)['scripts']` → `[]` | **成立，A 级**（且我实测无 `npm run` 报错，直接读文件更确定） |
| U10 | `ohos-tailscale` `app/` 壳**从未编译**（无 DevEco 工具链） | SRV1 | 未跑（需 DevEco）。仅转述 `README.md` 已知问题 1 | **转述成立，证据 C 级。** 写进基线时须标「文档声称」，不可标 A |
| U11 | 归档的「学员产物」可复评（`deploy-pack/out/student_pack1` 对 oracle → exit 0），证明留档不是 oracle 自说自话 | MM-F | 未单独跑该条（我跑的是 speaker-mapping 的红/绿路）。`dp_student_eval.json` 留档与 MM-F 结果方向一致 | **方向可信，标 B（本方未复现）。** 有价值但需降级 |
| U12 | `.zcode/workflow-drafts/` 下三份 `盘点*.dwf.ts` 即三名盘点员的编排脚本 | GLM、MM-F | 按红线未读其内容 | **存在性成立**（`ls` 可见），**内容未核**。不入基线 |

### 5.2 不成立 / 需修正

| 原结论 | 出处 | 我的实测 | 处置 |
|---|---|---|---|
| 「标签 13 个」 | GLM、SRV1 | `git tag \| wc -l` → **12** | **不成立**。以 MM-F 的 12 为准（E1） |
| 「工作树 9 条符号链接脏项」 | GLM、MM-F | 逐条 `git ls-files -s` → **10 条全部 120000** | **数字不成立**（10）。定性成立 |
| 「5 D / 7 M / 6 ??」 | SRV1 | 实测 **5 D / 5 T / 7 ??** | **不成立**。总数 17 三方一致 |
| 「Mimosa 两次扫描 run」 | SRV1 | 根 2 + 仓内 2 = **4** | **不成立**（漏读 `afp-clone/.mimosa/`） |
| 「另 8 项未跟踪产物」 | MM-F（报告内部） | 实测 **7** 项 | **数字不成立**（自相矛盾，列举只有 7） |
| 「bridge 根因 = 测试期望值写错」单一口径 | MM-F | 见 §2.1 | **不完全**：缺陷判定正确，但**成因归于清洗漏洗**，且 MM-F 未发现第 125 行的第二处残留 |
| 「bridge 根因 = filter-repo 清洗副作用」单一口径 | GLM | 见 §2.1 | **不完全**：成因正确，但未察觉清洗**没清干净**（`PUBLIC-SCRUB-NOTE §3` 的承诺被证伪） |
| 「`git fetch` 失败 → 无法确认远端」 | GLM | `git ls-remote` 同样失败 | **成立**，且我补出「10:18 成功过、之后断」的时序（§4 补验） |

---

## 6. 给合并总文者的建议

### 6.1 结构（建议五段，对应本报告）

1. **可复现验收基线**（绿档）——按项目分档，每条带「命令 + exit + 数字 + 前置条件」。**前置条件必须与命令同框**（ohos 的 `npm install`、chenmai8 的 `.venv` 重建、video 的 77G 素材+金标）。
2. **当前为红 / 不可执行**（红档 + 灰档分开）——红 = 实测矛盾（peidian 门禁、ohos bridge）；灰 = 环境阻断、**不断言对错**（video、chenmai8 门禁数字）。
3. **证据链强度分级**——A（本次实测）/ B（本机留档未重跑）/ C（仅文档声称）。**建议额外加一档「A-否」：实测与声称矛盾**（peidian 233、ohos bridge 13/13），这样「打问号」不用塞进 C 档里偷渡。
4. **待办与残留**——`NUL`、`%TEMP%joint_gate_out.txt`、真实 IP 残留、spec_hash 待重登记。**每条带「为什么没修」（权限/保留名/需 owner 签字）**。
5. **协作规约**——**并发验收会互相污染**（peidian 实证）+ **保留名文件会破坏 git 工具链** + **符号链接在 Windows 上不可物化**。这三条是本工作区特有的、且都不是一次性的。

### 6.2 取舍

- **必须保留（不可压缩）**：
  - ① peidian 门禁的四口径表（233 / 182 / 184 / 51）与 spec_hash「全历史无匹配」的 git 考古结论——这是本次最有价值的负面发现；
  - ② ohos bridge 的**双根因合并表述** + 那张字节数组残留的 grep 证据；
  - ③ 并发污染实证（`src/m2_information/__init__.py:170`）；
  - ④ 「12-high 无底稿」+ Mimosa hook 活性改用**状态文件**举证（GLM 的「被拦截」不可复现，别写成 A 级）。
- **建议合并掉（避免同一事实被写三遍）**：三份报告各自的「环境版本」段（Python 3.12.10 / Node v22.23.2 / npm 10.9.8 / git 2.55.0 / ffmpeg 6.1.1，四方一致）合并成一处；`git remote -v` 输出同理。
- **建议降级**：所有 chenmai8 基线数字（8/8、4/4、122 tests、9/9、6/6）一律标 **C（09-30 声称，本次未复现）**；`ohos app/ 壳从未编译` 同理。
- **建议补入（三方共同的空白）**：`typecheck:bridge` exit 0；`.gitignore` 已忽略 `runtime/` 与 `node_modules`（所以并发与安装都不脏工作树——但前者污染结果）。

### 6.3 基线口径的硬规矩（照抄进总文）

1. **任何数字必须带命令与 exit code**，且**前置条件与命令同框**。`npm test` 280/280 与 78/50/28 是同一份代码的两个环境态，不写前置就是误导。
2. **「声称 vs 实测」必须成对出现**，并给出失败的具体机制（peidian = spec_hash；bridge = 清洗漏洗字节数组），不能只写「不一致」。
3. **「不在盘内」与「未运行」是两回事**：12-high 是前者（永久不可核验），chenmai8 各仓数字是后者（可复现，只是没做）。
4. **Windows 特有坑单列一节**：`core.symlinks=false` 的伪差、`NUL` 保留名、`%TEMP%` 重定向事故产物、`%TEMP%joint_gate_out.txt` / `package/NUL` 两个残留。接手者会**第一天**撞上这四条。
5. **推断与事实分层**：bundle 的「推送传输载体」角色、clean-room 的用途，都是**推断**（因远端不可达），必须与 A 级的「169fd8eb = HEAD 父提交」分开写。

### 6.4 仍未解决、需 owner 拍板的三件事

1. **peidian m1/m6 的 spec_hash 重登记**——需改测试资产（`tests/CHANGELOG.md` 已有回写先例），盘点员权限外。**在此之前 233/233 不得入基线。**
2. **bridge 断言修复 + 真实 IP 清除**——一次提交同时改 `disco-netcheck.test.ts:79,125`，并回写 `PUBLIC-SCRUB-NOTE.md` §3 的不实承诺。**在公开仓上，这比测试变绿更重要。**
3. **GitHub 推送通道**——hk-gateway 的 socks5 代理（`C:/Users/Administrator/.gitconfig`: `http.https://github.com.proxy=socks5h://100.64.0.3:7864`）**10:18 尚通、13:35 已断**；本地 10 ahead / 25 behind。R11 台账的「两波推送」**无任何机器可核验证据**，且 25-behind 的分叉与 10-01 的历史重写相容——**推送状态是本次盘点最大的未闭合项。**

---

*审校员 X-MMF（minimax/Minimax-M3.1-Flash-Preview）｜2026-10-03｜全程只读原始资产，未 commit / push / 改删任何既有文件；唯一写入为本报告 + 系统临时目录下 X-MMF-* 产物。仲裁期间执行的 `run_evals.py` / `npm test` / gate 脚本产生的落盘均在 `.gitignore` 覆盖范围内（`peidian-agent/.gitignore:2 runtime/`、`ohos-tailscale/.gitignore:2 node_modules/`），开工前后工作树脏项恒为 17。*
