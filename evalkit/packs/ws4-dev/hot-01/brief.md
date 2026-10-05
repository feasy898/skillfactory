# 任务：把一组卖点整理成短视频口播稿骨架

## 输入

- `fixtures/input.json`：`{"platform": "dy", "topic": <主题>, "points": [<卖点1>, <卖点2>, <卖点3>]}`。

## 输出（写到 `out/` 目录）

**1. `out/structure.json`**，顶层键依次为：

```
template_version, platform, platform_name, structure_name, topic,
points_input_count, points_used, points_unused, element_count, elements, placeholder_stats
```

- `platform` = `"dy"`；`platform_name` = `"短视频口播稿"`；`structure_name` = `"3秒钩子 + 痛点 + 价值点×3 + 行动号召"`；
- `topic` = 输入主题；`points_input_count` = 输入卖点条数；
- `points_used` + `points_unused` 合起来必须恰等于输入 `points` 全集（不多不少不重）；
- `elements` 为对象数组，每个元素 `{"name": <要素名>, "content": <内容>}`，**name 序列逐字为**：
  `["钩子", "痛点", "价值点1", "价值点2", "价值点3", "行动号召"]`（共 6 个，`element_count` = 6）；
- 每个要素 `content` 非空；
- `placeholder_stats` = `{"slots": 3, "filled": 3, "placeholders": 0}`（本任务卖点恰 3 条，全部用上）。

**2. `out/骨架.md`**：正文按要素顺序，每行一段，格式 `【要素名】内容`（要素名与 structure.json 一致）。

## 判定要点（判定即按此执行）

- 钩子内容 ≥ 8 个字符；行动号召内容含 `关注`/`评论`/`私信`/`点击` 至少一词；
- `价值点N` 的内容必须逐字包含对应的第 N 条卖点；
- **合规红线**：两个输出文件中不得出现下列绝对化用语（源自《中华人民共和国广告法》第九条及市场监管公开解读词样）：
  `国家级`、`世界级`、`最高级`、`最佳`、`第一`、`顶级`、`独家`、`万能`、`百分百`、`绝对`、`永久有效`、`全网第一`；
- 不得残留 `{{ }}` 形式的模板占位。

## 环境

- 纯文本/JSON 产出，无需联网。
