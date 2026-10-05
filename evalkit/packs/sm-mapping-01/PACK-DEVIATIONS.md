# PACK-DEVIATIONS · sm-mapping-01 对 PLAN §3.3 通用任务包格式的显式偏离

> 登记于 SF-0003（2026-10-03，worker-glm-m4）。本文件是包级偏离台账：偏离项 / 依据 /
> 适用范围 / 建议回写条款。**PLAN §3.3 本身本卡不改**（回写由 planner 决定）。

## 偏离 1 · 黄金输入目录名 `inputs/` → `fixtures/`

- **偏离项**：PLAN §3.3 任务包格式字面写 `inputs/ 黄金输入（两臂同等提供，§4.3-4）`；
  本包自 SF-0003（修法 A）起黄金输入目录名为 **`fixtures/`**（6 文件保内容改名，
  改名前后逐文件 sha256 见 `runs/sf0003/inputs-pre-rename-sha256.json`）。
- **依据**：PLAN §3.1 分层语义——L1 层逐字节比对的前提是「被测与参照**同形态**」。
  本包参照基线（oracle/out）由 oracle 参照实现在 oracle/ 下以
  `--transcript fixtures/…` 形态生成；黄金输入目录名与运行条款必须与该形态同构，
  否则路径回显恒与基线差、产物轨检查 4 双臂恒红（SF-0001 §4.2 根因链，
  「尺子坏了，不是模型不行」）。
- **适用范围**：**仅本包**（sm-mapping-01）。装置侧已做 EI-20 双名兼容
  （pack_checks.py 对 fixtures/inputs 都放行、一名即可、双名混用判红），
  后续新包可按 PLAN §3.3 通用字面用 inputs/，或沿用 fixtures/——
  以「与参照基线生成形态同构」为准绳（见建议条款）。
- **建议回写 PLAN §3.3 的条款文本**（供 planner 决定，原文为「inputs/ 黄金输入」）：

  > `inputs/`（或 `fixtures/`）黄金输入（两臂同等提供，§4.3-4）。**目录名必须与本包
  > 参照基线的生成形态同构**（L1 逐字节比对的前提，§3.1）：参照基线以
  > `--transcript <dir>/…` 生成时，被测运行条款用同一目录名与同一参数形态。
  > 装置对两名均放行（EI-20 双名），同一包内不得混用。

## 关联留痕

- brief.md 运行条款同步改写（臂根 cwd / `--transcript "fixtures/…"` / `--out "out/…"`）。
- 装置 4 处适配：make_arms.py / pack_checks.py（EI-7/EI-9/EI-20 双名）/
  process_track.py（引引面正则）/ evalkit README 目录表。
- 0 模型 replay 证据：runs/sf0003-replay/（检查 4 首次转绿，见 SF-0003 交付报告 E 组）。
