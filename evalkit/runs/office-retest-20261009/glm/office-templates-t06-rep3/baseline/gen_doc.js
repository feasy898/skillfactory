const path = require("path");
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun,
  AlignmentType, HeadingLevel, BorderStyle,
} = require("docx");

const OUT_DIR = path.join(__dirname, "out");

const FONT_BODY = { ascii: "Times New Roman", eastAsia: "SimSun" };
const FONT_HEAD = { ascii: "Times New Roman", eastAsia: "SimHei" };
const BLACK = "000000";

function safeText(value, placeholder) {
  if (value === undefined || value === null || value === "" ||
      String(value) === "NaN" || String(value) === "undefined") {
    return placeholder || "【待填写】";
  }
  return String(value);
}

const data = JSON.parse(fs.readFileSync(path.join(__dirname, "yuguang_week.json"), "utf8"));

// 报送日期未随数据提供：取正文中本周最后一项已完成工作的日期（10月11日月度盘点差异复核），
// 该日亦为「2026年10月第2周」的周日（周报收口日），是落款报送日的唯一自洽选择。
const submitDate = "2026年10月11日";

const title = `${safeText(data["部门"])}工作周报`;
const periodLine = `（${safeText(data["周期"])}）`;

function titlePara(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 80, line: 414, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, size: 36, color: BLACK, font: FONT_HEAD })],
  });
}

function subtitlePara(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200, line: 312 },
    children: [new TextRun({ text, size: 24, color: BLACK, font: FONT_BODY })],
  });
}

function infoLine() {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { after: 240, line: 312 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "8C8C8C", space: 6 } },
    children: [
      new TextRun({ text: `部门：${safeText(data["部门"])}`, size: 24, color: BLACK, font: FONT_BODY }),
      new TextRun({ text: "\u3000\u3000", size: 24, color: BLACK, font: FONT_BODY }),
      new TextRun({ text: `填报人：${safeText(data["填报人"])}`, size: 24, color: BLACK, font: FONT_BODY }),
    ],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 28, color: BLACK, font: FONT_HEAD })],
  });
}

function numberedItem(num, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 480 },
    spacing: { after: 40, line: 312 },
    children: [new TextRun({ text: `${num}. ${safeText(text)}。`, size: 24, color: BLACK, font: FONT_BODY })],
  });
}

function signOffLine(text, spaceBefore) {
  return new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 200 },
    spacing: { before: spaceBefore || 0, after: 40, line: 312 },
    children: [new TextRun({ text, size: 24, color: BLACK, font: FONT_BODY })],
  });
}

const children = [
  titlePara(title),
  subtitlePara(periodLine),
  infoLine(),

  sectionHeading("一、本周工作内容"),
  ...data["本周工作内容"].map((t, i) => numberedItem(i + 1, t)),

  sectionHeading("二、下周工作计划"),
  ...data["下周工作计划"].map((t, i) => numberedItem(i + 1, t)),

  sectionHeading("三、问题与需协调事项"),
  ...data["问题与需协调事项"].map((t, i) => numberedItem(i + 1, t)),

  signOffLine(`填报人：${safeText(data["填报人"])}`, 600),
  signOffLine(`报送日期：${submitDate}`),
];

const doc = new Document({
  creator: safeText(data["部门"]),
  title: `${title}（${safeText(data["周期"])}）`,
  styles: {
    default: {
      document: {
        run: { font: FONT_BODY, size: 24, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: FONT_HEAD, size: 28, bold: true, color: BLACK },
        paragraph: { spacing: { before: 280, after: 120, line: 312 } },
      },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const outPath = path.join(OUT_DIR, "文书.docx");
  fs.writeFileSync(outPath, buf);
  console.log("written:", outPath, buf.length, "bytes");
});
