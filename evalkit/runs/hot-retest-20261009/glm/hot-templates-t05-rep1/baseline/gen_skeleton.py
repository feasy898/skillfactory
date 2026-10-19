#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性内容骨架生成器（baseline 自备引擎，未挂载任何 skill 包）。

用法:
    python3 gen_skeleton.py --platform xhs --topic 阳台种菜入门 \
        --points '<JSON串或文件路径>' --outdir out/A-inline

卖点 --points 两种合法形态:
  1) 内联 JSON 串        : '["卖点1","卖点2","卖点3"]'
  2) 文件路径            : points.json（utf-8-sig 读取，容忍 BOM）
  JSON 顶层可为纯字符串列表，或含 "points" 键的包装对象 {"points":[...]}。

引擎性质: 无时间戳、无随机数、无网络、零第三方依赖;
同一语义输入（platform/topic/points 归一化后相同）产出逐字节一致,
产物不含任何输入形态、路径等环境信息。
"""
import argparse
import json
import os
import re
import sys

EXIT_USAGE = 2


def die(msg):
    sys.stderr.write("[gen_skeleton.py] 错误：%s\n" % msg)
    sys.exit(EXIT_USAGE)


def load_points(spec):
    """归一化四种合法输入形态为同一个字符串列表。"""
    if os.path.isfile(spec):
        # 文件形态: utf-8-sig 读取, 带 BOM 与无 BOM 文件得到同一字符串
        with open(spec, "r", encoding="utf-8-sig") as f:
            raw = f.read()
    else:
        # 内联 JSON 串形态
        raw = spec
    try:
        data = json.loads(raw)
    except ValueError as e:
        die("--points 不是合法 JSON（按内联串解析失败，若为文件请确认路径）: %s" % e)
    if isinstance(data, dict):
        if "points" not in data:
            die('--points 为对象形态但缺少 "points" 键')
        data = data["points"]
    if not isinstance(data, list):
        die("--points 顶层必须是字符串列表或含 points 键的对象")
    points = []
    for i, item in enumerate(data):
        if not isinstance(item, str):
            die("--points 第 %d 项不是字符串" % (i + 1))
        s = item.strip()
        if not s:
            die("--points 第 %d 项为空白串" % (i + 1))
        points.append(s)
    return points


# ---------------------------------------------------------------- xhs 模板

def build_data(topic, points):
    """平台=xhs 的小红书图文骨架数据; 输出的唯一决定因素是 (topic, points)。"""
    tag_first = re.sub(r"^#|\s+", "", topic)[:4]
    return {
        "schema": "hot-content-skeleton/v1",
        "platform": "xhs",
        "platform_notes": "小红书图文：标题决定点击、封面决定转化、正文分块短段落配 emoji 导航、标签组决定搜索流量",
        "topic": topic,
        "genre": "新手入门攻略型（可收藏、可照做）",
        "target_audience": "零基础阳台党：出租屋/小阳台，想低成本吃上自己种的菜",
        "core_promise": "不买贵设备、不翻车：3 个零成本门道（排水、补钙、配光），30 天吃上第一茬",
        "emotion_curve": [
            "共鸣（菜蔫了）", "安心（有解）", "行动（3 门道）",
            "成就（第一茬）", "收藏/转发（照做清单）",
        ],
        "points_input_count": len(points),
        "points_used": points,
        "title_candidates": [
            {
                "text": "阳台种菜入门：3个零翻车门道，直接抄🌱",
                "angle": "人群+数字",
                "recommended": True,
            },
            {
                "text": "泡沫箱种菜总烂根？这3招菜蹭蹭长🥬",
                "angle": "痛点+方案",
                "recommended": False,
            },
            {
                "text": "0基础阳台种菜：照这3步做，30天摘头茬菜",
                "angle": "具体利益+时间锚点",
                "recommended": False,
            },
        ],
        "title_rules": [
            "控制在 20 字以内，关键词（阳台种菜/新手/烂根）前置到前 10 字",
            "「3 个门道/3 步」数字锚点必须保留，干货感来源",
            "标题至多 1 个 emoji，避免被判营销号",
            "不用绝对化用语（必活/保证丰收/第一），降低平台风险",
        ],
        "cover": {
            "main": "阳台种菜 3 个零翻车门道",
            "sub": "新手直接抄作业",
            "image": "泡沫箱打孔实拍图（配图位②同款）",
        },
        "sections": [
            {
                "id": "hook",
                "type": "opening_hook",
                "role": "共鸣场景+自嘲+转折承诺",
                "word_budget": [60, 100],
                "beats": [
                    "开场画面：新买的菜苗两周就蔫的黄叶特写（配图位①）→「明明按教程浇水施肥，怎么还是蔫？」",
                    "共鸣铺垫：浇水越勤死得越快（其实是烂根）/蛋壳整颗丢盆里发臭招小飞虫/北阳台硬种番茄只长叶不结果",
                    "转折承诺：入门先抓 3 个门道——容器排水、底肥补钙、位置配光；零成本、今天就能动手",
                ],
                "image_slot": "配图位① 菜苗黄叶实拍",
            },
            {
                "id": "p1",
                "type": "point",
                "point": points[0],
                "order": 1,
                "subtitle_template": "泡沫箱种菜的第一死因不是旱，是涝",
                "pain_point": "箱底没孔，浇下去的水积在底部，根长期泡水缺氧就烂根；叶子蔫了看着像缺水，越浇越糟",
                "actions": [
                    "装土前先打孔：烧热的螺丝刀/电烙铁在箱底烫 6–10 个孔，孔径约 0.5–1cm，四角+中心分布",
                    "铺 2–3cm 排水层：陶粒、碎泡沫或松针都行，之后再覆土，水多了有去处",
                    "箱底架空：垫两根木条或砖块，浇完水多余的水能流走，根不闷",
                ],
                "data_or_tip": "浇水口诀参考「表土发白变干再浇、一次浇到箱底微渗」（按自家阳台通风情况调整）",
                "golden_sentence": "菜多数不是旱死的，是浇死的——先解决水往哪走，再谈种什么。",
                "image_slot": "配图位② 打孔+排水层步骤三宫格",
            },
            {
                "id": "p2",
                "type": "point",
                "point": points[1],
                "order": 2,
                "subtitle_template": "整壳埋土等于白扔，碾碎才是肥",
                "pain_point": "生菜心叶发黑、番茄屁股烂（脐腐病），多半是缺钙；可整颗蛋壳直接埋土里，一年半载不分解，还招小飞虫",
                "actions": [
                    "蛋壳洗净内膜、彻底晒干或低温烘干，干透才碾得碎",
                    "擀面杖/研磨碗压碎到米粒大小再拌土——是「碾碎」不是「掰碎」，越碎越快变成本可吸收的钙",
                    "用量与时机：换盆配土时拌入，约一升土配一勺碎壳；撒土表面基本等于白撒",
                ],
                "data_or_tip": "碎壳边缘还能挡蜗牛和鼻涕虫，补钙防虫一举两得",
                "golden_sentence": "蛋壳补钙的关键不在壳，在「碎」——越碎，越快变成菜吃得动的钙。",
                "image_slot": "配图位③ 蛋壳处理三步图（洗→晒→碾）",
            },
            {
                "id": "p3",
                "type": "point",
                "point": points[2],
                "order": 3,
                "subtitle_template": "把菜种在对的位置，比天天伺候更管用",
                "pain_point": "阳台只有半天光却硬种番茄辣椒，光不够只徒长不结果；娇气的全日照菜占了最晒位，耐阴的反而没地方放",
                "actions": [
                    "北侧/每天约 3–4 小时散射光的位置，种生菜、油麦菜、菠菜、小葱等耐阴速生菜",
                    "最晒的南面留给番茄、辣椒、黄瓜等结果类——它们才吃得下强光",
                    "生菜约 30–40 天首收，掐叶吃不断茬，是新手最快「吃到自己种的菜」的成就感闭环",
                ],
                "data_or_tip": "品种按当地气候选（〔待补:本地适应品种〕）；夏季北位凉爽，反而适合生菜越夏",
                "golden_sentence": "光照是种菜的硬通货——耐阴的守北面，爱吃光的占南面，各就各位。",
                "image_slot": "配图位④ 阳台南北分区示意图",
            },
            {
                "id": "ending",
                "type": "cta_interaction",
                "role": "收束+收藏钩子+评论互动+下期预告",
                "word_budget": [60, 100],
                "beats": [
                    "一句话收束 3 门道：容器能排水、底肥有钙、位置配光——零成本，周末就能照着配一遍",
                    "收藏钩子：先收藏，凑齐「泡沫箱+蛋壳+分区」三件事再动手",
                    "评论区互动（置顶同款）：你家阳台朝哪边、最想种什么菜？报朝向，帮你对号入座",
                    "下期预告：阳台菜病虫害自查（小白虫/黑斑怎么治）——关注不迷路",
                ],
                "image_slot": "（可选）首茬收获实拍对比图",
            },
        ],
        "tag_group": {
            "count": 7,
            "first_tag_from_topic": "#" + tag_first,
            "tags": [
                "#" + tag_first, "#种菜入门", "#新手种菜",
                "#泡沫箱种菜", "#阳台花园", "#都市农夫", "#生菜",
            ],
        },
        "emoji_map": {
            "标题": "🌱（至多 1 个）",
            "做法导航": "✅",
            "原理提示": "💡",
            "避坑警示": "⚠️",
            "标签组": "🏷️",
        },
        "word_budget": {
            "total": [600, 900],
            "per_point": [120, 180],
            "paragraph_max_lines": 3,
        },
        "formatting": {
            "正文分块": "每门道一个 emoji 小标题导航，段落均不超过 3 行",
            "金句": "单独成段，方便截图传播",
            "小标题徽章": "三个门道统一「门道 N｜」样式，强化攻略结构感",
            "标签位置": "文末标签组一行放齐，首标签由主题派生",
        },
        "compliance_notes": [
            "不用「必活/保证丰收」等绝对化表述；浇水与天数数字标「约/参考」",
            "品种推荐不带购买链接，保持攻略中立",
            "配图用自家实拍，避免搬运被判重",
        ],
    }


def render_md(d):
    L = []
    L.append("# 小红书图文爆款内容骨架｜%s" % d["topic"])
    L.append("")
    L.append("> platform：`%s`（小红书图文）｜topic：`%s`｜体裁：%s" % (
        d["platform"], d["topic"], d["genre"]))
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 0. 定位速览")
    L.append("")
    L.append("| 项 | 内容 |")
    L.append("|---|---|")
    L.append("| 目标读者 | %s |" % d["target_audience"])
    pain_all = "菜苗买回来两周就蔫：浇水越勤死得越快、蛋壳整丢发臭招虫、北阳台种啥啥不活"
    L.append("| 核心痛点 | %s |" % pain_all)
    L.append("| 核心承诺 | %s |" % d["core_promise"])
    L.append("| 情绪曲线 | %s |" % " → ".join(d["emotion_curve"]))
    L.append("| 预估正文字数 | %d–%d 字，段落均不超过 %d 行，emoji 小标题分块导航 |" % (
        d["word_budget"]["total"][0], d["word_budget"]["total"][1],
        d["word_budget"]["paragraph_max_lines"]))
    L.append("| 差异化角度 | 不讲大而全的种植百科，只抓「容器/底肥/位置」三个翻车率最高的入门关口 |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 1. 标题（三选一，支持 A/B）")
    L.append("")
    for i, t in enumerate(d["title_candidates"], 1):
        mark = "，主推" if t["recommended"] else ""
        L.append("%d. **%s**（%s%s）" % (i, t["text"], t["angle"], mark))
    L.append("")
    L.append("**标题写作要点**")
    for r in d["title_rules"]:
        L.append("- %s" % r)
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 2. 封面（首图文案）")
    L.append("")
    L.append("- **大字**：%s" % d["cover"]["main"])
    L.append("- **小字**：%s" % d["cover"]["sub"])
    L.append("- **配图**：%s" % d["cover"]["image"])
    L.append("")
    L.append("---")
    L.append("")

    sec = {s["id"]: s for s in d["sections"]}
    hook = sec["hook"]
    L.append("## 3. 开头钩子（共鸣场景，%d–%d 字）" % tuple(hook["word_budget"]))
    L.append("")
    for b in hook["beats"]:
        L.append("- %s" % b)
    L.append("- **配图位**：%s" % hook["image_slot"])
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 4. 正文主体：3 个门道（每条 %d–%d 字）" % tuple(d["word_budget"]["per_point"]))
    L.append("")
    for pid in ("p1", "p2", "p3"):
        s = sec[pid]
        L.append("### 门道 %d｜%s ✅" % (s["order"], s["point"]))
        L.append("")
        L.append("- **小标题模板**：%s" % s["subtitle_template"])
        L.append("- **痛点句**：%s" % s["pain_point"])
        L.append("- **核心做法**（逐条展开，每条 2–3 行）：")
        for j, a in enumerate(s["actions"], 1):
            L.append("  %d. %s" % (j, a))
        L.append("- **提示/数据位** 💡：%s" % s["data_or_tip"])
        L.append("- **金句**：%s" % s["golden_sentence"])
        L.append("- **配图位**：%s" % s["image_slot"])
        L.append("")
    L.append("---")
    L.append("")
    ending = sec["ending"]
    L.append("## 5. 收尾 + 互动（%d–%d 字）" % tuple(ending["word_budget"]))
    L.append("")
    for b in ending["beats"]:
        L.append("- %s" % b)
    L.append("- **配图位**：%s" % ending["image_slot"])
    L.append("")
    L.append("---")
    L.append("")
    tg = d["tag_group"]
    L.append("## 6. 标签组（%d 个，首标签由主题派生）" % tg["count"])
    L.append("")
    L.append(" ".join(tg["tags"]))
    L.append("")
    L.append("---")
    L.append("")
    md = "\n".join(L)
    # 槽位统计（对最终 md 全文口径统计，与 structure.json 同源）
    tokens = []
    for m in re.finditer(r"〔待补:([^\]]+)〕", md):
        if m.group(1) not in tokens:
            tokens.append(m.group(1))
    for m in re.finditer(r"配图位[①②③④]", md):
        if m.group(0) not in tokens:
            tokens.append(m.group(0))
    stats = {
        "total": len(tokens),
        "rule": "正则口径：〔待补:X〕 与 配图位①–④，全文去重保序",
        "tokens": tokens,
    }
    d["placeholder_stats"] = stats
    L.append("## 7. 待补槽位统计")
    L.append("")
    L.append("发布前需人工/AI 补写或实拍的开放槽位共 **%d 处**：" % stats["total"])
    L.append("")
    for t in stats["tokens"]:
        L.append("- %s" % t)
    L.append("")
    L.append("> 金句可直接用；占位内容补写时不得改动本文小标题与门道顺序。")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="确定性内容骨架生成器（xhs）")
    ap.add_argument("--platform", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--points", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    if args.platform != "xhs":
        die("platform 仅支持 xhs（本基线引擎只实现小红书图文模板）")
    topic = args.topic.strip()
    if not topic:
        die("topic 不能为空")

    points = load_points(args.points)
    if len(points) < 3:
        die("卖点至少 3 条（本模板为 3 个门道槽位），当前 %d 条" % len(points))

    data = build_data(topic, points[:3])
    md = render_md(data)
    structure_json = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "骨架.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    with open(os.path.join(args.outdir, "structure.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(structure_json)

    print("OK platform=%s topic=%s sections=%d points=%d open_slots=%d -> %s" % (
        data["platform"], data["topic"], len(data["sections"]),
        data["points_input_count"], data["placeholder_stats"]["total"], args.outdir))


if __name__ == "__main__":
    main()
