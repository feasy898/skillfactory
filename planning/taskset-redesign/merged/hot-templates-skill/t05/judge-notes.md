# hot t05 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. 四目录各含 `骨架.md` + `structure.json`，四次调用全部成功（端态：产物齐非空、内容口径一致）。
2. **逐字节一致**：四份 `骨架.md` 两两 md5 相等；四份 `structure.json` 两两 md5 相等（唯一允许差异=无——`structure.json` 不含 outdir 路径，确认口径以重跑同输入到不同目录结果为准）。
3. `structure.json`：points_input_count=3、points_used=3 原文、points_unused=[]。
4. 首标签=`#阳台种菜入门`；summary_block 三点复述含 3 卖点原文。
5. **复审第 6/14 条**：占位重计口径=structure.json elements[].text（四方均=7）；stdout OK 行不作判分项。

## 期望（引擎实测 2026-10-09）

四形态四方 md5 全等（骨架.md 与 structure.json 各一个 md5 值）；四方 structure.json 均 element_count=7、占位合计=7、stats={7,10}、points_used=3 原文。

## 判挂点

判挂点统一计分规则（复审第二轮 R1）：加权分按 rubric 公式（10 × Σ(维度分×权重)/Σ权重，0-10 刻度舍 1 位）重算，必须真实跌破通过线。

- BOM 文件被当非法 JSON（失败）→ 形态处理失守：正确性 0.4 档 ⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 0.16+0.3+0.3=0.76 → 7.6 < 8.0。
- 包装对象漏解 points 键（失败或 points_used 空）→ 同上 ⟦正确性=0.4,完整性=1.0,可验证性=1.0⟧ → 7.6 < 8.0。
- 四产物不一致（如某次 topic/卖点被改写）→ 同一性破坏：完整性 0（全有全无）⟦正确性=1.0,完整性=0,可验证性=1.0⟧ → 0.4+0+0.3=0.70 → 7.0 < 8.0。

## 机判方法

`md5sum` 逐字节比对；structure.json 端态断言。若 structure.json 含 outdir 相关差异（引擎不应有），以「同输入重跑到两个临时目录的输出互 diff」复核后按实际口径评。

## 引擎实测校准记录（2026-10-09，零模型）

命令：四形态各跑 `/usr/bin/python3 dist/hot-templates-skill/scripts/gen.py --platform xhs --topic 阳台种菜入门 --points <形态>`，均 exit 0。
真值：四份 骨架.md md5 全等、四份 structure.json md5 全等（实测单值）；四方 elements=7、占位合计=7、stats={7,10}。