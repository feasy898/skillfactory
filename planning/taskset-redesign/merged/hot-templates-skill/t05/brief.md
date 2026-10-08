# ht-t05 · points 四形态等价：内联串/无 BOM 文件/BOM 文件/包装对象——四产物逐字节一致

> 投喂题面存档：以下正文与 `task.json.instruction` 逐字一致，是 harness 投喂两臂的唯一文本。
> 判定要点/期望表/判挂点/机判方法在 `judge-notes.md`（判官专用，投喂面禁读）；评分标准见 `rubric.md`。

---

帮我做一次生成输入形态的验证：platform=`xhs`、topic=`阳台种菜入门`、同一份卖点（`["泡沫箱打孔防涝", "蛋壳补钙碾碎拌土", "北侧种耐阴生菜"]`）以四种合法输入形态各生成一次，分别输出到 `<outdir>/A-inline/`、`<outdir>/B-plain/`、`<outdir>/C-bom/`、`<outdir>/D-wrapped/`：

- A：卖点以内联 JSON 串形态直接给出；
- B：存成 `points_plain.json`（UTF-8 无 BOM，内容=该数组）后以文件形态给出；
- C：存成 `points_bom.json`（UTF-8 **带 BOM**，内容同 B）后以文件形态给出；
- D：存成 `points_wrapped.json`（内容=`{"points": [同数组]}`）后以文件形态给出。

三个 JSON 文件由你自备（保存到工作目录）。四次生成都要成功出产物（各含 `骨架.md` + `structure.json`）。
