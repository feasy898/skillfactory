# -*- coding: utf-8 -*-
"""spec_hot — hot-templates-skill 新任务集（t01–t08）。

旧题考点（反饱和对照，见 ../DESIGN.md 差异表）：
  ab-001 dy 满3卖点：6 要素顺序 + filled_from_input 含 point#1..3 + placeholder_count 自洽 + 无 {{ }}
  ab-002 xhs 5卖点：7 要素 + emoji 四映射 + 超出截断 points_unused + 标签组「3-8 个 #」+ 首标签派生
  ab-003 wx 0卖点：5 要素 + 三段论开头 + points_used [null,null,null] + total_open 求和
  ab-004 video 1卖点：6 镜 + 表头四列 + 时间轴冻结 + shot_3 填充 shot_4/5 占位 + 分镜总表
  ab-005 确定性双跑逐字节 + 非法 platform exit 2 + 空 topic exit 2
旧输入 8 份（4 平台 × case1/case2）全部被旧题集使用。

本集新考点（均为旧题集空白）：
  dy 冻结字面（钩子/CTA 句式）与 pain_point/cta 的 filled_from_input=[]
  xhs 标签组精确计数 ==6（字面口径）/ 标题数字恒为 3
  wx 满 3 卖点 total_filled_from_input == 7（4 topic + 3 point）/ thesis_how 逐字三行 / 金句逐字
  video 0 卖点全缺失：要素 name 冻结 + meta 7 键 + shot_4 placeholder_count==4 & 去重 3 token + 总 open==18
  多平台一次生成 → 一次一跑（四平台各跑一次）
  卖点空白串按缺失处理 + 保序
  --points 形态矩阵（对象形态 / BOM 文件 / 非字符串项 / 不存在路径四类）
  冻结 token 防改写 + {{ }} 残留 + 三向统计同源
"""

PKG = "hot-templates-skill"

N = {
    "t01": "hot-t01-8a12f7",
    "t02": "hot-t02-3d6b90",
    "t03": "hot-t03-5f24c8",
    "t04": "hot-t04-b70a36",
    "t05": "hot-t05-1c9e5d",
    "t06": "hot-t06-42fb8a",
    "t07": "hot-t07-e60d31",
    "t08": "hot-t08-9a7c04",
}

CMD = "python <pkg>/scripts/gen.py --platform <dy|xhs|wx|video> --topic <主题> --points <卖点.json 或内联 JSON> --outdir <outdir>"


def pts(*items):
    return list(items)


P = {
    # t01 dy 满 3 卖点
    "t01": pts("前一晚把第二天三件要事写下来",
               "通勤路上只听行业播客不刷短视频",
               "到工位先花十分钟写当日清单"),
    # t02 xhs 4 卖点（1 条超出 → points_unused 恰 1 条）
    "t02": pts("签约前核对房东房产证与承租人证件是否一致",
               "押金退还条件与时限逐条写进合同",
               "入住当天全屋拍照录像留档",
               "水电燃气表底数抄进合同附件"),
    # t03 wx 满 3 卖点
    "t03": pts("把日程表改成九十分钟时间块",
               "关掉所有推送建立一个免打扰岛",
               "用固定的下班仪式给大脑按结束键"),
    # t04 video 0 卖点
    "t04": [],
    # t06 空白串卖点（保序）
    "t06": pts("第一件事先把台面清空",
               "   ",
               "第三件事当天做完不留隔夜"),
    # t07 卖点形态矩阵
    "t07": pts("把旧数据先导出再重装",
               "换固态后先跑一次全盘体检",
               "保留一份原系统镜像以备回退"),
}


def _md_case(points, topic, note=None):
    """points 文件 + 运行参数。"""
    return {
        "files": [{"path": "points.json", "encoding": "utf-8", "data": points}],
        "args": {"platform": None, "topic": topic, "points_arg": "points.json"},
        "note": note or "",
    }


TASKS = [
    {
        "task_id": "t01", "dim": "能力", "nonce": N["t01"],
        "title": "dy 冻结字面与槽位口径：6 要素每恰 1 个 token、total_open=6、钩子/CTA 句式冻结、痛点与 CTA 无填充",
        "nonce_values": {"topic": "旧笔记本的续命改装",
                          "卖点": P["t01"], "要素数": 6, "总占位": 6, "去重 token 数": 6},
        "entry": CMD,
        "input": _md_case(P["t01"], "旧笔记本的续命改装"),
        "instruction": (
            "使用 hot-templates 技能，生成抖音口播爆款内容骨架，产物写入 <outdir>"
            "（<outdir>/骨架.md 与 <outdir>/structure.json）。材料自含——platform=dy，"
            "topic=旧笔记本的续命改装，points 见 data/points.json（恰好 3 条）。"
            "模板冻结：3 秒钩子 + 痛点 + 价值点×3 + CTA，各要素的开放槽位字面不得改写。"),
        "goal_state": "6 要素顺序冻结、每要素恰 1 个占位（total_open=6、去重 token=4）、钩子与 CTA 句式逐字、pain_point/cta 无输入填充。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "<outdir> 恰含 骨架.md 与 structure.json，均非空",
             "method": "find 计数 + 文件大小", "expect": "计数=2，均非空"},
            {"id": "A2", "group": "端态", "assert": "退出码 0，stdout 打印一行 OK 前缀摘要",
             "method": "echo $? + stdout 首行", "expect": "码 0，首行以 `OK platform=dy` 开头"},
            {"id": "S1", "group": "语义", "assert": "hook_3s 文本逐字以「别划走！还在为「旧笔记本的续命改装」反复内耗的人」开头（冻结句式，主题代入尖括号内）",
             "method": "structure.json 元素文本 startswith 断言", "expect": "逐字命中"},
            {"id": "S2", "group": "语义", "assert": "cta 文本逐字含「点赞收藏，评论区扣「1」」（冻结扣词）",
             "method": "元素文本 in 断言", "expect": "逐字命中"},
            {"id": "S3", "group": "语义", "assert": "pain_point 与 cta 的 filled_from_input 均为 []（这两要素不含 topic 填充），value_1..3 各恰含一个 point#N",
             "method": "structure.json 逐要素字段比对", "expect": "pain_point/cta == []；value_1/2/3 == [\"point#1\"/\"point#2\"/\"point#3\"]"},
            {"id": "F1", "group": "结构版式", "assert": "6 个要素 id 顺序恰为 hook_3s、pain_point、value_1、value_2、value_3、cta",
             "method": "structure.json elements[].id 序列比对", "expect": "顺序一致，无增删"},
            {"id": "F2", "group": "结构版式", "assert": "每个要素恰 1 个占位 token（by_element 六项全为 1），total_open == 6",
             "method": "structure.json placeholder_stats 比对 + 正文正则重计数", "expect": "by_element 六项 ==1；total_open == 6"},
            {"id": "C1", "group": "机械自洽", "assert": "每个元素的 placeholder_count 与其 text 正则重计数一致；total_open（出现次数）== 6，而 open_tokens_unique（去重保序）== 4（value_1..3 共用同一 token，去重后计 1）",
             "method": "正则 `【占位:([^】]*)】` 重计数 vs by_element，并读 open_tokens_unique", "expect": "6/6 一致；unique 长度 4"},
            {"id": "C2", "group": "机械自洽", "assert": "骨架.md 首行为 `# 抖音口播稿 · 爆款骨架`，含主题行与尾部「占位符统计」节，统计数字与 structure.json 同源",
             "method": "骨架.md 文本比对 + 数字比对", "expect": "逐字一致，数字 == 6"},
            {"id": "B1", "group": "边界纪律", "assert": "未为开放槽位编造内容填充（占位 token 内文保持冻结字面），未把骨架扩写成成文",
             "method": "占位 token 文本逐字比对", "expect": "无填充、无扩写"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "s=json.load(open('<outdir>/structure.json',encoding='utf-8'))\n"
            "els={e['id']:e for e in s['elements']}\n"
            "print('IDS', [e['id'] for e in s['elements']])\n"
            "print('STATS', s['placeholder_stats'])\n"
            "print('FILL', {k:els[k]['filled_from_input'] for k in ('hook_3s','pain_point','value_1','value_2','value_3','cta')})\n"
            "print('HOOK_HEAD', els['hook_3s']['text'][:34])\n"
            "print('CTA_OK', '点赞收藏，评论区扣「1」' in els['cta']['text'])\n"
            "print('MD_HEAD', open('<outdir>/骨架.md',encoding='utf-8').readline().rstrip())\n"
            "PY"
        ),
        "check_expect": "IDS 6 个顺序冻结 / STATS total_open=6、by_element 六项为 1、open_tokens_unique 长度 4 / FILL pain_point=[] cta=[] / HOOK_HEAD '别划走！还在为「旧笔记本的续命改装」反复内耗的人' / CTA_OK True / MD_HEAD '# 抖音口播稿 · 爆款骨架'",
        "anti_saturation": (
            "旧 ab-001 只断言「钩子与 CTA 的 text 均非空」——**从未断言冻结字面**，"
            "也从未断言 pain_point 与 cta 的 filled_from_input 为空数组。"
            "本题把「非空」升级为逐字冻结断言，并加上「哪两个要素不含 topic」这一结构化负向断言。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型几乎不可能逐字复现钩子/CTA 的冻结句式"
            "（这些字面只在 references/frozen-tokens.md 与引擎里），S1/S2 双否即掉语义维度；"
            "而「照着 SKILL.md 概述编一份合理口播稿」的倾向会使 B1 失分。"),
        "old_task_avoided": [
            "不复现 ab-001 的「钩子/CTA 非空」弱断言与 placeholder_count 自洽（本题断言的是冻结字面与每要素恰好 1 个）",
            "不复现 ab-002 的 emoji 映射与 5 卖点截断（留给 t02）",
            "不复现 ab-005 的确定性与失败路径（留给 t08 / t07）",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/references/frozen-tokens.md dy 表（token 与 filled_from_input）",
            "dist/hot-templates-skill/scripts/gen.py:108 钩子冻结句式",
            "dist/hot-templates-skill/scripts/gen.py:126 CTA 冻结句式",
        ],
    },
    {
        "task_id": "t02", "dim": "能力", "nonce": N["t02"],
        "title": "xhs 精确口径：标签组 `#[^\\s#]+` 计数恰 6、标题数字恒为 3、emoji 四映射、4 卖点截断",
        "nonce_values": {"topic": "小户型厨房的收纳动线",
                          "卖点4": P["t02"], "标签期望（正则 #[^\\s#]+ 计数，含占位 token 内 2 个示例标签）": ["#小户型厨房的收纳动线", "#干货分享", "#方法论", "#自我提升", "#时间管理", "#精力管理】"],
                          "标签计数": 6},
        "entry": CMD,
        "input": _md_case(P["t02"], "小户型厨房的收纳动线"),
        "instruction": (
            "使用 hot-templates 技能，生成小红书图文爆款内容骨架，产物写入 <outdir>"
            "（骨架.md + structure.json）。材料自含——platform=xhs，topic=小户型厨房的收纳动线，"
            "points 见 data/points.json（共 4 条）。模板冻结：标题带数字 + emoji 规则 + 正文分块 + 标签组。"
            "请按包内规定的标签口径与截断口径如实产出。"),
        "goal_state": "7 要素冻结；标签组按正则恰 6 个 # 标签且首标签由主题派生；标题数字恒为 3；4 卖点取前 3、第 4 条入 points_unused。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F3",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全非空、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "标签组文本逐字 = 「#小户型厨房的收纳动线 #干货分享 #方法论 #自我提升 【占位:2个垂直领域标签，如：#时间管理 #精力管理】」",
             "method": "structure.json tag_group.text 逐字比对", "expect": "逐字命中（首标签为主题派生，已去 # 与空白）"},
            {"id": "S2", "group": "语义", "assert": "标题文本中的数字恒为 3（模板冻结为价值点数 3），即便输入给了 4 条卖点也不得变成 4",
             "method": "正则提取 title.text 里的数字", "expect": "恰含数字 3，且不含数字 4"},
            {"id": "S3", "group": "语义", "assert": "截断：points_used 恰为前 3 条原文；points_unused 恰含第 4 条原文，保序不乱",
             "method": "structure.json points_used / points_unused 比对", "expect": "used 长度 3、unused 长度 1；points_input_count == 4"},
            {"id": "F1", "group": "结构版式", "assert": "7 个要素 id 顺序恰为 title、hook_block、point_block_1..3、summary_block、tag_group",
             "method": "elements[].id 序列比对", "expect": "顺序一致，无增删"},
            {"id": "F2", "group": "结构版式", "assert": "标签计数口径：按正则 `#[^\\s#]+` 在 tag_group.text 上计数恰为 6（4 个字面标签 + 占位 token 内 2 个示例标签）",
             "method": "re.findall(r'#[^\\s#]+', text) 计数", "expect": "6；末个 token 因正则不排除右括号而形如「#精力管理】」（口径说明，不另设考点）；不得按「3-8 个」的宽口径判过"},
            {"id": "F3", "group": "结构版式", "assert": "emoji 映射冻结：title=🔥、hook_block=✅、point_block_*=💡、summary_block=📌、tag_group=🏷️（meta.emoji 逐项比对）",
             "method": "structure.json meta.emoji 逐要素比对", "expect": "五项全对"},
            {"id": "C1", "group": "机械自洽", "assert": "title / hook_block / summary_block 的 filled_from_input 含 topic；summary_block 另含 point#1..3",
             "method": "structure.json 逐要素比对", "expect": "三要素含 topic；summary 含 4 项"},
            {"id": "C2", "group": "机械自洽", "assert": "placeholder_stats.by_element 求和 == total_open（满 3 卖点应为 7），且与骨架.md「占位符统计」节数字一致",
             "method": "json 求和 + md 数字比对", "expect": "total_open == 7；两处数字相同"},
            {"id": "B1", "group": "边界纪律", "assert": "未自行给标签组增删标签以「凑到 3-8 个」的直觉区间；未把第 4 条卖点塞进正文块",
             "method": "标签计数 + points_used 比对", "expect": "计数恰 6、正文仅前 3 条"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "s=json.load(open('<outdir>/structure.json',encoding='utf-8'))\n"
            "els={e['id']:e for e in s['elements']}\n"
            "tg=els['tag_group']['text']\n"
            "print('TAGS', re.findall(r'#[^\\s#]+', tg))\n"
            "print('TAG_COUNT', len(re.findall(r'#[^\\s#]+', tg)))\n"
            "print('TITLE', els['title']['text'])\n"
            "print('NUM_IN_TITLE', re.findall(r'\\d', els['title']['text']))\n"
            "print('INPUT/USED/UNUSED', s['points_input_count'], s['points_used'], s['points_unused'])\n"
            "print('EMOJI', {e['id']: e['meta'].get('emoji') for e in s['elements']})\n"
            "print('TOTAL_OPEN', s['placeholder_stats']['total_open'])\n"
            "PY"
        ),
        "check_expect": "TAGS 6 个（前 5 个为 #小户型厨房的收纳动线/#干货分享/#方法论/#自我提升/#时间管理，第 6 个带尾部 】）/ TAG_COUNT 6 / NUM_IN_TITLE ['3'] / INPUT 4、USED 3 条、UNUSED 1 条 / EMOJI 五项冻结 / TOTAL_OPEN 7",
        "anti_saturation": (
            "旧 ab-002 的标签断言是「含 3-8 个 # 话题标签」——这个宽口径**任何**产物都能蒙混过关，"
            "是旧题集最接近饱和的一条。本题换成 references/frozen-tokens.md 明确写死的「计数口径 = 6」，"
            "并新增「标题数字恒为 3」这一在 4 卖点输入下的负向断言。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。宽口径「3-8 个」被换成精确到 6 的口径后，"
            "裸模型凭「标签要 3-8 个」的常识几乎必然给错个数或漏掉占位 token 内的两个示例标签；"
            "标题数字在 4 卖点输入下保持 3 也需要读 references 才能守住。"),
        "old_task_avoided": [
            "不复现 ab-002 的 3-8 个宽口径标签断言与 points_unused 存在性断言（本题断言精确计数与保序内容）",
            "不复现 ab-003 的 wx 零卖点边界（留给 t03）",
            "不复现 ab-004 的 video 时间轴冻结（留给 t04）",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/references/frozen-tokens.md xhs 表与标签计数口径 = 6",
            "dist/hot-templates-skill/scripts/gen.py:160-164 tag_group 字面",
            "dist/hot-templates-skill/scripts/gen.py:132-136 title 字面（数字 3 冻结）",
        ],
    },
    {
        "task_id": "t03", "dim": "能力", "nonce": N["t03"],
        "title": "wx 满 3 卖点：total_filled_from_input == 7（4 topic + 3 point）/ thesis_how 三行逐字 / 金句收尾逐字",
        "nonce_values": {"topic": "把周报写成三句话",
                          "卖点3": P["t03"], "总填充": 7, "topic 填充要素数": 4},
        "entry": CMD,
        "input": _md_case(P["t03"], "把周报写成三句话"),
        "instruction": (
            "使用 hot-templates 技能，生成公众号文章爆款内容骨架，产物写入 <outdir>"
            "（骨架.md + structure.json）。材料自含——platform=wx，topic=把周报写成三句话，"
            "points 见 data/points.json（恰好 3 条）。模板冻结：引子 + 三段论（是什么/为什么/怎么办）+ 金句收尾。"),
        "goal_state": "5 要素冻结；thesis_how 三行结构逐字；三抓手同居 thesis_how；总填充 7（topic 记 4 次 + point 记 3 次）；金句结构逐字。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全非空、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "thesis_how 文本首行逐字「三、怎么办」，次行逐字「落到操作层面，给你三个抓手：」，其后三行形如 `N. <卖点>——【占位:展开：具体做法+一个例子】`（N 为半角数字 + 空格）",
             "method": "按 \\n 切分后逐行比对", "expect": "共 5 行；三行序号为 1. 2. 3."},
            {"id": "S2", "group": "语义", "assert": "golden_ending 文本结构逐字：`「把周报写成三句话这件事，【占位:金句主体——句式建议：真正的…不是靠…，而是靠…】」` + 换行 + `共勉。`",
             "method": "逐字比对", "expect": "逐字命中，两行结构"},
            {"id": "S3", "group": "语义", "assert": "三个卖点全部同居 thesis_how 的三抓手，不得被拆到 thesis_what / thesis_why",
             "method": "三个卖点文本的全文出现位置断言", "expect": "每条只在 thesis_how 出现一次；其余两要素不含卖点原文"},
            {"id": "F1", "group": "结构版式", "assert": "5 个要素 id 顺序恰为 lead_in、thesis_what、thesis_why、thesis_how、golden_ending",
             "method": "elements[].id 序列比对", "expect": "顺序一致"},
            {"id": "F2", "group": "结构版式", "assert": "三个 thesis 要素的文本分别以「一、是什么」「二、为什么」「三、怎么办」开头",
             "method": "startswith 断言", "expect": "三处全中"},
            {"id": "C1", "group": "机械自洽", "assert": "placeholder_stats.total_filled_from_input == 7（topic 在 4 个要素各记一次 + point#1..3 各一次）",
             "method": "structure.json 逐要素 filled_from_input 汇总求和", "expect": "7"},
            {"id": "C2", "group": "机械自洽", "assert": "topic 填充恰出现在 4 个要素（lead_in / thesis_what / thesis_why / golden_ending），不出现在 thesis_how",
             "method": "脚本：含 'topic' 的要素 id 集合比对", "expect": "集合恰为那 4 个"},
            {"id": "B1", "group": "边界纪律", "assert": "未把「三抓手」扩写成正文段落（骨架只给结构 + 开放槽位）",
             "method": "文本比对", "expect": "无扩写、无编造案例"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json\n"
            "s=json.load(open('<outdir>/structure.json',encoding='utf-8'))\n"
            "els={e['id']:e for e in s['elements']}\n"
            "print('IDS', [e['id'] for e in s['elements']])\n"
            "print('HOW', els['thesis_how']['text'].split('\\n'))\n"
            "print('ENDING', els['golden_ending']['text'].split('\\n'))\n"
            "print('STATS', s['placeholder_stats']['total_filled_from_input'], s['placeholder_stats']['total_open'])\n"
            "print('TOPIC_IN', [e['id'] for e in s['elements'] if 'topic' in e['filled_from_input']])\n"
            "PY"
        ),
        "check_expect": "IDS 5 个 / HOW 五行（首两行为冻结文案，后三行为 `N. 卖点——【占位:…】`）/ ENDING 两行 / 填充总数 7、total_open 10 / TOPIC_IN 四要素",
        "anti_saturation": (
            "旧 ab-003 用的是**零卖点**输入，因此 `total_filled_from_input` 在旧题集里永远等于 4（只记 topic），"
            "「满 3 卖点 = 7」这条 references 里写死的口径从未被断言过；"
            "thesis_how 的三行逐字格式与金句收尾的两行结构也从未被断言。本题全部补上。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型极可能把三个抓手分配到三个 thesis 要素里（S3 失分，"
            "这正是 references gotcha 点名的错误），或在 thesis_how 里加自己的小标题（S1 失分）。"
            "C1 的 ==7 需要精确到「topic 记 4 次」这一反直觉细节，是本包最细的机判点之一。"),
        "old_task_avoided": [
            "不复现 ab-003 的零卖点边界（points_used 三 null、抓手全部占位）",
            "不复现 ab-003 的 total_open 求和断言（本题 total_open=10 是满 3 卖点形态）",
            "不复现 ab-004 的 video 要素结构",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/references/frozen-tokens.md wx 表与 thesis_how 行格式、金句结构、filled=7 口径",
            "dist/hot-templates-skill/SKILL.md:103 wx 三个卖点槽位同居 thesis_how",
            "dist/hot-templates-skill/scripts/gen.py:186-197 how_lines 与 golden_ending",
        ],
    },
    {
        "task_id": "t04", "dim": "能力", "nonce": N["t04"],
        "title": "video 零卖点全缺失：要素 name 冻结 + meta 7 键 + shot_4 占位 4 次/去重 3 token + 总 open 18",
        "nonce_values": {"topic": "高铁商务座的值不值", "卖点": 0,
                          "总占位": 18, "shot_4 占位次数": 4, "shot_4 去重 token 数": 3,
                          "要素名样例": "分镜1（00:00-00:03）"},
        "entry": CMD,
        "input": _md_case([], "高铁商务座的值不值",
                          note="points 为空列表（零卖点边界）"),
        "instruction": (
            "使用 hot-templates 技能，生成短视频分镜表爆款内容骨架，产物写入 <outdir>"
            "（骨架.md + structure.json）。材料自含——platform=video，topic=高铁商务座的值不值，"
            "**没有给任何卖点**（points 为空列表）。模板冻结：6 镜 45 秒分镜表（时间轴/画面/口播/字幕）。"
            "卖点槽位全部空缺，请如实保留开放槽位，不要自行编卖点填充。"),
        "goal_state": "6 要素 name/meta 全部冻结；三个卖点镜（shot_3/4/5）的卖点槽位全部落占位；total_open == 18。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S2", "structure": "F1–F3",
                       "mechanical": "C1–C3", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全非空、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "shot_3/4/5 的口播与字幕列均落 【占位:价值点1/2/3】（缺失槽位 token 字面冻结）",
             "method": "structure.json 三个镜的 text 逐字比对", "expect": "三镜各含对应价值点 token；points_used == [null,null,null]"},
            {"id": "S2", "group": "语义", "assert": "shot_4 文本的 placeholder_count 恰为 4（画面 1 + 口播 2 + 字幕 1），去重后 open token 恰为 3 个",
             "method": "正则重计数 + by_element 读取", "expect": "placeholder_count == 4；去重 token 数 == 3"},
            {"id": "F1", "group": "结构版式", "assert": "6 个要素 id 为 shot_1..shot_6，name 逐字冻结为「分镜N（起-止）」（如 分镜1（00:00-00:03）、分镜6（00:40-00:45））",
             "method": "structure.json elements[].name 逐项比对", "expect": "六个 name 全部逐字命中"},
            {"id": "F2", "group": "结构版式", "assert": "每镜 meta 恰 7 键：shot_no / time_range / duration_sec / visual / voiceover / subtitle / beat",
             "method": "meta 键集比对", "expect": "六镜键集全为这 7 项"},
            {"id": "F3", "group": "结构版式", "assert": "时间轴冻结为 00:00-00:03 / 00:03-00:10 / 00:10-00:20 / 00:20-00:30 / 00:30-00:40 / 00:40-00:45（3/7/10/10/10/5 秒）；骨架.md 含表头四列与「共 45 秒」",
             "method": "meta.time_range / duration_sec 序列比对 + md 文本", "expect": "六段全对；md 含 `| 序号 | 时间轴 | 画面 | 口播 | 字幕 |` 与「共 45 秒」"},
            {"id": "C1", "group": "机械自洽", "assert": "placeholder_stats.total_open == 18（零卖点形态的总占位口径）",
             "method": "structure.json 读取 + 正文正则重计数", "expect": "18"},
            {"id": "C2", "group": "机械自洽", "assert": "by_element 求和 == total_open；各镜逐个重计数一致",
             "method": "脚本求和 + 逐镜正则", "expect": "求和 == 18；6/6 一致"},
            {"id": "C3", "group": "机械自洽", "assert": "骨架.md「占位符统计」节的数字与 structure.json.placeholder_stats 同源",
             "method": "两处数字比对", "expect": "均为 18"},
            {"id": "B1", "group": "边界纪律", "assert": "未为三个卖点镜自行编造卖点内容（占位 token 内文保持冻结字面）",
             "method": "token 内文逐字比对", "expect": "无填充"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "s=json.load(open('<outdir>/structure.json',encoding='utf-8'))\n"
            "print('NAMES', [e['name'] for e in s['elements']])\n"
            "print('META_KEYS', sorted(s['elements'][0]['meta']))\n"
            "print('TIMES', [e['meta']['time_range'] for e in s['elements']])\n"
            "print('DURS', [e['meta']['duration_sec'] for e in s['elements']])\n"
            "e4=s['elements'][3]\n"
            "toks=re.findall(r'【占位:([^】]*)】', e4['text'])\n"
            "print('SHOT4_COUNT', len(toks), 'UNIQ', len(dict.fromkeys(toks)), 'TOKENS', toks)\n"
            "print('TOTAL_OPEN', s['placeholder_stats']['total_open'], 'POINTS_USED', s['points_used'])\n"
            "PY"
        ),
        "check_expect": "NAMES 六个冻结名 / META_KEYS 七键 / TIMES 六段冻结 / DURS [3,7,10,10,10,5] / SHOT4_COUNT 4 UNIQ 3 / TOTAL_OPEN 18 / POINTS_USED [None,None,None]",
        "anti_saturation": (
            "旧 ab-004 用的是 **1 条卖点**，只断言了「shot_4/shot_5 含价值点2/3 占位」与时间轴；"
            "三个结构性考点从未被断言：① 要素 `name` 冻结为「分镜N（起-止）」；② 每镜 `meta` 恰 7 键；"
            "③ references 里写死的零卖点口径 shot_4 占位 4 次 / 去重 3 token / 总 open 18。"
            "本题把断言从「有占位」收紧到「精确计数 + 精确键集 + 精确名字」。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。「零卖点的 18」「shot_4 恰好 4 次占位、去重后 3 个 token」"
            "这两条只有读过 references/frozen-tokens.md 才可能答对；裸模型会按「6 镜 × 平均 2 个占位」估算，"
            "几乎必然错。meta 7 键与 name 冻结也超出 SKILL.md 概述的信息量。"),
        "old_task_avoided": [
            "不复现 ab-004 的 1 卖点场景与 shot_3 填充断言",
            "不复现 ab-004 的分镜总表存在性断言（本题断言总数与表头字面）",
            "不复现 ab-005 的确定性与非法 platform",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/references/frozen-tokens.md video 表（name 冻结、meta 7 键、shot_4 示例、总 open 表）",
            "dist/hot-templates-skill/scripts/gen.py:219-251 sub() 与 build_video",
        ],
    },
    {
        "task_id": "t05", "dim": "边界", "nonce": N["t05"],
        "title": "边界：一次一平台——四平台各跑一次，四份产物互不串台",
        "nonce_values": {"topic": "论文文献管理的最小工具", "平台数": 4,
                          "卖点3": ["先用 Zotero 收集再分类", "标签体系控制在两层以内", "每周固定半小时重读摘要"]},
        "entry": CMD + "（四个平台各跑一次，各自独立 outdir）",
        "input": {"files": [{"path": "points.json", "encoding": "utf-8", "data":
                             ["先用 Zotero 收集再分类", "标签体系控制在两层以内", "每周固定半小时重读摘要"]}],
                  "args": {"platform": ["dy", "xhs", "wx", "video"], "topic": "论文文献管理的最小工具",
                           "points_arg": "points.json", "outdirs": ["out/dy", "out/xhs", "out/wx", "out/video"]}},
        "instruction": (
            "我想要四个平台的爆款骨架：抖音口播、小红书图文、公众号文章、短视频分镜表，"
            "主题都是「论文文献管理的最小工具」，卖点用 data/points.json 里这三条。"
            "使用 hot-templates 技能，产物分别写入 out/dy、out/xhs、out/wx、out/video 四个目录。"),
        "goal_state": "四个目录各恰含 骨架.md + structure.json；每个 structure.json 的 platform / platform_name / 要素数与所在目录一致，无跨平台串台。",
        "assert_map": {"endpoint": "A1–A3", "semantic": "S1–S2", "structure": "F1–F2",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "四次调用退出码均为 0",
             "method": "echo $? ×4", "expect": "0,0,0,0"},
            {"id": "A2", "group": "端态", "assert": "四个目录各恰含 2 件产物",
             "method": "find 计数 ×4", "expect": "四个目录各计数 2"},
            {"id": "A3", "group": "端态", "assert": "未产出「一次生成四平台」的合并产物或第 5 个目录",
             "method": "find <workdir> -name 骨架.md 计数 + 目录列举", "expect": "骨架.md 恰 4 个；out 下恰 4 个子目录"},
            {"id": "S1", "group": "语义", "assert": "每份 structure.json 的 platform 字段与所在目录一致（dy/xhs/wx/video）",
             "method": "json 读 + 与路径比对", "expect": "4/4 一一对应"},
            {"id": "S2", "group": "语义", "assert": "platform_name 与 structure_name 逐平台正确（抖音口播稿 / 小红书图文 / 公众号文章 / 短视频分镜表 及各自 structure_name）",
             "method": "json 读比对", "expect": "4/4 正确，无串台"},
            {"id": "F1", "group": "结构版式", "assert": "要素个数逐平台为 6 / 7 / 5 / 6，且 id 序列各自冻结",
             "method": "structure.json element_count + ids 比对", "expect": "dy=6、xhs=7、wx=5、video=6"},
            {"id": "F2", "group": "结构版式", "assert": "骨架.md 首行分别为 `# 抖音口播稿 · 爆款骨架`、`# 小红书图文 · 爆款骨架`、`# 公众号文章 · 爆款骨架`、`# 短视频分镜表 · 爆款骨架`",
             "method": "各 md 首行比对", "expect": "4/4 逐字命中"},
            {"id": "C1", "group": "机械自洽", "assert": "每份 elements 内不得出现其它平台的要素 id（如 dy 产物里不得有 shot_1、wx 产物里不得有 hook_3s）",
             "method": "脚本：id 前缀跨平台污染检测", "expect": "4/4 无污染"},
            {"id": "C2", "group": "机械自洽", "assert": "四份产物均无 {{ 或 }} 模板残留；四份的 topic 都逐字等于「论文文献管理的最小工具」",
             "method": "正则扫描 + json topic 比对", "expect": "残留 0；topic 4/4 一致"},
            {"id": "B1", "group": "边界纪律", "assert": "遵守「一次一跑」：未把四个平台合成一次调用（引擎无此能力），也未擅自扩写任一平台的成文",
             "method": "复核执行轨迹为 4 次调用 + 裁判通读", "expect": "4 次独立调用，无扩写"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,glob,os\n"
            "exp={'dy':6,'xhs':7,'wx':5,'video':6}\n"
            "for p in ('dy','xhs','wx','video'):\n"
            "    s=json.load(open(f'out/{p}/structure.json',encoding='utf-8'))\n"
            "    print(p, s['platform'], s['platform_name'], s['element_count'], exp[p], s['element_count']==exp[p])\n"
            "print('MD_COUNT', len(glob.glob('out/*/骨架.md')))\n"
            "PY"
        ),
        "check_expect": "四行 platform 与所在目录一致、element_count 分别 6/7/5/6 全 True / MD_COUNT 4",
        "anti_saturation": (
            "旧 ab-005 出现过「用户要多平台」的暗示，但它的断言只覆盖 dy 单平台一次生成 + 两次失败路径，"
            "从未真正跑过一次「四平台各一跑」。本题把 SKILL 的「一次一跑」边界做成可判的产物级断言，"
            "并新增**跨平台串台检测**（C1）——这是旧题集完全没有的类型。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型极可能自行发明「一次生成四平台」的产物形态"
            "（如在同一个 structure.json 里放四组 elements），C1 的串台检测会直接判负；"
            "此外容易把 platform 字段写错或沿用上一次的输出目录。"),
        "old_task_avoided": [
            "不复现 ab-005 的确定性双跑（留给 t08）与非法 platform / 空 topic 失败路径（留给 t07）",
            "不复现 ab-001/002/003/004 任何单平台的要素结构断言",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/SKILL.md:65 用户要多个平台时一次一跑",
            "dist/hot-templates-skill/SKILL.md:32 不适用：多平台一次生成",
            "dist/hot-templates-skill/scripts/gen.py BUILDERS 单平台映射",
        ],
    },
    {
        "task_id": "t06", "dim": "陷阱", "nonce": N["t06"],
        "title": "陷阱：空白串卖点按缺失处理，且槽位保序（不得把第 3 条挤进第 2 槽）",
        "nonce_values": {"topic": "家庭备餐的十分钟流程",
                          "卖点": ["第一件事先把台面清空", "（空白串）", "第三件事当天做完不留隔夜"],
                          "points_input_count": 3, "缺失槽位": 2},
        "entry": CMD,
        "input": _md_case(P["t06"], "家庭备餐的十分钟流程"),
        "instruction": (
            "使用 hot-templates 技能，生成抖音口播爆款内容骨架，产物写入 <outdir>"
            "（骨架.md + structure.json）。材料自含——platform=dy，topic=家庭备餐的十分钟流程，"
            "points 见 data/points.json（3 条，其中第 2 条只有空白字符）。"
            "请如实处理这条空白卖点，不要跳过它把后面的卖点往前挪，也不要替它编内容。"),
        "goal_state": "第 2 槽落 【占位:价值点2】且 points_used[1] 为 null；第 3 条卖点仍入第 3 槽（保序）；points_input_count == 3。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S3", "structure": "F1",
                       "mechanical": "C1–C2", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "两件产物齐全非空、退出码 0", "method": "find 计数 + echo $?", "expect": "计数=2，码 0"},
            {"id": "S1", "group": "语义", "assert": "value_2 文本恰含 【占位:价值点2】（空白串按缺失处理，不是空字符串、也不是被跳过）",
             "method": "structure.json value_2.text 包含断言", "expect": "含「【占位:价值点2】」"},
            {"id": "S2", "group": "语义", "assert": "保序：value_1 = 第 1 条卖点、value_3 = 第 3 条卖点（第三条不得被挤进第 2 槽）",
             "method": "value_1/value_3 文本逐字比对", "expect": "value_1 含「第一件事先把台面清空」；value_3 含「第三件事当天做完不留隔夜」"},
            {"id": "S3", "group": "语义", "assert": "points_used 恰为 [第1条, null, 第3条]（缺失位为 JSON null 而非空串或被删除）",
             "method": "structure.json points_used 逐位比对", "expect": "长度 3，中间为 null"},
            {"id": "F1", "group": "结构版式", "assert": "value_2 的 filled_from_input 为 []（未填充槽位不记 point#2）",
             "method": "structure.json 逐要素比对", "expect": "[]；value_1/3 为 [\"point#1\"]/[\"point#3\"]"},
            {"id": "C1", "group": "机械自洽", "assert": "points_input_count == 3（输入条数，与规整后的 3 槽是两个概念，不得写成 2）",
             "method": "structure.json 读取", "expect": "3"},
            {"id": "C2", "group": "机械自洽", "assert": "total_open == 7（6 个冻结 token + 第 2 槽多出的 价值点2），by_element 中 value_2 == 2",
             "method": "json 读取 + 正文正则重计数", "expect": "7；value_2 为 2，其余五要素为 1"},
            {"id": "B1", "group": "边界纪律", "assert": "未替空白卖点编造内容；未把空白卖点静默丢弃导致槽位前移",
             "method": "value_2 文本逐字比对", "expect": "占位 token 保持冻结字面，无编造、无前移"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,re\n"
            "s=json.load(open('<outdir>/structure.json',encoding='utf-8'))\n"
            "els={e['id']:e for e in s['elements']}\n"
            "print('INPUT_COUNT', s['points_input_count'])\n"
            "print('USED', s['points_used'])\n"
            "print('V1', els['value_1']['text'][:28])\n"
            "print('V2', els['value_2']['text'])\n"
            "print('V3', els['value_3']['text'][:30])\n"
            "print('FILL', {k: els[k]['filled_from_input'] for k in ('value_1','value_2','value_3')})\n"
            "print('TOTAL_OPEN', s['placeholder_stats']['total_open'], 'BY_EL', s['placeholder_stats']['by_element'])\n"
            "PY"
        ),
        "check_expect": "INPUT_COUNT 3 / USED [第1条, None, 第3条] / V2 含【占位:价值点2】/ FILL value_2=[] / TOTAL_OPEN 7、by_element.value_2=2",
        "anti_saturation": (
            "SKILL gotchas 明写「空白串卖点按缺失处理」，但旧 ab-001（满 3 条）、ab-002（5 条）、"
            "ab-004（1 条）三种输入里**没有一条包含空白串**——这条 gotcha 在旧题集里是死条文。"
            "本题把它变成实题，并叠加「保序」这一相邻陷阱（不得 compact 掉空槽）。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型最可能的两种错：① 过滤掉空白串后让第 3 条滑进第 2 槽"
            "（S2/S3 双否，这正是「不得 compact」的反饱和陷阱）；② 把 points_input_count 写成规整后的条数"
            "（C1 失分）。两处失败互相独立。"),
        "old_task_avoided": [
            "不复现 ab-001 的满 3 卖点全填充场景（本题第 2 槽缺失）",
            "不复现 ab-002 的超出截断（第 4 条入 points_unused）",
            "不复现 ab-004 的 1 卖点 / 零卖点位数口径",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/SKILL.md:100 空白串卖点按缺失处理、points_used 对应位为 null",
            "dist/hot-templates-skill/SKILL.md:43-46 卖点规整策略（超 3 取前 3、槽位固定 3 个）",
            "dist/hot-templates-skill/scripts/gen.py:367-374 point_slot / points_used 构建",
        ],
    },
    {
        "task_id": "t07", "dim": "陷阱", "nonce": N["t07"],
        "title": "陷阱：--points 形态矩阵（对象形态 / BOM 文件 / 非字符串项 / 不存在路径 四类入口）",
        "nonce_values": {"topic": "异地恋关系的沟通节奏", "形态": ["纯字符串列表文件", "含 points 键的对象文件", "带 BOM 的 utf-8-sig 文件", "非字符串项数组（exit 2）", "不存在的文件路径（exit 2）"]},
        "entry": CMD,
        "input": {"files": [
            {"path": "points_list.json", "encoding": "utf-8", "data": P["t07"], "role": "合法形态①：纯字符串列表文件"},
            {"path": "points_obj.json", "encoding": "utf-8", "data": {"points": P["t07"]}, "role": "合法形态②：含 points 键的对象文件"},
            {"path": "points_bom.json", "encoding": "utf-8-sig（首字节 BOM）", "data": P["t07"], "role": "合法形态③：带 BOM 的文件"},
            {"path": "points_bad.json", "encoding": "utf-8", "data": [123, 456], "role": "非法形态：含非字符串项 → exit 2"},
        ]},
        "instruction": (
            "使用 hot-templates 技能，针对主题「异地恋关系的沟通节奏」测试卖点输入的不同写法。"
            "先分别用 data/points_list.json、data/points_obj.json、data/points_bom.json 三份文件生成骨架，"
            "每次写到各自独立的 outdir；再用 data/points_bad.json（数组里是数字）跑一次；"
            "最后用 data/不存在的文件.json 再跑一次。请如实记录每次的退出码、产物与报错。"),
        "goal_state": "三种合法形态产物一致（platform/topic/三槽内容相同）；非字符串项与不存在路径均 exit 2 且不建输出目录。",
        "assert_map": {"endpoint": "A1–A4", "semantic": "S1–S2", "structure": "F1",
                       "mechanical": "C1–C2", "discipline": "B1–B2"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "三种合法形态各跑一次成功，退出码均 0，各恰含 2 件产物",
             "method": "echo $? ×3 + find 计数 ×3", "expect": "码 0,0,0；三目录各计数 2"},
            {"id": "A2", "group": "端态", "assert": "非字符串项输入（[123,456]）退出码为 2 且输出目录未被创建",
             "method": "echo $? + ls 目录", "expect": "码 2；目录不存在或为空"},
            {"id": "A3", "group": "端态", "assert": "不存在的文件路径退出码为 2 且输出目录未被创建",
             "method": "echo $? + ls 目录", "expect": "码 2；目录不存在"},
            {"id": "A4", "group": "端态", "assert": "两次失败运行均无任何残留产物文件",
             "method": "find 计数", "expect": "两次各 0 个产物"},
            {"id": "S1", "group": "语义", "assert": "含 points 键的对象形态被正确识别（等价于纯字符串列表），产物不因外层对象而报「缺 points 键」",
             "method": "obj 目录 structure.json 的 points_used 比对", "expect": "与 list 目录逐字相同"},
            {"id": "S2", "group": "语义", "assert": "带 BOM 的 utf-8-sig 文件被容忍，首字符未被 BOM 污染（卖点文本不含 U+FEFF）",
             "method": "structure.json 卖点文本扫 U+FEFF", "expect": "命中数 = 0"},
            {"id": "F1", "group": "结构版式", "assert": "三次合法运行的 element_count 与要素 id 序列完全一致（6 个 dy 要素冻结）",
             "method": "structure.json 序列比对", "expect": "三份一致"},
            {"id": "C1", "group": "机械自洽", "assert": "三次合法运行的 骨架.md 与 structure.json 逐字节一致（输入等价 → 产物等价）",
             "method": "sha256sum 三组文件", "expect": "三份 md 与三份 json 的哈希各相同"},
            {"id": "C2", "group": "机械自洽", "assert": "不存在路径这一路的报错文案应说明「不是合法 JSON」（该路径被当作内联 JSON 解析），而非「文件不存在」",
             "method": "捕获 stderr 文本", "expect": "stderr 含「不是合法 JSON」；不得声称文件不存在（若两种文案并存，须以实际行为为准并如实转述）"},
            {"id": "B1", "group": "边界纪律", "assert": "对不存在的路径，未「善意为用户」改用最近似的文件继续生成",
             "method": "执行轨迹核查 + find", "expect": "未产出该次运行的产物"},
            {"id": "B2", "group": "边界纪律", "assert": "对非字符串项输入，未自行 str() 化后继续生成（技能包要求 exit 2）",
             "method": "执行轨迹核查", "expect": "该次运行无产物"},
        ],
        "check_cmd": (
            "cd <workdir> && python - <<'PY'\n"
            "import json,hashlib\n"
            "def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]\n"
            "for d in ('out_list','out_obj','out_bom'):\n"
            "    s=json.load(open(f'{d}/structure.json',encoding='utf-8'))\n"
            "    print(d, s['platform'], s['element_count'], s['points_used'], h(f'{d}/structure.json'), h(f'{d}/骨架.md'))\n"
            "PY"
        ),
        "check_expect": "三行的 platform/element_count/points_used 完全一致，structure.json 与 骨架.md 的哈希三份各自相同",
        "anti_saturation": (
            "旧 ab-005 只测了 `--platform bilibili`（argparse）与**空 topic**两种失败入口，"
            "从未触碰 `--points` 的形态矩阵。SKILL 输入格式表里写明的三种合法形态"
            "（文件路径 / 含 points 键的对象 / 内联 JSON 串）与 utf-8-sig 容忍、以及 gotchas 里点名的"
            "「不存在路径 → 被当内联 JSON 解析 → 报不是合法 JSON」这条，在旧题集里全是死条文。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型极可能：① 把对象形态的 {\"points\":[...]} 当成非法"
            "（S1 失分——因为它会照直觉要求顶层是数组）；② 遇到不存在路径就自动找最近的 points.json（B1 失分）；"
            "③ 把 [123,456] 强转成字符串继续跑（B2 失分）。三条纪律型失败互相独立。"),
        "old_task_avoided": [
            "不复现 ab-005 的非法 platform（argparse 英文报错）与空 topic 两类失败路径",
            "不复现 ab-005 的同输入双跑确定性（本题是「等价输入 → 等价产物」的跨形态一致性，留给 t08 的同输入双跑）",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/SKILL.md:40 --points 两种形态与 utf-8-sig 容忍",
            "dist/hot-templates-skill/SKILL.md:101 不存在文件路径 → 当内联 JSON 解析报「不是合法 JSON」",
            "dist/hot-templates-skill/scripts/gen.py:56 utf-8-sig 读取与 points 校验分支",
        ],
    },
    {
        "task_id": "t08", "dim": "陷阱", "nonce": N["t08"],
        "title": "陷阱：冻结 token 防改写 + {{ }} 残留为 0 + 三向统计同源 + 同输入双跑逐字节一致",
        "nonce_values": {"topic": "阳台种薄荷的越冬方案",
                          "卖点2": ["霜降前把花盆搬进南向阳台", "控水到土干后再浇透"],
                          "双跑目录": ["outA", "outB"]},
        "entry": CMD + "（同输入连跑两次到两个目录）",
        "input": {"files": [{"path": "points.json", "encoding": "utf-8",
                             "data": ["霜降前把花盆搬进南向阳台", "控水到土干后再浇透"]}],
                  "args": {"platform": "xhs", "topic": "阳台种薄荷的越冬方案",
                           "points_arg": "points.json", "outdirs": ["outA", "outB"]}},
        "instruction": (
            "使用 hot-templates 技能，platform=xhs，主题「阳台种薄荷的越冬方案」，卖点见 data/points.json（2 条）。"
            "请用**完全相同的输入连续生成两次**，分别输出到 outA 与 outB。"
            "交付前请把两份产物读回来核对，不要只看退出码，也不要改写模板里冻结的占位 token。"),
        "goal_state": "两份产物逐字节一致；无 {{ }} 残留；每要素 placeholder_count 与正则重计数一致；md 与 json 统计同源。",
        "assert_map": {"endpoint": "A1–A2", "semantic": "S1–S2", "structure": "F1",
                       "mechanical": "C1–C4", "discipline": "B1"},
        "checks": [
            {"id": "A1", "group": "端态", "assert": "outA 与 outB 各恰含 骨架.md + structure.json，两次退出码均 0",
             "method": "find 计数 ×2 + echo $?", "expect": "各计数 2；码 0,0"},
            {"id": "S1", "group": "语义", "assert": "占位 token 内文逐字保持冻结字面，未被改写或补全（如 `2-3步操作拆解，越具体越好`、`一句真实经历/翻车现场`、`2个垂直领域标签，如：#时间管理 #精力管理`）",
             "method": "structure.json 各要素 text 与 references/frozen-tokens.md 的 token 表逐项比对",
             "expect": "三处 token 逐字命中"},
            {"id": "S2", "group": "语义", "assert": "两个产物的 structure.json 逐字节一致（sha256 相同）",
             "method": "sha256sum", "expect": "两值相同"},
            {"id": "F1", "group": "结构版式", "assert": "7 个要素 id 顺序冻结；2 卖点 → 第 3 槽落 【占位:价值点3】，前两槽为真实卖点",
             "method": "structure.json 逐要素比对", "expect": "point_block_3 含【占位:价值点3】；points_used 长度 3、第 3 位 null"},
            {"id": "C1", "group": "机械自洽", "assert": "两个产物的 骨架.md 逐字节一致（sha256 相同）",
             "method": "sha256sum", "expect": "两值相同"},
            {"id": "C2", "group": "机械自洽", "assert": "每个 element 的 placeholder_count == 其 text 的正则 `【占位:([^】]*)】` 重计数；by_element 求和 == total_open",
             "method": "脚本逐要素重计数 + 求和", "expect": "7/7 一致且求和相等"},
            {"id": "C3", "group": "机械自洽", "assert": "两份产物中 {{ 与 }} 的出现次数均为 0",
             "method": "grep -c '{{' 与 'grep -c '}}' 四个文件", "expect": "四个计数均为 0"},
            {"id": "C4", "group": "机械自洽", "assert": "骨架.md「占位符统计」节的数字与 structure.json.placeholder_stats 同源一致",
             "method": "两处数字比对", "expect": "相同"},
            {"id": "B1", "group": "边界纪律", "assert": "未手工复制 outA 产物冒充第二次真实运行；未以「第二次不一样是正常的」为由放过不确定性",
             "method": "复核执行轨迹（两次 --outdir 不同的调用）+ 裁判通读", "expect": "两次独立调用，如实处理差异"},
        ],
        "check_cmd": (
            "cd <workdir> && sha256sum outA/structure.json outB/structure.json outA/骨架.md outB/骨架.md && python - <<'PY'\n"
            "import json,re\n"
            "s=json.load(open('outA/structure.json',encoding='utf-8'))\n"
            "ok=all(e['placeholder_count']==len(re.findall(r'【占位:([^】]*)】', e['text'])) for e in s['elements'])\n"
            "print('PLACEHOLDER_SELF_OK', ok)\n"
            "st=s['placeholder_stats']\n"
            "print('SUM_OK', sum(st['by_element'].values())==st['total_open'], 'TOTAL', st['total_open'])\n"
            "full=open('outA/骨架.md',encoding='utf-8').read()+open('outA/structure.json',encoding='utf-8').read()\n"
            "print('MUSTACHE_RESIDUE', full.count('{{')+full.count('}}'))\n"
            "PY"
        ),
        "check_expect": "四个 sha256 两两相同 / PLACEHOLDER_SELF_OK True / SUM_OK True / MUSTACHE_RESIDUE 0",
        "anti_saturation": (
            "旧 ab-005 的确定性题只断言「两份 md 与 json 逐字节一致」和「失败路径 exit 2」，"
            "没有把**冻结 token 防改写**与**{{ }} 残留**、**placeholder_count 自洽**、"
            "**md 与 json 统计同源**这四条放到同一题里做联合断言。本题把四条合成一题，"
            "任一条失败都会同时打掉语义与机械两个维度（权重合计 62）。"),
        "design_note": (
            "设计目标：强裸模型通过率 ≤60%。裸模型在「让产物好看」的驱动下极易"
            "① 把占位 token 改写成更通顺的话（S1 失分）；② 复制一份而不是重跑（B1 失分）；"
            "③ 手工写 md 统计节导致与 json 不同源（C4 失分）。三条均为高频失败模式。"),
        "old_task_avoided": [
            "不复现 ab-005 的非法 platform / 空 topic 失败路径（留给 t07 的 --points 形态矩阵）",
            "不复现 ab-002 的 emoji 映射与截断、ab-003 的 wx 零卖点、ab-004 的 video 时间轴",
            "旧 ab-005 的确定性断言虽同型，但本题把它与三条新的自洽/残留/冻结断言联合，且换全新 nonce 输入",
        ],
        "design_basis_extra": [
            "dist/hot-templates-skill/SKILL.md:85 {{ }} 类未填充模板变量必须为 0",
            "dist/hot-templates-skill/SKILL.md:105 占位符统计正则口径与 structure.json 同源",
            "dist/hot-templates-skill/SKILL.md:79 同输入重跑逐字节一致",
        ],
    },
]

TASKS[1]["weights"] = {"endpoint": 12, "semantic": 32, "structure": 24, "mechanical": 18, "discipline": 14}
TASKS[2]["weights"] = {"endpoint": 12, "semantic": 30, "structure": 18, "mechanical": 26, "discipline": 14}
TASKS[3]["weights"] = {"endpoint": 12, "semantic": 24, "structure": 28, "mechanical": 22, "discipline": 14}
TASKS[4]["weights"] = {"endpoint": 16, "semantic": 24, "structure": 16, "mechanical": 22, "discipline": 22}
TASKS[6]["weights"] = {"endpoint": 18, "semantic": 24, "structure": 10, "mechanical": 20, "discipline": 28}
TASKS[7]["weights"] = {"endpoint": 14, "semantic": 26, "structure": 10, "mechanical": 36, "discipline": 14}