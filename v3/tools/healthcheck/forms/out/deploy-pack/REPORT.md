# TOOLING 形态体检报告（分形态 Healthcheck）

- 目标包：`/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/deploy-pack/package`
- 生成时间：2026-10-08T11:23:22+0800（healthcheck-forms.py 1.0.0 (tooling 形态)）
- 评级：**A**（A=0 失败 / B=1 失败 / C=≥2 失败）
- 汇总：3 项检查，3 通过 / 0 失败

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| cli_executable | ✅ PASS | 登记工具类 deploy-pack：gen_deploy.py --help exit=0（419 字节用法）; validate.py --help exit=0（276 字节用法） |
| eval_runner_red_green | ✅ PASS | 红绿两态成立：绿态 exit=0（python eval/runner.py oracle/out oracle/out，stdout 摘要: { "tool": "runner.py", "asset": "skillfactory/v5/assets/deploy-pack/eval", "candidate": "oracle/out", "reference": "oracle/out", "candidate_resolved": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/deploy-pack/oracle/out/pack-canonical", "candidate_resolved_via": "pack-canonical", "reference_resolved": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/deploy-pack/oracle/out/pack-c…）；红态 exit=1（被测根=空临时目录，fail-closed，stdout 摘要: { "tool": "runner.py", "asset": "skillfactory/v5/assets/deploy-pack/eval", "candidate": "/tmp/ws9-red-wz6a4a31", "reference": "oracle/out", "candidate_resolved": null, "candidate_resolved_via": "none", "reference_resolved": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/deploy-pack/oracle/out/pack-canonical", "reference_resolved_via": "pack-canonical", "oracle_resolved": "/home/pan-ding/…） |
| skill_md_fields_relaxed | ✅ PASS | front-matter 放宽口径字段齐备：name=deploy-pack、description 非空（109 字符）｜豁免注记（REGISTRY.md 2026-10-08 ④裁体检形态豁免）：工具类技能在旧 5 项 skill 口径下失分属形态错配；本形态放宽为 name/description 两字段非空，version/license/permissions 不作要求（留档备查，不等于免检） |

## 检查口径出处

- skill 包 front-matter 通行口径：SKILL.md 以 --- 块起始，name/description 为通行必填两要素；解析同本仓 v3 spec.md §3 R4（行级 key: value，非完整 YAML）。
- 确定性评测红绿纪律：本仓 v3/tools/healthcheck/spec.md R6/R8——单次确定性调用，绿态 exit 0 + 红态 fail-closed exit 1 两态缺一不可。
- registry 豁免：REGISTRY.md 2026-10-08 ④裁体检形态豁免注记——hotwords/deploy-pack/speaker-mapping 三件旧 5 项失分为形态错配，放宽口径并逐报告留档豁免注记。

## 建议

评级 A：无失败项，tooling 形态口径全绿。
