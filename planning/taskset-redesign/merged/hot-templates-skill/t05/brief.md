帮我做一次生成输入形态的验证：platform=`xhs`、topic=`阳台种菜入门`、同一份卖点（`["泡沫箱打孔防涝", "蛋壳补钙碾碎拌土", "北侧种耐阴生菜"]`）以四种合法输入形态各生成一次，分别输出到 `<outdir>/A-inline/`、`<outdir>/B-plain/`、`<outdir>/C-bom/`、`<outdir>/D-wrapped/`：

- A：卖点以内联 JSON 串形态直接给出；
- B：存成 `points_plain.json`（UTF-8 无 BOM，内容=该数组）后以文件形态给出；
- C：存成 `points_bom.json`（UTF-8 **带 BOM**，内容同 B）后以文件形态给出；
- D：存成 `points_wrapped.json`（内容=`{"points": [同数组]}`）后以文件形态给出。

三个 JSON 文件由你自备（保存到工作目录）。四次生成都要成功出产物（各含 `骨架.md` + `structure.json`）。
