#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/ws4_gen.py — WS4 dev 题池「实例 + oracle」生成器库（SF-0005 卡 A）。

设计依据：
- PLAN §3.5-1 nonce 化实例：每题关键实体（人名/编号/日期/金额/部门名）由
  seed+nonce_set 派生一次性注入；oracle 参照产物由**独立参照实现**按同一 nonce
  程序化生成（本模块即该参照实现，不调用任何资产代码）。
- PLAN §3.8 D2：同种子逐字节复现（BQ-10）+ 生成器红绿自检（BQ-8）+ 陈旧 oracle
  必红（BQ-9：nonce-A 的 oracle 判 nonce-B 实例必须红）。
- 生成树内零墙钟戳：全部产物确定性；docx 经 canonical zip 归一（固定
  date_time/顺序/压缩），否则 python-docx 的 zip 头时间戳会破坏逐字节复现。

各包入口 = packs/ws4-dev/<pkg>/gen_oracle.py 薄包装，调 main(task_id, argv)。
用法（透传）：
    python gen_oracle.py --seed 42 --nonce-set A --out <dir>   # 生成树
    python gen_oracle.py --selftest                            # BQ-8/9/10 三合一自检
生成树布局：
    <out>/fixtures/<输入件>     实例输入（与包内 fixtures/ 同构）
    <out>/oracle/<产物件>       oracle 参照产物（与一次产物运行的 out/ 同构）
    <out>/manifest.json         {task, seed, nonce_set, sha256:{rel:...}}（无时间戳）
"""

import argparse
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
EVALKIT = os.path.dirname(HARNESS_DIR)
WS4_ROOT = os.path.join(EVALKIT, "packs", "ws4-dev")

# ---------------------------------------------------------------- nonce 池 --
# 全部虚构。与损坏注入用的「编造词池」(FABRIC_POOL) 刻意不相交，保证 BQ-9/红路
# 判定不受词汇碰撞干扰。
SURNAMES = "王李张刘陈杨黄赵周吴徐孙"
GIVEN = ["志远", "晓雯", "建国", "丽娜", "俊杰", "雨桐", "海涛", "静怡", "文博", "嘉欣"]
DEPTS = ["市场部", "研发中心", "运营部", "财务部", "供应链组", "客户成功部", "综合办", "质量组"]
PROJECTS = ["青澜会员中台", "星帆订单系统", "云岭数据看板", "海川履约平台", "瑞和结算引擎", "望舒客服工作台"]
COMPANIES = ["青澜科技", "星帆互联", "云岭数科", "海川网络", "瑞和信息", "望舒智能"]
DATES = ["6月30日", "7月4日", "本周五", "下周一", "7月中旬", "月底前", "下周三"]
AMOUNTS = ["28万元", "45万元", "120万元", "8.6万元", "300万元", "16万元"]
THINGS = ["压测报告", "外包坐席名单", "灰度放量方案", "供应商对账单", "应急预案演练脚本",
          "验收清单", "数据迁移脚本", "复盘纪要"]
TOPICS = ["时间管理", "宿舍收纳", "通勤读书", "家常快手菜", "晨间习惯", "旧物改造", "阳台种菜", "记账习惯"]
HOOK_TAILS = ["第2个最容易被忽略", "最后一个几乎没人坚持", "从明天早上就能用起来", "亲测三周见效"]
CTA_WORDS = ["关注", "评论", "私信", "点击"]
EMOJIS = ["✅", "🔥", "💡", "📌", "🌱"]
HASHTAG_POOL = ["自律打卡", "效率提升", "干货分享", "生活整理", "碎片时间", "习惯养成", "亲测有效"]
FABRIC_POOL = ["量子茶歇机", "反重力白板", "次元投影仪", "玄学打卡器"]  # 仅损坏注入用

# 《广告法》第九条及市场监管公开解读中的绝对化用语词样（公开法条派生，非资产内容）
BANNED_WORDS = ["国家级", "世界级", "最高级", "最佳", "第一", "顶级", "独家", "万能",
                "百分百", "绝对", "永久有效", "全网第一"]

MM_SECTIONS = ("一、决议事项", "二、待办事项", "三、风险与关注")
MM_SECTION_KEYS = ("决议事项", "待办事项", "风险与关注")
TODO_HEADER = ("事项", "负责人", "期限")

HOT_ELEMENTS = {
    "dy": ["钩子", "痛点", "价值点1", "价值点2", "价值点3", "行动号召"],
    "xhs": ["标题", "开头", "要点1", "要点2", "要点3", "标签"],
    "wx": ["引入", "论点1", "论点2", "论点3", "总结"],
}
HOT_PLATFORM_NAME = {"dy": "短视频口播稿", "xhs": "图文笔记", "wx": "公众号文章"}
HOT_STRUCT_NAME = {"dy": "3秒钩子 + 痛点 + 价值点×3 + 行动号召",
                   "xhs": "数字标题 + 开头 + 要点×3 + 标签",
                   "wx": "引入 + 论点×3 + 总结"}

OFC_FIELDS = {
    "周报": ["部门", "填报人", "周期", "本周工作内容", "下周工作计划", "问题与需协调事项", "报送日期"],
    "请示函": ["主送单位", "事由", "申请事项", "资金额度", "资金来源", "联系人", "联系电话", "落款单位", "落款日期"],
    "会议通知": ["会议名称", "会议时间", "会议地点", "参会人员", "议题", "落款单位", "落款日期"],
}
OFC_SIGN = {"周报": ("填报人", "报送日期"), "请示函": ("落款单位", "落款日期"), "会议通知": ("落款单位", "落款日期")}
OFC_SALUTATION = {"周报": False, "请示函": True, "会议通知": True}


def rnd_for(task_id, seed, nonce_set):
    return random.Random("%s|%s|%s" % (task_id, seed, nonce_set))


def pick_unique(rnd, pool, n):
    return rnd.sample(pool, n) if len(pool) >= n else [pool[i % len(pool)] for i in range(n)]


# ------------------------------------------------------- 确定性 docx 落盘 --
def canonical_docx_bytes(doc):
    """python-docx 内存文档 → 确定性字节串：先存内存，再按 (固定时间戳/排序/压缩) 重打包。"""
    buf = io.BytesIO()
    doc.save(buf)
    src = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(src.namelist()):
            data = src.read(name)
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 0
            zi.external_attr = 0
            zf.writestr(zi, data)
    src.close()
    return out.getvalue()


def write_file(root, rel, data):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    kw = {} if isinstance(data, bytes) else {"encoding": "utf-8", "newline": "\n"}
    with open(path, mode, **kw) as f:
        f.write(data)
    return path


def sha256_tree(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


# =============================================================== mm 线 ====
def gen_mm_instance(task_id, seed, nonce_set):
    rnd = rnd_for(task_id, seed, nonce_set)
    people = pick_unique(rnd, [s + g for s in SURNAMES for g in GIVEN], 5)
    project = rnd.choice(PROJECTS)
    company = rnd.choice(COMPANIES)
    dept_a, dept_b = pick_unique(rnd, DEPTS, 2)
    amount = rnd.choice(AMOUNTS)
    d1, d2, d3 = pick_unique(rnd, DATES, 3)
    thing_a, thing_b, thing_c = pick_unique(rnd, THINGS, 3)

    # 决议/风险：模板不含第三人称名，由说话人自己陈述；owner=该行说话人
    decisions = [
        "%s整体进度正常，会议同意按原计划推进，里程碑保持不变" % project,
        "会议同意%s项目预算%s，走专项列支，由%s跟进执行" % (project, amount, dept_a),
    ]
    decision_owners = [people[0], people[1]]
    risks = [
        "%s侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案" % dept_b,
        "%s的数据口径尚未对齐，复盘前需要补齐基线数据" % thing_a,
    ]
    risk_owners = [people[2], people[0]]
    todos = [
        {"content": "%s在%s前完成%s并同步给%s" % (people[1], d1, thing_b, dept_b),
         "owner": people[1], "deadline": d1},
        {"content": "%s负责把%s整理成%s归档" % (people[3], thing_c, d2),
         "owner": people[3], "deadline": d2},
    ]
    if task_id == "mm-02":  # 近邻负例：无时间戳 + 同名说话人 + 一条待办无期限
        decisions.append("%s的验收标准按新版执行，旧版同时作废" % project)
        decision_owners.append(people[4])
        todos.append({"content": "%s牵头梳理%s的责任分工" % (people[2], project),
                      "owner": people[2], "deadline": "未明确"})

    speakers = list(people)
    lines = []
    hh, mm = 9, rnd.randint(0, 20)
    def stamp():
        nonlocal hh, mm
        mm += rnd.randint(1, 6)
        if mm >= 60:
            mm -= 60
            hh += 1
        return "[%02d:%02d]" % (hh, mm)

    if task_id == "mm-01":
        lines.append("%s 主持人: 今天主要过一下%s的进展，人到齐就开始。" % (stamp(), project))
        for text, owner in zip(decisions, decision_owners):
            lines.append("%s %s: %s。" % (stamp(), owner, text))
        lines.append("%s 主持人: 好，这几项就议定下来。" % stamp())
        for t in todos:
            lines.append("%s %s: %s。" % (stamp(), t["owner"], t["content"]))
        for text, owner in zip(risks, risk_owners):
            lines.append("%s %s: %s。" % (stamp(), owner, text))
    else:
        same = people[0]  # 同名说话人脏点：多个角色共用同一姓名，无任何区分标记
        lines.append("%s: 现在开会，先过%s的事项。" % (same, project))
        for i, (text, owner) in enumerate(zip(decisions, decision_owners)):
            spk = same if i == 0 else owner  # 首条决议由同名者陈述（归属待核的来源）
            lines.append("%s: %s。" % (spk, text))
        for t in todos:
            lines.append("%s: %s。" % (t["owner"], t["content"]))
        for text, owner in zip(risks, risk_owners):
            lines.append("%s: %s。" % (owner, text))
        lines.append("%s: 我这边补充一点，%s的资料我随后发群里。" % (same, thing_a))

    transcript = "\n".join(lines) + "\n"
    spec = {
        "project": project, "company": company, "people": people,
        "decisions": decisions, "decision_owners": decision_owners,
        "risks": risks, "risk_owners": risk_owners, "todos": todos,
        "speakers": sorted(set(speakers + (["主持人"] if task_id == "mm-01" else []))),
        "same_name": people[0] if task_id == "mm-02" else None,
    }
    return {"transcript.txt": transcript.encode("utf-8")}, spec


def gen_mm_oracle(spec, task_id):
    doc = Document()
    doc.add_paragraph("%s项目例会会议纪要" % spec["project"])
    for sec, key in zip(MM_SECTIONS, MM_SECTION_KEYS):
        doc.add_paragraph(sec)
        if key == "待办事项":
            table = doc.add_table(rows=1 + len(spec["todos"]), cols=3)
            for j, h in enumerate(TODO_HEADER):
                table.rows[0].cells[j].text = h
            for i, t in enumerate(spec["todos"]):
                table.rows[i + 1].cells[0].text = t["content"]
                table.rows[i + 1].cells[1].text = t["owner"]
                table.rows[i + 1].cells[2].text = t["deadline"]
        else:
            items = spec["decisions"] if key == "决议事项" else spec["risks"]
            owners = spec["decision_owners"] if key == "决议事项" else spec["risk_owners"]
            for n, (it, owner) in enumerate(zip(items, owners), 1):
                suffix = "（归属待核）" if (task_id == "mm-02" and owner == spec.get("same_name")) else ""
                doc.add_paragraph("%d. 【%s · %s】%s%s" % (n, key, owner, it, suffix))
    counts = {"决议事项": len(spec["decisions"]), "待办事项": len(spec["todos"]),
              "风险与关注": len(spec["risks"])}
    counts["合计"] = sum(counts.values())
    docx_bytes = canonical_docx_bytes(doc)
    summary = (json.dumps(counts, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {"纪要.docx": docx_bytes, "summary.json": summary}


# ============================================================== hot 线 ====
def gen_hot_instance(task_id, seed, nonce_set):
    rnd = rnd_for(task_id, seed, nonce_set)
    platform = {"hot-01": "dy", "hot-02": "xhs", "hot-03": "wx"}[task_id]
    topic = rnd.choice(TOPICS)
    project = rnd.choice(PROJECTS)
    n_points = 2 if task_id == "hot-03" else 3
    point_tpl = [
        "用四象限法给%s相关任务排优先级" % project,
        "按25分钟专注加5分钟休息的节奏执行" if platform != "wx" else "把25分钟专注法写进每日安排",
        "每周日晚固定30分钟复盘本周得失",
        "把%s的关键节点贴在看得见的地方" % project,
    ]
    points = point_tpl[:n_points]
    rnd.shuffle(points)
    inp = {"platform": platform, "topic": topic, "points": points}
    return {"input.json": (json.dumps(inp, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}, inp


def _hot_element_contents(platform, inp, rnd):
    topic, points = inp["topic"], inp["points"]
    slots = 3
    filled = points[:slots]
    placeholders = slots - len(filled)
    if platform == "dy":
        hook = "3个把%s坚持下来的笨办法，%s" % (topic, rnd.choice(HOOK_TAILS))
        pain = "很多人%s总是三天打鱼两天晒网，不是不努力，是没有抓手" % topic
        cta = "觉得有用就%s一下，下期继续拆第2个方法" % rnd.choice(CTA_WORDS)
        elems = [("钩子", hook), ("痛点", pain)]
        for i, p in enumerate(filled, 1):
            elems.append(("价值点%d" % i, "方法%d：%s" % (i, p)))
        elems.append(("行动号召", cta))
    elif platform == "xhs":
        emoji = rnd.choice(EMOJIS)
        title = "%d个让%s变简单的习惯%s" % (len(filled), topic, emoji)
        tags = " ".join("#" + t for t in rnd.sample(HASHTAG_POOL, 4))
        elems = [("标题", title), ("开头", "这篇笔记整理了我在%s上亲测有效的%d个习惯" % (topic, len(filled)))]
        for i, p in enumerate(filled, 1):
            elems.append(("要点%d" % i, "要点%d：%s" % (i, p)))
        elems.append(("标签", tags))
    else:
        elems = [("引入", "关于%s，与其讲道理，不如给可执行的步骤" % topic)]
        for i in range(slots):
            if i < len(filled):
                elems.append(("论点%d" % (i + 1), "论点%d：%s" % (i + 1, filled[i])))
            else:
                elems.append(("论点%d" % (i + 1), "【占位:价值点%d】待补充第%d条内容" % (i + 1, i + 1)))
        elems.append(("总结", "把以上%d条串起来，%s就能形成闭环" % (len(filled), topic)))
    return elems, slots, placeholders


def gen_hot_oracle(inp, rnd_seed_tuple):
    platform, task_id, seed, nonce_set = rnd_seed_tuple
    rnd = rnd_for(task_id + "|oracle", seed, nonce_set)
    elems, slots, placeholders = _hot_element_contents(platform, inp, rnd)
    structure = {
        "template_version": "1.0",
        "platform": platform,
        "platform_name": HOT_PLATFORM_NAME[platform],
        "structure_name": HOT_STRUCT_NAME[platform],
        "topic": inp["topic"],
        "points_input_count": len(inp["points"]),
        "points_used": inp["points"][:slots],
        "points_unused": inp["points"][slots:],
        "element_count": len(elems),
        "elements": [{"name": n, "content": c} for n, c in elems],
        "placeholder_stats": {"slots": slots, "filled": len(inp["points"][:slots]),
                              "placeholders": placeholders},
    }
    md_lines = ["# %s-%s" % (platform, inp["topic"]), ""]
    for n, c in elems:
        md_lines.append("【%s】%s" % (n, c))
        md_lines.append("")
    return {
        "structure.json": (json.dumps(structure, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "骨架.md": ("\n".join(md_lines).rstrip() + "\n").encode("utf-8"),
    }


# ============================================================== ofc 线 ====
def gen_ofc_instance(task_id, seed, nonce_set):
    rnd = rnd_for(task_id, seed, nonce_set)
    template = {"ofc-01": "周报", "ofc-02": "请示函", "ofc-03": "会议通知"}[task_id]
    dept = rnd.choice(DEPTS)
    person = rnd.choice(SURNAMES) + rnd.choice(GIVEN)
    project = rnd.choice(PROJECTS)
    company = rnd.choice(COMPANIES)
    date1 = "2026年%d月%d日" % (rnd.randint(7, 10), rnd.randint(1, 28))
    values = {}
    if template == "周报":
        values = {
            "部门": dept, "填报人": person, "周期": "2026年10月第2周",
            "本周工作内容": "%s一期联调完成，压测通过率99.2%%，遗留问题3个已登记" % project,
            "下周工作计划": "启动%s灰度放量，并完成数据口径核对" % project,
            "问题与需协调事项": "需要%s协调测试环境两台" % rnd.choice(DEPTS),
            "报送日期": date1,
        }
    elif template == "请示函":
        values = {
            "主送单位": "公司领导班子",
            "事由": "关于%s建设经费的请示" % project,
            "申请事项": "采购《%s运维服务》（含二期扩容）" % project,
            "资金额度": rnd.choice(AMOUNTS),
            "联系人": person,
            "落款单位": "%s%s" % (company, dept),
            "落款日期": date1,
        }
    else:
        values = {
            "会议名称": "%s二期方案评审会" % project,
            "会议时间": "２０２６年１０月１５日 9:30",
            "会议地点": "%s三号会议室" % company,
            "议题": "审议《%s二期方案》等３项议题" % project,
            "落款单位": "%s%s" % (company, dept),
            "落款日期": date1,
        }
    fields = [{"name": n, "required": True, "kind": "text",
               "value": values.get(n)} for n in OFC_FIELDS[template]]
    if template == "周报":
        title = "%s工作周报" % dept
    elif template == "请示函":
        title = values["事由"]
    else:
        title = values["会议名称"]
    inp = {"template": template, "title": title, "fields": fields}
    return {"input.json": (json.dumps(inp, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}, inp


def gen_ofc_oracle(inp):
    template = inp["template"]
    salut = OFC_SALUTATION[template]
    sign_fields = OFC_SIGN[template]
    doc = Document()
    tp = doc.add_paragraph(inp["title"])
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if salut:
        salut_text = "%s：" % inp["fields"][0]["value"] if template == "请示函" else "各部门："
        if inp["fields"][0]["value"] is None:
            salut_text = "____："
        doc.add_paragraph(salut_text)
    body_fields = [f for f in inp["fields"]
                   if f["name"] not in sign_fields and not (salut and f["name"] == "主送单位")]
    for f in body_fields:
        val = f["value"] if f["value"] is not None else "____"
        p = doc.add_paragraph("%s：%s" % (f["name"], val))
        p.paragraph_format.first_line_indent = Pt(24)
    for f in inp["fields"]:
        if f["name"] in sign_fields:
            p = doc.add_paragraph(f["value"] if f["value"] is not None else "____")
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    filled = [f["name"] for f in inp["fields"] if f["value"] is not None]
    missing = [f["name"] for f in inp["fields"] if f["value"] is None]
    fields_json = {
        "template": template, "title": inp["title"],
        "filled_fields": filled, "missing_fields": missing,
        "fields": [{"name": f["name"], "required": f["required"], "kind": f["kind"],
                    "status": "filled" if f["value"] is not None else "missing",
                    "value": f["value"]} for f in inp["fields"]],
    }
    return {"文书.docx": canonical_docx_bytes(doc),
            "fields.json": (json.dumps(fields_json, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}


# ============================================================ 总装与自检 ====
def generate(task_id, seed, nonce_set, out_root):
    task_cfg = load_task_cfg(task_id)
    line = task_cfg["line"]
    if line == "mm":
        fixtures, spec = gen_mm_instance(task_id, seed, nonce_set)
        oracle = gen_mm_oracle(spec, task_id)
    elif line == "hot":
        fixtures, inp = gen_hot_instance(task_id, seed, nonce_set)
        oracle = gen_hot_oracle(inp, (task_cfg["platform"], task_id, seed, nonce_set))
    else:
        fixtures, inp = gen_ofc_instance(task_id, seed, nonce_set)
        oracle = gen_ofc_oracle(inp)
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)
    for rel, data in fixtures.items():
        write_file(out_root, os.path.join("fixtures", rel), data)
    for rel, data in oracle.items():
        write_file(out_root, os.path.join("oracle", rel), data)
    manifest = {"task": task_id, "seed": seed, "nonce_set": nonce_set,
                "sha256": dict(sha256_tree(out_root))}
    write_file(out_root, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def load_task_cfg(task_id):
    path = os.path.join(WS4_ROOT, task_id, "task.json")
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def run_checker(pack_dir, product_root, input_basis=None):
    cmd = [sys.executable, os.path.join(pack_dir, "checks", "run_check.py"), product_root]
    if input_basis:
        cmd += ["--input-basis", input_basis]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=pack_dir,
                       env=dict(os.environ, MSYS_NO_PATHCONV="1", PYTHONIOENCODING="utf-8"))
    return p.returncode, p.stdout + p.stderr


# ----------------------------------------------------------- 损坏注入库 --
def corrupt(task_id, name, src_root, dst_root):
    """确定性损坏：copy src→dst 后按 name 破坏一处。返回损坏说明。"""
    line = load_task_cfg(task_id)["line"]
    shutil.copytree(src_root, dst_root)
    if line == "mm":
        doc = Document(os.path.join(dst_root, "纪要.docx"))
        if name == "fabricated_entry":
            doc.add_paragraph("9. 【决议事项 · %s】关于%s的专项方案立即启动" %
                              ("主持人", FABRIC_POOL[hash(name) % len(FABRIC_POOL)]))
        elif name == "drop_section_heading":
            for p in doc.paragraphs:
                if p.text == MM_SECTIONS[2]:
                    p.text = "三、风险提示"
        elif name == "summary_count_wrong":
            sp = os.path.join(dst_root, "summary.json")
            d = json.load(io.open(sp, encoding="utf-8"))
            d["合计"] -= 1
            write_file(dst_root, "summary.json", json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        elif name == "todo_header_broken":
            doc.tables[0].rows[0].cells[2].text = "时间"
        else:
            raise ValueError(name)
        if name != "summary_count_wrong":
            write_file(dst_root, "纪要.docx", canonical_docx_bytes(doc))
        return name
    if line == "hot":
        md_p = os.path.join(dst_root, "骨架.md")
        sj_p = os.path.join(dst_root, "structure.json")
        if name == "banned_word":
            write_file(dst_root, "骨架.md", io.open(md_p, encoding="utf-8").read() + "\n全网最佳方案就在这里\n")
        elif name == "points_accounting":
            d = json.load(io.open(sj_p, encoding="utf-8"))
            d["points_used"] = d["points_used"][:-1]
            write_file(dst_root, "structure.json", json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        elif name == "artifact_missing":
            os.remove(sj_p)
        elif name == "template_residue":
            write_file(dst_root, "骨架.md", io.open(md_p, encoding="utf-8").read() + "\n{{价值点}}\n")
        elif name == "placeholder_missing":
            md = io.open(md_p, encoding="utf-8").read().replace("【占位:价值点3】", "这里是第三条")
            write_file(dst_root, "骨架.md", md)
        else:
            raise ValueError(name)
        return name
    # ofc
    doc = Document(os.path.join(dst_root, "文书.docx"))
    fj = os.path.join(dst_root, "fields.json")
    if name == "invented_missing_value":
        for p in doc.paragraphs:
            if "____" in p.text:
                p.text = p.text.replace("____", "13800000000")
        write_file(dst_root, "文书.docx", canonical_docx_bytes(doc))
    elif name == "title_left_aligned":
        doc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        write_file(dst_root, "文书.docx", canonical_docx_bytes(doc))
    elif name == "fields_list_inconsistent":
        d = json.load(io.open(fj, encoding="utf-8"))
        d["filled_fields"] = d["filled_fields"][:-1]
        write_file(dst_root, "fields.json", json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    elif name == "value_altered":
        d = json.load(io.open(fj, encoding="utf-8"))
        cands = [f for f in d["fields"] if f["status"] == "filled" and f["value"] and
                 ("《" in f["value"] or "２" in f["value"])]
        if not cands:
            cands = [f for f in d["fields"] if f["status"] == "filled" and f["value"]]
        tgt = cands[0]
        old = tgt["value"]
        new = old.replace("（", "(").replace("《", "<").replace("２", "2")
        if new == old:  # 兜底变形必须保证值真的变了，否则损坏不成立
            new = old[:-1] if len(old) > 2 else old + "改"
        tgt["value"] = new
        # 损坏 = 产物内部自洽地一起偏离输入基准（fields.json 与 docx 同改），由 verbatim 门抓红
        write_file(dst_root, "fields.json", json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        newdoc = Document(os.path.join(dst_root, "文书.docx"))
        for p in newdoc.paragraphs:
            if old in p.text:
                p.text = p.text.replace(old, new)
        write_file(dst_root, "文书.docx", canonical_docx_bytes(newdoc))
    else:
        raise ValueError(name)
    return name


CORRUPTIONS = {
    "mm": ["fabricated_entry", "drop_section_heading", "summary_count_wrong", "todo_header_broken"],
    "hot": ["banned_word", "points_accounting", "artifact_missing", "template_residue",
            "placeholder_missing"],
    "ofc": ["invented_missing_value", "title_left_aligned", "fields_list_inconsistent",
            "value_altered"],
}


def selftest(task_id):
    """BQ-8 红绿两态 + BQ-9 nonce 交叉红 + BQ-10 同种子逐字节 + fixtures 漂移守卫。"""
    cfg = load_task_cfg(task_id)
    pack = os.path.join(WS4_ROOT, task_id)
    seed = cfg["canonical_seed"]
    lines = []
    ok = True

    tA = tempfile.mkdtemp(prefix="ws4-%s-A-" % task_id)
    generate(task_id, seed, "A", tA)
    rc, out = run_checker(pack, os.path.join(tA, "oracle"))
    green = rc == 0
    ok &= green
    lines.append("GREEN  oracle(判自家 fixtures) exit=%d %s" % (rc, "PASS" if green else "FAIL"))

    # fixtures 漂移守卫：包内 fixtures 必须与 canonical 种子生成树逐字节一致
    gen_fix = os.path.join(tA, "fixtures")
    pack_fix = os.path.join(pack, "fixtures")
    drift = {k: v for k, v in sha256_tree(gen_fix).items()
             if sha256_tree(pack_fix).get(k) != v} if os.path.isdir(pack_fix) else None
    same_fix = drift == {} if drift is not None else False
    ok &= same_fix
    lines.append("FIXT   包内fixtures==canonical生成 %s" % ("PASS" if same_fix else "FAIL: %s" % drift))

    # BQ-8 红态：逐个损坏注入必须 exit 1
    has_missing_field = False
    if cfg["line"] == "ofc":
        try:
            _inp = json.load(io.open(os.path.join(pack, "fixtures", "input.json"), encoding="utf-8"))
            has_missing_field = any(f.get("value") is None for f in _inp["fields"])
        except Exception:  # noqa: BLE001
            has_missing_field = False
    for cname in CORRUPTIONS[cfg["line"]]:
        if cname == "placeholder_missing" and cfg["line"] == "hot" and cfg.get("platform") != "wx":
            continue
        if cname == "invented_missing_value" and cfg["line"] == "ofc" and not has_missing_field:
            continue  # 无缺失必填的题（如周报正例）不适用该损坏
        td = tempfile.mkdtemp(prefix="ws4-%s-c-" % task_id)
        dst = os.path.join(td, "oracle")
        corrupt(task_id, cname, os.path.join(tA, "oracle"), dst)
        rc, _ = run_checker(pack, dst)
        red = rc == 1
        ok &= red
        lines.append("RED    corrupt=%-26s exit=%d %s" % (cname, rc, "PASS" if red else "FAIL"))

    # BQ-9：nonce-A oracle 判 nonce-B 实例必须红
    tB = tempfile.mkdtemp(prefix="ws4-%s-B-" % task_id)
    generate(task_id, seed, "B", tB)
    rc, _ = run_checker(pack, os.path.join(tA, "oracle"), input_basis=os.path.join(tB, "fixtures"))
    cross = rc == 1
    ok &= cross
    lines.append("CROSS  oracle(A)判fixtures(B)       exit=%d %s" % (rc, "PASS" if cross else "FAIL"))

    # BQ-10：同种子两次生成逐字节一致
    tA2 = tempfile.mkdtemp(prefix="ws4-%s-A2-" % task_id)
    generate(task_id, seed, "A", tA2)
    h1, h2 = sha256_tree(tA), sha256_tree(tA2)
    ident = h1 == h2
    ok &= ident
    diff = {k for k in set(h1) | set(h2) if h1.get(k) != h2.get(k)}
    lines.append("DET    同种子双跑逐字节             %s%s" % ("PASS" if ident else "FAIL: %s" % diff, ""))

    print("== %s selftest（BQ-8/9/10）==" % task_id)
    for ln in lines:
        print(ln)
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(task_id, argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--nonce-set", default="A", choices=["A", "B"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_task_cfg(task_id)
    seed = args.seed if args.seed is not None else cfg["canonical_seed"]
    if args.selftest:
        return selftest(task_id)
    if not args.out:
        print("用法: gen_oracle.py [--seed N] [--nonce-set A|B] --out <dir> | --selftest", file=sys.stderr)
        return 2
    m = generate(task_id, seed, args.nonce_set, args.out)
    print("generated %s seed=%d nonce=%s -> %s (%d files)" %
          (task_id, seed, args.nonce_set, args.out, len(m["sha256"])))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tid = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(tid, sys.argv[1:]))
