# TOOLING 形态体检报告（分形态 Healthcheck）

- 目标包：`/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/speaker-mapping/package`
- 生成时间：2026-10-08T11:23:22+0800（healthcheck-forms.py 1.0.0 (tooling 形态)）
- 评级：**A**（A=0 失败 / B=1 失败 / C=≥2 失败）
- 汇总：3 项检查，3 通过 / 0 失败

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| cli_executable | ✅ PASS | 登记工具类 speaker-mapping：map_speakers.py --help exit=0（440 字节用法） |
| eval_runner_red_green | ✅ PASS | 红绿两态成立：绿态 exit=0（python eval/runner.py oracle/out oracle/out，stdout 摘要: { "ok": true, "summary": { "total": 4, "pass": 4, "fail": 0, "tested_root": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/speaker-mapping/oracle/out", "reference_root": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/speaker-mapping/oracle/out" }, "checks": [ { "name": "replacement_line_by_line", "pass": true, "detail": "9 组映射产物逐字节等于期望常量（含替换正确、未映射标签原样保留、时间戳/冒号/正文逐字节不动）" }, { "n…）；红态 exit=1（被测根=空临时目录，fail-closed，stdout 摘要: { "ok": false, "summary": { "total": 4, "pass": 0, "fail": 4, "tested_root": "/tmp/ws9-red-ncr8swsm", "reference_root": "/home/pan-ding/workspace/skill工厂/skillfactory/v5/assets/speaker-mapping/oracle/out" }, "checks": [ { "name": "replacement_line_by_line", "pass": false, "detail": "不一致 9/9: normal__m_full.txt: 缺少 /tmp/ws9-red-ncr8swsm/normal__m_full.txt; normal__m_partial.txt: 缺少 /tmp/ws9-red-ncr…） |
| skill_md_fields_relaxed | ✅ PASS | front-matter 放宽口径字段齐备：name=speaker-mapping、description 非空（132 字符）｜豁免注记（REGISTRY.md 2026-10-08 ④裁体检形态豁免）：工具类技能在旧 5 项 skill 口径下失分属形态错配；本形态放宽为 name/description 两字段非空，version/license/permissions 不作要求（留档备查，不等于免检） |

## 检查口径出处

- skill 包 front-matter 通行口径：SKILL.md 以 --- 块起始，name/description 为通行必填两要素；解析同本仓 v3 spec.md §3 R4（行级 key: value，非完整 YAML）。
- 确定性评测红绿纪律：本仓 v3/tools/healthcheck/spec.md R6/R8——单次确定性调用，绿态 exit 0 + 红态 fail-closed exit 1 两态缺一不可。
- registry 豁免：REGISTRY.md 2026-10-08 ④裁体检形态豁免注记——hotwords/deploy-pack/speaker-mapping 三件旧 5 项失分为形态错配，放宽口径并逐报告留档豁免注记。

## 建议

评级 A：无失败项，tooling 形态口径全绿。
