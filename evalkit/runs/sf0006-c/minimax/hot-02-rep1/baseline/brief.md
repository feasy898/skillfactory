# 任务：把一组卖点整理成图文笔记骨架

## 输入

- `fixtures/input.json`：`{"platform": "xhs", "topic": <主题>, "points": [<卖点1>, <卖点2>, <卖点3>]}`。

## 输出（写到 `out/` 目录）

**1. `out/structure.json`**，顶层键依次为：

```
template_version, platform, platform_name, structure_name, topic,
points_input_count, points_used, points_unused, element_count, elements, placeholder_stats
```

- `platform` = `"xhs"`；`platform_name` = `"图文笔记"`；`structure_name` = `"数字标题 + 开头 + 要点×3 + 标签"`；
- `topic` = 输入主题；`points_input_count` = 输入卖点条数；
- `points_used` + `points_unused` 合起来必须恰等于输入 `points` 全集（不多不少不重）；
- `elements` 为对象数组，每个元素 `{"name": <要素名>, "content": <内容>}`，**name 序列逐字为**：
  `["标题", "开头", "要点1", "要点2", "要点3", "标签"]`（共 6 个，`element_count` = 6）；
- `placeholder_stats` = `{"slots": 3, "filled": 3, "placeholders": 0}`（本任务卖点恰 3 条，全部用上）。

**2. `out/骨架.md`**：正文按要素顺序，每行一段，格式 `【要素名】内容`（要素名与 structure.json 一致）。

## 判定要点（判定即按此执行）

- `标题` 内容必须同时：含至少一个阿拉伯数字、含至少一个 emoji 表情字符（如 ✅🔥💡📌🌱）；
- `标签` 内容为空格分隔的话题标签，形如 `#标签1 #标签2`，数量在 3–8 个之间；
- `要点N` 的内容必须逐字包含对应的第 N 条卖点；
- **合规红线**：两个输出文件中不得出现下列绝对化用语（源自《中华人民共和国广告法》第九条及市场监管公开解读词样）：
  `国家级`、`世界级`、`最高级`、`最佳`、`第一`、`顶级`、`独家`、`万能`、`百分百`、`绝对`、`永久有效`、`全网第一`；
- 不得残留 `{{ }}` 形式的模板占位。

## 环境

- 纯文本/JSON 产出，无需联网。
