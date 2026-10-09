// 屿光咖啡营运部工作周报生成器
// 输出: out/文书.docx + out/fields.json （yuguang_week.json 已单独保存为原始数据）
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  LevelFormat,
} = require("docx");
const fs = require("fs");
const path = require("path");

const BASE = __dirname;
const OUT_DIR = path.join(BASE, "out");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

// ---------- 数据 ----------
// 原始数据（与 brief 完全一致，已存 yuguang_week.json）
const source = JSON.parse(fs.readFileSync(path.join(BASE, "yuguang_week.json"), "utf8"));

// 报送日期推导：周期为 2026年10月第2周（10月5日—11日，11日为周日），
// 正文中本周工作内容的最后一项为「10月11日完成月度盘点差异复核」，
// 周报于周末工作完成后报送，故取正文中的 10月11日，补全年份 → 2026年10月11日。
const REPORT_DATE = "2026年10月11日";

// fields.json = 原始字段 + 推导出的报送日期
const fields = {
  部门: source.部门,
  填报人: source.填报人,
  周期: source.周期,
  报送日期: REPORT_DATE,
  本周工作内容: source.本周工作内容,
  下周工作计划: source.下周工作计划,
  问题与需协调事项: source.问题与需协调事项,
};

function safeText(value, placeholder) {
  if (value === undefined || value === null || value === "" ||
      String(value) === "NaN" || String(value) === "undefined") {
    return placeholder || "【待填写】";
  }
  return String(value);
}

// ---------- 样式常量（Profile A 正式公文风：黑字、宋体正文、黑体标题） ----------
const BLACK = "000000";
const BORDER_GRAY = "9AA6B2";
const LABEL_FILL = "F1F5F9";
const FONT_BODY = { ascii: "Times New Roman", eastAsia: "SimSun" };
const FONT_HEAD = { ascii: "Times New Roman", eastAsia: "SimHei" };

// ---------- 组件 ----------
function docTitle(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: true,
    spacing: { before: 120, after: 280, line: 506, lineRule: "atLeast" }, // 22pt*23
    children: [new TextRun({ text: safeText(text), bold: true, size: 44, color: BLACK, font: FONT_HEAD })],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 300, after: 140, line: 322, lineRule: "atLeast" }, // 14pt*23
    children: [new TextRun({ text: safeText(text), bold: true, size: 28, color: BLACK, font: FONT_HEAD })],
  });
}

function decimalListRef(reference) {
  return {
    reference,
    levels: [{
      level: 0,
      format: LevelFormat.DECIMAL,
      text: "%1.",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 480, hanging: 480 } } },
    }],
  };
}

function listItem(reference, text) {
  return new Paragraph({
    numbering: { reference, level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 60, line: 312 },
    children: [new TextRun({ text: safeText(text), size: 24, color: BLACK, font: FONT_BODY })],
  });
}

function metaLabelCell(text, widthPct) {
  return new TableCell({
    width: { size: widthPct, type: WidthType.PERCENTAGE },
    shading: { type: ShadingType.CLEAR, fill: LABEL_FILL },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { line: 312 },
      children: [new TextRun({ text: safeText(text), bold: true, size: 24, color: BLACK, font: FONT_HEAD })],
    })],
  });
}

function metaValueCell(text, widthPct, span) {
  return new TableCell({
    width: { size: widthPct, type: WidthType.PERCENTAGE },
    columnSpan: span,
    margins: { top: 80, bottom: 80, left: 160, right: 120 },
    verticalAlign: "center",
    children: [new Paragraph({
      spacing: { line: 312 },
      children: [new TextRun({ text: safeText(text), size: 24, color: BLACK, font: FONT_BODY })],
    })],
  });
}

const tableBorders = {
  top: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
  left: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
  right: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
  insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
  insideVertical: { style: BorderStyle.SINGLE, size: 4, color: BORDER_GRAY },
};

const metaTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  borders: tableBorders,
  rows: [
    new TableRow({
      tableHeader: true,
      cantSplit: true,
      children: [
        metaLabelCell("部门", 12),
        metaValueCell(source.部门, 44),
        metaLabelCell("填报人", 12),
        metaValueCell(source.填报人, 32),
      ],
    }),
    new TableRow({
      cantSplit: true,
      children: [
        metaLabelCell("周期", 12),
        metaValueCell(source.周期, 88, 3),
      ],
    }),
  ],
});

function signatureLine(label, value, spaceBefore) {
  return new Paragraph({
    alignment: AlignmentType.RIGHT,
    spacing: { before: spaceBefore || 0, line: 312 },
    children: [
      new TextRun({ text: safeText(label), size: 24, color: BLACK, font: FONT_BODY }),
      new TextRun({ text: safeText(value), size: 24, color: BLACK, font: FONT_BODY }),
    ],
  });
}

// ---------- 组装 ----------
const doc = new Document({
  creator: safeText(source.填报人),
  title: "屿光咖啡营运部工作周报",
  styles: {
    default: {
      document: {
        run: { font: FONT_BODY, size: 24, color: BLACK },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: FONT_HEAD, size: 28, bold: true, color: BLACK },
        paragraph: { spacing: { before: 300, after: 140, line: 322 } },
      },
    },
  },
  numbering: {
    config: [
      decimalListRef("list-this-week"),
      decimalListRef("list-next-week"),
      decimalListRef("list-issues"),
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
      },
    },
    children: [
      docTitle("屿光咖啡营运部工作周报"),
      metaTable,
      sectionHeading("一、本周工作内容"),
      ...source.本周工作内容.map(item => listItem("list-this-week", item)),
      sectionHeading("二、下周工作计划"),
      ...source.下周工作计划.map(item => listItem("list-next-week", item)),
      sectionHeading("三、问题与需协调事项"),
      ...source.问题与需协调事项.map(item => listItem("list-issues", item)),
      signatureLine("填报人：", source.填报人, 600),
      signatureLine("报送日期：", REPORT_DATE, 60),
    ],
  }],
});

// ---------- 输出 ----------
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(OUT_DIR, "文书.docx"), buf);
  fs.writeFileSync(path.join(OUT_DIR, "fields.json"), JSON.stringify(fields, null, 2) + "\n", "utf8");
  console.log("OK: out/文书.docx + out/fields.json written");
});
