# 测试卡门槛脚本（planner 落成，2026-10-08）

本目录是 alpha 测试卡（见 `evidence/owner-delegated-signing-20261008.md` 第三节）的**机检门槛**落成物，由主代理（planner）编写，**开发方（GLM-5.3-Flash）不得修改**——判卷器与施工方分离。

| 脚本 | 覆盖条款 | 说明 |
|---|---|---|
| `gate_sf0006a.py` | A-01..A-06、A-11、A-12 | A-13/A-14 本轮不机检（开发方按卡面命令执行并汇报，B 层实测复验）；A-07..A-10 等 D3 金标注入 |
| `gate_sf0009.py` | R-01..R-06 | REGISTRY 只追加回写 ③④ 裁定 |
| `gate_sf0007.py` | K5A-01..K5A-07 | dist/build 变体文档修补（零模型、不发布） |

运行方式：`python3 <gate>.py <venv-python 路径>`，退出码 0=全过。`base_commit.txt` 记录开发开工时的 HEAD，作为各卡 git diff 条款的基线。
