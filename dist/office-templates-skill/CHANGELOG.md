# CHANGELOG — office-templates package（实现层）

## 1.0.1 — 2026-10-09（office 补强重打包，K-5 回炉重测前置）

- 以补强后资产源 `v3/assets/office-templates`（提交 e82b3cb：docx 容器时间戳归一化 + SKILL §9-5 自评规程，oracle 参照与 eval/runner.py 零改动）按首发（1.0.0）打包口径重建本分发包：**包结构不变、内容更新**。
  - `SKILL.md`：正文逐字节更新为 `package/SKILL.md` 补强版（§2/§5/§6-V8 确定性口径升级为整文件逐字节一致；§9 增第 5 步「确定性/交付自评」：同命令连跑两遍快照对拍 sha256 + run_log.json 留痕规程）；front-matter 照分发包体例保留，版本随包升 1.0.1。
  - `scripts/gen_doc.py`：逐字节更新为补强版引擎（canonicalize_docx_zip()——保存后原子重写 zip 容器，17 条目时间戳归一化 1980-01-01，D1+ 整文件逐字节可复现；失败退回 D1 语义下限不影响退出码）。
  - `references/`（四份）、`requirements.txt`、`eval/runner.py`、`eval/golden.json`、`reference/inputs/`：源零改动，逐字节复制校验一致（打包器实算）。
  - `reference/out/`：照旧例取自 `oracle/out`（本轮 oracle 参照零改动，逐字节未变）；fields.json 沿用首发包侧 CRLF→LF 归一形态。
  - `README.md`：设计红线②「确定性可复现」表述同步为整文件逐字节口径（仅此一处）。
  - 新写面（`LICENSE`/`EVALUATION.md`/`MANIFEST.md`/`eval/results/benchmark.json`）零改动；版本号面（front-matter/本文件/MANIFEST 标题）随包升 1.0.1。
- 冻结纪律（K5B-09 口径）：`eval/golden.json` 逐字节未动，sha256=2fa58b07… 与 REGISTRY.md 登记值一致。
- canonical 源 `v3/assets/office-templates` 本轮零改动。

## 1.0.0 — 2026-09-30（分发包首发）

- 自开发资产源（spec.md v1.0，2026-09-30 固化）打包为可分发技能包：
  - `SKILL.md`：取自 `package/SKILL.md`（正文逐字节复制），按分发包体例补 front-matter（name/version/license=MIT/description/permissions/metadata，对齐 meeting-minutes-skill 先例）；正文内 `package/` 前缀命令在分发包中对应包根相对路径，见 README「快速开始」。
  - `scripts/gen_doc.py`、`references/`（周报/请示函/会议通知/工作总结四份）、`requirements.txt`：取自 `package/`，逐字节复制（md5 校验一致）。
  - `eval/runner.py` + `eval/golden.json`：取自资产根 `eval/`（contract §5 冻结接口），逐字节复制。**注意**：runner 无参数缺省路径写死为 `<包根>/oracle/out`，分发包内不存在，必须显式传 `<被测产物根> <参照产物根>` 两参数运行，约定见 README。
  - `reference/`：样例参照——`oracle/inputs/`（8 份数据 JSON）→ `reference/inputs/`，`oracle/out/`（8 个参照产物单元）→ `reference/out/`，逐字节复制（md5 校验一致）。
  - 新写：`LICENSE`（MIT，Copyright (c) 2026 SkillFactory）、`README.md`、`EVALUATION.md` 与本文件。**说明**：v3 资产源内无 CHANGELOG 文件，本文件为分发时新写。
- 分发包自验证（2026-09-30 实跑，Python 3.12.10 / python-docx 1.2.0）：8 条 `scripts/gen_doc.py` 生成命令全部 exit=0；`python eval/runner.py out reference/out` → ok=true、68/68 checks 全 pass、字段填充一致率 100.0%（66/66）、exit 0；绿自检 exit 0、空目录红检 exit 1；D1 双跑 fields.json 除 outputs 外逐字节一致、docx zip 17 条目 CRC 全等。详见 EVALUATION.md「2.4」。
- 盲评体检（v0.2 双臂双重复 5 任务）：基线 7.7 → 治疗 8.9，Δ +1.20、任务级胜率 100%、反向 0，判定达标；聚合原始数据见开发方评测存档（未随包分发）。

> **更正注记（2026-10-09，alpha 终裁复核追加；上方 1.0.0 历史条目原文不改）**：上条所载「基线 7.7 → 治疗 8.9，Δ +1.20、任务级胜率 100%、反向 0，判定达标」系**开发管线自评口径**（v0.2 双臂双重复 5 任务自评，K5B 提交前自评），跨代，**未获 K-5 采信**，不构成本包现行判定（EVAL-SPEC v0.2.1 §3.7-4：跨代数字禁止 Δ 对位或合并披露）。现行判定状态以 [EVALUATION.md](EVALUATION.md) 结论先行为准：K-5 回炉重测 round2 **accepted（provisional，single_round_signal=true）**；历代数字按代分节见 EVALUATION.md「二、结果」。
