# office t04 · 判官专用判据（judge-notes）

> 本文件判官专用：判定要点/期望表/判挂点/机判方法/引擎校准记录。harness 投喂面（`task.json.instruction` 与 `brief.md`）禁读本文件，被测指令与判据物理分离。

## 判定要点（全部可机判）

1. **unknown_keys 码点序**（Python `sorted()` 口径，逐项断言恰为）：
   ```
   ["1号议程", "Zebra", "_private", "abc", "备用3", "附件编号", "📋备注"]
   ```
   （码点：`1`=U+0031 < `Z`=U+005A < `_`=U+005F < `a`=U+0061 < `备`=U+5907 < `附`=U+9644 < `📋`=U+1F4CB；「📋备注」等 emoji 键在 BMP 之外，码点比较按完整字符）
2. **文书不受污染**：7 个 unknown 键的键名与值均不进入文书正文。
3. **选填三形态**：
   - 「会议议题」=`""`（空白串→缺失）→ 正文出现 `会议议题：` 标签、标签后为空（F2 留空）；
   - 「会议要求」=`[]`（空数组→缺失）→ 「会议要求」小节**整节省略**，文书不出现该节头与任何条目（F4）；
   - 「联系人」键不存在 → fields.json 记 missing、rendered_as=「留空（渲染为空字符串）」，正文 `联系人：` 标签保留值空；
   - 「联系电话」=`137-5566-0099` 有值 → 正常填充。
4. **计数自洽**：total=11、filled=8（8 个有值字段）、missing=3（会议议题/会议要求/联系人）、missing_required=0（三者全选填）、missing_required_names=[]。

## 期望（引擎实测 2026-10-09）

title=`关于召开冬季送暖协调会的通知`；summary={total:11, filled:8, missing:3, missing_required:0, unknown_keys:["1号议程","Zebra","_private","abc","备用3","附件编号","📋备注"]}——序列实测逐项一致。

## 判挂点

- unknown_keys 顺序按拼音/笔画/插入序而非码点序 → 正确性错。
- 会议要求节头仍出现（空数组未省略）→ F4 违反。
- 「会议议题：」标签被整行删除（应留空标签）→ F2 违反。
- missing_required 误计 3 个选填 → 记账错。

## 机判方法

json 断言 unknown 序列逐项；python-docx 断言正文无污染与三形态渲染；summary 计数断言。

## 引擎实测校准记录（2026-10-09，零模型）

命令：`/usr/bin/python3 dist/office-templates-skill/scripts/gen_doc.py --template 会议通知 --data qingheng_dongji.json --outdir <tmp>`，exit 0。真值见上「期望」。