# tt03 · 极端空数据的全占位渲染：空对象 {} 与键全在值全空白

> 投喂题面存档：以下正文与 `task.json.instruction` 逐字一致，是 harness 投喂两臂的唯一文本。
> 判定要点/期望表/判挂点/机判方法在 `judge-notes.md`（判官专用，投喂面禁读）；评分标准见 `rubric.md`。

---

这里有两份数据要成文，分别保存后用生成流程处理：

- A：`qingshi_empty.json`（请示函）→ 生成到 `<outdir>/请示函-empty/`
- B：`zongjie_blank.json`（工作总结）→ 生成到 `<outdir>/工作总结-blank/`

各自产出 `文书.docx` + `fields.json`。两份都得给我出文件，数据没填的地方照实处理就行，别报错中断。

A（qingshi_empty.json）内容就是字面的空对象：`{}`

B（zongjie_blank.json）内容：
```json
{
  "总结主体": "  ",
  "总结时段": "",
  "工作回顾": [],
  "主要成绩": [" "],
  "存在问题": "  ",
  "下一步工作打算": [],
  "成文日期": "　"
}
```
