# goldens 标注翻改登记（RELABEL · A-09）

> 依据：owner-delegated-signing-20261008.md A-09「标注不可静默翻改」——verdict.json
> 一经写入不得静默改写；任何翻改必须在本登记簿留痕（旧值/新值/理由）。
>
> 本轮翻改依据：**alpha 开卷裁决（2026-10-08，owner 委托，对 checker 输出开卷）**
> 对 ofc 三题 D3 真实对拍 9 处分歧定谳：6 处 checker-wrong（修判卷器，
> evalkit/CHANGELOG.md FIX-C10）+ 3 处 annotation-wrong（本登记簿翻改金标）。
> 三份样本的 `product/` 与 `product_sha256` 均未变动（翻改前逐样本复算
> hash_tree(product) == verdict.product_sha256 全对）；`annotator`
> （"owner 委托 alpha 代行"）与 `annotator_kind`（"delegated-signing-model"）不变；
> 仅 `expected_pass` 字段按裁决翻改。

## 1. bench/devpool-r1/goldens/ofc-01/s07/verdict.json

- source：`handmade:blankpara-after-title-indent4`
- 旧值：`"expected_pass": false`
- 新值：`"expected_pass": true`
- 理由（alpha 裁决 reasoning 要点）：产物为标题后多一空段 + fields.json 采用 4 空格
  缩进的序列化变体。题面只规定「正文每字段一段 `字段名：值`、缩进 20–28 磅档、
  落款两段右对齐只写值、fields.json 记账与输入一致」，**未禁止**空段存在，也**未
  规定** fields.json 的缩进风格（JSON 语义与空白无关）；四个下划线、全角冒号、
  值逐字、记账集合等实质条款全部达标。rubric 裁判不得在题面之外自行加码
  （「空段/缩进风格」属加码），判 checker-wrong 不成立，故金标翻改为应过。

## 2. bench/devpool-r1/goldens/ofc-02/s06/verdict.json

- source：`handmade:blankpara-before-sign-single-line-json`
- 旧值：`"expected_pass": false`
- 新值：`"expected_pass": true`
- 理由（alpha 裁决 reasoning 要点）：产物为落款前多一空段 + fields.json 单行紧凑
  序列化（无缩进换行）。同上：题面未禁止空段，JSON 序列化风格（紧凑 vs 缩进）
  不在题面约束面内；缺失字段「资金来源：____」「联系电话：____」合规呈现、
  记账集合一致、值逐字含全角，实质条款全部达标。rubric 裁判不自行加码，
  金标翻改为应过。

## 3. bench/devpool-r1/goldens/ofc-03/s11/verdict.json

- source：`handmade:fields-json-arrays-reversed`
- 旧值：`"expected_pass": false`
- 新值：`"expected_pass": true`
- 理由（alpha 裁决 reasoning 要点）：fields.json 的 `filled_fields`/`missing_fields`/
  `fields` 三数组整体倒序。题面对清单的措辞是「两个清单与 `fields` 两种 status 的
  字段名**集合**一致」（ofc-03/brief.md 判定要点），即**集合一致语义**，未规定
  数组元素次序；docx 侧缺失「参会人员：____」合规、值逐字含全角达标。
  按题面集合语义判应过，金标翻改。

---

- 登记：SF-0006-OFCFIX 第 1 轮（执行=dev GLM-5.3-Flash，2026-10-08）
- 配套判卷器修复（6 处 checker-wrong，不动本登记簿样本）：见 evalkit/CHANGELOG.md
  FIX-C10（全角冒号+字段前缀检查 / 缺失判定去「____」全篇兜底 /
  fields[].value 与输入回对）。
