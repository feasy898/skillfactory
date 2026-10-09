// 青蘅茶社 会议通知生成脚本（公文格式，非红头）
// 依据 docx skill scenes/official-doc.md：Template A 通知，GB/T 9704 版式
const {
  Document, Packer, Paragraph, TextRun, Footer,
  AlignmentType, PageNumber, LineRuleType,
} = require("docx");
const fs = require("fs");
const path = require("path");

const data = JSON.parse(fs.readFileSync(path.join(__dirname, "qingheng_teahui.json"), "utf8"));

// 会议议题源数据首尾各有一个半角空格，按公文排版规范剔除后渲染
const topic = data["会议议题"].trim();

const F_FANGSONG = { ascii: "Times New Roman", eastAsia: "FangSong" }; // 正文三号仿宋
const F_HEI = { ascii: "Times New Roman", eastAsia: "SimHei" };        // 一级条目标签黑体
const F_TITLE = { ascii: "Times New Roman", eastAsia: "STXiaoBiaoSong" }; // 标题小标宋（缺字体时退化为加粗宋体观感）
const SIZE_BODY = 32;  // 三号 16pt
const LINE = { line: 560, lineRule: LineRuleType.EXACT }; // 固定 28pt 行距
const INDENT2 = 640;   // 三号两字符缩进

// 正文段（仿宋三号，首行缩进两字，两端对齐）
function bodyPara(children, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: INDENT2 },
    spacing: { ...LINE, ...(opts.spacing || {}) },
    children,
  });
}

// 一级条目：黑体标签「一、会议时间：」＋仿宋值
function item(num, label, value) {
  const runs = [new TextRun({ text: `${num}、${label}：`, font: F_HEI, size: SIZE_BODY })];
  if (value) runs.push(new TextRun({ text: value, font: F_FANGSONG, size: SIZE_BODY }));
  return bodyPara(runs);
}

// 二级条目（一）—（六）：条目原文末尾无标点，按公文列表规范补「；」，末条补「。」
const cnNums = ["一", "二", "三", "四", "五", "六"];
const reqParas = data["会议要求"].map((s, i) => {
  const tail = i === data["会议要求"].length - 1 ? "。" : "；";
  return bodyPara([
    new TextRun({ text: `（${cnNums[i]}）${s}${tail}`, font: F_FANGSONG, size: SIZE_BODY }),
  ]);
});

const doc = new Document({
  title: `${data["召开单位"]}关于召开${data["会议名称"]}的通知`,
  creator: data["召开单位"],
  styles: {
    default: {
      document: {
        run: { font: F_FANGSONG, size: SIZE_BODY, color: "000000" },
        paragraph: { spacing: LINE },
      },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 2098, bottom: 1984, left: 1588, right: 1474 }, // GB/T 9704 版心
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { line: 240, lineRule: LineRuleType.AUTO },
            children: [
              new TextRun({ text: "\u2014 ", font: F_FANGSONG, size: 28 }),
              new TextRun({ children: [PageNumber.CURRENT], font: F_FANGSONG, size: 28 }),
              new TextRun({ text: " \u2014", font: F_FANGSONG, size: 28 }),
            ],
          })],
        }),
      },
      children: [
        // 标题：二号小标宋，居中（压缩题下空距，保证成文日期与正文同页）
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { line: 700, lineRule: LineRuleType.AT_LEAST, after: 240 },
          children: [new TextRun({
            text: `${data["召开单位"]}关于召开${data["会议名称"]}的通知`,
            font: F_TITLE, size: 44, bold: true,
          })],
        }),
        // 主送对象：顶格，全角冒号
        new Paragraph({
          alignment: AlignmentType.LEFT,
          spacing: LINE,
          children: [new TextRun({ text: `${data["主送对象"]}：`, font: F_FANGSONG, size: SIZE_BODY })],
        }),
        // 导语
        bodyPara([new TextRun({
          text: `为安排秋季茶会流程、预告冬至茶会事宜，经研究，定于${data["会议时间"]}在${data["会议地点"]}召开${data["会议名称"]}。现将有关事项通知如下：`,
          font: F_FANGSONG, size: SIZE_BODY,
        })]),
        // 条目一至四
        item("一", "会议时间", data["会议时间"]),
        item("二", "会议地点", data["会议地点"]),
        item("三", "参会人员", data["参会人员"]),
        item("四", "会议议题", topic),
        // 条目五：会议要求（二级条目逐条列出）
        item("五", "会议要求"),
        ...reqParas,
        // 条目六、七：联系人、联系电话
        item("六", "联系人", data["联系人"]),
        item("七", "联系电话", data["联系电话"]),
        // 结束语
        bodyPara([new TextRun({ text: "特此通知。", font: F_FANGSONG, size: SIZE_BODY })]),
        // 落款：署名右空二字，成文日期右空四字（阿拉伯数字，GB/T 9704—2012）；
        // 落款前空距压缩为半行，确保署名与日期随正文同页
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          indent: { right: INDENT2 },
          spacing: { ...LINE, before: 240 },
          children: [new TextRun({ text: data["召开单位"], font: F_FANGSONG, size: SIZE_BODY })],
        }),
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          indent: { right: 1280 },
          spacing: LINE,
          children: [new TextRun({ text: data["发文日期"], font: F_FANGSONG, size: SIZE_BODY })],
        }),
      ],
    },
  ],
});

const outDir = path.join(__dirname, "out");
fs.mkdirSync(outDir, { recursive: true });
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(outDir, "文书.docx"), buf);
  console.log("OK out/文书.docx", buf.length, "bytes");
});
