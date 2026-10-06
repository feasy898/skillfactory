# evalkit · 自有 bench 的跑批装置（WS1 · eval harness MVP）

> 落盘位置按 PLAN §8 **O-17** 两段式：MVP 在**工作区新建 `evalkit/`（不进 afp-clone，先证后落）**，
> 管道验证通过后才升格 `skillfactory/v6/`。
> 本目录与 `afp-clone/` **平级**；所有指向资产树的路径都从 `__file__` 相对推导，整目录搬迁后不改代码。

> **本轮产出物叫「管线验证信号」，不是验收结论**（PLAN §5.4 三条纪律）。
> n=1、单任务、单族，禁止据此声称任何增益数字。

## 一分钟上手

```bash
cd D:/new-workspace/agent-asset/evalkit

# 0) 装置自检 + 钉版
python harness/freeze_device.py verify

# 1) 步 0：绿路 / 红路 / oracle 哈希基线
python packs/sm-mapping-01/checks/run_check.py            # 绿路，期望 exit 0
python packs/sm-mapping-01/checks/run_check.py <空目录>    # 红路，期望 exit 1
python harness/oracle_gate.py hash    --root <资产>/oracle --record baseline.json
python harness/oracle_gate.py calibrate --root <资产>/oracle --runs 3

# 2) 步 1：建臂树 + 隔离实测 + 前置三断言
python harness/make_arms.py --pack packs/sm-mapping-01 --run-id r1 --asset-skill <资产>/package
python harness/isolation_probe.py runs/r1/baseline
python harness/pack_checks.py --pack packs/sm-mapping-01 --arms runs/r1/baseline --arms runs/r1/treatment

# 3) 步 2：跑臂（一臂一进程）
python harness/run_arm.py --run-id r1 --arm baseline  --arm-dir <abs>/runs/r1/baseline  --family glm
python harness/run_arm.py --run-id r1 --arm treatment --arm-dir <abs>/runs/r1/treatment --family glm

# 4) 步 3：三轨 + 看板 + 哈希终检
python evaluators/artifact_track.py --pack packs/sm-mapping-01 --product-root <abs>/runs/r1/treatment/out
python evaluators/process_track.py  --arm-dir <abs>/runs/r1/treatment
python evaluators/quality_track.py  --pack packs/sm-mapping-01 --arm treatment
python evaluators/aggregate.py      --run-dir <abs>/runs/r1 --pack packs/sm-mapping-01
python harness/oracle_gate.py verify --root <资产>/oracle --record baseline.json

# 5) 负控（管道正确 = 负控全红 + 正常臂不误报）
python nc/run_nc.py
```

一键复跑：`python harness/run_all.py --run-id <新 id>`。

## 目录

| 路径 | 作用 | 对应测试 |
|---|---|---|
| `packs/sm-mapping-01/` | 任务包：brief（两臂逐字相同）/ fixtures（黄金输入，SF-0003 修法 A 改名，见包内 PACK-DEVIATIONS.md）/ rubric / checks（薄封套）/ out / transcript / records | PLAN §3.3、EI-20 |
| `harness/oracle_gate.py` | oracle 树哈希门：整树 sha256 + 文件清单 + 文件数；行尾基准显式声明；易变面三跑标定 | EI-3 EI-4 EI-5 |
| `harness/isolation_probe.py` | 臂隔离探针（find 而非看它说什么） | EI-6、MT-2 |
| `harness/pack_checks.py` | 前置三断言：brief 公平 / 输入树公平 / 任务包 conformance | EI-7 EI-9 EI-20 |
| `harness/make_arms.py` | 建 treatment/baseline 两棵臂树 | PLAN §5.4 步 1 |
| `harness/run_arm.py` | 臂驱动：一臂一进程 + 分族超时 + records 落盘 + db 遥测 join | EI-0、§5.2、§5.6 |
| `harness/freeze_device.py` | 装置钉版（keyfiles.sha256，相对路径） | EI-23 |
| `evaluators/artifact_track.py` | 产物轨（零模型，每次必跑） | §5.3 |
| `evaluators/process_track.py` | 过程轨四断言 | EI-10..EI-14 |
| `evaluators/quality_track.py` | 质量轨（无跨族裁判时显式 unjudgeable，**不出分**） | §5.3、O-7 |
| `evaluators/classify.py` | 三桶分类 + 降级链 + 单族整列作废 | EI-15..EI-19 |
| `evaluators/aggregate.py` | matrix.json 落盘 + schema 校验 + 写-读往返 | AG-15、EI-21 |
| `nc/run_nc.py` | 负控 8 条 + 阴性对照 | NC-1..NC-8 |

## 三条硬纪律（装置自带的，不靠人记）

1. **runner 零改动**：判分逻辑只有一份，在资产树里。本装置只 import，不复制、不改写；
   判分器 sha256 进 `keyfiles.sha256` 与每臂 `model_pin.json`，改一个字节就 verify 红。
2. **参照区只读**：所有写/删实验只在 oracle 的**独立副本**上做（`nc/` 下 `nc-` 前缀树）。
   K-3 彩排 D3 已经真清空过一次参照区——harness 自己不能再犯一次。
3. **不判绿就明说**：无遥测 → `unjudgeable`；无跨族裁判 → `unjudgeable`；
   `delta_vs_prev` 首轮 → `null` 而非 `0`。三种「没差异」不许合并成一个 0。

## 已知限制（2026-10-03 首轮实测，勿当已解决）

- **模型钉版（O-6 已裁定）**：zcode headless `-p` 无 `--model` 选项，实测落点为 **GLM-5.3**
  （`account:bigmodel-individual-coding-plan/GLM-5.3`，两臂一致；不是 EVAL-SPEC §4.1 钉版的
  GLM-5.3-Flash）。**裁定（PLAN §8 O-6，2026-10-03）**：接受该落点，evalbench 版本 bump 至
  **v6-mvp-0.2**、旧基线作废（r1-probe 数字 citable:false）；跨版本并列由 `aggregate.py`
  的 AG-7 拒绝门拦截。四族矩阵在 headless 进程驱动拓扑下**当前只通一族**（跨族比较推 WS5 前解）。
- **质量轨无裁判**：跨族裁判要求裁判族与被测集无交集（O-7），本轮被测集=GLM 族，本机第二族
  通道未通 → 质量轨 `unjudgeable`，不出分。
- **`/skill` 在 Git Bash 下会被 MSYS 改写成路径**：`zcode -p "/skill"` 必须带
  `MSYS_NO_PATHCONV=1`，否则模型收到的是 `C:/Program Files/Git/skill`（PLAN R-7 同族坑）。
- **Git Bash `/` 转换**同族：一切 spawn 子进程的脚本都要透传 `MSYS_NO_PATHCONV=1`。
- `pack_checks.py` 的资产名扫描是**兜底不是防线**（TESTS EI-7 原文：负例句式库首版覆盖有限，标 [假设]）。
- **验收卡版本锚随装置 bump 漂红（升卡 2026-10-06 收口）**：`verify_sf0003.py` 的 B5/F4 版本断言
  锚定卡面常量 `CUR_VERSION`（现 **v6-mvp-0.3**，与 `aggregate.py` 声明面同步）；B5 的同版本
  prev 基准（runs/sf0003/ag7-prev-same.json）改由 verify 运行时按卡面锚自生成，不再用 0.2 时代
  静态文件。**装置再 bump（0.4+）时 B5/F4 会诚实转红，须随附升卡**；D2 已诚实降级为 historical
  断言（卡时点改动已由 5654f83 commit 落盘，改以 ac18867 基线↔HEAD git 史断言）。

## 落盘纪律（Windows 事故族）

一律用 Python `open(..., encoding="utf-8", newline="\n")`，**不用 shell 重定向**写产物
（PLAN R-7：`hw_student_eval.json` 是「合法 UTF-8 但非 JSON」的反面教材）。
