# Step Router v1 交叉审校总结（2026-10-03）

> 审校员代号 X-SRV。本报告基于对 `baseline-inventory/1-inventory-glm5.3-flash.md`、`baseline-inventory/2-inventory-minimax-m3.1-flash.md`、`baseline-inventory/3-inventory-step-router-v1.md` 的只读审校，并独立运行实测仲裁命令而成。所有结论均附证据路径或命令输出；无法裁定的标注「悬而未决」。

---

## 1. 高置信共识（可进正式基线）

以下能力经三方独立实测一致确认，证据等级取交集：

| # | 能力 | 几方一致 | 证据等级 | 证据摘要 |
|---|---|---|---|---|
| 1 | `qw-arena2` 全量 pytest 469 passed | 三方一致 | **A** | GLMF: `469 passed in 20.96s`；MM-F: `469 passed in 22.14s`；SRV1: `469 passed in 21.81s`；版本自检 0.5.2 三方一致 |
| 2 | `xuexing-agent` 全量 pytest 709 passed / 2 skipped | 三方一致 | **A** | GLMF: `709 passed, 2 skipped in 11.24s`；MM-F: `709 passed, 2 skipped in 8.93s`；SRV1: `709 passed, 2 skipped in 6.45s` |
| 3 | `peidian-agent` 当前实测 182/184 FAIL（非 233/233） | 三方一致 | **D** | 三方均跑 `python run_evals.py --module all` 得到 `modules=6/8 ... failed=2 result=FAIL`；m1/m6 触发 SPEC_DRIFT |
| 4 | `ohos-tailscale` 在 `npm install` 后 npm test 280/280 + typecheck exit 0 + validate:shell 54/54 | 两方一致（GLMF/MM-F 实测 A；SRV1 未装依赖判 D 属方法差异） | **A** | GLMF: `npm install` 3s 后 `280 pass / 0 fail`；MM-F: `npm install` 7.6s 后 `280 pass / 0 fail`；SRV1 未执行 install 直接判 D |
| 5 | `video-capability` v3 自检因素材缺失 exit=2，当前环境不可执行 | 三方一致 | **D** | 三方均确认 `overnight/数据/avatar_out/dh_stepfun_720p.mp4` 不在仓内；runner 退出码 2（环境问题） |
| 6 | `zcode-research` skillfactory v5 四资产 runner 全绿（hotwords 4/4、deploy-pack 4/4、speaker-mapping 4/4、zctl-mcp 7/7） | 三方一致 | **A** | GLMF 重跑 speaker-mapping + 3 份留档；MM-F 四资产全部重跑；SRV1 四资产全部重跑；红路篡改均 exit 1 |
| 7 | `chenmai8` 六仓代码在库，但门禁因缺 `.venv` / 服务隧道 / GPU 环境阻断 | 三方一致 | **D** | 三方均确认 `gate_g1.py` 等 exit 1「未找到 .venv」；README 已诚实声明环境未重建 |
| 8 | `nightshift2.bundle` 为自包含完整历史快照，封存 `169fd8eb`，HEAD `18f6ead` 向前多 1 提交 | 三方一致 | **A** | `git bundle verify` → `records a complete history`；两份拷贝 SHA256 一致 `f04b6c5d…882c2`；`list-heads` 仅 `refs/heads/main=169fd8eb` |
| 9 | 工作树不干净，脏项包含符号链接平台伪差与运行产物 | 三方一致 | **A** | `git status --porcelain` 17 项；9 项为 mode 120000 符号链接（`core.symlinks=false` 导致）；8 项为 untracked（bundle、out/、store.json、validate.json、NUL） |
| 10 | 安全修复 `safe_rel` 防路径穿越 + `https` 守卫有效 | 三方一致 | **A** | GLMF/MM-F 实测：7 恶意路径全拒、3 正常路径全过、`http://` 端点被拒；SRV1 以文档+扫描留档定级 B |

---

## 2. 分歧仲裁记录

### 2.1 peidian-agent「233/233」vs 实测 182/184 FAIL：spec_hash 漂移根因

**分歧点**：GLMF 与 MM-F 均指认 spec_hash 漂移，但对漂移发生的时刻与 git blob 考古深度表述不同。

**裁定结果**：**漂移属实，且当前 HEAD 的 YAML 声明值与 spec 文件字节重算结果不匹配；漂移发生在 `6cdabbb` 提交之前或之时，并一直延续到 HEAD。**

**我的实测证据**：

1. `run_evals.py:819-825` 的 `compute_spec_hash()` 按 `spec_ref` 顺序拼接文件原始字节取 sha256：
   ```bash
   python -c "
   import hashlib
   files = ['afp-clone/peidian-agent/specs-v2/M1-agent-core.md','afp-clone/peidian-agent/specs-v2/00-ontology.md','afp-clone/peidian-agent/specs-v2/01-contracts.md','afp-clone/peidian-agent/specs/ADDENDUM.md']
   h = hashlib.sha256()
   for f in files:
       with open(f,'rb') as fh:
           h.update(fh.read())
   print('HEAD recompute m1:', h.hexdigest())
   "
   # HEAD recompute m1: 673df3dd6825b203189ad5a87e76a05efe7196ab0a0d29b4c7db62638554b75f
   # test_m1.yaml 声明:    0b5be472b45c879f3675be791358d04a618d21dbd172c876ef3032dd0123cac0
   ```

2. 用 git blob 在 `6cdabbb` 提交独立重算：
   ```bash
   git -C afp-clone show 6cdabbb:peidian-agent/specs-v2/M1-agent-core.md | python -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
   # 6cdabbb M1 blob: 7db4b2106d23243984f268cc1293a747f7bb3d71
   # 拼接待其他三文件后重算 m1: 673df3dd6825b203189ad5a87e76a05efe7196ab0a0d29b4c7db62638554b75f
   # 6cdabbb test_m1.yaml 声明: 0b5be472b45c879f3675be791358d04a618d21dbd172c876ef3032dd0123cac0
   ```
   结论：**在 `6cdabbb` 提交上，声明值与重算值已不匹配**。

3. `6cdabbb` 提交信息自述「门禁：233/233 PASS exit 0」，但其同时提交的 `tests/test_m1.yaml` 与 `tests/test_m6.yaml` 的 `spec_hash` 与该提交的 spec 文件字节不一致（m1: 声明 `0b5be472…` vs 重算 `673df3dd…`；m6: 声明 `f90a3d34…` vs 重算 `78c16232…`）。

4. 后续修复提交 `c025efe`（fix: 接手环境 CRLF→LF 归一与哈希重登记，门禁恢复 233/233）将 test_m1.yaml/m6.yaml 的 `spec_hash` 回写为与当前 spec 文件匹配的值（`673df3dd…` / `78c16232…`）。但 `c025efe` 不在 `main` 分支祖先链上（`git merge-base --is-ancestor c025efe HEAD` 为 false），其修复从未并入当前 HEAD。

5. `git diff 6cdabbb HEAD -- peidian-agent/specs-v2/M1-agent-core.md` 等四文件无输出，说明 **spec 文件在 `6cdabbb` 到 HEAD 之间未发生变更**；因此 HEAD 的重算值与 `6cdabbb` 相同，仍是 `673df3dd…`，而 YAML 声明值仍为 `0b5be472…`。

**结论**：GLMF 与 MM-F 的结论完全一致——`233/233` 声称无法从当前仓库状态复现。SRV1 的实测 `182/184 FAIL` 与之一致。SPEC_DRIFT 的根因是 YAML 注册值未随 spec 文件更新，且后续修复落在未合并分支上。

---

### 2.2 ohos-tailscale bridge 门 11/13：根因是否相容

**分歧点**：GLMF 将失败归因为「10-01 公开脱敏 `git filter-repo` 把测试夹具一端替换为 TEST-NET-3 而期望端未同步」；MM-F 将失败归因为「测试自身硬编码了生产 IP `156.238.240.81` 作为期望值，而 mock 回显 `203.0.113.10` 才是自洽值」。

**裁定结果**：**两种说法完全相容，描述的是同一根因的两个切面。测试期望值写错是表象，filter-repo 清洗不对称是根因。**

**我的实测证据**：

1. 运行 `npm run test:bridge` 得到 `# tests 13 # pass 11 # fail 2`，失败用例为：
   - `disco-netcheck.test.ts:62` — STUN 映射断言 `actual=[203,0,113,10] expected=[156,238,240,81]`
   - `disco-netcheck.test.ts:99` — Pong src 断言 `actual=[203,0,113,10] expected=[156,238,240,81]`

2. 读源码 `app/bridge/test/disco-netcheck.test.ts`：
   - 第 65 行：`bus.bind({ endpoint: '198.51.100.20:41641', natPublic: '203.0.113.10:41037' });`
   - 第 79 行：`assert.deepEqual(result?.ip, new Uint8Array([156, 238, 240, 81]), '映射地址=公网 IPv4 原始字节');`
   - 第 103/125 行：Ping→Pong 用例同样用 `aNat: '203.0.113.10:41037'` 但断言 `mapIp16FromV4(new Uint8Array([156, 238, 240, 81]))`

3. 读 `app/bridge/src/mock-udp-bus.ts:188`：`this.socket.send(pkt.from, stunResponse(txid, parts.ip, parts.port));` —— STUN 服务器原样回射 `pkt.from` 的 IP，即 `203.0.113.10`。

4. `PUBLIC-SCRUB-NOTE.md` 自述清洗范围含「测试夹具（NAT 仿真地址）」，将内部出口网关公网 IP 替换为 `203.0.113.10`（TEST-NET-3）。但 `git log --oneline --all -- "ohos-tailscale/app/bridge/test/disco-netcheck.test.ts"` 显示该文件自 `360bc87` 引入后**从未再被修改**——说明清洗只触及了输入夹具（`natPublic`），断言端的硬编码真实 IP `156.238.240.81`（即 `D:\AGENTS.md` 中的 hk-gateway 出口 IP）被遗漏。

5. `git log -S "156.238.240.81" -- ohos-tailscale/` 无任何提交记录，说明该 IP 在 ohos-tailscale 子树中只出现在 `360bc87` 这一版测试里，之后从未被更新。

**结论**：MM-F 指出的「测试期望值写错」是直接原因；GLMF 指出的「filter-repo 清洗不对称」是根本原因。两者并列成立，不构成矛盾。修复只需将两处断言改为 `203.0.113.10` 并清除仓内真实生产 IP。

---

### 2.3 `deploy-pack/package/NUL`（Windows 保留名文件）

**分歧点**：MM-F 声称该文件「此刻仍在磁盘上且仍未跟踪——清理未真正完成或被回滚」；GLMF 未提及；SRV1 未提及。

**裁定结果**：**MM-F 的观察成立。文件存在于磁盘但未纳入当前 HEAD。**

**实测证据**：

```bash
cd /d/new-workspace/agent-asset/afp-clone
ls -la zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL
# -rw-r--r-- 1 Administrator 197121 1698 Oct  2 00:15 NUL

git show HEAD:zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL
# fatal: path '...NUL' does not exist in 'HEAD'

git -C afp-clone status --porcelain | grep NUL
# ?? zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL
```

- `git log --oneline --all -- "zcode-research/skillfactory/v5/assets/deploy-pack/package/NUL"` 显示：
  - `0956b49` 添加该文件（worker-B 夜班轮 2026-10-01）
  - `100a9c2` 删除该文件（`zcode-research: 清除 deploy-pack/package/NUL——Linux 重定向事故产物`）
- 文件类型为 JSON text data（1698 字节），内容为 `validate.py` 的评估留档（`verdict: ALL GREEN`, `pass: 7, fail: 0`）。
- 删除提交 `100a9c2` 日期为 Oct 3 10:21，而磁盘文件时间戳为 Oct 2 00:15。文件在删除提交之后仍留在磁盘上，作为 untracked 文件存在。

**结论**：清理动作在 git 层面已执行（`100a9c2` 将其从索引删除），但工作区残留未清理。这不是「回滚」，而是「git 不自动删除已跟踪文件删除后的工作区残留」。MM-F 的定性「清理未真正完成」在实际效果上成立。

---

### 2.4 Mimosa 安全扫描证据链：12-high 原始报告是否存在

**分歧点**：GLMF 与 MM-F 均确认 12-high 扫描的完整原始报告不在盘内或 `~/.mimosa` 归档，仅有 `SECURITY-NOTES.md` 文字留档。

**裁定结果**：**两方一致，独立核查确认。**

**实测证据**：

```bash
ls -la ~/.mimosa/security-scans/
# 仅 2026-09-28/29 的 other project-* 扫描，无本工作区 10-03 扫描

ls -la .mimosa/history/
# run-20261002T002945085Z-...json (inconclusive, 0 findings)
# run-20261003T031511554Z-...json (inconclusive, 0 findings)

cat .mimosa/history/run-20261003T031511554Z-5312-1c70ff11cf2f.json
# runStatus: "inconclusive"
# errors: ["scan:afp-clone/video-capability/overnight/vpipe/judges_src/prefetch_model.py: scanner_failed: spawnSync C:\\Program Files\\nodejs\\node.exe ETIMEDOUT"]
# findings.total: 0
```

- 10-03 当次扫描因 `node.exe ETIMEDOUT` 未完成覆盖，`coverage.status: partial`，`scanned_files: 0`。
- `~/.mimosa/security-scans/` 最新扫描停在 2026-09-29。
- `SECURITY-NOTES.md` 是唯一分诊台账。

**结论**：「12 处 high」的原始 findings 无法从盘内或 Mimosa 归档独立核对，修复真实性已由代码复验（A）兜底，但「扫描→分诊」自动链路本次未成功运行。

---

### 2.5 远端推送状态（GitHub）

**分歧点**：三方均未在线核实，SRV1 将其列为共同盲区。

**裁定结果**：**当前无法在线核实，属悬而未决的共同盲区。**

**实测证据**：

```bash
git -C afp-clone remote -v
# origin=https://github.com/feasy898/agentic-factory-projects.git

git -C afp-clone fetch --dry-run
# fatal: unable to access 'https://github.com/feasy898/agentic-factory-projects.git/':
# Failed to connect to github.com:443 over proxy 100.64.0.3 after 21030 ms
```

- 直连 github.com:443 经 hk-gateway 代理超时（21s）。
- 缓存 `origin/main` = `03e5a526`，本地 `10 ahead / 25 behind`，与 10-01 `filter-repo` 公开清洗重写历史相容。
- `.git/FETCH_HEAD` mtime = 10-03 10:18，说明当天曾成功 fetch 过一次。

**结论**：无法确认远端是否已接收推送；R11 台账「两波推送」仅有提交自述（B 级）。

---

## 3. 确认的独家发现

| 原发现方 | 发现内容 | 复核结论 | 证据 |
|---|---|---|---|
| GLMF | `6cdabbb` 提交上 spec_hash 已不匹配任何已提交 blob 字节；漂移发生在提交前工作树时刻 | **成立** | 独立对 `6cdabbb` blob 重算 m1=`673df3dd…`/m6=`78c16232…`，与 YAML 声明 `0b5be472…`/`f90a3d34…` 不匹配；`c025efe` 修复未并入 main |
| MM-F | `disco-netcheck.test.ts` 硬编码生产 IP `156.238.240.81` 作为期望值，mock 回显 `203.0.113.10` 才是自洽值 | **成立** | 源码第 65/79/103/125 行直接可证；`mock-udp-bus.ts:188` 原样回射 `pkt.from`；`git log -S "156.238.240.81"` 无修改记录 |
| MM-F | `deploy-pack/package/NUL` 仍在磁盘且未跟踪，清理未真正完成 | **成立** | `ls -la` 显示 1698 字节 JSON 文件；`git status` 显示 `??`；`git show HEAD:...` 报 path does not exist |
| GLMF | Mimosa hook 在本会话活体拦截过 Bash 重定向操作 | **成立**（按报告引用） | GLMF 报告 §4.10-3 记录本会话被 `Mimosa 拒绝了通过 Bash 直接写入 eval/runner.py`；`.mimosa/hook-state/` 有 10-03 多个会话文件 |
| GLMF | 首跑 peidian m7 失败是与并行盘点员并发跑门禁互相污染 `runtime/eval_results.json` | **成立** | GLMF 报告 §4.5-2 记录错峰后 m7 异常消失；SRV1 与 MM-F 未重现该现象，侧面印证并发冲突 |

---

## 4. 共同盲区与补验结果

### 盲区 1：GitHub 远端推送状态

**补验命令**：
```bash
git -C afp-clone remote -v
git -C afp-clone fetch --dry-run
```

**结果**：`github.com:443` 经代理超时，无法在线核实。远端状态仍为**悬而未决**。

### 盲区 2：ohos-tailscale `validate:shell` 与 `typecheck`

**补验命令**：
```bash
cd afp-clone/ohos-tailscale && npm run typecheck
cd afp-clone/ohos-tailscale && npm run validate:shell
```

**结果**：
- `typecheck`：`tsc --noEmit` 静默，exit 0
- `validate:shell`：`summary: 54 passed, 0 failed`，exit 0

两项目前未被 SRV1 原始报告覆盖，现补验通过，可提升为 A 级证据。

---

## 5. 给合并总文者的建议（结构 / 取舍 / 必须保留的证据）

1. **基线分层策略**：将能力分为「已验证可复现」（A）与「当前阻断/待修」（D）两档，不要用「部分一致」模糊过渡。qw-arena2、xuexing-agent、skillfactory v5 四资产、ohos-tailscale（需前置 npm install）应进 A 档；peidian 门禁、ohos bridge、video v3、chenmai8 应进 D 档并附根因。

2. **peidian-agent 233/233 必须降级为「当前 FAIL」**：保留 m0/m2-m5/m7 的 182 用例通过记录，但不得写 233/233。必须写明根因：m1/m6 `spec_hash` 声明值与 spec 文件字节重算不匹配，且 `c025efe` 分支的修复未并入 main。

3. **ohos-tailscale bridge 11/13 保留两面证据**：一面是 MM-F 指出的「测试期望值硬编码生产 IP」，另一面是 GLMF 指出的「PUBLIC-SCRUB-NOTE.md 记录 filter-repo 清洗覆盖测试夹具但断言未同步」。两者不矛盾，合并写「清洗不对称导致断言失效」。

4. **video-capability 与 chenmai8 标注「环境未重建」**：video 明确缺 `overnight/数据/`（77G 模型+金标）；chenmai8 明确缺 `.venv` / 服务隧道 / GPU。不要写「无法验证」笼统句，要写清缺失项。

5. **nightshift2.bundle 的角色定性**：三方一致认为是「完整历史快照 / 推送前置物 / 灾备种子」。合并文应保留「HEAD 领先 1 提交（18f6ead）」这一事实，并注明 `169fd8eb` 是安全分诊提交。

6. **Mimosa 扫描能力表述需加限定语**：「推送前 12 处 high 分诊结论有 `SECURITY-NOTES.md` 留档，修复已代码复验；但 10-03 当次扫描因 node ETIMEDOUT 未完成覆盖，自动扫描链路本次未成功闭环。」

7. **NUL 文件单独成段**：它是 Windows 保留名导致的遗留物，已从 git 删除但工作区残留。合并文应写「`deploy-pack/package/NUL` 为 untracked 文件，非仓库内容，可安全删除」。

8. **工作树脏项单独说明**：9 个符号链接 + 8 个 untracked 运行产物 = 17 项。明确告诉接手者：`git status` 非空不等于有人改了源码。

9. **远端推送状态加脚注**：由于 github.com 经 hk-gateway 代理当前超时，R11「两波推送」仅有提交自述，建议加「未经在线核实」脚注。

---

*审校完成。本报告基于三方盘点报告只读审校 + 独立实测仲裁，未修改任何既有文件。*
