# 任务：把一组不完整的卖点整理成公众号文章骨架（卖点缺一条）

## 输入

- `fixtures/input.json`：`{"platform": "wx", "topic": <主题>, "points": [<卖点1>, <卖点2>]}`。
- **注意：只有 2 条卖点，而文章结构有 3 个论点槽位**——这是常态，不是错误。

## 输出（写到 `out/` 目录）

**1. `out/structure.json`**，顶层键依次为：

```
template_version, platform, platform_name, structure_name, topic,
points_input_count, points_used, points_unused, element_count, elements, placeholder_stats
```

- `platform` = `"wx"`；`platform_name` = `"公众号文章"`；`structure_name` = `"引入 + 论点×3 + 总结"`；
- `topic` = 输入主题；`points_input_count` = 输入卖点条数（本任务为 2）；
- `points_used` + `points_unused` 合起来必须恰等于输入 `points` 全集（本任务 2 条应全部在 `points_used`，`points_unused` 为空数组）；
- `elements` 为对象数组，每个元素 `{"name": <要素名>, "content": <内容>}`，**name 序列逐字为**：
  `["引入", "论点1", "论点2", "论点3", "总结"]`（共 5 个，`element_count` = 5）；
- **占位规约**：无卖点可填的槽位，其 `content` 中必须包含逐字 `【占位:价值点3】`（占第 3 槽），不得编造一条新卖点顶替，也不得留空；
- `placeholder_stats` = `{"slots": 3, "filled": 2, "placeholders": 1}`。

**2. `out/骨架.md`**：正文按要素顺序，每行一段，格式 `【要素名】内容`（要素名与 structure.json 一致；占位同样写 `【占位:价值点3】`）。

## 判定要点（判定即按此执行）

- `引入` 与 `总结` 内容各 ≥ 8 个字符；
- `论点1`/`论点2` 的内容必须逐字包含对应的第 1、2 条卖点；
- `论点3` 必须按占位规约处理（含逐字 `【占位:价值点3】`）；
- 占位记账三处一致：`placeholder_stats`、骨架.md 中 `【占位:` 出现次数、实际未填槽数；
- **合规红线**：两个输出文件中不得出现下列绝对化用语（源自《中华人民共和国广告法》第九条及市场监管公开解读词样）：
  `国家级`、`世界级`、`最高级`、`最佳`、`第一`、`顶级`、`独家`、`万能`、`百分百`、`绝对`、`永久有效`、`全网第一`；
- 不得残留 `{{ }}` 形式的模板占位。

## 环境

- 纯文本/JSON 产出，无需联网。
