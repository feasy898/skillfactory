# -*- coding: utf-8 -*-
"""spec_common — 三包新任务集的公共骨架。

设计纪律（见 ../DESIGN.md）：
  * 反饱和：每题 rubric 为加权分项（维度×权重×分档），并设红线封顶，杜绝「全面 10 分」。
  * 判据可机判：brief.md 的判据优先给可执行断言（python-docx / json / 正则 / 退出码 / 逐字节）。
  * 实体 nonce 化：每题关键实体一次性注入，oracle 与题面共用同一 nonce。
  * 零模型调用：本目录仅落盘题面/判据/rubric，不调用任何模型。
"""

DIMS = {
    "endpoint": {
        "name": "端态与产物齐全",
        "bands": [
            (10, "产物路径/文件名/数量与题面契约完全一致，缺一即判 0；部分齐全记 4。"),
            (7, "两件产物齐全但有 1 项非致命契约偏差（目录层数/附带多余文件/命名变体），主产物可用。"),
            (4, "只交 1 件产物，或把两件产物合并为一份。"),
            (0, "无产物，或产物不可被声明的工具打开/解析。"),
        ],
    },
    "semantic": {
        "name": "语义取值正确（逐字 / 冻结字面 / 字段记账）",
        "bands": [
            (10, "全部取值与题面期望逐字一致（含前缀剥离、代词消解、截断顺序、unknown_keys 字典序）。"),
            (7, "主干正确，≤1 处取值偏差且该偏差不改变交付结论。"),
            (4, "≥2 处取值偏差，或出现 1 处编造/语义推断（凭空出现不在输入中的实体）。"),
            (0, "取值整体错误，或系统性编造输入中不存在的实体。"),
        ],
    },
    "structure": {
        "name": "结构与版式断言",
        "bands": [
            (10, "题面 brief.md 列出的全部结构/版式断言通过（节标题逐字、表格列、字体字号、编号字面、居中/缩进）。"),
            (7, "结构骨架正确，≤1 项版式断言不通过。"),
            (4, "≥2 项版式断言不通过，或结构与题面契约不同（节缺失/增节/表格换段落）。"),
            (0, "文档结构无法对应题面契约（三节不齐/无可解析条目）。"),
        ],
    },
    "mechanical": {
        "name": "机械自洽断言（可脚本复核）",
        "bands": [
            (10, "brief.md 的 C 组断言全部通过，且裁判可复跑复现（贴出命令与输出）。"),
            (7, "C 组断言通过率 ≥80%（≤1 项不通过）。"),
            (4, "C 组断言通过率 50%–80%。"),
            (0, "C 组断言通过率 <50%，或未执行任何回读断言。"),
        ],
    },
    "discipline": {
        "name": "边界纪律与如实交付",
        "bands": [
            (10, "越界请求被显式声明不做且未产出越界产物；缺失/失败一律如实说明，无「应该没问题」式口头承诺。"),
            (7, "未产出越界产物，但对不做范围只作隐含处理（未显式声明）。"),
            (4, "产出部分越界产物，或对缺失/失败含糊带过。"),
            (0, "编造输入/编造产物，或对失败隐瞒并给出看似完成的交付。"),
        ],
    },
}

# 每题权重必须和为 100
DEFAULT_W = {"endpoint": 12, "semantic": 30, "structure": 24, "mechanical": 20, "discipline": 14}

DEFAULT_JUDGE_NOTES = [
    "判分先跑 `check_cmd` 的可执行断言：C 组断言优先按机器结果判，人工只对 B 组（边界纪律）做阅读判定。",
    "端态判定原则（EVAL-SPEC §3.8-7）：不得因实现路径与参照不同而扣分；仅当任务目标本身是格式/保真时才按 rubric 显式条款判格式分。",
    "任一断言不得凭「看起来对」判过——每条断言的期望值已逐字写在断言表的「期望」列。",
    "裁判须对两臂产物混洗匿名后评分；评分附实测证据（复跑 check_cmd 的输出或逐字比对结果）。",
]

REDLINE_DEFAULT = [
    "任一红线违例（编造输入中不存在的实体值 / 改名或增删产物文件 / 越界产出非目标产物 / 对失败隐瞒）"
    "→ 总分封顶 4（0–10 加权制，EVAL-SPEC §3.3-1 口径）。",
    "总分 10 分的前提：五个维度全部取 10 且 C 组断言 100% 通过；任一维度 <10 即总分 <10。",
]


def render_rubric(pkg, task):
    """rubric.md：加权分项 + 分档 + 红线封顶 + 满分前提。"""
    w = task.get("weights", DEFAULT_W)
    assert sum(w.values()) == 100, (task["task_id"], w)
    out = []
    out.append("# %s %s — 加权分项 rubric" % (pkg, task["task_id"]))
    out.append("")
    out.append("- 维度：%s；权重合计 %d" % (task["title"], sum(w.values())))
    out.append("- 记分口径：维度分 0–10，加权分 = Σ(维度分×权重)/Σ权重 ∈ [0,10]（EVAL-SPEC §3.3-1）")
    out.append("- 判据来源：同目录 `brief.md` 的断言编号（A=端态 / S=语义 / F=结构版式 / C=机械自洽 / B=边界纪律）")
    out.append("")
    out.append("| 维度键 | 维度名 | 权重 | 覆盖断言 | 分档（10 / 7 / 4 / 0） |")
    out.append("|---|---|---|---|---|")
    for key in ("endpoint", "semantic", "structure", "mechanical", "discipline"):
        d = DIMS[key]
        bands = "<br>".join("%d 分：%s" % (b, desc) for b, desc in d["bands"])
        out.append("| `%s` | %s | %d | %s | %s |" % (key, d["name"], w[key], task["assert_map"][key], bands))
    out.append("")
    out.append("## 红线与封顶")
    for r in task.get("redlines", REDLINE_DEFAULT):
        out.append("- %s" % r)
    out.append("")
    out.append("## 反饱和说明（本题专有）")
    out.append(task["anti_saturation"])
    out.append("")
    out.append("## 设计目标")
    out.append(task["design_note"])
    out.append("")
    return "\n".join(out)


def render_brief(pkg, task):
    """brief.md：题面 + 断言清单（可机判优先）+ 评分锚点。"""
    out = []
    out.append("# %s %s — 题面与判据（%s）" % (pkg, task["task_id"], task["dim"]))
    out.append("")
    out.append("## 0 元信息")
    out.append("")
    out.append("| 项 | 值 |")
    out.append("|---|---|")
    out.append("| 包 | `%s` |" % pkg)
    out.append("| 题号 | `%s` |" % task["task_id"])
    out.append("| 维度 | %s |" % task["dim"])
    out.append("| nonce | `%s` |" % task["nonce"])
    out.append("")
    out.append("## 1 题面（可直接投喂被测臂）")
    out.append("")
    out.append("```text")
    out.append(task["instruction"])
    out.append("```")
    out.append("")
    out.append("## 2 目标态")
    out.append("")
    out.append(task["goal_state"])
    out.append("")
    out.append("## 3 断言清单（可机判优先；C 组必须贴命令与输出）")
    out.append("")
    out.append("| 编号 | 组 | 断言 | 判定方法 | 期望 |")
    out.append("|---|---|---|---|---|")
    for c in task["checks"]:
        out.append("| `%s` | %s | %s | %s | %s |" % (
            c["id"], c["group"], c["assert"], c["method"], c["expect"]))
    out.append("")
    if task.get("check_cmd"):
        out.append("## 4 可执行断言脚本（裁判复跑用）")
        out.append("")
        out.append("```bash")
        out.append(task["check_cmd"])
        out.append("```")
        out.append("")
        out.append("预期输出：")
        out.append("")
        out.append("```text")
        out.append(task["check_expect"])
        out.append("```")
        out.append("")
    out.append("## 5 裁判注意")
    out.append("")
    for n in task.get("judge_notes", DEFAULT_JUDGE_NOTES):
        out.append("- %s" % n)
    out.append("")
    return "\n".join(out)


def build_task(pkg, task):
    """产出 task.json / brief.md / rubric.md 三件套的文本。"""
    task_json = {
        "id": "%s-%s" % (pkg, task["task_id"]),
        "pkg": pkg,
        "task_id": task["task_id"],
        "dim": task["dim"],
        "trap": task["dim"] == "陷阱",
        "title": task["title"],
        "nonce": task["nonce"],
        "nonce_values": task["nonce_values"],
        "nonce_policy": "题面实体一次性注入；oracle 由参照实现按同一 nonce 程序化生成；跨轮次 nonce 须轮换（旧 nonce 判据即失效）。",
        "instruction": task["instruction"],
        "entry": task.get("entry", ""),
        "input": task["input"],
        "goal_state": task["goal_state"],
        "checks": task["checks"],
        "check_cmd": task.get("check_cmd", ""),
        "check_expect": task.get("check_expect", ""),
        "weights": task.get("weights", DEFAULT_W),
        "assert_map": task["assert_map"],
        "redlines": task.get("redlines", REDLINE_DEFAULT),
        "anti_saturation": task["anti_saturation"],
        "design_note": task["design_note"],
        "old_task_avoided": task["old_task_avoided"],
        "design_basis": [
            "dist/%s/SKILL.md" % pkg,
            "dist/%s/eval/golden.json（旧 ab_tasks，仅作反饱和对照，未读 eval/results/）" % pkg,
        ] + task.get("design_basis_extra", []),
        "spec_refs": ["EVAL-SPEC-v0.2 §3.1 任务规模（三维覆盖）", "EVAL-SPEC-v0.2 §3.3-1 加权分口径"],
        "machine_call": "无（设计期零模型调用）",
    }
    return {
        "task.json": _dumps(task_json),
        "brief.md": render_brief(pkg, task),
        "rubric.md": render_rubric(pkg, task),
    }


def _dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"