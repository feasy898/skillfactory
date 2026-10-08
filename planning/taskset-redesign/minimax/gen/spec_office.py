# -*- coding: utf-8 -*-
"""spec_office — office-templates-skill 新任务集（t01–t08）。

旧题考点（反饱和对照，见 ../DESIGN.md 差异表）：
  ab1 四模板全量生成 + 版式 V2–V5 + A4 版心 + fields 键集
  ab2 必填缺失 ____ 占位 + missing_required 记账 + unknown_keys（单键「备注」）+ 选填留空/省略
  ab3 空数组占位条目 + 字符串型列表单项化 + 选填小节省略
  ab4 四种非法输入 exit 2 + 零产物残留
  ab5 确定性连跑两遍 + runner 红绿自校验 + 三件套齐全
旧输入 8 份（4 模板 × case1/case2）全部被旧题集使用。

本集新考点（均为旧题集空白）：
  F5 strip 全链路（文本 + 列表项 + 台账 value）/ F3 非字符串类型宽容（数字、布尔、对象）
  全空白数组判缺失（区别于 ab3 的空数组）/ 多余外键字典序 / 四模板版式细节（编号「四」、
  裸日期落款、称谓只对两类模板生效）/ 非目标拒答（pdf、红头、字段增删、多文档合并）
  数据语义校验不做（非法电话/日期原样透传 + exit 0）
"""

PKG = "office-templates-skill"

N = {
    "t01": "ofc-t01-3e7b52",
    "t02": "ofc-t02-9a04d8",
    "t03": "ofc-t03-51c6ef",
    "t04": "ofc-t04-b87a29",
    "t05": "ofc-t05-2df916",
    "t06": "ofc-t06-6e3b47",
    "t07": "ofc-t07-c1058a",
    "t08": "ofc-t08-74d2b0",
}

# ---------------------------------------------------------------- 输入素材（nonce 化）

# t01：F5 strip 全链路（带前后空白/全角空格/制表符）
D_T01 = {
    "部门": "  智造事业部　",
    "填报人": "张浩\t",
    "周期": "\n2026-10-05 至 2026-10-11\n",
    "本周工作内容": ["  完成三批次评分器回归  ", "\t复核 12 份标注台账", "　　"],
    "下周工作计划": ["  上线自动抽检脚本  "],
    "问题与需协调事项": ["\t压测机位排期冲突  "],
    "报送日期": " 2026-10-11 ",
}

# t02：F3 列表取值宽容（字符串 / 含空白项数组 / 数字等非字符串类型）
D_T02 = {
    "总结主体": "度量研究院",
    "总结时段": "2026 年 9 月",
    "工作回顾": "完成三平台评分器回归",
    "主要成绩": [" 一致率从 6.1 提到 7.4 ", "   ", "周期缩短 30%"],
    "存在问题": [2026, True, {"备注": "待与厂商对齐"}],
    "下一步工作打算": 4,
    "成文日期": "2026年9月30日",
}

# t03：版式细节（四模板各一份，全字段齐全）
D_T03 = {
    "请示函": {
        "请示事由": "申请扩容标注平台算力",
        "主送机关": "数据治理组",
        "请示缘由": "标注量环比增长四成，现有算力无法满足批量推理排期。",
        "请示事项": "申请购置八卡服务器一台，预算 33万元，三个月内到货验收。",
        "请示单位": "度量研究院",
        "联系人": "田怡",
        "联系电话": "017-05171598",
        "成文日期": "2026年9月30日",
    },
    "会议通知": {
        "会议名称": "四季度标注规范宣贯会",
        "召开单位": "度量研究院",
        "主送对象": "各标注小组、各质量负责人",
        "会议时间": "2026年10月15日（周四）15:30",
        "会议地点": "5 号楼 302 培训室",
        "参会人员": "各标注小组组长",
        "会议议题": "标注规范 v2 宣贯与答疑",
        "会议要求": ["会前阅读规范 v2 全文", "现场提交本组疑问清单"],
        "联系人": "左芬",
        "联系电话": "087-15250114",
        "发文日期": "2026年9月30日",
    },
    "工作总结": {
        "总结主体": "数据治理组",
        "总结时段": "2026 年 9 月",
        "工作回顾": ["完成标注规范 v2 起草", "组织两轮标注一致性抽检"],
        "主要成绩": ["一致性抽检合格率提升 9 个百分点"],
        "存在问题": ["跨组判定口径仍有分歧"],
        "下一步工作打算": ["发布规范 v2 并冻结判定样例"],
        "成文日期": "2026年9月30日",
    },
}

# t04：F6 模板外键字典序（周报用无关键 3 个）
D_T04 = {
    "部门": "供应链计划处",
    "填报人": "魏娥",
    "周期": "2026-10-05 至 2026-10-11",
    "本周工作内容": ["完成四批物料到货核销"],
    "下周工作计划": ["编制下月采购计划"],
    "问题与需协调事项": ["到货台账需与仓储口径对齐"],
    "报送日期": "2026-10-11",
    "审批人": "魏娥",
    "备注": "此键不在模板字段内",
    "密级": "内部",
}

# t05：全空白数组 / 空白字符串 → 缺失（near-miss，区别于旧 ab3 的空数组）
D_T05 = {
    "总结主体": "   ",
    "总结时段": "2026 年 9 月",
    "工作回顾": "   ",
    "主要成绩": ["   ", "\t", ""],
    "存在问题": ["   ", "\t"],
    "下一步工作打算": ["固化标注口径并冻结判定样例"],
    "成文日期": "  ",
}

# t06：必填全缺（会议通知）
D_T06 = {
    "会议议题": "议题本身是选填，但用来证明其它字段缺了也要照常成文",
}

# t07：非目标拒答（同一份数据，三类越界请求）
D_T07 = {
    "总结主体": "平台工程部",
    "总结时段": "2026 年 9 月",
    "工作回顾": ["完成网关灰度切换"],
    "主要成绩": ["切换期间零回滚"],
    "存在问题": ["老旧实例尚未下线"],
    "下一步工作打算": ["把灰度流程沉淀为标准作业"],
    "成文日期": "2026年9月30日",
}

# t08：数据语义不做校验（非法电话 / 非法日期 / 非字符串电话）
D_T08 = {
    "会议名称": "KP-A-86018 项目结项评审会",
    "召开单位": "平台工程部",
    "主送对象": "各项目组",
    "会议时间": "下下周某天，具体再定",
    "会议地点": "3 号楼 501 会议室",
    "参会人员": "项目组成员",
    "会议议题": "结项指标复核与后续路线确认",
    "会议要求": ["会前提交结项自评表"],
    "联系人": "左芬",
    "联系电话": "010-abc",
    "发文日期": "待定",
}


def _json_case(name, data):
    return {"files": [{"path": "%s/%s.json" % (name[0], name[1]), "encoding": "utf-8", "data": data}]}


def _case(name, data):
    return {"files": [{"path": "%s.json" % name, "encoding": "utf-8", "data": data}]}


CMD = "python <pkg>/scripts/gen_doc.py --template <模板> --data <数据.json> --outdir <outdir>"

TASKS = [
    {
        "task_id": "t01", "dim": "能力", "nonce": N["t01"],
        "title": "F5 strip 全链路：正文无首尾空白、台账 value 已 strip、缺失判定不受空白串影响",
        "nonce_values": {"部门": "智造事业部", "填报人": "张浩", "周期": "2026-10-05 至 2026-10-11",
                          "条目": ["完成三批次评分器回归", "复核 12 份标注台账", "上线自动抽检脚本"],
                          "报送日期": "2026-10-11"},
        "entry": CMD,
        "input": _case("周报/case1.json", D_T01),
        "instruction": (
            "使用 office-templates 技能，把 data/周报/case1.json 渲染成周报，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据的字段值带着多余的前后空白与制表符。"
            "请按技能包规定的取值口径渲染，并把台账里的 value 一并处理干净。"),
        "goal_state": "文书正文不含任何首尾空白；台账 value 为 strip 后的值；全空白列表项被丢弃且不导致字段判缺失。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "<outdir> 恰含 文书.docx 与 fields.json，退出码 0",
             "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "标题段逐字 = 「智造事业部工作周报」（无前后空白、无全角空格残留）",
             "method": "doc.paragraphs[0].text", "expect": "智造事业部工作周报"},
            {"id": "S2", "group": "语义", "assert": "基本信息行逐字 = 「填报人：张浩　　周期：2026-10-05 至 2026-10-11」（两个全角空格分隔；值两端无空白）",
             "method": "段落文本逐字比对（注意分隔符是两个全角空格 U+3000）", "expect": "逐字相同"},
            {"id": "S3", "group": "语义", "assert": "列表项入文已 strip：本周工作内容恰 2 条（第三条全空白项被丢弃），条目前后无空白",
             "method": "抽取小节条目段落文本并 strip 后比对 + 断言原文无首尾空白",
             "expect": "2 条；条目标题为「完成三批次评分器回归」「复核 12 份标注台账」"},
            {"id": "C1", "group": "机械自洽", "assert": "fields.json 每个 filled 项的 value 均等于 strip 后的输入值（文本为字符串、list 为数组）",
             "method": "脚本比对 fields.filled 项与输入 JSON 的 strip 值", "expect": "7/7 相等"},
            {"id": "C2", "group": "机械自洽", "assert": "fields.summary == {total:7, filled:7, missing:0, missing_required:0, missing_required_names:[], unknown_keys:[]}；filled+missing=total",
             "method": "json 读 + 自洽断言", "expect": "全部齐全，无字段因空白被判缺失"},
            {"id": "F1", "group": "结构版式", "assert": "标题居中黑体 22pt；正文首行缩进两字符（firstLineChars=200）、仿宋 16pt、28 磅固定行距",
             "method": "python-docx 读 alignment / run.font / w:firstLineChars", "expect": "逐项成立"},
            {"id": "F2", "group": "结构版式", "assert": "落款行逐字 = 「报送日期：2026-10-11」，右对齐且右缩进两字",
             "method": "末个非空段文本 + alignment + right_indent", "expect": "逐字相同，值不带尾随空格"},
            {"id": "B1", "group": "边界纪律", "assert": "未因数据带空白就自行「美化」标点（如把全角空格改成两个半角空格或加逗号）",
             "method": "正文逐字比对", "expect": "未改写任何字符"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "d=Document('<outdir>/文书.docx')\n"
            "ps=[p.text for p in d.paragraphs]\n"
            "print('TITLE', repr(ps[0]))\n"
            "print('INFO', repr(ps[1]))\n"
            "print('SIG', repr([p for p in ps if p.strip()][-1]))\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "print('SUMMARY', f['summary'])\n"
            "print('VALUES', {x['name']:x['value'] for x in f['fields']})\n"
            "PY"
        ),
        "check_expect": "TITLE '智造事业部工作周报' / INFO '填报人：张浩　　周期：2026-10-05 至 2026-10-11' / SUMMARY total=7 filled=7 missing=0 / VALUES 全部 strip",
        "anti_saturation": (
            "F5（填充值 strip）在旧题集里一次都没被断言过——旧 ab1 的四份 case1 全是干净输入，"
            "旧 ab2/ab3 断言的是「缺失怎么渲染」，不是「存在怎么规整」。本题把取值规整做成主考点，"
            "并叠一个 near-miss：列表里的全空白项被丢弃但**不**导致该字段判为缺失（F3 与缺失判定是两回事）。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型的典型失败是原样搬运带空白的值（正文出现「  智造事业部　工作周报」），"
            "或在台账里存未 strip 的原值；两者都会被 S1/S2/C1 三处独立判负，属稳定区分点。"),
        "old_task_avoided": [
            "不复现 ab1 的四模板全量生成与版式四要素（本题单模板）",
            "不复现 ab2 的必填缺失 ____ 占位与 missing_required 记账",
            "不复现 ab3 的空数组占位条目与字符串型列表单项化",
            "不复现 ab4 的非法输入拒答、ab5 的确定性",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:58 F5 填充值 strip",
            "dist/office-templates-skill/SKILL.md:52 缺失判定（strip 后为空）",
            "dist/office-templates-skill/scripts/gen_doc.py:92-106 norm_text / norm_list",
        ],
    },
    {
        "task_id": "t02", "dim": "能力", "nonce": N["t02"],
        "title": "F3 列表取值宽容：字符串→单项 / 数组含空白项 / 非字符串类型 str().strip() 单项",
        "nonce_values": {"总结主体": "度量研究院", "总结时段": "2026 年 9 月",
                          "主要成绩": ["一致率从 6.1 提到 7.4", "周期缩短 30%"],
                          "存在问题原样": ["2026", "True", "{'备注': '待与厂商对齐'}"],
                          "下一步工作打算": "4"},
        "entry": CMD,
        "input": _case("工作总结/case1.json", D_T02),
        "instruction": (
            "使用 office-templates 技能，把 data/工作总结/case1.json 渲染成工作总结，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据里的列表字段写法不统一：有的给了字符串，"
            "有的给了带空格的数组，还有的直接给了数字。请按技能包规定的取值口径渲染并如实记账。"),
        "goal_state": "三个 list 字段按 F3 宽容口径规整：字符串→单项、数组去空后逐项、非字符串类型 str() 单项。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S4", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "工作回顾为字符串 → 渲染为单项条目，fields value = [\"完成三平台评分器回归\"]",
             "method": "台账 value 比对", "expect": "字符串数组，长度 1"},
            {"id": "S2", "group": "语义", "assert": "主要成绩为数组含一个全空白项 → 去空后 2 项",
             "method": "台账 value 比对 + 正文条目数", "expect": "value 长度 2，正文 2 条"},
            {"id": "S3", "group": "语义", "assert": "存在问题为非字符串数组 [2026, True, {...}] → 每项 str().strip() 后成单项，共 3 项，值分别为 \"2026\"、\"True\"、\"{'备注': '待与厂商对齐'}\"",
             "method": "台账 value 比对（逐字）", "expect": "长度 3，元素全为字符串，非原类型（不得是 int/bool/dict）"},
            {"id": "S4", "group": "语义", "assert": "下一步工作打算为数字 4（非列表）→ str().strip() 单项，value = [\"4\"]，正文条目为「4」而非报错或丢弃",
             "method": "台账 value + 正文条目比对", "expect": "value == [\"4\"]，status=filled"},
            {"id": "C1", "group": "机械自洽", "assert": "所有 filled 的 list 字段 value 元素全为字符串（str 化），无 int/bool/dict 残留",
             "method": "脚本：for v in value: assert isinstance(v,str)", "expect": "4/4 字段满足"},
            {"id": "C2", "group": "机械自洽", "assert": "fields.summary == {total:7, filled:7, missing:0, missing_required:0, missing_required_names:[], unknown_keys:[]}",
             "method": "json 读 + 自洽断言", "expect": "全部齐全（宽容取值不算缺失）"},
            {"id": "F1", "group": "结构版式", "assert": "小节编号为「一、工作回顾」「二、主要成绩」「三、存在问题」「四、下一步工作打算」（第四节为「四」）",
             "method": "段落文本逐字比对", "expect": "四个节头齐全且编号为 一/二/三/四"},
            {"id": "F2", "group": "结构版式", "assert": "条目编号为全角点「1．2．3．」；落款两行 = 「度量研究院」+「2026年9月30日」（日期为裸日期、无标签）",
             "method": "末两非空段文本逐字比对", "expect": "第二行为「2026年9月30日」而非「成文日期：…」"},
            {"id": "B1", "group": "边界纪律", "assert": "未把数字 4 当成「4 条计划」自行扩写，未把 True 渲染成「是」、未把 dict 渲染成 JSON 串",
             "method": "正文逐字比对", "expect": "正文为 str() 结果的字面值"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "v={x['name']:x['value'] for x in f['fields']}\n"
            "for k in ('工作回顾','主要成绩','存在问题','下一步工作打算'): print(k, v[k])\n"
            "print('ALL_STR', all(isinstance(i,str) for k in ('工作回顾','主要成绩','存在问题','下一步工作打算') for i in v[k]))\n"
            "ps=[p.text for p in Document('<outdir>/文书.docx').paragraphs]\n"
            "print('SECS', [p for p in ps if p[:2] in ('一、','二、','三、','四、')])\n"
            "print('SIG', [p for p in ps if p.strip()][-2:])\n"
            "PY"
        ),
        "check_expect": "四字段 value 均为字符串数组 / ALL_STR True / SECS 四节含「四、下一步工作打算」/ SIG ['度量研究院','2026年9月30日']",
        "anti_saturation": (
            "旧 ab3 只测了「字符串型列表 → 单项」这一种宽容形态。本题把 F3 的三分支全部铺开，"
            "并新增旧题集从未出现的两个形态：非字符串标量（数字 4）与非字符串数组元素（int/bool/dict）。"
            "再叠一个旧 rubric 从未断言的版式细节——工作总结第四节编号是「四、」且落款日期行为裸日期。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型的高频失败是「按直觉处理 JSON」："
            "对数字字段报错或丢弃（S4）、对 bool/dict 保留原类型入台账（S3/C1）、"
            "对裸日期擅自加「成文日期：」标签（F2）。三处失败互相独立，可稳定压到 60% 线以下。"),
        "old_task_avoided": [
            "不复现 ab3 的空数组 → 占位条目「1．____」（本题无必填缺失）",
            "不复现 ab3 的字符串型列表单项化（旧题仅 工作回顾 一例；本题把三分支全测且换 nonce 实例）",
            "不复现 ab2 的 missing_required 记账与 ____ 占位",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:55 F3 列表取值宽容",
            "dist/office-templates-skill/SKILL.md:101 V5 落款（日期行为裸日期）",
            "dist/office-templates-skill/scripts/gen_doc.py:92-106 norm_list 三分支",
            "dist/office-templates-skill/scripts/gen_doc.py:288-300 工作总结四小节与两行落款",
        ],
    },
    {
        "task_id": "t03", "dim": "能力", "nonce": N["t03"],
        "title": "四类模板版式细节：称谓仅两类模板生效 / 条目全角点编号 / 会议通知行内标签 / 两行落款右对齐",
        "nonce_values": {"主送机关": "数据治理组", "请示单位": "度量研究院", "预算": "33万元",
                          "主送对象": "各标注小组、各质量负责人", "召开单位": "度量研究院",
                          "总结主体": "数据治理组", "成文日期": "2026年9月30日"},
        "entry": CMD + "（三份数据各跑一次，各自独立 outdir）",
        "input": {"files": [{"path": "请示函/case1.json", "encoding": "utf-8", "data": D_T03["请示函"]},
                            {"path": "会议通知/case1.json", "encoding": "utf-8", "data": D_T03["会议通知"]},
                            {"path": "工作总结/case1.json", "encoding": "utf-8", "data": D_T03["工作总结"]}]},
        "instruction": (
            "使用 office-templates 技能，分别把 data/请示函/case1.json、data/会议通知/case1.json、"
            "data/工作总结/case1.json 三份数据各渲染成一份文书，输出到三个独立目录 "
            "<outdir>/请示函、<outdir>/会议通知、<outdir>/工作总结，每个目录下放该次调用的 文书.docx 与 fields.json。"
            "请严格按各模板的版式规范成文。"),
        "goal_state": "三类模板的称谓/落款/编号/行内标签四组版式细节各自成立，无串味（不得给工作总结加称谓段）。",
        "assert_map": {"endpoint": "A1–A3", "semantic": "S1–S2", "structure": "F1–F5",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "三个子目录各恰含 2 件产物，三次调用退出码均 0",
             "method": "find 计数 ×3 + echo $?", "expect": "三个目录各计数 2，码均 0"},
            {"id": "A2", "group": "端态", "assert": "文件名逐字为 文书.docx / fields.json，未改名",
             "method": "ls", "expect": "逐字一致"},
            {"id": "A3", "group": "端态", "assert": "三份 fields.json 的 template 字段与实际模板一一对应，未串台",
             "method": "json 读 template", "expect": "请示函/会议通知/工作总结 各归其位"},
            {"id": "S1", "group": "语义", "assert": "三份 title 逐字：请示函=「关于申请扩容标注平台算力的请示」；会议通知=「关于召开四季度标注规范宣贯会的通知」；工作总结=「数据治理组2026 年 9 月工作总结」",
             "method": "title 段文本 + fields.title 双向比对（要求两者相等）", "expect": "三条公式全中；fields.title == 标题段全文"},
            {"id": "S2", "group": "语义", "assert": "台账 value 已 strip：总结时段「 2026 年 9 月 」渲染为「2026 年 9 月」，标题不含首尾空白",
             "method": "台账 value 比对", "expect": "strip 后相等"},
            {"id": "F1", "group": "结构版式", "assert": "称谓段仅请示函/会议通知有：请示函第二段 = 「数据治理组：」顶格无首行缩进；会议通知第二段 = 「各标注小组、各质量负责人：」顶格",
             "method": "段落文本 + w:ind 首行为空", "expect": "两段顶格；总结内文全文无「：」结尾称谓段"},
            {"id": "F2", "group": "结构版式", "assert": "工作总结不得出现称谓段（V3 只适用请示函/会议通知）",
             "method": "遍历段落找以全角冒号结尾的顶格段", "expect": "命中数 = 0"},
            {"id": "F3", "group": "结构版式", "assert": "会议通知行内标签串逐字 = 「联系人：左芬　　联系电话：087-15250114」（两个全角空格）",
             "method": "段落文本逐字比对", "expect": "逐字相同"},
            {"id": "F4", "group": "结构版式", "assert": "条目编号使用全角点「1．2．3．」；会议通知选填小节节头为「一、会议要求」",
             "method": "正则 `^\\d+．` 计数 + 节头文本比对", "expect": "编号全为全角点；节头存在"},
            {"id": "F5", "group": "结构版式", "assert": "落款：请示函两行「度量研究院」+「2026年9月30日」；会议通知两行「度量研究院」+「2026年9月30日」；工作总结两行「数据治理组」+「2026年9月30日」；三份均右对齐且右缩进两字",
             "method": "末两非空段文本 + alignment=right + right_indent≈32pt", "expect": "六个落款段全对；三份的第二行为裸日期"},
            {"id": "C1", "group": "机械自洽", "assert": "三份台账 summary 自洽（filled+missing=total，missing_required_names 与明细一致）",
             "method": "脚本三份逐项断言", "expect": "3/3 自洽；请示函 8/8、会议通知 11/11、工作总结 7/7 全填"},
            {"id": "C2", "group": "机械自洽", "assert": "三份 fields.json 顶层恰 7 键、summary 恰 6 键",
             "method": "json 键集断言", "expect": "键数 7/6"},
            {"id": "B1", "group": "边界纪律", "assert": "未给周报/工作总结补称谓段，未给请示函/会议通知合并落款为一行",
             "method": "版式断言 + 裁判通读", "expect": "无越界版式"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "for t in ('请示函','会议通知','工作总结'):\n"
            "    d=Document(f'<outdir>/{t}/文书.docx')\n"
            "    ps=[p.text for p in d.paragraphs]\n"
            "    f=json.load(open(f'<outdir>/{t}/fields.json',encoding='utf-8'))\n"
            "    print(t, 'TITLE', repr(ps[0]), '| SIG', [p for p in ps if p.strip()][-2:], '| SUM', f['summary'])\n"
            "PY"
        ),
        "check_expect": "三行：TITLE 逐字命中三条公式 / SIG 两行且第二行为裸日期 / SUMMARY 8-0-0、11-0-0、7-0-0",
        "anti_saturation": (
            "旧 ab1 断言过「请示函/会议通知称谓顶格」，但从未断言**工作总结/周报不得有称谓段**"
            "（负向版式），也未断言行内标签的全角空格分隔字面与「裸日期无标签」这两处字面。"
            "本题把版式断言从「四要素对四类成立」收紧到「逐字字面 + 负向断言」，且换成全新 nonce 实例。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型常给工作总结加「各位领导：」式称谓（F2 负向断言失分）、"
            "把全角空格分隔写成半角（F3 失分）、给裸日期加标签（F5 失分）。"
            "负向断言（F2）是旧题集完全没有的类型，对裸模型的区分度最高。"),
        "old_task_avoided": [
            "不复现 ab1 的「四模板 × case1 全量生成 + 字段一致率 ≥90%」口径（本题只跑三类、断言落在版式字面）",
            "不复现 ab2/ab3 的缺失记账与占位渲染（本题三份数据全字段齐全）",
            "不复现 ab5 的确定性与 runner 红绿自校验",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:99 V3 称谓仅两类模板",
            "dist/office-templates-skill/SKILL.md:101 V5 落款与裸日期",
            "dist/office-templates-skill/SKILL.md:102 V6 全角点编号",
            "dist/office-templates-skill/scripts/gen_doc.py:252-300 build_doc 三分支",
        ],
    },
    {
        "task_id": "t04", "dim": "能力", "nonce": N["t04"],
        "title": "F6 模板外键：字典序记账、不进台账明细、不影响文书",
        "nonce_values": {"部门": "供应链计划处", "填报人": "魏娥",
                          "外键": ["备注", "审批人", "密级"], "外键期望序（Python sorted() 码位序）": ["备注", "审批人", "密级"]},
        "entry": CMD,
        "input": _case("周报/case2.json", D_T04),
        "instruction": (
            "使用 office-templates 技能，把 data/周报/case2.json 渲染成周报，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据里有几个键不在周报模板的字段表内。"
            "请如实处理它们，并在交付时告诉我这些键的情况。"),
        "goal_state": "unknown_keys 按字典序恰为 [\"密级\",\"备注\",\"审批人\"]；三键不出现于 fields 明细与 filled/missing；不影响文书。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S2", "structure": "F1",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "summary.unknown_keys 逐字 == [\"备注\", \"审批人\", \"密级\"]（字典序 = Python sorted() 的码位序，非输入顺序：备 U+5907 < 审 U+5BA1 < 密 U+5BC6）",
             "method": "json 读并做 == 比对", "expect": "顺序为 备注→审批人→密级"},
            {"id": "S2", "group": "语义", "assert": "三个外键的值（内部 / 此键不在模板字段内 / 魏娥）未被渲染进文书任何段落",
             "method": "正文全文包含检索三个外键值", "expect": "三处命中数均为 0"},
            {"id": "C1", "group": "机械自洽", "assert": "外键不出现在 fields 明细、filled_fields、missing_fields 任何位置",
             "method": "脚本：外键集合 ∩ (明细名 ∪ filled ∪ missing) == 空集", "expect": "交集为空"},
            {"id": "C2", "group": "机械自洽", "assert": "summary 自洽：total=7, filled=7, missing=0（外键不计入 total，明细仍恰 7 项）",
             "method": "json 读 + 自洽断言", "expect": "filled+missing=total=7"},
            {"id": "F1", "group": "结构版式", "assert": "文书结构不受外键影响：小节一/二/三齐全（问题与需协调事项有值故不省略）",
             "method": "段落遍历", "expect": "三个节头齐全；节序 一→二→三"},
            {"id": "B1", "group": "边界纪律", "assert": "交付回复中主动提示存在未被模板消费的键（SKILL 工作流第 4 步）",
             "method": "裁判通读回复", "expect": "点名 3 个外键或明确说明有未消费键"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "names=[x['name'] for x in f['fields']]\n"
            "extra={'密级','备注','审批人'}\n"
            "print('UNKNOWN', f['summary']['unknown_keys'])\n"
            "print('LEAK_INTO_LEDGER', sorted(extra & (set(names)|set(f['filled_fields'])|set(f['missing_fields']))))\n"
            "full='\\n'.join(p.text for p in Document('<outdir>/文书.docx').paragraphs)\n"
            "print('VALUES_IN_DOC', {v: full.count(v) for v in ('内部','此键不在模板字段内')})\n"
            "PY"
        ),
        "check_expect": "UNKNOWN ['密级','备注','审批人'] / LEAK_INTO_LEDGER [] / VALUES_IN_DOC 计数均 0",
        "anti_saturation": (
            "旧 ab2 只用一个外键「备注」，且 rubric 只断言 `unknown_keys=[备注]`，"
            "既没测**字典序**（单键时顺序不可观测），也没测外键**不进台账明细**这条负向断言。"
            "本题用三键把顺序变成可观测量，并新增两条负向断言。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型常按输入顺序记录外键（S1 失分）、"
            "或把外键一并塞进台账明细导致 total=10（S2/C1/C2 三处失分）。"
            "「total 仍为 7」这一条能把「顺手记账」的失败模式一次抓住。"),
        "old_task_avoided": [
            "不复现 ab2 的必填缺失 ____ 占位与选填留空/省略渲染（本题全字段齐全，只缺选填列表）",
            "不复现 ab3 的空数组占位条目",
            "外键场景虽与 ab2 重叠，但断言维度完全不同（字典序 + 负向不进明细 + 不计入 total），且实例为全新 nonce",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:59 F6 模板外键按字典序记入 summary.unknown_keys",
            "dist/office-templates-skill/SKILL.md:140 交付前核对 unknown_keys",
            "dist/office-templates-skill/scripts/gen_doc.py:157 sorted(...)，外键不进 details",
        ],
    },
    {
        "task_id": "t05", "dim": "边界", "nonce": N["t05"],
        "title": "边界：空白串与全空白数组一律判缺失（near-miss），必填缺失 → 占位条目与占位，仍 exit 0",
        "nonce_values": {"总结时段": "2026 年 9 月", "下一步": "固化标注口径并冻结判定样例",
                          "空白文本字段": ["总结主体", "成文日期"],
                          "全空白列表字段": ["工作回顾（空白串形态）", "主要成绩（三项全空白数组）", "存在问题（选填，两项全空白）"]},
        "entry": CMD,
        "input": _case("工作总结/case1.json", D_T05),
        "instruction": (
            "使用 office-templates 技能，把 data/工作总结/case1.json 渲染成工作总结，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据里有些字段是空字符串、有些是只有空白的数组、"
            "有些列表里的每一项都是空白。请按技能包规定判断哪些字段算缺失、缺失了怎么渲染，"
            "并在交付时把缺哪些字段说清楚。"),
        "goal_state": "3 个必填字段（总结主体/工作回顾/主要成绩）判缺失并按 F1/F4 渲染；2 个选填字段判缺失走省略或留空；exit 0；台账如实记账。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "退出码为 0（必填缺失不是运行错误），两件产物齐全",
             "method": "echo $? + find 计数", "expect": "码 0，计数=2"},
            {"id": "S1", "group": "语义", "assert": "总结主体为空白串「   」→ 判缺失，标题代入占位符，逐字 = 「____2026 年 9 月工作总结」",
             "method": "标题段文本逐字比对 + fields.title 比对", "expect": "两者相等且恰含一处 ____"},
            {"id": "S2", "group": "语义", "assert": "工作回顾为空白串形态的必填列表 → 判缺失、value=null、rendered_as=「以____占位条目」",
             "method": "台账明细三项（status/value/rendered_as）比对", "expect": "missing / null / 以____占位条目"},
            {"id": "S3", "group": "语义", "assert": "主要成绩为三项全空白数组（三项分别为空格串、制表符、空串）→ 判缺失，不得判为「有 3 个空条目」的 filled",
             "method": "台账明细比对", "expect": "missing / null / 以____占位条目"},
            {"id": "C1", "group": "机械自洽", "assert": "summary 自洽：total=7, filled=2, missing=5, missing_required=3",
             "method": "json 读 + 自洽断言", "expect": "filled+missing=7；filled 仅 总结时段 与 下一步工作打算"},
            {"id": "C2", "group": "机械自洽", "assert": "missing_required_names 逐字 == [\"总结主体\",\"工作回顾\",\"主要成绩\"]，顺序等于字段表顺序而非字典序",
             "method": "脚本比对字段表顺序", "expect": "顺序为 总结主体 → 工作回顾 → 主要成绩"},
            {"id": "F1", "group": "结构版式", "assert": "两个必填列表缺失 → 各渲染一个占位条目「1．____」（小节标题保留）",
             "method": "正文检索 `1．____` 计数", "expect": "命中数 = 2，分别落在「一、工作回顾」「二、主要成绩」节下"},
            {"id": "F2", "group": "结构版式", "assert": "选填小节「存在问题」缺失 → 整节省略（文中无该节头），其后一节编号仍为「四、」",
             "method": "段落遍历 + 节头逐字比对", "expect": "无「三、存在问题」；有「四、下一步工作打算」"},
            {"id": "B1", "group": "边界纪律", "assert": "交付回复中点名缺失的必填字段；未因数据「几乎全空」而拒绝成文或编造总结内容",
             "method": "裁判通读回复 + 正文检索具体实体", "expect": "点名 3 个必填缺失；正文无编造条目"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "print('SUM', f['summary'])\n"
            "print('DETAIL', {x['name']: (x['status'], x['value'], x.get('rendered_as')) for x in f['fields']})\n"
            "full='\\n'.join(p.text for p in Document('<outdir>/文书.docx').paragraphs)\n"
            "print('PLACEHOLDER_ITEM_HITS', full.count('1．____'))\n"
            "print('SECTIONS', [l for l in full.split('\\n') if l[:2] in ('一、','二、','三、','四、')])\n"
            "PY"
        ),
        "check_expect": "SUM {'total':7,'filled':2,'missing':5,'missing_required':3,'missing_required_names':['总结主体','工作回顾','主要成绩'],'unknown_keys':[]} / PLACEHOLDER_ITEM_HITS 2 / SECTIONS 无「三、存在问题」",
        "anti_saturation": (
            "旧 ab3 测的是**空数组** `[]` 与**空字符串** `\"\"`；本题改测**非空但全空白**的形态："
            "必填 text 的空白串（\"   \"）、必填 list 的空白串形态、必填 list 的三项全空白数组"
            "（[\"   \",\"\\t\",\"\"]）、选填 list 的两项全空白数组。这是 SKILL §3.2 缺失判定里明写、"
            "但旧题集从未触发的一条。near-miss 变体是反饱和的标准做法。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型倾向把 `[\"   \",\"\\t\",\"\"]` 当作「有 3 个条目」从而判 filled（S3/C1 双否），"
            "或把选填的全空白数组当成有效小节照常成文（F2 失分）。本题是本包区分度最高的一类断言。"),
        "old_task_avoided": [
            "不复现 ab3 的空数组 `[]` 与字符串型列表单项化（本题全部是空白形态，且模板换为工作总结）",
            "不复现 ab2 的非法模板名/不存在文件/非法 JSON/顶层非对象四组拒答",
            "复用了「必填缺失 → ____ 占位」这一 SKILL 规则，但断言维度是缺失**判定**（空白 vs 空）而非旧题的渲染形态枚举",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:52 缺失判定（空白字符串 / 空数组 / 全空白数组）",
            "dist/office-templates-skill/SKILL.md:56-57 F4 列表缺失渲染分支",
            "dist/office-templates-skill/scripts/gen_doc.py:92-106 norm_list 的 items 过滤与 bool 判定",
        ],
    },
    {
        "task_id": "t06", "dim": "边界", "nonce": N["t06"],
        "title": "边界：必填字段全部缺失 → 占位标题 + 占位正文 + 台账 10 missing 仍 exit 0（本模板无必填 list，故无占位条目）",
        "nonce_values": {"标题期望": "关于召开____的通知", "占位条目数": 2},
        "entry": CMD,
        "input": _case("会议通知/case1.json", D_T06),
        "instruction": (
            "使用 office-templates 技能，把 data/会议通知/case1.json 渲染成会议通知，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据里绝大多数字段都没有给。"
            "请按技能包规定如实渲染并记账，不要为了凑齐一份像样的通知而自行编造会议名称、时间、地点或参会人员。"),
        "goal_state": "标题 = 关于召开____的通知；六个必填文本全部 ____ 占位且全文 ____ 计数恰 6；台账 filled=1/missing=10/missing_required=6；exit 0。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "退出码 0，两件产物齐全", "method": "echo $? + find 计数", "expect": "码 0，计数=2"},
            {"id": "S1", "group": "语义", "assert": "标题逐字 = 「关于召开____的通知」（四个下划线代入缺失的会议名称）",
             "method": "标题段文本逐字比对 + fields.title 比对", "expect": "两者相等且含 ____"},
            {"id": "S2", "group": "语义", "assert": "六个必填文本（会议名称/召开单位/主送对象/会议时间/会议地点/参会人员）全部以 ____ 占位，无一被编造",
             "method": "正文全文检索是否出现任何具体会议名/日期/地点；台账 missing_required_names 比对",
             "expect": "missing_required_names == [\"会议名称\",\"召开单位\",\"主送对象\",\"会议时间\",\"会议地点\",\"参会人员\"]（字段表顺序）"},
            {"id": "S3", "group": "语义", "assert": "选填小节（会议要求）缺失 → 整节省略，文中不出现「一、会议要求」节头",
             "method": "段落遍历", "expect": "无「一、会议要求」"},
            {"id": "C1", "group": "机械自洽", "assert": "summary 自洽：total=11, filled=1, missing=10, missing_required=6",
             "method": "json 读 + 自洽断言", "expect": "filled+missing=11；filled 仅 会议议题"},
            {"id": "C2", "group": "机械自洽", "assert": "负向断言：会议通知字段表中**没有必填 list 字段**，故正文不得出现任何「1．____」占位条目（防止把「所有缺失字段都渲染成占位条目」的错误泛化到本模板）",
             "method": "正文检索 `1．____`", "expect": "命中数 = 0"},
            {"id": "F1", "group": "结构版式", "assert": "全文 ____ 出现次数恰为 6（标题 1 + 称谓 1 + 会议时间/地点/参会人员 3 + 落款 1）；称谓段「____：」仍顶格",
             "method": "正文计数 + 段落 w:ind", "expect": "计数 = 6；称谓段无首行缩进"},
            {"id": "F2", "group": "结构版式", "assert": "落款两行：召开单位位置为 ____（必填缺失占位）+ 发文日期行为空",
             "method": "末两非空段文本 + alignment", "expect": "第一行含 ____；两行均右对齐"},
            {"id": "B1", "group": "边界纪律", "assert": "未编造会议名称/时间/地点/参会人员；交付回复中如实指出缺哪些必填字段",
             "method": "裁判通读正文与回复 + 检索是否出现具体值", "expect": "无编造；回复点名 6 个必填缺失字段"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "print('SUM', f['summary'])\n"
            "print('TITLE', repr(f['title']))\n"
            "d=Document('<outdir>/文书.docx')\n"
            "full='\\n'.join(p.text for p in d.paragraphs)\n"
            "print('PLACEHOLDER_COUNT', full.count('____'))\n"
            "print('SEC_HEADERS', [p for p in d.paragraphs if p.text.startswith(('一、','二、','三、'))])\n"
            "PY"
        ),
        "check_expect": "SUM {'total':11,'filled':1,'missing':10,'missing_required':6, ...} / TITLE '关于召开____的通知' / PLACEHOLDER_COUNT 6 / SEC_HEADERS 空",
        "anti_saturation": (
            "旧 ab2 测的是**部分**必填缺失（请示函 2 个、会议通知 2 个），"
            "本题推到**必填全部缺失**（会议通知 6 个必填全缺、仅剩 1 个选填有值）的极端边界，"
            "并新增一条负向断言 C2：必填列表缺失才渲染占位条目，本模板没有必填 list，"
            "所以「1．____」必须为 0 次——防止把「所有缺失字段都渲染成占位条目」的错误泛化。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型在这种极端输入下极易「脑补」会议名称与时间（B1/S2 失分），"
            "或把缺失一律渲染成占位条目（C2 失分）。负向断言 C2 是旧题集没有的类型，区分度强。"),
        "old_task_avoided": [
            "不复现 ab2 的具体缺失清单（[\"主送机关\",\"请示事项\"] 与 [\"会议名称\",\"会议地点\"]）与 unknown_keys 场景",
            "不复现 ab3 的「周期空字符串 + 本周工作内容空数组」组合",
            "不复现 ab4 的四组非法输入拒答",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:53-57 F1/F2/F4 缺失渲染三分支",
            "dist/office-templates-skill/SKILL.md:60 必填缺失不是运行错误（F7/C3）",
            "dist/office-templates-skill/scripts/gen_doc.py:242-250 emit_list 占位条目仅在 items 为空时",
        ],
    },
    {
        "task_id": "t07", "dim": "陷阱", "nonce": N["t07"],
        "title": "陷阱：越界请求（docx→pdf / 红头公章 / 增删字段 / 多文档合并）必须显式拒答且不产出越界产物",
        "nonce_values": {"总结主体": "平台工程部", "越界请求数": 4},
        "entry": CMD,
        "input": _case("工作总结/case1.json", D_T07),
        "instruction": (
            "使用 office-templates 技能，把 data/工作总结/case1.json 写成工作总结。\n"
            "另外我还有几个要求，一并做掉：\n"
            "1）顺便把它转成 PDF，我好直接发出去；\n"
            "2）给这份总结加个红头文件和公章；\n"
            "3）再加两个字段：「审批人」和「密级」，一起放进台账；\n"
            "4）把这季度的另外三份总结合并成一份总文件。"),
        "goal_state": "只交付范围内产物（文书.docx + fields.json）；四项越界请求逐条显式声明不做；无 pdf/红头/新增字段/合并文件。",
        "assert_map": {"endpoint": "A1–A3", "semantic": "S1–S2", "structure": "F1",
                       "mechanical": "C1–C2", "discipline": "B1–B4"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "退出码 0；<outdir> 恰含 文书.docx + fields.json",
             "method": "echo $? + find 计数", "expect": "码 0，计数=2"},
            {"id": "A2", "group": "端态", "assert": "无 PDF 产物（全盘检索 .pdf/.docx 变体）",
             "method": "find <workdir> -iname '*.pdf'", "expect": "命中数 = 0"},
            {"id": "A3", "group": "端态", "assert": "无合并总文件（未产出第二份含多季度内容的 docx）",
             "method": "find <workdir> -name '*.docx' + 逐份标题核对", "expect": "只有 1 份 docx，标题 = 「平台工程部2026 年 9 月工作总结」"},
            {"id": "S1", "group": "语义", "assert": "文书内容严格来自输入数据，未因「加审批人/密级」而把新键写入正文",
             "method": "正文检索「审批人」「密级」", "expect": "命中数 = 0"},
            {"id": "S2", "group": "语义", "assert": "fields.json 未被扩字段：顶层恰 7 键、明细恰 7 项",
             "method": "json 键数与明细计数", "expect": "7 键 / 7 项；无「审批人」「密级」"},
            {"id": "C1", "group": "机械自洽", "assert": "summary.unknown_keys == []（新键未被写入数据文件）",
             "method": "json 读", "expect": "[]"},
            {"id": "C2", "group": "机械自洽", "assert": "summary 自洽：total=7, filled=7, missing=0",
             "method": "json 自洽断言", "expect": "7/7 全填"},
            {"id": "F1", "group": "结构版式", "assert": "版式符合 V1–V6（标题居中黑体二号、正文仿宋三号缩进两字符、落款两行右对齐）",
             "method": "python-docx 读属性", "expect": "逐项成立"},
            {"id": "B1", "group": "边界纪律", "assert": "对「转 PDF」显式声明不做（非目标），并指出该技能只出 docx",
             "method": "裁判通读回复", "expect": "有明确的不做说明"},
            {"id": "B2", "group": "边界纪律", "assert": "对「红头文件 / 公章」显式声明不做（非目标）",
             "method": "裁判通读回复", "expect": "有明确的不做说明"},
            {"id": "B3", "group": "边界纪律", "assert": "对「增删字段」显式声明不做；并说明未消费的多余键会记入 unknown_keys（如需可另行处理）",
             "method": "裁判通读回复", "expect": "有明确的不做说明"},
            {"id": "B4", "group": "边界纪律", "assert": "对「多文档合并」显式声明不做（非目标）",
             "method": "裁判通读回复", "expect": "有明确的不做说明"},
        ],
        "check_cmd": (
            "cd <workdir> && echo '--- artifacts ---' && find . -name '*.docx' -o -name '*.pdf' -o -name 'fields.json' | sort && python - <<'PY'\n"
            "import json\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "print('TOP_KEYS', len(f), sorted(f))\n"
            "print('DETAIL_N', len(f['fields']))\n"
            "print('SUMMARY', f['summary'])\n"
            "PY"
        ),
        "check_expect": "仅 <outdir>/文书.docx 与 <outdir>/fields.json；TOP_KEYS 7 / DETAIL_N 7 / SUMMARY filled=7 unknown_keys=[]",
        "anti_saturation": (
            "旧 ab1–ab5 全是「范围内的正例」，五题里没有一道涉及非目标拒答。本题把 SKILL §2「何时不用」"
            "的四条非目标（模板定制/字段增删/多文档合并、docx→pdf、红头公章）逐条做成 trap，"
            "并给出「做了反而失败」的正向判据（A2/A3/S1/S2 四条）。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型面对「顺便转 PDF」「加个字段」这类追加请求时，"
            "有很强的「尽力满足」倾向（要么假装做了、要么用 libreoffice 硬转），这是本题的主攻点；"
            "B 组四条独立判负、discipline 权重 40 分，裸模型在此题上极易崩盘。"),
        "old_task_avoided": [
            "旧题集无任何非目标/拒答类题目（ab4 的拒答只针对非法输入，不涉及非目标请求）",
            "不复现 ab2 的必填缺失渲染（本题全字段齐全）",
            "不复现 ab5 的确定性与 runner 自校验",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:29-33 何时不用（四条非目标）",
            "dist/office-templates-skill/SKILL.md:120-126 环境依赖（无 pdf/红头能力）",
            "dist/office-templates-skill/scripts/gen_doc.py:258-300 build_doc 无 pdf/合并/字段增删路径",
        ],
    },
    {
        "task_id": "t08", "dim": "陷阱", "nonce": N["t08"],
        "title": "陷阱：数据语义校验不做——非法电话/日期原样透传、exit 0、台账按原样记账",
        "nonce_values": {"会议名称": "KP-A-86018 项目结项评审会", "会议时间": "下下周某天，具体再定",
                          "联系电话": "010-abc", "发文日期": "待定"},
        "entry": CMD,
        "input": _case("会议通知/case1.json", D_T08),
        "instruction": (
            "使用 office-templates 技能，把 data/会议通知/case1.json 渲染成会议通知，产物写入 <outdir>"
            "（文书.docx + fields.json）。这份数据里的会议时间写得比较随意，电话也不是标准号码格式。"
            "请按技能包规定如实成文。"),
        "goal_state": "非法电话与随意时间原样入文、不报错不改写；台账 value 为 strip 后的原字面；exit 0；11/11 全填。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1–B2"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "退出码为 0（语义不合法不是非法输入）", "method": "echo $?", "expect": "0"},
            {"id": "A2", "group": "端态", "assert": "两件产物齐全", "method": "find 计数", "expect": "计数=2"},
            {"id": "S1", "group": "语义", "assert": "联系电话原样入文为「010-abc」，未被改写成合法号码、未被清洗为数字",
             "method": "正文包含检索 + 逐字比对", "expect": "逐字为 010-abc"},
            {"id": "S2", "group": "语义", "assert": "会议时间原样入文为「下下周某天，具体再定」，未被解析/补全/报错",
             "method": "正文逐字比对", "expect": "逐字相同"},
            {"id": "S3", "group": "语义", "assert": "发文日期「待定」原样入文（选填但有值 → filled，非 missing）",
             "method": "台账明细 + 落款段比对", "expect": "status=filled，落款第二行 = 待定"},
            {"id": "C1", "group": "机械自洽", "assert": "summary 自洽：total=11, filled=11, missing=0, unknown_keys=[]",
             "method": "json 自洽断言", "expect": "11/11 全填"},
            {"id": "C2", "group": "机械自洽", "assert": "台账 value 与输入 strip 后逐字相等（未做任何语义规整）",
             "method": "脚本逐字段比对", "expect": "11/11 相等"},
            {"id": "F1", "group": "结构版式", "assert": "行内标签串逐字 = 「联系人：左芬　　联系电话：010-abc」",
             "method": "段落逐字比对", "expect": "逐字相同"},
            {"id": "F2", "group": "结构版式", "assert": "落款两行「平台工程部」+「待定」，均右对齐右缩进两字",
             "method": "末两非空段 + alignment", "expect": "对齐与缩进成立"},
            {"id": "B1", "group": "边界纪律", "assert": "未因「电话不像号码」「时间不确定」而擅自替用户补全或拒绝成文",
             "method": "正文检索是否出现新增日期/号码；裁判通读", "expect": "无补全、无拒答"},
            {"id": "B2", "group": "边界纪律", "assert": "若回复中提到数据质量问题，只能表述为「按原样处理」，不得声称已校验通过",
             "method": "裁判通读回复", "expect": "无「已校验」「格式正确」类表述"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "from docx import Document\n"
            "d=Document('<outdir>/文书.docx')\n"
            "full='\\n'.join(p.text for p in d.paragraphs)\n"
            "print('PHONE_KEPT', '010-abc' in full)\n"
            "print('TIME_KEPT', '下下周某天，具体再定' in full)\n"
            "f=json.load(open('<outdir>/fields.json',encoding='utf-8'))\n"
            "print('SUM', f['summary'])\n"
            "print('VALUES', {x['name']:x['value'] for x in f['fields'] if x['name'] in ('联系电话','会议时间','发文日期')})\n"
            "PY"
        ),
        "check_expect": "PHONE_KEPT True / TIME_KEPT True / SUM {'total':11,'filled':11,'missing':0,...} / VALUES 原字面",
        "anti_saturation": (
            "旧 ab4 的四组拒答全是**结构性非法输入**（模板名/文件/JSON/顶层类型），"
            "从未测过「数据语义不合法但必须照收」这一档。裸模型在「010-abc」「下下周某天」上的默认反应"
            "是报错或追问，正好与本技能的「数据语义校验不做、按原样字符串处理」正面对撞。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。本题是「过度尽职」陷阱：裸模型极易"
            "① 因电话非法而 exit 2（A1 失分）；② 主动清洗/补全数据（S1/S2 失分）；"
            "③ 反问用户后再交付，导致本次无产物（A1/A2 失分）。三处均为「帮倒忙」型失败，区分度稳定。"),
        "old_task_avoided": [
            "不复现 ab4 的四组结构性非法输入（本题输入是完全合法的 JSON 对象）",
            "不复现 ab2/ab3 的缺失占位与省略渲染（本题 11/11 全填，无缺失）",
            "不复现 ab1 的四模板全量 + 一致率口径、ab5 的确定性",
        ],
        "design_basis_extra": [
            "dist/office-templates-skill/SKILL.md:32 数据语义校验不在范围（日期/电话按原样字符串处理）",
            "dist/office-templates-skill/SKILL.md:117 必填缺失/选填缺失/模板外键/空列表/字符串型列表都不是错误",
            "dist/office-templates-skill/scripts/gen_doc.py:83-90 norm_text 原样 strip，不做语义规整",
        ],
    },
]

TASKS[1]["weights"] = {"endpoint": 12, "semantic": 34, "structure": 20, "mechanical": 20, "discipline": 14}
TASKS[2]["weights"] = {"endpoint": 14, "semantic": 20, "structure": 34, "mechanical": 18, "discipline": 14}
TASKS[4]["weights"] = {"endpoint": 12, "semantic": 30, "structure": 20, "mechanical": 24, "discipline": 14}
TASKS[6]["weights"] = {"endpoint": 10, "semantic": 18, "structure": 16, "mechanical": 16, "discipline": 40}
TASKS[7]["weights"] = {"endpoint": 12, "semantic": 34, "structure": 16, "mechanical": 24, "discipline": 14}