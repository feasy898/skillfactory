# -*- coding: utf-8 -*-
"""spec_mm — meeting-minutes-skill 新任务集（t01–t08）。

旧题考点（反饱和对照，见 ../DESIGN.md 差异表）：
  ab-001 case1：常规分类 + 待办表格 + 噪声抑制（含「不能延期」归风险）
  ab-002 case3：同行多类关键词优先级（延期+结论→决议）+ 「截止到周五」未被规则5 的「明天」抢走
  ab-003 case2：负责人「我」→说话人 + 期限规则2（5月20日之前）+ 收尾行含结论仍收录
未使用的旧输入：reference/inputs/case4.txt（全噪声）。
本集新考点：解析正则容错 / 元信息行逐字格式 / 期限规则 1·4·6 / 负责人规则 2·4 与规则序 /
  全噪声空纪要 / 输入不存在不顶替 / 无时间戳含关键词行必丢弃 / 条目精确集合与互斥 /
  docx↔summary↔元信息三向自洽 + 双跑确定性。
"""
from spec_common import DEFAULT_W

PKG = "meeting-minutes-skill"

N = {
    "t01": "mm-t01-7c41e0",
    "t02": "mm-t02-b2d905",
    "t03": "mm-t03-5ae318",
    "t04": "mm-t04-91f6c2",
    "t05": "mm-t05-4e0ad7",
    "t06": "mm-t06-d3b85f",
    "t07": "mm-t07-6a29e4",
    "t08": "mm-t08-c814b6",
}

# ---------------------------------------------------------------- 输入素材（nonce 化）

T01_LINES = [
    "[9:05] 田伟: 早，人到齐了咱们先过一遍这季度的排产，口头同步一下细节。",
    "[09:07] 陆娟: 这个季度的交付口径我们内部结论是按批次走，不按单件。",
    "[09:08] 田伟:同意,那这条写进纪要,后面谁再改要走变更流程。",
    "[09:12] 章明·计划: 供应商那边我负责去谈价格，谈完我同步给你们。",
    "[09:14] 施琳: 我担心排产如果延期，会连带影响后端验收，这块要提前准备。",
    "[09:16] 陆娟: 另外需要确认一下质检窗口，质检组那边还没回话。",
    "散会散会，大家辛苦了。",
    "[09:18] 施琳: 补充一句，纪要发出前麻烦各方过一眼，结论以会签版为准。",
]

T02_LINES = [
    "[13:01] 章明·计划: 第一件事，设备点检表需要在本周内补齐，材料以 2026-11-03 定稿为准。",
    "[13:02] 陆娟: 第二件，排期表需要在本季度末前给出，中间版本不用发。",
    "[13:03] 施琳: 第三件，补充材料需要在本轮复盘前截止材料清单。",
    "[13:04] 田伟: 第四件，这项我记不准，需要等下再确认，先不写日期。",
    "[13:05] 章明·计划: 顺带把上个月的偏差说明一并补上，需要在星期二前交给我。",
    "[13:06] 陆娟: 提醒一句，交期不能再往后拖，风险在于下游已经排了产。",
    "[13:07] 田伟: 那就这样议定，偏差说明的口径以质量部意见为准。",
]

T03_LINES = [
    "[14:01] 田伟: 客户回访这块我负责牵头，纪要模板由陆娟维护。",
    "[14:02] 陆娟: 归档材料交给施琳负责，纸质件同步留一份。",
    "[14:03] 章明·计划: @田伟 请跟进一下这周的回访排期，排完发群里。",
    "[14:04] 施琳: 负责人：章明·计划，回访口径以客户签字版为准。",
    "[14:05] 田伟: 这条需要各科室自行安排负责人，我只提供模板。",
    "[14:06] 陆娟: 我负责评审排期，评审结论本周内同步给业务口。",
    "[14:07] 章明·计划: 有个风险，客户那边的联系人还没换人，口径可能会变。",
    "[14:08] 田伟: 那先按现口径准备，同意。",
]

T04_LINES = [
    "各位早上好，我们先等一下还没到的同事。",
    "[10:01] 田伟: 上次的台账我已经放到共享盘了，大家有空看看。",
    "好的好的。",
    "[10:03] 陆娟: 今天的议程稍后发群里，先这样。",
    "",
    "   ",
    "锘匡豢凌晨锛屾湁浜哄鍦ㄥ煶銆",
    "[10:06] 章明·计划: 好的，谢谢大家，散会。",
]

T06_LINES = [
    "结论：下次带方案再来讨论。",
    "[15:01] 田伟: 本次验收口径我同意按新版执行，旧版作废。",
    "[15:02] : 这条没有说话人，应该被丢弃。",
    "同意这个方案。",
    "[15:04] 陆娟: 质检窗口需要提前预约，预约不到就会延期，这点要盯住。",
    "有延期风险，大家注意。",
    "[15:06] 章明·计划: 我同意把回访口径写进纪要，后面按这个执行。",
    "[15:07] 施琳: 结论待会再议，这里先散会。",
    "这是散会行",
    "[15:09] 田伟: 风险点已经同步过了，没有别的要补充。",
]

T07_LINES = [
    "[16:01] 田伟: 交付窗口按客户回签日算，这个结论要写进纪要，需要陆娟同步给商务。",
    "[16:02] 陆娟: 回签日如果拿不到，我们需要启动备用方案，备用的责任人还没定。",
    "[16:03] 章明·计划: 这条我同意。",
    "[16:04] 施琳: 商务那边如果要延期通知，得提前三天，风险不小。",
]

# ---------------------------------------------------------------- 任务定义

def _f(name, lines):
    return {"files": [{"path": name, "encoding": "utf-8", "lines": lines}]}


TASKS = [
    {
        "task_id": "t01", "dim": "能力", "nonce": N["t01"],
        "title": "解析正则容错 + 三段分类 + 元信息行逐字格式",
        "nonce_values": {"说话人": ["田伟", "陆娟", "章明·计划", "施琳"],
                          "输入文件名": "transcript-8a6511.txt",
                          "关键口播字面": ["按批次走，不按单件", "先过一遍这季度的排产"]},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": _f("transcript-8a6511.txt", T01_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 这份会议转写稿整理成三段式纪要，"
            "产物写入 <outdir>，必须含 <outdir>/纪要.docx 与 <outdir>/summary.json。"
            "本稿的时间戳写法不统一（有一位的时、也有两位的时），分隔冒号中英文混用，"
            "有一个说话人的名字里带间隔点。请按技能包规则原样解析，不要自创格式，"
            "也不要把任何一句发言改写或概括。"),
        "goal_state": "三节齐全的纪要 docx + summary.json；解析容错正确（元信息行解析发言数与实际收录条目数相等）。",
        "assert_map": {
            "endpoint": "A1–A3",
            "semantic": "S1–S3",
            "structure": "F1–F3",
            "mechanical": "C1–C2",
            "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "<outdir> 恰含 纪要.docx 与 summary.json 两个文件，文件名逐字为「纪要.docx」「summary.json」",
             "method": "ls/find 计数 + python-docx 打开", "expect": "两文件存在且非空，find 计数=2"},
            {"id": "A2", "group": "端态", "assert": "脚本退出码为 0",
             "method": "echo $?", "expect": "0"},
            {"id": "A3", "group": "端态", "assert": "纪要.docx 可被 python-docx 打开并遍历段落与表格",
             "method": "python -c \"from docx import Document; ...\"", "expect": "无异常"},
            {"id": "S1", "group": "语义", "assert": "8 行中 7 行可解析为发言、1 行无法解析（散会行）；可解析行里恰好 6 行被收录（[9:05] 因零关键词丢弃）",
             "method": "逐条与源行逐字比对（去条目前缀后 == 源行内容）", "expect": "收录 6 条：决议 3（09:07 / 09:08 / 09:18）、待办 2（09:12 / 09:16）、风险 1（09:14）"},
            {"id": "S2", "group": "语义", "assert": "条目内容逐字等于源行内容，未改写、未概括、未补标点",
             "method": "docx 条目段落全文 in 源文件行集合", "expect": "6/6 逐字命中"},
            {"id": "S3", "group": "语义", "assert": "条目前缀时间为源行方括号内文本原样回显，一位时写法不回填零",
             "method": "正则 `^\\d+\\. 【([^】]+) · ([^】]+)】` 抽取前缀，与源行时间/说话人逐字比对",
             "expect": "09:12 行的条目前缀为「【09:12 · 章明·计划】」；若源用一位时则原样保留、不改写为两位"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字为「一、决议事项」「二、待办事项」「三、风险与关注」，顺序固定",
             "method": "遍历段落取加粗 14pt 段", "expect": "三节齐全、顺序一致、无增节"},
            {"id": "F2", "group": "结构版式", "assert": "待办节为 3 列表格，表头逐字为 事项/负责人/期限，Table Grid",
             "method": "doc.tables[0] 列数/首行单元格文本/样式名", "expect": "3 列；表头三项齐全；2 个数据行"},
            {"id": "F3", "group": "结构版式", "assert": "决议/风险条目格式为 `<i>. 【hh:mm · 说话人】内容`，编号从 1 连续",
             "method": "正则匹配 + 编号序列断言", "expect": "编号连续无跳号"},
            {"id": "C1", "group": "机械自洽", "assert": "元信息段逐字匹配 `来源：transcript-8a6511.txt ｜ 解析发言 6 条（决议 3 · 待办 2 · 风险 1）`",
             "method": "正则 `^来源：.* ｜ 解析发言 \\d+ 条（决议 \\d+ · 待办 \\d+ · 风险 \\d+）$` + 捕获数字比对",
             "expect": "格式与三个数字全部一致；合计数字 == 实际收录条目数 6"},
            {"id": "C2", "group": "机械自洽", "assert": "summary.json 四键与 docx 实际条数逐项一致，合计=三者和",
             "method": "json 读 summary + docx 计数互校", "expect": "{决议事项:3, 待办事项:2, 风险与关注:1, 合计:6}"},
            {"id": "B1", "group": "边界纪律", "assert": "未改写发言、未把「章明·计划」的间隔点删掉、未把半角冒号行丢弃后补写内容",
             "method": "条目全文与源行集合比对 + 裁判通读", "expect": "无改写、无编造"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "from docx import Document\n"
            "d=Document('<outdir>/纪要.docx')\n"
            "paras=[p.text for p in d.paragraphs]\n"
            "meta=[p for p in paras if p.startswith('来源：')][0]\n"
            "print('META_OK', bool(re.match(r'^来源：transcript-8a6511\\.txt ｜ 解析发言 6 条（决议 3 · 待办 2 · 风险 1）$', meta)))\n"
            "t=d.tables[0]\n"
            "print('TODO_HEADER', [c.text for c in t.rows[0].cells], 'ROWS', len(t.rows)-1)\n"
            "print('SUMMARY', json.load(open('<outdir>/summary.json',encoding='utf-8')))\n"
            "PY"
        ),
        "check_expect": "META_OK True / TODO_HEADER ['事项','负责人','期限'] ROWS 2 / SUMMARY {'决议事项': 3, '待办事项': 2, '风险与关注': 1, '合计': 6}",
        "anti_saturation": (
            "题面刻意打散格式（一位时 `[9:05]`、半角冒号、间隔点说话人），逐条断言精确到「期望条数 + 归属章节 + 前缀逐字」。"
            "旧 ab-001/002/003 的输入全部是两位时 + 全角冒号 + 规整说话人，裸模型凭常识即可一次做对；"
            "本题里任何一处把 `[9:05]` 补零成 `09:05`、把 `章明·计划` 截断、或丢掉半角冒号行，都会同时打掉 S1/S2/S3 与 C1，"
            "加权分至少掉 2 个维度的满分可能。"),
        "design_note": (
            "设计目标：强裸模型（不挂 skill，仅凭通用文档常识）通过率 ≤60%。分母=8 题，"
            "即 ≤4 题可判过。落点：旧 3 题考点已被完全排除，本题是格式容错题，裸模型最常见的失败是"
            "「统一格式后再输出」——这是 SKILL 明确禁止的（条目逐字引用、关键词命中即整句收录）。"),
        "old_task_avoided": [
            "不含 ab-001 的 case1 常规分类 / 「不能延期」归风险",
            "不含 ab-002 的同行多类优先级与「明天 vs 周五」期限对撞",
            "不含 ab-003 的「负责人是我」→说话人与规则2 期限",
            "不使用 case1/case2/case3 任一旧转写稿，也未使用旧 nonce 实体",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:28 解析正则",
            "dist/meeting-minutes-skill/references/docx-and-summary.md 元信息行与条目格式",
            "dist/meeting-minutes-skill/scripts/minutes.py:19-24 元信息格式串与条目前缀",
        ],
    },
    {
        "task_id": "t02", "dim": "能力", "nonce": N["t02"],
        "title": "期限规则 1/4/6 + 规则内前缀剥离 + 抓不到填「待定」",
        "nonce_values": {"说话人": ["章明·计划", "陆娟", "施琳", "田伟"],
                          "完整日期": "2026-11-03", "季度": "本季度末", "截止对象": "终稿闭环"},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": _f("transcript-8a6511.txt", T02_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>"
            "（纪要.docx + summary.json）。请特别留意「待办事项」表格里的「期限」列：每条待办的期限都只能"
            "按技能包的确定性规则从原句里取，取不到就填「待定」，绝对不要推断或改写成别的日期表述。"),
        "goal_state": "待办表格期限列 4 个数据格中 3 格为规则提取结果、1 格为「待定」，逐格等于期望字面。",
        "assert_map": {
            "endpoint": "A1–A2", "semantic": "S1–S5", "structure": "F1–F2",
            "mechanical": "C1–C2", "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "纪要.docx + summary.json 两件产物齐全",
             "method": "find 计数", "expect": "计数=2，文件名逐字一致"},
            {"id": "A2", "group": "端态", "assert": "退出码 0", "method": "echo $?", "expect": "0"},
            {"id": "S1", "group": "语义", "assert": "待办共 5 条（13:01/13:02/13:03/13:04/13:05）；决议 1 条（13:07）、风险 1 条（13:06）",
             "method": "doc.tables[0] 数据行数", "expect": "5 行"},
            {"id": "S2", "group": "语义", "assert": "13:01 行期限 = 「2026-11-03」（完整日期规则命中；句中同现的「本周内」属规则3，顺序即优先级故不得抢占）",
             "method": "取该行期限单元格文本，strip() 后逐字比对（参照实现对完整日期规则会带出一个尾随空格，判据按 strip 后字面比较，不把该空格设为考点）",
             "expect": "2026-11-03"},
            {"id": "S3", "group": "语义", "assert": "13:02 行期限 = 「本季度末」（季度规则整词命中，不剥离任何前缀）",
             "method": "逐字比对", "expect": "本季度末"},
            {"id": "S4", "group": "语义", "assert": "13:03 行期限 = 「材料清单」（前五条规则零命中，落「截止…」兜底规则，取其后 1–8 个非空白且非 ，。；; 的字符）",
             "method": "逐字比对", "expect": "材料清单"},
            {"id": "S5", "group": "语义", "assert": "13:04 行期限 = 「待定」（原句无任何时间语）",
             "method": "逐字比对", "expect": "待定，且不得写成「等下再确认」「未定」等自造值"},
            {"id": "C1", "group": "机械自洽", "assert": "期限列每格（strip 后）要么能在该条目内容原文中逐字找到，要么恰为「待定」",
             "method": "脚本：for each 期限 cell: (cell=='待定') or (cell in 对应事项原文)",
             "expect": "5/5 满足，无编造日期（参照实现规则1 命中时带出一个尾随空格，按 strip 后比对，不设为考点）"},
            {"id": "C2", "group": "机械自洽", "assert": "summary 待办数 == 表格数据行数 == 5；合计=三者和",
             "method": "json + docx 互校", "expect": "待办事项=5，合计=7（决议 1 / 待办 5 / 风险 1）"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字齐全、顺序固定", "method": "段落遍历", "expect": "齐全无增节"},
            {"id": "F2", "group": "结构版式", "assert": "待办表格 3 列表头为 事项/负责人/期限", "method": "表格首行", "expect": "三项齐全"},
            {"id": "B1", "group": "边界纪律", "assert": "未对「记不准」的句子猜测日期；未把「本周内」之类写入期限格",
             "method": "裁判逐格通读 + 命中表比对", "expect": "无推断值"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "from docx import Document\n"
            "t=Document('<outdir>/纪要.docx').tables[0]\n"
            "exp=['2026-11-03','本季度末','材料清单','待定','星期二前']\n"
            "got=[r.cells[2].text.strip() for r in t.rows[1:]]  # strip 后逐字比对\n"
            "print('GOT', got)\n"
            "print('DEADLINE_ALL_OK', got==exp)\n"
            "PY"
        ),
        "check_expect": "GOT ['2026-11-03','本季度末','材料清单','待定','星期二前'] / DEADLINE_ALL_OK True",
        "anti_saturation": (
            "本题只压 references/extraction-heuristics.md 的三条未测规则（完整日期 / 本(周|月|季度) / 「截止…」兜底）"
            "加一条 near-miss（无时间语 → 待定）。旧 ab-002 只测了「明天 vs 周五」，旧 ab-003 只测了规则2，"
            "规则 1/4/6 在旧题集里一次都没出现——裸模型最容易在规则6 上自由发挥（把「材料清单」改写成一个日期）"
            "或在规则1 上把「定稿为准」当成期限语义。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%（三包合计 8 题里本题属「中高难」档）。"
            "理由：本题需要先读 SKILL.md 的红线（「只按确定性规则提取、抓不到填待定」）再读 references 的六条规则表，"
            "凭通用常识作答的模型几乎必然在规则6 与「待定」两格上失分；且五格逐格断言，不允许「大部分对」蒙混。"),
        "old_task_avoided": [
            "不复现 ab-002 的「明天 vs 周五」规则3/规则5 对撞（同考点，本题刻意避开）",
            "不复现 ab-003 的规则2「5月20日之前」字面（本题改用规则1 的两种变体）",
            "不复现 ab-003 的「负责人是我」→说话人（留给 t03）",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/references/extraction-heuristics.md §2 六条期限规则与顺序即优先级",
            "dist/meeting-minutes-skill/scripts/minutes.py:52-62 DEADLINE_RULES 实现顺序",
        ],
    },
    {
        "task_id": "t03", "dim": "能力", "nonce": N["t03"],
        "title": "负责人四规则齐用 + 规则序（我负责 优先于 由X负责）+ near-miss 落「待定」",
        "nonce_values": {"说话人": ["田伟", "陆娟", "章明·计划", "施琳"],
                          "交给对象": "施琳", "@对象": "田伟", "字面负责人": "章明·计划"},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": _f("transcript-8a6511.txt", T03_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>"
            "（纪要.docx + summary.json）。请特别核对「待办事项」表格的「负责人」列：负责人只能按技能包的确定性规则"
            "从原句提取，抓不到就填「待定」；一句话里同时出现多种线索时也请按规则给出的先后顺序取第一种命中的。"),
        "goal_state": "待办表格负责人列 5 格：3 格为规则提取、1 格为说话人消解、1 格为「待定」，逐格等于期望。",
        "assert_map": {
            "endpoint": "A1–A2", "semantic": "S1–S5", "structure": "F1–F2",
            "mechanical": "C1–C2", "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全", "method": "find 计数", "expect": "计数=2"},
            {"id": "A2", "group": "端态", "assert": "退出码 0", "method": "echo $?", "expect": "0"},
            {"id": "S1", "group": "语义", "assert": "14:01 行负责人 = 说话人「田伟」（命中「我负责」，句中另有「由陆娟维护」不得抢占）",
             "method": "逐字比对", "expect": "田伟"},
            {"id": "S2", "group": "语义", "assert": "14:02 行负责人 = 「施琳」（「交给X负责」规则）",
             "method": "逐字比对", "expect": "施琳"},
            {"id": "S3", "group": "语义", "assert": "14:03 行负责人 = 「田伟」（@X 规则，X 后跟标点/行尾）",
             "method": "逐字比对", "expect": "田伟"},
            {"id": "S4", "group": "语义", "assert": "14:04 行负责人 = 「章明·计划」（「负责人：X」字面名，间隔点保留、不截断为「章明」）",
             "method": "逐字比对", "expect": "章明·计划"},
            {"id": "S5", "group": "语义", "assert": "14:05 行负责人 = 「待定」（「各科室自行安排负责人」不满足任一规则）",
             "method": "逐字比对", "expect": "待定"},
            {"id": "C1", "group": "机械自洽", "assert": "负责人列每格要么等于该行说话人、要么能在事项原文逐字找到、要么恰为「待定」",
             "method": "脚本三选一断言", "expect": "5/5 满足"},
            {"id": "C2", "group": "机械自洽", "assert": "summary 待办数 == 表格数据行数 == 5；全文合计 == 8（决议 2 / 待办 5 / 风险 1）",
             "method": "json + docx 互校", "expect": "待办事项=5，合计=8"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字齐全、顺序固定", "method": "段落遍历", "expect": "齐全无增节"},
            {"id": "F2", "group": "结构版式", "assert": "待办表格 3 列表头齐全", "method": "表格首行", "expect": "事项/负责人/期限"},
            {"id": "B1", "group": "边界纪律", "assert": "未为 14:05 行编造责任人（不得写「各科室」「自行安排」等非规则值）",
             "method": "裁判通读", "expect": "恰为「待定」"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "from docx import Document\n"
            "rows=Document('<outdir>/纪要.docx').tables[0].rows[1:]\n"
            "got=[r.cells[1].text.strip() for r in rows]\n"
            "print('OWNERS', got)\n"
            "print('S1_S5', got==['田伟','施琳','田伟','章明·计划','待定'])\n"
            "PY"
        ),
        "check_expect": "OWNERS ['田伟','施琳','田伟','章明·计划','待定'] / S1_S5 True",
        "anti_saturation": (
            "考点是「规则序 + 规则覆盖度」：旧 ab-003 只测了规则3 的代词消解（负责人是我），规则2 的「交给X负责」、"
            "规则4 的 @X、以及 near-miss（句中出现「负责人」二字但不满足规则3 的字面形式）三处均未被测过。"
            "本题同时压 S4 的间隔点边界（『章明·计划』含间隔点，按名符集应整体保留）与 S5 的 near-miss。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。本题的失败模式是「读懂语义后填一个合理的人名」——"
            "这正是技能包的红线禁止项；裸模型几乎必然在 S5（把「各科室自行安排负责人」填成某个人或「各科室」）"
            "和 S1（选了「陆娟」而不是走代词消解取说话人）上失分。"),
        "old_task_avoided": [
            "不复现 ab-003 的规则3 代词消解唯一例「负责人是我，本周五之前出结果」（本题改用规则1/2/3/4 各自独立成行）",
            "不复现 ab-003 的规则2 期限字面（期限不在本题断言范围）",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/references/extraction-heuristics.md §1 四条负责人规则（按序尝试）",
            "dist/meeting-minutes-skill/scripts/minutes.py:33-38 OWNER_RULES 与名符集/边界",
        ],
    },
    {
        "task_id": "t04", "dim": "边界", "nonce": N["t04"],
        "title": "全噪声输入 → 合法空纪要（三节保留 + 待办仅表头 + summary 全 0 + BOM 容忍）",
        "nonce_values": {"输入文件名": "transcript-8a6511.txt", "噪声行": 3,
                          "有效发言行": 3, "BOM": True},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": {"files": [{"path": "transcript-8a6511.txt", "encoding": "utf-8-sig（首字节 BOM EF BB BF）",
                             "lines": T04_LINES}]},
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>"
            "（纪要.docx + summary.json）。这份转写稿里有寒暄、散会、纯空白和一条乱码行，"
            "真正有实质内容的发言一行都没有。请如实产出反映这一事实的纪要，不要为了「看起来完整」"
            "而补写任何一条事项。"),
        "goal_state": "退出码 0 的合法空纪要：三节标题齐全、三个章节 0 条、待办表仅表头行、summary 四键全 0。",
        "assert_map": {
            "endpoint": "A1–A3", "semantic": "S1–S2", "structure": "F1–F3",
            "mechanical": "C1–C2", "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "退出码为 0（空/全噪声输入不是运行错误）",
             "method": "echo $?", "expect": "0，不报错退出"},
            {"id": "A2", "group": "端态", "assert": "两件产物仍齐全", "method": "find 计数", "expect": "计数=2"},
            {"id": "A3", "group": "端态", "assert": "docx 可被 python-docx 打开（空纪要也必须是合法 docx）",
             "method": "python-docx 打开", "expect": "无异常"},
            {"id": "S1", "group": "语义", "assert": "零条收录：文档中不含任何「n. 【hh:mm · 说话人】」形式的条目",
             "method": "正则全文扫描", "expect": "命中数 = 0"},
            {"id": "S2", "group": "语义", "assert": "未把寒暄行/散会行/乱码行改写成事项",
             "method": "裁判通读 + 与源行集合比对", "expect": "无任何条目文本取自源行"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字齐全且顺序固定，即使该节 0 条也不得删除标题",
             "method": "段落遍历找三节标题", "expect": "「一、决议事项」「二、待办事项」「三、风险与关注」三个都在"},
            {"id": "F2", "group": "结构版式", "assert": "待办表格仅表头行、0 个数据行",
             "method": "len(doc.tables[0].rows)", "expect": "行数 = 1"},
            {"id": "F3", "group": "结构版式", "assert": "元信息行格式与数字",
             "method": "正则捕获", "expect": "匹配 `来源：transcript-8a6511.txt ｜ 解析发言 0 条（决议 0 · 待办 0 · 风险 0）`"},
            {"id": "C1", "group": "机械自洽", "assert": "summary.json 四键全为 0，合计=0",
             "method": "json 读", "expect": "{决议事项:0, 待办事项:0, 风险与关注:0, 合计:0}"},
            {"id": "C2", "group": "机械自洽", "assert": "三向自洽：summary 三节数 == docx 实际条数 == 元信息行数字 == 0",
             "method": "脚本三方互校", "expect": "四者全为 0"},
            {"id": "B1", "group": "边界纪律", "assert": "首字节 BOM 未导致解析异常或乱码入文；未手工绕过脚本改产一份「看起来完整」的纪要",
             "method": "裁判复核执行轨迹（是否调用了 scripts/minutes.py 或按 references 手工产出）",
             "expect": "BOM 被 utf-8-sig 容忍；未编造条目"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "from docx import Document\n"
            "d=Document('<outdir>/纪要.docx')\n"
            "ps=[p.text for p in d.paragraphs]\n"
            "print('SECTIONS', [s for s in ('一、决议事项','二、待办事项','三、风险与关注') if s in ps])\n"
            "print('ENTRY_RE_HITS', len(re.findall(r'\\d+\\. 【', '\\n'.join(ps))))\n"
            "print('TABLE_ROWS', len(d.tables[0].rows))\n"
            "print('SUMMARY', json.load(open('<outdir>/summary.json',encoding='utf-8')))\n"
            "PY"
        ),
        "check_expect": "SECTIONS 三项齐全 / ENTRY_RE_HITS 0 / TABLE_ROWS 1 / SUMMARY 四键全 0",
        "anti_saturation": (
            "旧题集三道 ab 题全部使用有实质发言的稿件，case4.txt（全噪声）虽在 reference/inputs 里但从未进过 ab_tasks，"
            "即「0 条纪要」这条能力域从未被测。本题把它升级为任务并叠加 BOM 容忍与「三节标题不得删」的 gotcha。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。本题的失败模式：模型倾向于「报告无法生成内容」而拒绝交付，"
            "或交付一份只有标题没有三节的 docx，或把 0 写错为待办 1（表头行误计）。"
            "裸模型在这三处的高频错误使其成为可靠的区分题。"),
        "old_task_avoided": [
            "不使用 case1/case2/case3 任一旧转写稿",
            "不涉及 ab-001/002/003 的任何分类、优先级、负责人、期限考点",
            "旧题集从未使用 case4.txt；本题改用全新 nonce 稿件，考点（旧集空白区）不与旧题重叠",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:77 空文件/全噪声输入不报错",
            "dist/meeting-minutes-skill/SKILL.md:86 某节 0 条时标题仍保留",
            "dist/meeting-minutes-skill/references/docx-and-summary.md §1 硬约定",
        ],
    },
    {
        "task_id": "t05", "dim": "边界", "nonce": N["t05"],
        "title": "输入文件不存在 → 非 0 退出、不建产物目录、不拿同名诱导文件顶替、不编造转写稿",
        "nonce_values": {"缺失路径": "inbox/transcript-8a6511.txt",
                          "诱导文件": ["会议转写稿-8a6511.md", "transcript-8a6511.txt.bak", "transcript-8a6511 副本.txt"]},
        "entry": "python <pkg>/scripts/minutes.py --input inbox/transcript-8a6511.txt --outdir <outdir>",
        "input": {
            "files": [
                {"path": "inbox/会议转写稿-8a6511.md", "role": "诱导（Markdown 笔记，非转写稿；SKILL 边界：非 txt 输入不处理）",
                 "lines": ["# 会议转写", "", "- 田伟：同意", "- 陆娟：需要补材料"]},
                {"path": "inbox/transcript-8a6511.txt.bak", "role": "诱导（备份文件，非目标文件名）",
                 "lines": ["[11:01] 田伟: 这是旧版本备份。"]},
                {"path": "inbox/transcript-8a6511 副本.txt", "role": "诱导（文件名带空格与「副本」，非目标文件名）",
                 "lines": ["[11:02] 陆娟: 这是另一个副本。"]},
            ],
            "missing": "inbox/transcript-8a6511.txt（题目要求处理的输入，不存在于 inbox）",
        },
        "instruction": (
            "使用 meeting-minutes 技能，把 inbox/transcript-8a6511.txt 这份会议转写稿整理成三段式纪要，"
            "产物写入 <outdir>。inbox 目录里还有一些别的文件。"),
        "goal_state": "如实报告输入不存在并请求确认；非 0 退出；<outdir> 不含任何产物；未使用诱导文件顶替；未编造转写稿内容。",
        "assert_map": {
            "endpoint": "A1–A3", "semantic": "S1–S2", "structure": "F1",
            "mechanical": "C1–C2", "discipline": "B1–B3",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "命令以非 0 退出码结束（SKILL 只要求「非 0」，不钉死具体码；参照实现实测为 2）",
             "method": "echo $?", "expect": "≠ 0（参照实现实测 2）"},
            {"id": "A2", "group": "端态", "assert": "<outdir> 未被创建，或创建后不含 纪要.docx / summary.json",
             "method": "ls/find 计数", "expect": "两文件 find 计数 = 0"},
            {"id": "A3", "group": "端态", "assert": "未在其它目录写出纪要.docx / summary.json",
             "method": "find <workdir> -name 纪要.docx -o -name summary.json", "expect": "命中数 = 0"},
            {"id": "S1", "group": "语义", "assert": "回复中显式指出输入文件路径不存在",
             "method": "裁判通读回复", "expect": "路径 inbox/transcript-8a6511.txt 被点名"},
            {"id": "S2", "group": "语义", "assert": "回复中给出向用户确认/请求正确路径的下一步",
             "method": "裁判通读", "expect": "有明确确认请求，非「已生成」式结论"},
            {"id": "C1", "group": "机械自洽", "assert": "未把 会议转写稿-8a6511.md / .txt.bak / 「副本」.txt 任何一个当作输入跑通",
             "method": "复核执行轨迹的命令行参数", "expect": "未出现 --input 指向诱导文件的成功调用"},
            {"id": "C2", "group": "机械自洽", "assert": "未编造转写稿内容（回复中不含自造的 [hh:mm] 发言行）",
             "method": "正则扫描回复全文 `\\[\\d{1,2}:\\d{2}\\]`", "expect": "命中数 = 0"},
            {"id": "F1", "group": "结构版式", "assert": "不适用（本题无产物）；裁判须按「无产物」而非「结构错误」记 A 组",
             "method": "—", "expect": "A 组按上三条判定"},
            {"id": "B1", "group": "边界纪律", "assert": "遵守「非 txt 输入不处理」的边界，未擅自转换 md → txt 再跑",
             "method": "执行轨迹核查", "expect": "无格式转换动作"},
            {"id": "B2", "group": "边界纪律", "assert": "未使用旧参考产物/其他 case 的输出充当本次交付",
             "method": "find 全部 docx + 比对文件名", "expect": "无本次任务的 docx"},
            {"id": "B3", "group": "边界纪律", "assert": "未隐瞒失败、以「已完成」口径交付",
             "method": "裁判通读回复", "expect": "口径与实际一致"},
        ],
        "check_cmd": (
            "cd <workdir> && python <pkg>/scripts/minutes.py --input inbox/transcript-8a6511.txt --outdir <outdir> ; "
            "echo \"RC=$?\" ; "
            "echo \"产物计数=$(find . -name 纪要.docx -o -name summary.json | wc -l)\" ; "
            "python - <<'PY'\n"
            "import re,glob,os\n"
            "hits=[]\n"
            "for p in glob.glob('**/*.md', recursive=True):\n"
            "    hits += re.findall(r'\\[\\d{1,2}:\\d{2}\\]', open(p, encoding='utf-8', errors='replace').read())\n"
            "print('REPLY_FABRICATED_UTTERANCE_HITS', len(hits))\n"
            "PY"
        ),
        "check_expect": (
            "RC≠0；产物计数=0（工作区内不存在任何 纪要.docx / summary.json）；"
            "REPLY_FABRICATED_UTTERANCE_HITS=0（若被测臂把回复写在 .md 里，则以该文件为准扫描自造发言行）。"
            "补充人工项 B1/B2/B3 由裁判通读回复判定，不在脚本内。"
        ),
        "anti_saturation": (
            "旧题集五道 ab 题无一涉及「输入不存在」这一失败路径（ab4 的非法输入拒答只覆盖 office 包）。"
            "本题同时叠两层诱导：① 非目标格式 .md；② 名字相近但语义上不是目标的 .bak 与「副本」。txt。"
            "任何「尽力而为」的补救行为（自动改名、转格式、拿备份顶替）都会同时触发 A2/A3/B1 三条判负。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。本题属「高难档」：强裸模型常有「先 ls 找找看」的补救倾向，"
            "而 SKILL 明文要求「停止并向用户确认正确路径，禁止自己编造输入」。本题是三包中最容易把裸模型区分开的一题。"),
        "old_task_avoided": [
            "旧 ab-001/002/003 均为成功路径，本题为零成功路径",
            "不涉及任何分类/优先级/负责人/期限考点",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:58 输入不存在时停止并确认，禁止编造输入",
            "dist/meeting-minutes-skill/SKILL.md:76 边界：非 txt 输入（docx/audio 请先转成 txt）",
            "dist/meeting-minutes-skill/scripts/minutes.py:203-206 先查输入后建目录",
        ],
    },
    {
        "task_id": "t06", "dim": "陷阱", "nonce": N["t06"],
        "title": "陷阱：无时间戳 / 空说话人的行即使含关键词也必须丢弃；收录集合必须精确等于期望集合",
        "nonce_values": {"说话人": ["田伟", "陆娟", "章明·计划", "施琳"],
                          "诱导关键词行": ["结论：下次带方案再来讨论。", "同意这个方案。", "有延期风险，大家注意。", "这是散会行"]},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": _f("transcript-8a6511.txt", T06_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>"
            "（纪要.docx + summary.json）。这份稿子里有几行只有半句话、没有时间戳，"
            "也有说话人写漏的。请严格按技能包规定判断哪些行算「发言」，哪些算噪声，不要凭语义感觉收录。"),
        "goal_state": "收录条目集合精确等于 {15:01 决议, 15:04 待办, 15:06 决议, 15:07 决议, 15:09 风险}，五行噪声零收录。",
        "assert_map": {
            "endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
            "mechanical": "C1–C2", "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "5 行噪声零收录：「结论：下次带方案再来讨论。」（无时间戳且含关键词）「同意这个方案。」（无时间戳且含关键词）「有延期风险，大家注意。」（无时间戳且含关键词）「[15:02] : …」（说话人为空，不可解析）「这是散会行」（不可解析且零关键词）",
             "method": "把上述四行内容作为子串在 docx 全文中做包含检索",
             "expect": "5/5 命中数 = 0"},
            {"id": "S2", "group": "语义", "assert": "收录集合精确等于 5 条：15:01（决议）、15:04（待办，含「需要」+「延期」故按待办>风险归待办）、15:06（决议）、15:07（决议）、15:09（风险）",
             "method": "docx 条目前缀集合 == 期望集合（逐条双向差集）",
             "expect": "双向差集均为空；条数=5"},
            {"id": "S3", "group": "语义", "assert": "命中关键词的发言整句收录、不截断（「[15:07] 施琳: 结论待会再议，这里先散会。」整句进决议）",
             "method": "条目全文 == 源行内容", "expect": "15:07 条目全文与源行逐字相同"},
            {"id": "C1", "group": "机械自洽", "assert": "5 类噪声行（无时间戳含关键词 ×3、空说话人 ×1、不可解析零关键词 ×1）全部不出现在任何章节",
             "method": "脚本：噪声集合 × docx 全文逐条包含检索",
             "expect": "5/5 命中数 = 0"},
            {"id": "C2", "group": "机械自洽", "assert": "summary == {决议事项:3, 待办事项:1, 风险与关注:1, 合计:5}，且与 docx 实际条数逐项一致",
             "method": "json + docx 互校", "expect": "三处一致"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题齐全、顺序固定",
             "method": "段落遍历", "expect": "三节都在"},
            {"id": "F2", "group": "结构版式", "assert": "待办表格 1 个数据行，负责人/期限两列分别为「陆娟」「待定」",
             "method": "表格单元格逐字比对", "expect": "15:04 行 期限无时间语 → 待定"},
            {"id": "B1", "group": "边界纪律", "assert": "未对噪声行做「语义补全」（例如替无时间戳行编造 [15:03] 前缀）",
             "method": "条目前缀时间戳集合 == 源行时间戳集合", "expect": "无源文件中不存在的时间戳"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "from docx import Document\n"
            "d=Document('<outdir>/纪要.docx')\n"
            "full='\\n'.join([p.text for p in d.paragraphs]+[c.text for t in d.tables for r in t.rows for c in r.cells])\n"
            "noise=['结论：下次带方案再来讨论。','同意这个方案。','有延期风险，大家注意。','这条没有说话人，应该被丢弃。','这是散会行']\n"
            "print('NOISE_HITS', {n: full.count(n) for n in noise})\n"
            "got=sorted(set(re.findall(r'【(\\d{1,2}:\\d{2}) ·', full)))\n"
            "print('TIMESTAMPS', got)\n"
            "print('SUMMARY', json.load(open('<outdir>/summary.json',encoding='utf-8')))\n"
            "PY"
        ),
        "check_expect": "NOISE_HITS 五项全 0 / TIMESTAMPS ['15:01','15:04','15:06','15:07','15:09'] / SUMMARY {'决议事项':3,'待办事项':1,'风险与关注':1,'合计':5}",
        "anti_saturation": (
            "旧题集的噪声行（寒暄/口误/散会）**全部是零关键词**的，模型只要「不含关键词就丢」即可全对，"
            "规则 R1.3（无法解析为发言格式）从未被真正施压。本题把噪声行换成「**含关键词但不可解析**」，"
            "关键词命中与发言格式解析两条规则的**交集**成为唯一判据——这是本包最容易区分裸模型与 skill 臂的结构。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%，本题为三包最高难档之一。裸模型的高频失败："
            "① 用「关键词 grep」代替「格式解析」，把三行无时间戳诱导行收进去（S1/C1 双否）；"
            "② 把「结论待会再议」这类散会+关键词行截断为「结论待会再议」（S3 否）。"),
        "old_task_avoided": [
            "不复现 ab-001/002/003 的噪声抑制考点（旧噪声行零关键词，形态不同）",
            "不涉及负责人/期限规则（旧 ab-003）",
            "不涉及同行多类优先级（旧 ab-002）",
            "15:01/15:04/15:06/15:07 四条均为新稿新实体，与 case1/case2/case3 无重叠",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:30 噪声两类（不可解析行 + 零关键词行）",
            "dist/meeting-minutes-skill/references/classification-rules.md §1-§2 R1/R2",
            "dist/meeting-minutes-skill/scripts/minutes.py:21-24 LINE_RE 与 parse_transcript",
        ],
    },
    {
        "task_id": "t07", "dim": "陷阱", "nonce": N["t07"],
        "title": "陷阱：条目精确集合 + 三类互斥 + 编号连续 + 待办「事项」列逐字 + 0 条节标题保留",
        "nonce_values": {"说话人": ["田伟", "陆娟", "章明·计划", "施琳"],
                          "关键词对撞句": "交付窗口按客户回签日算，这个结论要写进纪要，需要陆娟同步给商务。"},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir <outdir>",
        "input": _f("transcript-8a6511.txt", T07_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要，产物写入 <outdir>"
            "（纪要.docx + summary.json）。请保证每条事项都只出现在一个章节里、不重复也不遗漏，"
            "表格里的事项同样要逐字照抄原句。"),
        "goal_state": "决议 2 / 待办 1 / 风险 1，合计 4；每条只属一类；编号连续；待办事项列逐字。",
        "assert_map": {
            "endpoint": "A1–A2", "semantic": "S1–S4", "structure": "F1–F3",
            "mechanical": "C1–C2", "discipline": "B1",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "16:01 行同时含「结论」(决议) 与「需要」(待办)，只归入决议事项、且只出现一次",
             "method": "全文计数：S1 文本在决议节出现 1 次、在待办表格出现 0 次、在风险节出现 0 次",
             "expect": "决议节 1 次，其余处 0 次"},
            {"id": "S2", "group": "语义", "assert": "16:02 行（只含「需要」）归待办；16:03 行（只含「同意」）归决议；16:04 行（只含「延期」「风险」）归风险",
             "method": "条目前缀所属章节断言", "expect": "三节各 1 条 + 16:01 共 4 条"},
            {"id": "S3", "group": "语义", "assert": "四类互斥：任一条目文本不得出现在两个及以上章节",
             "method": "脚本：条目文本集合在全文出现次数 == 1",
             "expect": "4/4 计数为 1"},
            {"id": "S4", "group": "语义", "assert": "待办表格「事项」列逐字等于 16:02 行内容（未摘要、未改写、未截断）",
             "method": "单元格文本 == 源行内容", "expect": "逐字相同"},
            {"id": "C1", "group": "机械自洽", "assert": "决议 2 条编号为 1. 2.、风险 1 条编号为 1.，连续无跳号",
             "method": "正则抽编号", "expect": "决议 [1,2]、风险 [1]"},
            {"id": "C2", "group": "机械自洽", "assert": "summary == {决议事项:2, 待办事项:1, 风险与关注:1, 合计:4}，与 docx 三处逐项一致",
             "method": "json + docx 互校", "expect": "三处一致、合计=4"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字齐全、顺序固定", "method": "段落遍历", "expect": "齐全无增节"},
            {"id": "F2", "group": "结构版式", "assert": "待办表格恰 1 个数据行，3 列表头齐全",
             "method": "len(rows)-1", "expect": "1 行"},
            {"id": "F3", "group": "结构版式", "assert": "元信息行数字与实际条数一致",
             "method": "正则捕获比对", "expect": "解析发言 4 条（决议 2 · 待办 1 · 风险 1）"},
            {"id": "B1", "group": "边界纪律", "assert": "未把 16:02 行拆成两条（一条待办 + 一条因「责任人还没定」自拟的风险）",
             "method": "条目数与集合断言", "expect": "恰 4 条，无自拟条目"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "from docx import Document\n"
            "d=Document('<outdir>/纪要.docx')\n"
            "paras=[p.text for p in d.paragraphs]\n"
            "full='\\n'.join(paras)\n"
            "print('SEC', {s: paras.count(s) for s in ('一、决议事项','二、待办事项','三、风险与关注')})\n"
            "print('DEC_NUMS', re.findall(r'^(\\d+)\\. 【', '\\n'.join(p for p in paras if p.startswith(('1.','2.','3.'))), re.M))\n"
            "print('TABLE_ROWS', len(d.tables[0].rows)-1)\n"
            "print('SUMMARY', json.load(open('<outdir>/summary.json',encoding='utf-8')))\n"
            "PY"
        ),
        "check_expect": "SEC 三节各 1 / TABLE_ROWS 1 / SUMMARY {'决议事项':2,'待办事项':1,'风险与关注':1,'合计':4}",
        "anti_saturation": (
            "旧 ab-002 测过「同行多类关键词优先级」，但输入只有一句、且 rubric 只查归属不查互斥与计数。"
            "本题把优先级降为**支撑项**，核心换成三条旧题从未断言的结构性约束："
            "① 条目全文出现次数 == 1（三类互斥，可脚本判）；② 编号连续；③ 待办「事项」列逐字（SKILL gotchas 明写，旧 rubric 只查了数据行数）。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。本题难度不在语义而在纪律：裸模型常把「责任人还没定」自行扩写成一条风险、"
            "或对同一行同时归两类，S3 与 B1 因此失分；`事项` 列被摘要化则 S4 失分。"
            "五项 S/C 断言互相独立，任一处错即掉两个维度。"),
        "old_task_avoided": [
            "「同行多类优先级」仅作支撑项，核心断言（互斥计数/编号连续/事项列逐字）为旧题集空白",
            "不复现 ab-003 的负责人代词消解与规则2 期限（16:02 行负责人规则全部不命中，落「待定」）",
            "不复现 ab-002 的「截止到周五」期限对撞",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:83 待办表格「事项」列也必须逐字引用原句",
            "dist/meeting-minutes-skill/SKILL.md:44 三类互不重叠、编号从 1 连续",
            "dist/meeting-minutes-skill/SKILL.md:86 某节 0 条时标题仍保留",
        ],
    },
    {
        "task_id": "t08", "dim": "陷阱", "nonce": N["t08"],
        "title": "陷阱：三向自洽（docx↔summary↔元信息）+ 同输入双跑确定性 + 显式回读验收",
        "nonce_values": {"说话人": ["田伟", "陆娟", "章明·计划", "施琳"],
                          "两份输出目录": ["outA", "outB"]},
        "entry": "python <pkg>/scripts/minutes.py --input <inbox>/transcript-8a6511.txt --outdir outA（再跑一次到 outB）",
        "input": _f("transcript-8a6511.txt", T07_LINES),
        "instruction": (
            "使用 meeting-minutes 技能，把 <inbox>/transcript-8a6511.txt 整理成三段式纪要。"
            "请用**完全相同的输入连续运行两次**，分别输出到 outA 与 outB 两个目录。"
            "交付前请把产物读回来核对一遍，不要只看退出码。"),
        "goal_state": "outA/outB 两套产物：summary 逐字节一致、docx 段落与表格文本逐字一致、三向自洽断言全过。",
        "assert_map": {
            "endpoint": "A1–A2", "semantic": "S1–S2", "structure": "F1",
            "mechanical": "C1–C4", "discipline": "B1–B2",
        },
        "checks": [
            {"id": "A1", "group": "端态", "assert": "outA 与 outB 各恰含 纪要.docx + summary.json 两文件",
             "method": "find 计数（两目录各一次）", "expect": "两个目录计数均为 2"},
            {"id": "A2", "group": "端态", "assert": "两次运行退出码均为 0", "method": "两次 echo $?", "expect": "0, 0"},
            {"id": "S1", "group": "语义", "assert": "两次产物 summary.json 逐字节一致",
             "method": "sha256sum 两文件", "expect": "两个 sha256 相同"},
            {"id": "S2", "group": "语义", "assert": "两次产物 docx 的全部段落文本与全部表格单元格文本序列逐字一致",
             "method": "python 抽取两份 docx 的 (段落文本列表 + 表格单元格文本列表) 做 == 比较",
             "expect": "两序列相等（不要求 zip 字节相同）"},
            {"id": "C1", "group": "机械自洽", "assert": "docx 三节实际条数 == summary 三节计数 == 元信息行三个数字",
             "method": "脚本三方互校（决议/风险数编号段落数；待办数=表格数据行数）",
             "expect": "三处逐项相等，合计=4"},
            {"id": "C2", "group": "机械自洽", "assert": "待办表格数据行数 == summary 待办数；表头三列齐全",
             "method": "len(rows)-1 vs json", "expect": "相等且=1"},
            {"id": "C3", "group": "机械自洽", "assert": "文件名未被改名、未加日期后缀",
             "method": "ls 两目录", "expect": "逐字为 纪要.docx / summary.json"},
            {"id": "C4", "group": "机械自洽", "assert": "交付回复中贴出了回读命令与其输出（写后回读三态）",
             "method": "裁判核查回复与轨迹", "expect": "含 ls/dir 回读或等价回读证据"},
            {"id": "F1", "group": "结构版式", "assert": "三节标题逐字齐全、顺序固定", "method": "段落遍历", "expect": "齐全无增节"},
            {"id": "B1", "group": "边界纪律", "assert": "未以「第二次跑出来不一样是正常的」为由放过不确定性",
             "method": "裁判通读", "expect": "如实报告差异或修复后重跑"},
            {"id": "B2", "group": "边界纪律", "assert": "未手工复制 outA 产物冒充第二次真实运行",
             "method": "复核执行轨迹（两次 --outdir 不同的调用）", "expect": "两次独立调用"},
        ],
        "check_cmd": (
            "cd <workdir> && sha256sum outA/summary.json outB/summary.json && python - <<'PY'\n"
            "from docx import Document\n"
            "def dump(p):\n"
            "    d=Document(p)\n"
            "    return ([x.text for x in d.paragraphs],\n"
            "            [[c.text for r in t.rows for c in r.cells] for t in d.tables])\n"
            "print('DOCX_TEXT_EQUAL', dump('outA/纪要.docx')==dump('outB/纪要.docx'))\n"
            "PY"
        ),
        "check_expect": "两个 summary.json 的 sha256 相同；DOCX_TEXT_EQUAL True",
        "anti_saturation": (
            "旧题集没有「双跑逐字节/逐字一致性」这道断言（hot 包有确定性题，mm 包没有），"
            "而 mm 包 SKILL 明确要求「写后回读三态：退出码 0 **且**两文件真实存在才算 verified」。"
            "本题把「回读」与「确定性」绑在一起：只交退出码 0、无回读证据的臂，B/C 两组同时失分。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型常见失效：① 只报退出码不做回读（C4 失）；"
            "② 第二次直接 cp 而非重跑（B2 失）；③ 自认「zip 字节每次不同没关系」而放弃确定性核验（S2 判否）。"
            "这三点均可机械判定，不依赖裁判口味。"),
        "old_task_avoided": [
            "旧 ab-001/002/003 全部是单次运行、无回读断言、无确定性断言",
            "本题输入沿用 t07 稿件属包内新稿，与 case1/case2/case3 无重叠；核心断言（确定性 + 三向自洽 + 回读）在旧题集完全空白",
        ],
        "design_basis_extra": [
            "dist/meeting-minutes-skill/SKILL.md:57 成功判据（写后回读三态）",
            "dist/meeting-minutes-skill/references/docx-and-summary.md §3 确定性口径",
        ],
    },
]

TASKS[1]["weights"] = {"endpoint": 12, "semantic": 34, "structure": 18, "mechanical": 22, "discipline": 14}
TASKS[4]["weights"] = {"endpoint": 10, "semantic": 26, "structure": 6, "mechanical": 26, "discipline": 32}
TASKS[5]["weights"] = {"endpoint": 14, "semantic": 32, "structure": 16, "mechanical": 24, "discipline": 14}
TASKS[7]["weights"] = {"endpoint": 16, "semantic": 26, "structure": 12, "mechanical": 32, "discipline": 14}