"""Generate the two 文书 from the fixture inputs.

A: fixtures/qingshi_empty.json -> out/请示函-empty/
B: fixtures/zongjie_blank.json -> out/工作总结-blank/

Both fixtures carry no usable content, so every slot resolves to a
【…】 placeholder. The generation never aborts on missing/blank data.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from docxlib import FS, HT, XBS, build_docx, para, para_lines, title_lines  # noqa: E402
from fields import resolve, write_fields_json  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
TITLE_FONT, TITLE_SIZE = XBS, 44   # 二号, 华文小标宋 -> 宋体加粗 fallback
BODY = 32                            # 三号 16pt


# --------------------------------------------------------------------------- #
# A. 请示函  (request-for-instructions letter)
# --------------------------------------------------------------------------- #
def gen_qingshi(src_path, out_dir):
    data = json.loads(src_path.read_text(encoding="utf-8"))

    specs = [
        ("发文机关", "【发文机关名称】", "标题（发文机关）"),
        ("请示事项", "【请示事项名称】", "标题（事由）"),
        ("主送机关", "【主送机关名称】", "主送机关"),
        ("请示事由", "【请示事由与事项说明】", "正文"),
        ("成文日期", "【成文日期】", "成文日期"),
    ]
    fs = {k: resolve(data, k, ph) for k, ph, _ in specs}
    records = []
    for k, ph, where in specs:
        r = dict(fs[k])
        r["template_slot"] = where
        records.append(r)

    body = "".join([
        para("", spacing_after=200),                       # 标题上留白
        para_lines(title_lines(f"{fs['发文机关']['rendered']}关于"
                               f"{fs['请示事项']['rendered']}的请示", TITLE_SIZE),
                   font=TITLE_FONT, size=TITLE_SIZE, bold=True,
                   align="center", line=600, spacing_after=300),
        para(f"{fs['主送机关']['rendered']}：", align="left",
             spacing_after=200),
        para(f"现将{fs['请示事项']['rendered']}有关情况请示如下：",
             first_indent=640, spacing_after=120),
        para(fs["请示事由"]["rendered"], first_indent=640, spacing_after=120),
        para("妥否，请批示。", first_indent=640, spacing_after=400),
        para(fs["发文机关"]["rendered"], align="right", spacing_after=0),
        para(fs["成文日期"]["rendered"], align="right"),
    ])

    docx_path = out_dir / "文书.docx"
    build_docx(docx_path, body, "请示函")

    return write_fields_json(
        out_dir / "fields.json",
        template_id="qingshi",
        template_name="请示函",
        out_dir=str(out_dir.relative_to(ROOT)),
        source_file=str(src_path.relative_to(ROOT)),
        data=data, fields=records,
        notes=[
            "输入为字面空对象 {}，模板全部槽位均无对应键，status 全为 missing。",
            "按公文文种固有要素保留「妥否，请批示。」结语；该句属文种格式，未虚构任何事实。",
            "未添加红头、发文字号、版记（brief 未要求红头格式）。",
            "正文页边距按 GB/T 9704 公文版式（上 3.7/下 3.5/左 2.8/右 2.6 cm），"
            "字体 小标宋(宋体加粗)标题 / 黑体一级标题 / 仿宋正文 三号，固定行距 28 磅。",
        ])


# --------------------------------------------------------------------------- #
# B. 工作总结
# --------------------------------------------------------------------------- #
def gen_zongjie(src_path, out_dir):
    data = json.loads(src_path.read_text(encoding="utf-8"))

    specs = [
        ("总结主体", "【总结主体名称】", "标题（发文主体）"),
        ("总结时段", "【总结时段】", "标题（时段）"),
        ("工作回顾", "【工作回顾内容】", "正文 一、工作回顾"),
        ("主要成绩", "【主要成绩内容】", "正文 二、主要成绩"),
        ("存在问题", "【存在问题内容】", "正文 三、存在问题"),
        ("下一步工作打算", "【下一步工作打算内容】", "正文 四、下一步工作打算"),
        ("成文日期", "【成文日期】", "成文日期"),
    ]
    fs = {k: resolve(data, k, ph) for k, ph, _ in specs}
    records = []
    for k, ph, where in specs:
        r = dict(fs[k])
        r["template_slot"] = where
        records.append(r)

    def section(heading, rec):
        """一级标题 + 若干条目；列表全空时落一条占位段。"""
        parts = [para(heading, font=HT, size=BODY, bold=True,
                      first_indent=640, spacing_before=120, spacing_after=120)]
        items = rec.get("items") if rec["input_type"] == "list" else None
        if items:
            for i, s in enumerate(items, 1):
                parts.append(para(f"{i}. {s}", first_indent=640,
                                  spacing_after=120))
        else:
            parts.append(para(rec["rendered"], first_indent=640,
                              spacing_after=120))
        return "".join(parts)

    body = "".join([
        para("", spacing_after=200),
        para_lines(title_lines(f"{fs['总结主体']['rendered']}关于"
                               f"{fs['总结时段']['rendered']}的工作总结", TITLE_SIZE),
                   font=TITLE_FONT, size=TITLE_SIZE, bold=True,
                   align="center", line=600, spacing_after=300),
        section("一、工作回顾", fs["工作回顾"]),
        section("二、主要成绩", fs["主要成绩"]),
        section("三、存在问题", fs["存在问题"]),
        section("四、下一步工作打算", fs["下一步工作打算"]),
        para("", spacing_after=200),
        para(fs["总结主体"]["rendered"], align="right", spacing_after=0),
        para(fs["成文日期"]["rendered"], align="right"),
    ])

    docx_path = out_dir / "文书.docx"
    build_docx(docx_path, body, "工作总结")

    return write_fields_json(
        out_dir / "fields.json",
        template_id="zongjie",
        template_name="工作总结",
        out_dir=str(out_dir.relative_to(ROOT)),
        source_file=str(src_path.relative_to(ROOT)),
        data=data, fields=records,
        notes=[
            "7 个键全部存在但均无可用内容：3 个纯空白字符串（总结主体/存在问题=U+0020×2，"
            "总结时段=\"\"）、1 个全空白数组（主要成绩=[\" \"]）、2 个空数组（工作回顾/"
            "下一步工作打算=[]）、1 个表意空格串（成文日期=U+3000）。status 全为 blank。",
            "空白项一律按未填写处理，落到对应【…】占位符，未中断生成。",
            "主要成绩 数组中的空白条目已剔除（items_dropped_as_blank=1），其余键原样留痕于 "
            "fields.json 的 raw / raw_codepoints。",
            "未虚构任何工作内容、数字或日期。",
            "版式同 A：GB/T 9704 页边距，标题宋体加粗二号，正文仿宋三号，"
            "一级标题黑体三号，固定行距 28 磅，页脚「— 页码 —」。",
        ])


def main():
    a = gen_qingshi(ROOT / "fixtures/qingshi_empty.json",
                    ROOT / "out/请示函-empty")
    b = gen_zongjie(ROOT / "fixtures/zongjie_blank.json",
                    ROOT / "out/工作总结-blank")
    for label, p in (("A 请示函", a), ("B 工作总结", b)):
        print(f"{label}: {p['field_count']} fields, "
              f"status={p['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())