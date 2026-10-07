"""生成会议纪要 docx 和 summary.json。

事实来源唯一为 fixtures/transcript.txt，所有条目内容逐字取自转写稿。
"""

import json
from pathlib import Path

from docx import Document
from docx.shared import Pt


BASE = Path(__file__).resolve().parent
TRANSCRIPT = BASE / "fixtures" / "transcript.txt"
OUT_DIR = BASE / "out"
DOCX_PATH = OUT_DIR / "纪要.docx"
JSON_PATH = OUT_DIR / "summary.json"


def load_transcript() -> str:
    return TRANSCRIPT.read_text(encoding="utf-8")


def must_be_in_transcript(verbatim: str, transcript: str, label: str) -> None:
    if verbatim not in transcript:
        raise AssertionError(f"{label} 非转写稿逐字：{verbatim!r}")


def build_docx(transcript: str) -> dict:
    decisions = [
        {
            "owner": "赵静怡",
            "text": "星帆订单系统整体进度正常，会议同意按原计划推进，里程碑保持不变",
        },
        {
            "owner": "黄雨桐",
            "text": "会议同意星帆订单系统项目预算300万元，走专项列支，由市场部跟进执行",
        },
    ]

    todos = [
        {
            "item": "完成复盘纪要并同步给财务部",
            "owner": "黄雨桐",
            "due": "本周五前",
        },
        {
            "item": "把数据迁移脚本整理成7月4日归档",
            "owner": "徐静怡",
            "due": "7月4日",
        },
    ]

    risks = [
        {
            "owner": "吴志远",
            "text": "财务部侧存在履约风险，去年高峰期出现过积压，今年需要提前准备预案",
        },
        {
            "owner": "赵静怡",
            "text": "灰度放量方案的数据口径尚未对齐，复盘前需要补齐基线数据",
        },
    ]

    # 校验：决议与风险的内容、待办的「事项」「负责人」均逐字可溯源
    speakers_seen = {"主持人", "赵静怡", "黄雨桐", "徐静怡", "吴志远"}

    for d in decisions:
        if d["owner"] not in speakers_seen:
            raise AssertionError(f"决议/建议 未公开说话人：{d['owner']}")
        must_be_in_transcript(d["text"], transcript, "决议事项")

    for t in todos:
        if t["owner"] not in speakers_seen:
            raise AssertionError(f"待办负责人非转写稿说话人：{t['owner']}")
        must_be_in_transcript(t["item"], transcript, "待办事项 事项")

    for r in risks:
        if r["owner"] not in speakers_seen:
            raise AssertionError(f"风险与关注 未公开说话人：{r['owner']}")
        must_be_in_transcript(r["text"], transcript, "风险与关注")

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = 1  # 居中
    run = title.add_run("星帆订单系统项目例会纪要")
    run.bold = True
    run.font.size = Pt(16)

    # 一、决议事项
    doc.add_heading("一、决议事项", level=1)
    for i, d in enumerate(decisions, 1):
        line = f"{i}. 【决议事项 · {d['owner']}】{d['text']}"
        doc.add_paragraph(line)

    # 二、待办事项（表格）
    doc.add_heading("二、待办事项", level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "事项"
    hdr[1].text = "负责人"
    hdr[2].text = "期限"
    for t in todos:
        row = table.add_row().cells
        row[0].text = t["item"]
        row[1].text = t["owner"]
        row[2].text = t["due"]

    # 三、风险与关注
    doc.add_heading("三、风险与关注", level=1)
    for i, r in enumerate(risks, 1):
        line = f"{i}. 【风险与关注 · {r['owner']}】{r['text']}"
        doc.add_paragraph(line)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_PATH)

    return {
        "决议事项": len(decisions),
        "待办事项": len(todos),
        "风险与关注": len(risks),
    }


def main() -> None:
    transcript = load_transcript()
    counts = build_docx(transcript)
    total = counts["决议事项"] + counts["待办事项"] + counts["风险与关注"]
    payload = {
        "决议事项": counts["决议事项"],
        "待办事项": counts["待办事项"],
        "风险与关注": counts["风险与关注"],
        "合计": total,
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    print("生成完成：", DOCX_PATH, JSON_PATH)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()