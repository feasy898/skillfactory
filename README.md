# skillfactory — skill 资产工厂 v5（AI 课程交付核心业务）

本仓库由 `feasy898/agentic-factory-projects` monorepo 子树拆分而来：

- **主体来源**：monorepo 的 `zcode-research/skillfactory/` 子树，经 `git subtree split` 保留完整提交历史
  （拆分基点：monorepo commit `a9ec968`，即 2026-10-05 推送后的 main；skillfactory 子树最后成果对应原仓 commit `05d01da` "skillfactory WS2: build.py 三变体构建器…"）。
- **合入成果**：`agent-asset` 顶层工作区成果（2026-10-05 留底 commit `b1e4784`）——
  `BASELINE.md`（与 planning/BASELINE.md 同源）、`planning/`（含 PLAN.md 裁定更新与 SF-0003/0004/0005 报告）、
  `bench/`、`evalkit/`、`baseline-inventory/`、`{dp,hw,sm}_student_eval.json`、`zctlmcp_eval.json`。
- **原仓**：<https://github.com/feasy898/agentic-factory-projects>（skillfactory 目录仍在原仓留档；今后本仓库为该业务线的权威仓库）。

## 目录速览

| 目录/文件 | 内容 |
|---|---|
| `REGISTRY.md` | skill 资产注册表 |
| `assets/` | 各 skill 资产源 |
| `v2/ v3/ v4/ v5/` | 各版本资产包（v5 = 三变体构建 + G0-5 合规门 + dist 三包） |
| `dist/` | 构建产物 |
| `planning/` | BASELINE / PLAN / TESTS + 思考与测试轨迹 + 报告 |
| `bench/` `evalkit/` `baseline-inventory/` | 评测基建与基线盘点 |
| `*_student_eval.json` `zctlmcp_eval.json` | 评测结果留底 |
