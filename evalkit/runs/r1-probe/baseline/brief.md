# 任务简报：会议转写稿说话人标签映射（两臂逐字相同）

## 背景

会议录音经说话人分离（diarization）后，导出的转写稿里每个发言人的标签是机器编号
（形如 `SPEAKER_00`）。客户要拿到的是**能直接读的稿子**：把机器编号换成真实姓名或职务，
其余内容一个字节都不能动。

本任务的业务成果 = **一份可交付的映射后转写稿集合**（改好的 `.txt` 稿子 + 可追溯的告警存档
+ 标签扫描清单），任何人拿到都能自检。

## 你拿到的输入

本目录 `inputs/` 下 6 个文件，两类：

| 类别 | 文件 | 内容 |
|---|---|---|
| 转写稿 | `normal.txt` | 标准会议：3 个说话人、10 条发言 |
| 转写稿 | `partial.txt` | 评审会：4 个说话人、10 条发言（有中途加入的新面孔） |
| 转写稿 | `empty.txt` | 口述整理稿：无说话人标签 |
| 标签映射表 | `m_full.json` | 三个标签都填了姓名 |
| 标签映射表 | `m_partial.json` | 只填了其中两个标签 |
| 标签映射表 | `m_empty.json` | 空表（一个都没填） |

## 你要交付什么

在**本任务工作目录**（你启动时所在的目录）下产出一个**产物根目录** `out/`，
里面是**平铺的 24 个文件**（不建子目录）：

```
out/normal__m_full.txt          out/normal__m_full.stderr.txt
out/normal__m_partial.txt       out/normal__m_partial.stderr.txt
out/normal__m_empty.txt         out/normal__m_empty.stderr.txt
out/partial__m_full.txt         out/partial__m_full.stderr.txt
out/partial__m_partial.txt      out/partial__m_partial.stderr.txt
out/partial__m_empty.txt        out/partial__m_empty.stderr.txt
out/empty__m_full.txt           out/empty__m_full.stderr.txt
out/partial... 同上三组 ...
out/empty__m_partial.txt        out/empty__m_partial.stderr.txt
out/empty__m_empty.txt          out/empty__m_empty.stderr.txt
out/discover__normal.json       out/discover__normal.stderr.txt
out/discover__partial.json      out/discover__partial.stderr.txt
out/discover__empty.json        out/discover__empty.stderr.txt
```

即：**3 转写稿 × 3 映射表 = 9 个映射产物（.txt）+ 9 个对应的 stderr 存档（.stderr.txt）
+ 3 个标签扫描草稿（.json）+ 3 个对应的 stderr 存档 = 24 个文件。**
命名规则：`<转写稿名>__<映射表名>.<扩展名>` 与 `discover__<转写稿名>.<扩展名>`。

## 硬性要求

1. **自己造工具**：你必须在本目录内自己写一个 Python 脚本（建议命名 `map_speakers.py`，
   只用标准库）来完成映射与扫描，并用它生成全部 24 个文件。
   **禁止从本目录之外的任何位置读取脚本、手册或参考资料**——本任务只允许用你写出来的代码。
2. **只换标签**：只允许替换行首的说话人标签（`SPEAKER_00` 这一段）。时间戳段、冒号、
   空白、正文内容、**行数**、**行尾风格**（CRLF/LF）全部保持与输入逐字节一致。
3. **不猜名**：映射表里没有的标签，原样保留，并在 stderr 里汇总告警
   （形如 `WARNING: 未映射说话人标签 "X"，出现 N 次`）。映射表里的键在转写稿中不存在时，
   也要告警（形如 `WARNING: 映射键 "X" 在转写稿中未出现`）。
   绝不允许自己编造姓名去填未映射的标签。
4. **相对路径产出**：所有 24 个文件必须在 `out/` 目录作为 **cwd**、以**相对路径**写出。
   stderr 要分别重定向到各自的 `.stderr.txt` 存档文件。
   每次成功写出会向 stderr 打一行汇总信息（形如 `INFO: 写出 …（共 N 行，替换 X 处，未映射 Y 种）`），
   这行信息也要进对应的 `.stderr.txt` 存档。
5. **扫描草稿**：对每个转写稿另做一次标签扫描（发现模式），产出 JSON，含四个字段：
   - `transcript`：输入文件路径回显（以 `<转写稿名>.txt` 结尾）
   - `total_utterances`：带标签的发言条数
   - `speakers`：数组，每项 `{label, utterances}`，**按标签首次出现顺序**排列
   - `draft_mapping`：对象，每个标签映射到空字符串 `""`
6. **退出码语义**（脚本须遵守，验收会看）：
   - `0` = 成功（**含**「有告警但成功」的情况）
   - `1` = 映射文件不是合法 JSON
   - `2` = 输入文件不存在 / 命令行参数错误
7. **确定性**：同样的输入重跑，产物必须逐字节一致。不许用网络、不许用随机数、不许在产物里
   写时间戳。

## 完成后

把 24 个文件留在 `out/` 里不要清理。不用写 README，不用写总结报告。
