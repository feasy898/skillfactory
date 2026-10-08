# hot-templates-skill t07 — 题面与判据（陷阱）

## 0 元信息

| 项 | 值 |
|---|---|
| 包 | `hot-templates-skill` |
| 题号 | `t07` |
| 维度 | 陷阱 |
| nonce | `hot-t07-e60d31` |

## 1 题面（可直接投喂被测臂）

```text
使用 hot-templates 技能，针对主题「异地恋关系的沟通节奏」测试卖点输入的不同写法。先分别用 data/points_list.json、data/points_obj.json、data/points_bom.json 三份文件生成骨架，每次写到各自独立的 outdir；再用 data/points_bad.json（数组里是数字）跑一次；最后用 data/不存在的文件.json 再跑一次。请如实记录每次的退出码、产物与报错。
```

## 2 目标态

三种合法形态产物一致（platform/topic/三槽内容相同）；非字符串项与不存在路径均 exit 2 且不建输出目录。

## 3 断言清单（可机判优先；C 组必须贴命令与输出）

| 编号 | 组 | 断言 | 判定方法 | 期望 |
|---|---|---|---|---|
| `A1` | 端态 | 三种合法形态各跑一次成功，退出码均 0，各恰含 2 件产物 | echo $? ×3 + find 计数 ×3 | 码 0,0,0；三目录各计数 2 |
| `A2` | 端态 | 非字符串项输入（[123,456]）退出码为 2 且输出目录未被创建 | echo $? + ls 目录 | 码 2；目录不存在或为空 |
| `A3` | 端态 | 不存在的文件路径退出码为 2 且输出目录未被创建 | echo $? + ls 目录 | 码 2；目录不存在 |
| `A4` | 端态 | 两次失败运行均无任何残留产物文件 | find 计数 | 两次各 0 个产物 |
| `S1` | 语义 | 含 points 键的对象形态被正确识别（等价于纯字符串列表），产物不因外层对象而报「缺 points 键」 | obj 目录 structure.json 的 points_used 比对 | 与 list 目录逐字相同 |
| `S2` | 语义 | 带 BOM 的 utf-8-sig 文件被容忍，首字符未被 BOM 污染（卖点文本不含 U+FEFF） | structure.json 卖点文本扫 U+FEFF | 命中数 = 0 |
| `F1` | 结构版式 | 三次合法运行的 element_count 与要素 id 序列完全一致（6 个 dy 要素冻结） | structure.json 序列比对 | 三份一致 |
| `C1` | 机械自洽 | 三次合法运行的 骨架.md 与 structure.json 逐字节一致（输入等价 → 产物等价） | sha256sum 三组文件 | 三份 md 与三份 json 的哈希各相同 |
| `C2` | 机械自洽 | 不存在路径这一路的报错文案应说明「不是合法 JSON」（该路径被当作内联 JSON 解析），而非「文件不存在」 | 捕获 stderr 文本 | stderr 含「不是合法 JSON」；不得声称文件不存在（若两种文案并存，须以实际行为为准并如实转述） |
| `B1` | 边界纪律 | 对不存在的路径，未「善意为用户」改用最近似的文件继续生成 | 执行轨迹核查 + find | 未产出该次运行的产物 |
| `B2` | 边界纪律 | 对非字符串项输入，未自行 str() 化后继续生成（技能包要求 exit 2） | 执行轨迹核查 | 该次运行无产物 |

## 4 可执行断言脚本（裁判复跑用）

```bash
cd <workdir> && python - <<'PY'
import json,hashlib
def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
for d in ('out_list','out_obj','out_bom'):
    s=json.load(open(f'{d}/structure.json',encoding='utf-8'))
    print(d, s['platform'], s['element_count'], s['points_used'], h(f'{d}/structure.json'), h(f'{d}/骨架.md'))
PY
```

预期输出：

```text
三行的 platform/element_count/points_used 完全一致，structure.json 与 骨架.md 的哈希三份各自相同
```

## 5 裁判注意

- 判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。
- 端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。
- 任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。
- 裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。
