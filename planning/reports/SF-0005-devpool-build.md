# SF-0005 交付报告 · WS4-A dev 题池构建（首发三型 8 题）

- 执行：worker-glm-bd · 2026-10-04 07:36–08:4x · 0 次模型调用（卡面红线守住）
- 写入面：`evalkit/packs/ws4-dev/`（8 包）、`evalkit/harness/ws4_gen.py / ws4_judge.py / ws4_d3_gate.py / ws4_pool_state.py`、`bench/devpool-r1/`；既有文件改动恰两处（卡面授权）：`evaluators/aggregate.py`（版本默认 v6-mvp-0.2→**v6-mvp-0.3**）+ `evalkit/CHANGELOG.md`（v6-mvp-0.3 增量条目）。afp-clone 差分为空（GE-1）。
- 结论：**8 题 status=built、READY=0 起步、签署台账全 WAITING_OWNER（ofc 3 题 D3 另 WAITING_WS3）**——这是卡面定义的合法交付形态；卡 B（SF-0006）开工门 GP-1 需 owner D1 签署 ≥5 题（mm2+hot3 兜底即满足）。

## 1. 八题清单

| id | 线 | 题型 | origin | 种子 | 输入 | L2 检查数 | L1 dist 桥 |
|---|---|---|---|---|---|---|---|
| mm-01 | 会议纪要 | positive | self-built | 4201 | transcript.txt（带时间戳） | 8 | meeting-minutes-skill |
| mm-02 | 会议纪要 | near-negative | **public-variant** | 4202 | transcript.txt（无时间戳+同名说话人+无期限待办） | 9 | meeting-minutes-skill |
| hot-01 | 内容结构 | positive | **public-variant** | 4203 | input.json（dy 口播稿） | 8 | hot-templates-skill |
| hot-02 | 内容结构 | positive | self-built | 4204 | input.json（xhs 图文笔记） | 8 | hot-templates-skill |
| hot-03 | 内容结构 | near-negative | self-built | 4205 | input.json（wx 公众号，2 卖点对 3 槽） | 8 | hot-templates-skill |
| ofc-01 | 办公文书 | positive | self-built | 4206 | input.json（周报，全字段有值） | 7 | office-templates-skill |
| ofc-02 | 办公文书 | adversarial | **public-variant** | 4207 | input.json（请示函，2 必填缺失+《》（）保真陷阱） | 8 | office-templates-skill |
| ofc-03 | 办公文书 | adversarial | self-built | 4208 | input.json（会议通知，缺字段+全角边界值陷阱） | 8 | office-templates-skill |

- 三层用例配比落位：**positive 4**（mm-01/hot-01/hot-02/ofc-01）/ **near-negative 2**（mm-02/hot-03）/ **adversarial 2**（ofc-02/ofc-03）——卡面 4/2/2 恰好。
- 三公开变体题 source_ref（GD-3，O-9 纪律：脱敏+nonce 改写+零原文复制）：
  - mm-02 → 《党政机关公文处理工作条例》（中办发〔2012〕14号，公开发布）「纪要」文种定义 + GB/T 9704-2012（openstd.samr.gov.cn 条目号）；
  - hot-01 → 抖音创作者服务中心公开规范页（creator.douyin.com）+《广告法》第九条（公开法条）；
  - ofc-02 → GB/T 9704-2012《党政机关公文格式》（openstd.samr.gov.cn，公开国标）——四条版式判据源自公开国标通行条款。
- 与 holdout 池零接触（卡面 T-O7 口径）：本卡全程未读任何 holdout 面；8 题全部自建/公开规范派生。

## 2. 装置结构（双层判分器，坑①②③逐条对冲）

- **L2 主判**（`harness/ws4_judge.py`，每包 `checks/run_check.py` 薄包装声明检查名契约）：检查名一律 `task_outcome_*`（GA-3/GA-4 全绿：checks/ 目录零 `reference_` 字样）；**判定基准=当前输入**（`--input-basis`，默认包内 fixtures）——nonce 交叉天然红（AR-2 原则）。
- **L1 子轨**（同文件 `l1_bridge`）：import dist 原版 runner 透传（零改动铁律），**显式传参照根**（`dist/<pkg>/reference/out`，坑①：绝不依赖 0 参默认的 oracle\out 死路径）；每包 `runner_contract.json` 落四字段（GC-1 全过：8/8 四字段齐+ref_root 存在+selfcheck_exit=0+redpath_exit=1）；结果只登记 record.l1 不判分（GC-2：controlled=true，崩溃才算装置 FAIL）。坑②（检查名 reference_* 冲突）由 L2 全新写 task_outcome_* 断言消解。
- **生成器**（`harness/ws4_gen.py`，每包 `gen_oracle.py` 薄包装）：nonce 化实例（人名/部门/项目/金额/日期/主题全 nonce 池派生）+ 独立参照实现产 oracle（docx 经 canonical zip 归一——固定时间戳/排序/压缩，否则 python-docx zip 头破坏逐字节复现）。
- **D3 门**（`harness/ws4_d3_gate.py`）：自环模式可用；`--real` 金标未注入 → **exit 3 + WAITING_OWNER 消息 fail-closed 绝不静默通过**（ofc 3 题 WAITING_WS3，卡面口径）。
- **坑③（freeze 对新增文件判红）**：按 SF-0003 三段式收工，见 §4 GE-2。

## 3. BQ 三门红绿证据（GB 组，8/8 包 SELFTEST PASS）

每包 `gen_oracle.py --selftest` 输出五行态（mm-01 原样摘录，其余同构）：

```
GREEN  oracle(判自家 fixtures) exit=0 PASS      ← BQ-8 绿态：oracle 过自家 checker 全绿
RED    corrupt=fabricated_entry   exit=1 PASS   ← BQ-8 红态：编造条目必红
RED    corrupt=drop_section_heading exit=1 PASS
RED    corrupt=summary_count_wrong  exit=1 PASS
RED    corrupt=todo_header_broken   exit=1 PASS
CROSS  oracle(A)判fixtures(B)       exit=1 PASS ← BQ-9：nonce-A oracle 判 nonce-B 实例必红
DET    同种子双跑逐字节             PASS        ← BQ-10：同种子两次生成逐字节一致
FIXT   包内fixtures==canonical生成  PASS        ← 附加守卫：包内输入与 canonical 种子零漂移
```

- 红态损坏库按线分发：mm 4 种（编造条目/毁节标题/计数错/毁表头）、hot 5 种（违禁词/卖点记账/删产物/模板残留/毁占位，最后一种仅 wx）、ofc 4 种（替缺失编值/标题左对齐/记账不一致/值变形）——全 33 次注入无一漏红。
- GB-3 字面命令（mm-01, seed=42）：`--out /tmp/a` + `--out /tmp/b` + `diff -r` → **exit 0**。
- BQ-9 机理：L2 判定基准跟输入走——oracle-A 的实体/卖点/字段值在 fixtures-B 中不存在 → 溯源/记账/verbatim 门红。

## 4. 自测逐条（对照 tests/visible/SF-0005-accept.md）

| 门 | 结果 | 证据摘要 |
|---|---|---|
| GA-1 | ✅ | `ls evalkit/packs/ws4-dev/ \| wc -l` = 8 |
| GA-2 | ✅（意图面）/ ⚠️（字面命令） | 8 包 EI-7（brief 公平+资产名扫描零命中）与 EI-20（六件齐+无 oracle/）全绿；**字面命令（无 --arms）因装置既有语义 EI-9「不足两臂」判红 exit 1**（sm-mapping-01 同行为，开工前实测在案）→ 用临时双臂树补跑 `--arms baseline --arms treatment` **8/8 exit 0 三断言全过**。GA-2 括号口径（EI-20 conformance）已满足；建议 planner 勘误验收命令为带 --arms 形态 |
| GA-3 | ✅ | `grep -L "task_outcome_"` exit=1（每包 wrapper 声明检查名清单） |
| GA-4 | ✅ | `grep -rn "reference_" */checks/` exit=1（零命中） |
| GB-1/2/3 | ✅ | 8/8 SELFTEST PASS（§3）；GB-3 diff exit 0 |
| GC-1 | ✅ | 8/8 runner_contract 四字段+ref_root 实存+selfcheck_exit=0+redpath_exit=1 |
| GC-2 | ✅ | L1 桥接受控 exit∈{0,1}，只登记 record.l1 不参与判分 |
| GD-1 | ✅ | 8 题 status=built；d1/d3 signoff 三字段键齐 |
| GD-2 | ✅ | 断言全 null（机检 `all(v is None)` 过）——反假人工门 |
| GD-3 | ✅ | 3 题 public-variant+source_ref 非空；5 题 self-built |
| GD-4 | ✅ | d2（种子/生成时间/输出逐文件 sha256+selftest 结果）；d4（band=null+首轮分布全带外记录+分拣规则注入位） |
| GE-1 | ✅ | afp-clone porcelain 前后差分=空（开工快照 20 条既有噪音不变） |
| GE-2 | ✅ | 三段式：verify 红（漂移恰=声明集：4 新 harness 文件 new + aggregate.py changed）→ freeze（16→20 文件）→ verify 绿 exit 0 |
| GE-3 | ✅ | `nc/run_nc.py` 负控 9/9（含 NC-CTRL 阴性对照不误报） |
| GE-4 | ✅ | brief 零 dist 资产名（grep exit=1） |
| 附 | ✅ | AG-7 回归：旧 v6-mvp-0.1 matrix 对 v6-mvp-0.3 拒绝并列 exit=1，拒绝先于落盘 |

## 5. 签署台账现状与 owner 签署指引（GE-5 核心）

**现状**：`bench/devpool-r1/pool-state.json` 8 题 d1_record/d3_record 的 signoff 三字段全 null = 全部 **WAITING_OWNER**（ofc 3 题 D3 另 WAITING_WS3）。机检门（GD-2）断言「存在且恒 null」——字段缺失或被代签都判红。

**D1 签署指引（每题一签，卡 B 需 ≥5）**：
1. 读题：`evalkit/packs/ws4-dev/<id>/brief.md`（题面）+ `fixtures/`（nonce 实例）+ `rubric.md`（质量轨维度）；
2. 核对 pool-state 该题 d1_record 四项自检（来源合法 drafted-awaiting-owner / 可机判 machine-green / 两臂公平 machine-green / 资产名零泄漏 machine-green——后三项证据已在档）；
3. 满意则把该题 d1_record.signoff 三字段填齐：`签署人`=本人姓名、`日期`=签署日、`被签对象sha256`=该题 pack_files_sha256 清单的 brief.md 值（pool-state 已逐题登记，防签错对象）；
4. mm-01+mm-02+hot-01..03 共 5 题签署即满足卡 B 兜底门（≥5、每臂 n≥2、三类用例配齐）。

**D3 装置就位说明**：`python evalkit/harness/ws4_d3_gate.py --task <id> --real` 已建成——mm/hot 5 题注入人工金标（`bench/devpool-r1/goldens/<id>/<样本>/product/`+`verdict.json{expected_pass,annotator}`）即可算对拍准确率（≥95% 出数、<95% exit 1、未注入 exit 3 WAITING_OWNER 绝不静默过）；ofc 3 题 WAITING_WS3（金标对拍归 WS3 独立工作流，PLAN §7）。**自环对拍（self_loop=true）已跑通但不替代人工金标**（卡面禁止条款）。

**D4 说明**：难度带首轮全带外（0 模型调用无臂数据，卡面允许「仅记录分布」）；SF-0006 跑完后按 treatment 通过率分拣（60-90% 迭代池/>90% 轮换池/<60% 归因五分类，阈值待实测校准=PLAN §3.2 [假设]）。

## 6. 未尽事项与给 planner 的发现

1. **run_all.py:51 版本残留**：`--evalbench-version` 透传 default 仍钉 v6-mvp-0.2（SF-0006 一键复跑会落旧版号）。修它=改第三个既有文件，超出本卡两文件授权 → 登记 CHANGELOG 已知残留+此处，请 planner 排一行小卡或令卡 B 编排器显式传参。
2. **freeze glob 不覆盖嵌套包**：`keyfiles.sha256` 的 glob `packs/*/checks/run_check.py` 只匹配一层目录，ws4-dev 8 个 wrapper 不入冻结账本（判分核心 ws4_judge.py 已在冻结面；wrapper 有运行时契约自校验+pool-state `pack_files_sha256` 补位清单）。改 glob 需动 freeze_device.py=既有文件，非本卡授权，留 planner 裁。
3. **GA-2 字面命令与装置语义错配**（§4 表内已述）：建议验收命令改带 `--arms` 或 planner 接受「无臂跑只看 EI-7/EI-20」口径。
4. 六个 dist runner 检查名（docx_opens_with_three_sections 等）并非全 `reference_*`（卡面坑②的表述与实物有出入——仅 mm 第 5 项/ofc 第 6 项等参照比对类含 reference 语义）；本卡 L2 全新命名不受影响，登记勘误供 planner 回改卡面。
5. **commit/push 未做**（红线：凭据+网络窗流程属交付面外，衔接 ESC-008）；规划/测试文档仍未 commit（既有状态）。

## 7. 复跑入口（冷上下文可续）

```bash
cd D:/new-workspace/agent-asset
python evalkit/packs/ws4-dev/<pkg>/gen_oracle.py --selftest        # 逐包 BQ-8/9/10
python evalkit/harness/ws4_pool_state.py                           # 重建 runner_contract+pool-state（幂等）
python evalkit/harness/freeze_device.py verify                     # 装置钉版（20 文件）
python evalkit/nc/run_nc.py                                        # 负控 9/9
python -c "import json;d=json.load(open('bench/devpool-r1/pool-state.json',encoding='utf-8'));print([(t['id'],t['status'],t['d1_record']['signoff']['签署人']) for t in d['tasks']])"
```
