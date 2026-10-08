# ht-t05 · points 四形态等价

## 任务

用 hot-templates 技能，以 platform=`xhs`、topic=`阳台种菜入门`、同一份卖点（`["泡沫箱打孔防涝", "蛋壳补钙碾碎拌土", "北侧种耐阴生菜"]`）分别以四种合法形态各跑一次：

| 目录 | 形态 |
|---|---|
| `<outdir>/A-inline/` | 内联 JSON 串直接作 --points |
| `<outdir>/B-plain/` | `points_plain.json`：UTF-8 无 BOM 文件，内容=该数组 |
| `<outdir>/C-bom/` | `points_bom.json`：UTF-8 **带 BOM** 文件，内容同 B（引擎按 utf-8-sig 读取须容忍） |
| `<outdir>/D-wrapped/` | `points_wrapped.json`：内容=`{"points": [同数组]}`（对象形态） |

三个 JSON 文件由被测自备（保存到工作目录）。四次生成全部成功。

## 判定要点（全部可机判）

1. 四目录各含 `骨架.md` + `structure.json`，四次调用 exit 0 且 OK 行 elements=7。
2. **逐字节一致**：四份 `骨架.md` 两两 md5 相等；四份 `structure.json` 两两 md5 相等（唯一允许差异=无——`structure.json` 不含 outdir 路径，确认口径以重跑同输入到不同目录结果为准）。
3. `structure.json`：points_input_count=3、points_used=3 原文、points_unused=[]。
4. 首标签=`#阳台种菜入门`；summary_block 三点复述含 3 卖点原文。

## 判挂点

- BOM 文件被当非法 JSON（exit 2）→ 形态处理失守。
- 包装对象漏解 points 键（exit 2 或 points_used 空）→ 同上。
- 四产物不一致（如某次 topic/卖点被改写）→ 同一性破坏。
