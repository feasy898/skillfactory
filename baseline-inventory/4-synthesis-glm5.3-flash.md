# GLM-5.3-Flash 交叉审校总结（2026-10-03）

> 交叉审校员：X-GLMF（GLM-5.3-Flash）。输入=三份相互独立的盘点报告（1-glm5.3-flash / 2-minimax-m3.1-flash / 3-step-router-v1），
> 全部分歧均以本会话亲手运行的命令与亲手读取的文件裁定；无法实测的如实标注。
> 红线遵守：未修改/删除任何既有文件，未 commit/push，未外发数据；新建文件仅本报告；临时输出在 `$TEMP/X-GLMF*` 与系统会话日志。
> 与三位盘点员（GLM-F / MM-F / SRV1）无任何上下文共享，报告亲缘不构成偏袒依据。

---

## 0. 审校方法与复核范围（我先做了什么）

- 通读三份报告并逐能力对齐（qw-arena2 / xuexing-agent / peidian-agent / ohos-tailscale / video-capability / zcode-research / chenmai8 / 安全链 / bundle / 协作痕迹）。
- 对全部 6 个候选仲裁点动手实测；另自行发现 2 个清单外分歧（标签数、工作树计数）与 1 个三方共同重大盲区（origin/main 缓存线）。
- 重跑关键门禁：peidian 全量门禁（2 次）、ohos test:bridge、qw-arena2 全量 pytest、xuexing 全量 pytest、speaker-mapping 评测绿路+红路、video v3 自检、chenmai8 三项子仓门禁、prefetch_model.py 安全函数行为。
- git 考古：spec_hash 全历史 blob 组合扫描（477 提交全部枚举）、bridge 测试文件 `git log -S` 双 IP 考古、NUL 文件全历史、reflog 全量、两线（HEAD vs origin/main）差异核对。

---

## 1. 高置信共识（可进正式基线）

以下每条注明几方一致 + 证据等级交集 + 我的复核结果。**「三方」= GLM-F / MM-F / SRV1。**

| # | 结论 | 几方一致 | 证据等级交集 | 我的复核（本次实测） |
|---|---|---|---|---|
| 1 | qw-arena2 全量 `python -m pytest tests -q` = **469 passed**（~18-22s） | **3/3 全部 A 级** | A | ✅ 复跑 `469 passed in 17.62s` |
| 2 | xuexing-agent 全量 `python -m pytest` = **709 passed, 2 skipped** | **3/3 全部 A** | A | ✅ 复跑 `709 passed, 2 skipped in 5.35s` |
| 3 | xuexing 三件套：validate_knowledge（189 kps/810 items/810 dual-verified）+ run_contract exit 0 + 凭据零入库 | 2/3（GLM-F、MM-F 均 A；SRV1 未跑） | A | 未重跑（两方独立 A 已足；无反证） |
| 4 | peidian 当前门禁 FAIL：`EVALS mode=all isolation=OK modules=6/8 pending=0 cases=182/184 failed=2 result=FAIL`，失败=m1/m6 SPEC_DRIFT | **3/3 全部 A**（SRV1 亦实跑同结果） | A | ✅ 复跑同结果，真实 exit=1；runtime/eval_results.json 逐模块核对：m0=49、m2=30、m3=30、m4=19、m5=27、m7=27 全过，m1/m6 各仅 1 条 SPEC_DRIFT 记录（30+21=51 例未执行） |
| 5 | peidian 副门真实绿：`ci_isolation.py` zero hits + ParkDSL `dsl/tests/run_tests.py` 15/15 | **3/3 全部 A** | A | 未重跑（三方独立 A，输出逐字一致） |
| 6 | ohos-tailscale：`npm install` 后 `npm test` = **280 pass / 0 fail**；typecheck exit 0；validate:shell 54/54 | 280 过=2/3 实测 A（GLM-F、MM-F）；SRV1 未装依赖得 50/78 并正确归因缺依赖 | A（带前置条件 npm install） | ✅ 复跑 `npm run test:bridge` 所在仓依赖在位；280 主数字未重复全量（两方独立 A + SRV1 的失败被 GLM-F 的无依赖对照实验（78 files/50 pass/28 fail 全 ERR_MODULE_NOT_FOUND）精确解释，闭环） |
| 7 | ohos bridge 门当前 **11/13**，2 个失败在 disco-netcheck.test.ts（STUN 映射回填 + disco Ping→Pong） | 2/3 实测 A（GLM-F、MM-F；SRV1 因依赖未跑） | A | ✅ 复跑 `# tests 13 # pass 11 # fail 2`；根因裁定见 §2-B |
| 8 | video-capability v3 自检在本工作区**不可执行**：exit 2「素材缺失 dh_stepfun_720p.mp4」，`overnight/数据` 从未入库，A–E 断言一条未跑 | **3/3**（GLM-F 记 D、MM-F 记 C 并明确不对 ALL PASS 表态、SRV1 记阻断） | A（实测 exit 2）+ C（对声称本身不作判断） | ✅ 复跑 `素材缺失: …（dh素材）`，exit=2 |
| 9 | skillfactory v5 四资产评测 runner 全绿：deploy-pack 4/4、speaker-mapping 4/4、hotwords 4/4（54 文件 100%）、zctl-mcp 7/7 | **3/3 全部 A** | A | ✅ 复跑 speaker-mapping 绿路 exit 0；与根目录留档 JSON 判定一致 |
| 10 | 评测红路 fail-closed：坏输入 → exit 1 | 2/3 A（GLM-F 篡改副本、MM-F 指向不存在目录；SRV1 未测红路） | A | ✅ 复跑 `runner.py /tmp/X-GLMF_definitely_missing oracle/out` → 真实 exit=1 |
| 11 | chenmai8 六子仓代码全量在库；各仓门禁因缺 `.venv` fail-closed 拒跑（feeding-arm `gate_g1.py` 报「未找到 .venv 解释器」） | **3/3**（gate_g1 三方全跑） | A（拒跑行为）/ C（09-30 基线数字，三方一致未复现） | 未重跑 gate_g1（三方输出逐字一致） |
| 12 | nightshift2.bundle：双份 SHA256 一致（`f04b6c5d…882c2`）、`git bundle verify` complete history、唯一 head `refs/heads/main=169fd8eb`=HEAD 的父提交（HEAD 领先 1 个提交） | **3/3** | A | ✅ `sha256sum` 两份均 `f04b6c5db190d0129dbce49db0dc0287dafbae0e45dae0ab5c63df29fb7882c2` |
| 13 | 仓库骨架：HEAD=`18f6ead`（R11 收口）、477 commits、工作树 17 行不干净但无源码内容改动 | **3/3** | A | ✅ 逐项复核（构成精化见 §2-E） |
| 14 | prefetch_model.py 安全修复（safe_rel 防穿越 + https 守卫）真实有效 | 2/3 A（GLM-F 7恶/3善、MM-F 6恶/2善；SRV1 B 仅文档） | A | ✅ 复跑：7 恶意路径（含 MM-F 未测的 `x/../y`）全拒、3 正常全过；https 守卫代码在 `prefetch_model.py:44-45`（运行时 http 拒绝未重测，GLM-F 已 A） |
| 15 | 「12 处 high」分诊的**原始扫描报告不在盘内**，机器可核证据链断裂；工作区全部 mimosa run `run_status=inconclusive`，10-03 03:15Z 那次对 prefetch_model.py `scanner_failed: node ETIMEDOUT` | 2/3（GLM-F、MM-F 深查；SRV1 引用 B） | B | ✅ 加查 `~/.mimosa/security-scans/`（7 项目目录）无 10-02 后任何文件；修复后复扫证据见 §4-2（新发现，部分弥补） |
| 16 | 总判断：**评测方法论真实可复现（最值钱资产），README「全绿」基调偏乐观；7 项目中 4 个当前可全绿，peidian 本地线门禁红、video/chenmai8 需重建环境** | **3/3**（各自独立得出同构结论） | A+B | 采纳 |

---

## 2. 分歧仲裁记录（分歧 | 裁定 | 我的实测证据）

### A. peidian「233/233」：数字口径 + 根因 + **远端线已修复（三方共同盲区，重大改写）**

**分歧**：GLM-F/MM-F 实测 182/184 FAIL；SRV1 写作「184 cases / 2 failed」并解读为「当前 HEAD 仅 184 用例」「README 可能基于旧版 runner 或不同模块集」。spec_hash 根因 GLM-F 与 MM-F 各做了不同深度的考古。

**裁定**：
1. **口径**：SRV1 错，MM-F 对。233 = m0–m7 八个活跃 YAML 套件用例总数；184 = 182 实跑通过 + 2 条模块级 SPEC_DRIFT 记录；51 例（m1=30、m6=21）从未执行。
   - 我的数据：`python` 逐文件正则计数 = m0:49、m1:30、m2:30、m3:30、m4:19、m5:27、m6:21、m7:27，**合计 233**；m8:7、m9:8 为后加套件不在活跃集；runtime/eval_results.json 模块级合计 = 184 项、182 过。
2. **根因**：GLM-F 与 MM-F 的考古**结论一致且我逐位复核成立**。m1 声明 `0b5be472…` vs 我重算：`6cdabbb^`=7708b52e…、`6cdabbb`=HEAD=工作树=673df3dd…、LF→CRLF 变换=516babd2…，均不匹配；全历史扫描：4 个 spec 文件在全部 477 提交中仅 2 种真实共存字节组合、**声明值不匹配任何已提交状态**。6cdabbb（09-29 20:22）提交信息自述「spec_hash 重算回写 + 门禁 233/233 PASS（本轮实跑）」——与其自己提交的字节自相矛盾。
   - **最终根因（本会话新证据，超出两方）**：缓存 origin/main 上的提交 `c025efe`（2026-10-02 01:56，作者 `agent:windev-01[bot]`，即另一台机器）提交信息写明：「**core.autocrlf=true 致全树 CRLF、登记口径=CRLF 字节**：LF 归一 338 文件……test_m1/test_m6 spec_hash 按 01 v2 §6 重登记……M1-agent-core.md 冻结后内容漂移登记为 R-2」。这解释了为何单纯 CRLF 变换也对不上（内容也漂移过）。GLM-F 的「注册漂移发生在提交前的工作树时刻」推断被证实且具体化。
3. **重大改写（三方盲区）**：`git show c025efe -- peidian-agent/tests/test_m1.yaml` 显示声明值被改为 `673df3dd…`——**正是我从已提交字节重算出的值**；我在 origin/main 尖端重算：m1 declared==recomputed（673df3dd）、m6 declared==recomputed（78c16232），**双双 MATCH=True**。即：**「233/233」在 origin/main 线上哈希自洽、按 c025efe 自述门禁恢复全绿（该修复完整存在于本地对象库，离线可验；本会话未联网验证门禁在远端线的实跑输出）。**
   - 结论修正：三份报告共同的「233/233 无法从仓库状态复现」**只对本地 main 线成立**。准确定性应为：「本地 main 落后且分叉于 origin/main，缺 c025efe 的重登记修复；合并远端线（或 cherry-pick 其 tests/test_m1.yaml、test_m6.yaml 重登记 + .gitattributes）即恢复绿门」。「带病数字」的说法过重——该数字在远端线上是站得住的。
4. **附带修正 GLM-F 一处推断**：GLM-F 称「缓存 origin/main 与本地 10 ahead/25 behind 的分叉与 10-01 filter-repo 公开清洗重写历史相容」。我逐条列出 25 个 origin 独有提交：日期全部为 10-02/10-03（bean-eye 批处理、硬件交接 docs、peidian 修复、arena 骨架），**是另一台机器在克隆之后的并行工作，与历史重写无关**。且 reflog `0ab1c25` 显示 afp-clone 本身是 2026-10-01 20:37:43 从 GitHub 克隆的——本地线从克隆时刻起就与远端各自演进。

### B. ohos bridge 11/13 的两个失败：根因两说 → **两说兼容且互补，因果链已闭合**

**分歧**：GLM-F 根因=「10-01 公开脱敏 filter-repo 把测试夹具一端替换、另一端未同步（脱敏副作用而非代码劣化）」；MM-F 根因=「测试自身期望值写死错误，actual=回显自洽，与平台无关，Linux 上同样失败」+ 独家安全卫生发现（真实生产 IP 硬编码进公开仓测试）。

**裁定**：**机制上 MM-F 对，因果上 GLM-F 对，二者不矛盾；「测试曾自洽、脱敏断链」的完整证据链如下。**
1. 现文件实读（`app/bridge/test/disco-netcheck.test.ts`）：夹具字符串 `natPublic: '203.0.113.10:41037'`（:65、:103）；断言是**字节数组** `new Uint8Array([156, 238, 240, 81])`（:79、:125）。`app/bridge/src/mock-udp-bus.ts:190` 实读：`this.socket.send(pkt.from, stunResponse(txid, parts.ip, parts.port))`——MockStunServer 回显 `pkt.from`，故 actual=203.0.113.10 自洽、断言过时（MM-F 机制完全成立）。
2. 时间线证据：
   - `PUBLIC-SCRUB-NOTE.md` §2 明列替换项「内部出口网关的公网 IP → `203.0.113.10`（TEST-NET-3）｜出现处：……**测试夹具（NAT 仿真地址）**」；§3「测试夹具中的地址已随上表一并示例化（`app/bridge/test/`、`packages/*/test/`）」。
   - 仓内 `ohos-tailscale/worklog.md:23`：worker-A 创建该测试当时实跑记录「node --test app/bridge/test/*.test.ts → **13 pass/0 fail EXIT=0**」——**测试编写时自洽通过**，不是「从来就写错」。
   - `git log --all -S '156.238.240.81'`：字符串在本地全部引用中**零出现**（本地历史=10-01 20:37 自 GitHub 克隆的重写后历史）；`git log -S '156, 238, 240, 81'` 与 `-S '203.0.113.10'`：均命中文件诞生提交 `360bc87`（10-01 04:38）后未再变。即：重写后历史里字符串形态只以脱敏值存在，字节数组形态（文本替换不可达）原样保留。
   - 注意边界：**脱敏前（含 `156.238.240.81` 字符串的原始 blob）不在本盘任何对象中**（克隆发生在重写后），故「filter-repo 精确改写了哪些行」无法从本盘字节级直证；以上是「worklog 实跑 13/13 记录 + NOTE 自述清洗范围 + 现存字节形态」三源互洽的因果重建，置信度高但非字节级铁证。
3. **MM-F 的安全卫生独家发现确认成立**：`156.238.240.81`（= 本机 hk-gateway 的真实生产出口 IP，见 `D:\AGENTS.md` 机器表）以字节数组形态残留在公开仓测试文件两处——**脱敏的既定目标（清除出口网关 IP）对字节表示形态未达成**。采纳 MM-F 的修复建议（断言改 `203.0.113.10` 对应字节 `[203, 0, 113, 10]`），可同时修复测试与完成脱敏。
4. 附：MM-F 称失败为「第 8、10 个用例」——这是 test:bridge 13 用例的全局编号（bridge.test.ts 7 个 + disco-netcheck 6 个，#8=STUN 全链路、#10=Ping→Pong），与 GLM-F 描述的两个失败同指，非实质分歧。

### C. deploy-pack/package/NUL：**MM-F 独家发现成立，且比他说的更严重**

**分歧**：GLM-F 引 reflog「10:21 清 NUL」暗示已清理；MM-F 称「声称已清除但该文件此刻仍在磁盘且未跟踪——清理未真正完成」。

**裁定**：MM-F 对。我的证据：
- 磁盘：`ls -la …/deploy-pack/package/` → `NUL`，1698 字节，mtime 10-02 00:15，且 `git status --porcelain` 中为 `??`（untracked）。
- git 侧：`git log --all -- …/package/NUL` 仅两笔——`0956b49`（10-01 03:42，入库）与 `100a9c2`（10-03 10:21，本地线删除，54 行）；**`git ls-tree origin/main -- …/package/` 显示 NUL 在远端线仍被跟踪**（blob 25ab5fc）。即：Windows 兼容清理提交只存在于本地线、未推送/未合并，且磁盘文件本体未删。origin 独有提交 `b228a92`/`8a4a55b` 还记载了「NUL 提交管线」（他机经专门管线提交 Windows 保留名文件）——解释了它如何进的库。任何从 GitHub 新克隆仍会拿到该损坏路径。

### D. ohos bridge 之外的门禁数字分歧（补充口径核对）

GLM-F「无依赖 78 tests/50 pass/28 fail」与 SRV1「tests 78, pass 50, fail 28」为**同一数字**（78=test 文件数，280=用例数），非分歧。三方对「28 个失败全因缺 `@ohos-tailscale/common`/`tweetnacl` 依赖」口径一致。

### E. 工作树脏项构成与计数（清单外分歧，我方发现）

**分歧**：GLM-F「9 条 D/T symlink 伪差异」；MM-F「9 个已跟踪脏条目全部 mode 120000」；SRV1「5 个删除（D）、7 个修改（M）、6 个未跟踪」。

**裁定**：实质结论从 GLM-F/MM-F（符号链接平台伪差、非源码改动），计数两家都差 1，SRV1 构成描述错误。我的精确数据（`git status --porcelain -z` + `git ls-files -s -z` 全量 -z 比对，规避引号/转义陷阱）：
- **17 行 = 10 条跟踪脏项（6 D + 4 T，10/10 全部 mode `120000` 符号链接，`core.symlinks=false`）+ 7 条 untracked**（bundle、NUL、deploy-pack out/ 与 oracle validate.json、hotwords out/ 与 store.json、speaker-mapping out/）。
- 结论：基线检查脚本不应把 `git status` 非空判为「有人改了代码」（采纳 MM-F 建议，数字修正为 10）。

### F. 标签数 12 vs 13（清单外分歧，我方发现）

GLM-F「13 个标签」、SRV1「13 个标签」、MM-F「12 个」。裁定：**`git tag | wc -l` = 12**（chengmai-feeding-arm/×8 + playable-factory/clean-room-v0 + classroom-v0.1 + xuexing-agent/×2）。GLM-F 自己的列举只列了 7 个 feeding-arm 标签——少数了 1 个又把总数写成 13，属笔误级；MM-F 对。

### G. nightshift2.bundle 角色定性：「符号链接平台伪差说 vs 其他」与「传输载体说」

**裁定**：候选仲裁点里的「符号链接平台伪差」实为工作树脏项的解释（见 §2-E），与 bundle 角色无关。bundle 角色三份报告无真分歧：GLM-F「推送前置物兼离线传输载体/灾备种子，非增量备份、不含 R11 最后一笔」、MM-F「推送传输载体」、SRV1「夜班工作流跨机传输/备份载体（git log --grep=nightshift 命中『本地 bundle 覆盖』纪律条目）」。我复核：SHA256 双份一致 ✓、（GLM-F 报告内）`list-heads`/`verify` 与 `169fd8eb ∈ HEAD 祖先` 三方一致。三方定性均为推断（B 级），**合并稿建议统一表述为「10-03 10:49-10:51 落盘的自包含完整历史快照（头=169fd8eb，恰为安全分诊提交），系推送前置物/离线传输载体，非增量备份；推送本体是否到达 GitHub 在线不可验」**。GLM-F 的「与 filter-repo 重写历史相容」分叉解释已被 §2-A-4 修正——分叉真实原因是多机并行工作。

### H. 悬而未决（无法仲裁）

1. **GitHub 远端当前在线状态/「两波推送」是否落库**：`git ls-remote origin` 实测失败（`Failed to connect to github.com:443 over proxy 100.64.0.3 after 21018 ms`，与 GLM-F 的 fetch 失败同模式、两时间点独立复现）。在线侧维持不可判；离线侧可判的已判尽（§2-A）。
2. **12 处 high 的原始 findings 清单**：见 §4-2。SECURITY-NOTES.md 文字台账 + 10:45 修复后干净复扫记录在案，但「12 处」的机器原始报告在盘内不存在，无法独立核对（GLM-F/MM-F 同判，我加深后仍维持）。
3. peidian 首跑 m7「任务已存在」×2 的并发污染（GLM-F 独家教训）：当时条件不可重放；机制合理（runtime/eval_results.json 单一输出位 + 其自述观察到两次读取内容不同），本次复跑无复现。维持「高可信教训、A 级证据不可得」。
4. SRV1 对 gov-ai-gateway（无 gate_final 入口脚本）与 drama-dub（需 GPU+推理服务）的「未验证」判断：未复核（环境重建远超单命令时限），维持 SRV1 原判「未验证」。

---

## 3. 确认的独家发现（原发现方 | 复核结论）

| 原发现方 | 独家发现 | 复核结论 | 我的证据 |
|---|---|---|---|
| GLM-F | Mimosa hook 现行活跃（活体执法，曾拦截其 Bash 重定向） | ✅ **成立（当场复现）** | 我以同型命令（Bash 向 `$TEMP/X-GLMF/runner_copy.py` 追加字节）被 PreToolUse 拦截：「Mimosa 拒绝了通过 Bash 直接写入 …runner_copy.py、…eval/runner.py 的操作」；`.mimosa/hook-state/` mtime 实时更新（13:48-13:52） |
| GLM-F | spec_hash 漂移发生在提交前工作树时刻（blob 级考古） | ✅ 成立并具体化 | 我逐位复现其全部数字 + 全历史扫描 + c025efe 提交信息给出「CRLF 登记口径」终审根因（§2-A） |
| MM-F | `hw_student_eval.json` 非纯 JSON（stdout 全量捕获，`json.load` 会炸） | ✅ 成立 | `python json.load`：hw `PARSE_FAIL: Expecting value: line 1 column 2`；dp/sm/zctlmcp 三份 `PURE_JSON_OK` |
| MM-F | xuexing-agent 根目录残留 `%TEMP%joint_gate_out.txt`（重定向事故产物） | ✅ 成立 | `ls -a xuexing-agent/` 首行即 `%TEMP%joint_gate_out.txt` |
| MM-F | 真实生产出口 IP 156.238.240.81 以字节数组硬编码在公开仓测试 | ✅ 成立（且为脱敏缺口） | 测试 ：79/:125 两处字节数组；`git log --all -S` 字符串零出现；IP 归属见 `D:\AGENTS.md`（hk-gateway） |
| MM-F | NUL 文件仍在磁盘、清理未真正完成 | ✅ 成立（更严重：远端线仍跟踪） | §2-C |
| MM-F | skillfactory 评测「评的是产物一致性不是源码单测」的口径提示 | ✅ 采纳（口径正确） | runner 以 out/ 对 oracle/out 比对（与三方实测行为一致） |
| SRV1 | chenmai-bean-eye `gate_d4.py` = FAIL 3/4（缺 .venv），中性名扫描 PASS（命中 0） | ✅ 成立 | 我复跑：①②③全因 `未找到 .venv 解释器` 跳过/失败，④ `中性名扫描零命中: 命中 0；扫描 124 个 git 跟踪文本文件…模式 23 条` |
| SRV1 | chenmai-playable-factory `npm run gate:m3` = FAIL，第 4 门差分证据缺失 | ✅ 成立 | 我复跑 `GATE-M3: FAIL（存在 FAIL 门项，墙钟 14.0s）`；`artifacts/diff/` 目录不存在（`d4-autoplay-streams.json` 无处） |
| SRV1 | chenmai-playable-ads 无 `test` 脚本（`npm run test` 报 Missing script） | ✅ 成立 | 我复现 npm error |
| GLM-F | bundle 双份逐字节一致 | ✅ 复核 | SHA256 相同（§1-12） |
| GLM-F | 三盘点员并发跑同一门禁会互踩 | ⚠️ 机制成立、当次事件不可重放 | §2-H-3 |

**未被确认/需降级的独家表述**：
- GLM-F「10 ahead/25 behind 与 filter-repo 重写相容」→ **修正**（§2-A-4，分叉=多机并行，非重写残留）。
- GLM-F、SRV1 的「13 个标签」→ 错，实为 12（§2-F）。
- GLM-F/MM-F 的「9 条 symlink 脏项」→ 实为 10 条（§2-E）。
- SRV1「当前 HEAD 仅 184 用例」→ 错，YAML 含 233 例（§2-A-1）。

---

## 4. 共同盲区与补验结果

### 4-1.【重大】origin/main 缓存线（三方全部漏看）——已补验，改写 peidian 结论
三份报告都只盯着本地 main，无人检查 `origin/main` 缓存引用里那 25 个提交的内容。我补验（全部离线，用本地已有对象）：
- `git log --oneline HEAD..origin/main`：25 个提交，全部 10-02/10-03 日期（bean-eye 批 1/批 2、硬件攻坚交接、peidian 修复、arena 骨架、docs）。
- `git show c025efe`：peidian spec_hash 重登记（0b5be472→673df3dd），提交信息自述根因（CRLF 登记口径）与「门禁恢复 233/233 PASS exit 0」。
- 我在 origin/main 尖端重算 m1/m6 拼接 spec sha256：**declared == recomputed，双 MATCH=True**。
- `git diff HEAD origin/main --stat -- ohos-tailscale` 为空：bridge 11/13 在两线上无差别（远端线无修复）。
- 影响：peidian 修复路径从「重算回写 spec_hash（改测试资产）」具体化为「合并 origin/main / cherry-pick c025efe 的登记变更」；「233/233 声称不可信」降级为「本地线过期」。
- 附带发现：reflog `0ab1c25`（10-01 20:37:43 `clone: from https://github.com/feasy898/agentic-factory-projects.git`）——**afp-clone 本身是脱敏重写后自 GitHub 克隆的**，这为 §2-B 的时间线定界（盘内无脱敏前对象）提供了根据。

### 4-2. 12-high 扫描原始证据链——已补验，结论细化（原始清单仍缺失）
- `ls ~/.mimosa/security-scans/`：7 个 project-* 目录，`find -newermt 2026-10-02` 零命中——10-03 扫描未走深度扫描归档通道（与 GLM-F/MM-F 一致）。
- `.mimosa/reports/task-review-…-20261003T031511554Z….json` 实读：diff 面恰为修复行（`prefetch_model.py` ranges 43-45=https 守卫、53-67=safe_rel、170、207-208），但 `errors[0].reason=scanner_failed: spawnSync node.exe ETIMEDOUT`、coverage=partial。
- **新发现**：`.mimosa/hook-status/sess_cad6cf65-…-16331c4390.json`（recordedAt 2026-10-03T02:45:35Z=本地 10:45，即 169fd8e 安全分诊提交前 3 分钟）：`event=PostToolUse, toolName=Edit, file=…/prefetch_model.py, outcome=clear, coverage=complete, findingCount=0`——**修复提交前，hook 对该文件完成过一次全覆盖扫描且零 findings**。
- 终判：修复动作有机器复扫背书（新证据）；但「12 处」的原始 findings 报告在盘内任何位置都不存在，该清单仍只有 SECURITY-NOTES.md 文字台账。

### 4-3. GitHub 在线状态——已补验，在线侧确认不可达
`git ls-remote origin` → 21s 代理超时（§2-H-1）。三方盲区中「可补验」的部分已补：结论=当前网络条件下在线核实不可行，远端状态只能钉死在最后成功 fetch（10-03 10:18，FETCH_HEAD mtime）时点。

### 4-4. 其他三方共同未覆盖的小项（列出不补验，供合并稿注记）
- qw-arena2 `tools/local_eval.py`（需 `DASHSCOPE_API_KEY`，SRV1 已注明不可跑）；`e2e_mock_packaged.py` 需先 `package.py` 构建 dist（GLM-F 已记）。
- ohos `app/` ArkTS 壳从未真编译（worklog 自述 GPU 机不可编译，huawei 登录墙）——三方均未触碰，无新证据。
- `.zcode/workflow-runs/` 内 10-02 46KB 生产 run 的脚本内容（本次按红线未读其他审校/盘点工作流正文）。

---

## 5. 给合并总文者的建议

**结构**：
1. 以「能力 × 当前可用状态」四档矩阵收拢：①开箱全绿（qw-arena2、xuexing-agent、ohos 主门[需 npm install]、skillfactory 评测体系）②带已知缺陷可用（peidian 副门+本地线门禁红但远端线有修复、ohos bridge 11/13）③需重建环境（video-capability、chenmai8 六仓）④文档级（chenmai8 09-30 基线数字、12-high 原始清单、GitHub 在线状态）。
2. peidian 段必须按 §2-A 重写：不再是「233/233 不成立」，而是「本地线 182/184 FAIL（SPEC_DRIFT，51 例未执行）+ 远端线 c025efe 已修复（离线可验哈希自洽）+ 根因=CRLF 登记口径（有提交自述铁证）」。
3. ohos bridge 段必须同时写机制（MM-F）与因果（GLM-F + worklog 13/13 记录 + NOTE §2），并把「真实生产 IP 残留」作为独立安全卫生项列出（修复断言=完成脱敏，一石二鸟）。

**取舍**：
- 采纳 §1 表 16 条共识为基线主体，证据等级按交集标注。
- 三份报告的计数类小错（13→12 标签、9→10 symlink 脏项、SRV1 的 184 用例口径）以本报告实测数为准，不必保留错误原话。
- GLM-F 的并发互踩教训值得保留为「多 agent 协作纪律」条目；MM-F 的「hw JSON 非纯 JSON」保留为资产卫生条目。

**必须保留的证据（合并稿不可丢）**：
- peidian：`c025efe` 的 diff 关键行（`-0b5be472… +673df3dd…`）与其提交信息（CRLF 根因自述）；我在 origin/main 尖端的双 MATCH=True 重算；182/184 门禁原样输出行。
- ohos：`disco-netcheck.test.ts:79/:125` 字节数组 vs `:65/:103` 夹具字符串的并存；`mock-udp-bus.ts:190` 回显；`worklog.md:23` 的「13 pass/0 fail EXIT=0」；`PUBLIC-SCRUB-NOTE.md` §2 清洗范围行。
- 安全：hook-status 10:45 `outcome=clear, coverage=complete, findingCount=0`；03:15Z task-review 的 `scanner_failed: node ETIMEDOUT`（diff 面恰为修复行）。
- NUL：`git ls-tree origin/main` 仍含 NUL blob 25ab5fc + 磁盘 `ls -la`（1698B, untracked）。
- 工作树：17 = 10 跟踪（6D+4T，全 120000）+ 7 untracked 的精确构成。
- 网络两次独立代理超时（GLM-F fetch + 本报告 ls-remote）——远端在线核实的不可行性本身是结论。

**基线书写红线（合并稿措辞建议）**：
- ohos 280/280 必须带前置「npm install」；peidian 门禁数字必须注明「本地 main @18f6ead」；video/chenmai8 一律「环境未重建，未验证」，不写「失败」也不写「通过」。

---

*X-GLMF（GLM-5.3-Flash）交叉审校完成于 2026-10-03。全部仲裁命令与输出已在正文各节内联；未跑成的检查均已如实标注（gov-gateway/drama-dub 门禁、http 端点运行时拒绝、280 全量第三次复跑、并发事件重放）。*
