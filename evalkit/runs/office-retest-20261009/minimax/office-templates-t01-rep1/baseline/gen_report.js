const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  Footer, PageNumber, LevelFormat,
} = require("docx");
const fs = require("fs");
const path = require("path");

const BASE = "/home/pan-ding/workspace/skill工厂/skillfactory/evalkit/runs/office-retest-20261009/minimax/office-templates-t01-rep1/baseline";
const LEDGER = JSON.parse(fs.readFileSync(path.join(BASE, "out/fields.json"), "utf8"));

// 台账取值：字段缺失一律走占位符，绝不输出 undefined / 空串
const byName = {};
for (const f of LEDGER.fields) byName[f.name] = f;

function val(name, placeholder) {
  const f = byName[name];
  if (!f || f.missing || f.value === null || f.value === undefined) return placeholder;
  const v = f.value;
  if (Array.isArray(v)) return v.length ? v : placeholder;
  return String(v).trim() === "" ? placeholder : String(v);
}
function items(name) {
  const f = byName[name];
  if (!f || !Array.isArray(f.value)) return [];
  return f.value;
}

// 配色：内部周报，克制的中性色
const C = {
  primary: "1F3A5F",
  label: "EDF1F6",
  body: "000000",
  meta: "5A6472",
  rule: "C3CDDA",
};

const FONT_HAN = { ascii: "Times New Roman", eastAsia: "SimHei" };
const FONT_SONG = { ascii: "Times New Roman", eastAsia: "SimSun" };

const HAIRLINE = { style: BorderStyle.SINGLE, size: 2, color: C.rule };
const TABLE_BORDERS = {
  top: HAIRLINE, bottom: HAIRLINE, left: HAIRLINE, right: HAIRLINE,
  insideHorizontal: HAIRLINE, insideVertical: HAIRLINE,
};

function safeText(v, ph) {
  if (v === undefined || v === null || v === "" || String(v) === "undefined" || String(v) === "NaN") {
    return ph || "【请填写】";
  }
  return String(v);
}

function title() {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 80, line: 560, lineRule: "atLeast" },
    children: [new TextRun({
      text: safeText(LEDGER.document_title, "【请填写】"),
      bold: true, size: 44, color: C.primary, font: FONT_HAN,
    })],
  });
}

function subtitle() {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 240, line: 320, lineRule: "atLeast" },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.primary, space: 6 } },
    children: [new TextRun({
      text: "内部工作周报",
      size: 21, color: C.meta, font: FONT_SONG,
    })],
  });
}

// 抬头信息表：2 列 × 2 组
function infoTable() {
  const cell = (text, isLabel, width) => new TableCell({
    width: { size: width, type: WidthType.PERCENTAGE },
    shading: isLabel ? { type: ShadingType.CLEAR, fill: C.label, color: "auto" } : undefined,
    margins: { top: 90, bottom: 90, left: 130, right: 130 },
    verticalAlign: "center",
    children: [new Paragraph({
      spacing: { before: 0, after: 0, line: 312, lineRule: "atLeast" },
      children: [new TextRun({
        text: safeText(text, "【请填写】"),
        bold: isLabel, size: isLabel ? 21 : 22,
        color: isLabel ? C.primary : C.body,
        font: isLabel ? FONT_HAN : FONT_SONG,
      })],
    })],
  });

  const row = (l1, v1, l2, v2) => new TableRow({
    cantSplit: true,
    children: [cell(l1, true, 15), cell(v1, false, 35), cell(l2, true, 15), cell(v2, false, 35)],
  });

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: TABLE_BORDERS,
    rows: [
      row("部门", val("部门", "【请填写】"), "报送周期", val("周期", "【请填写】")),
      row("填报人", val("填报人", "【请填写】"), "报送日期", val("报送日期", "【请填写】")),
    ],
  });
}

function sectionHeading(no, label) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    keepNext: true,
    spacing: { before: 280, after: 120, line: 320, lineRule: "atLeast" },
    children: [new TextRun({
      text: `${no}、${label}`,
      bold: true, size: 26, color: C.primary, font: FONT_HAN,
    })],
  });
}

function bodyPara(text, extra = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 0, after: 60, line: 312 },
    indent: { firstLine: 480 },
    ...extra,
    children: [new TextRun({ text: safeText(text, "【请填写】"), size: 24, color: C.body, font: FONT_SONG })],
  });
}

function listPara(text, ref, idx) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    numbering: { reference: ref, level: 0 },
    spacing: { before: 0, after: 60, line: 312 },
    children: [new TextRun({ text: safeText(text, "【请填写】"), size: 24, color: C.body, font: FONT_SONG })],
  });
}

function notice(text) {
  // 温馨提示：无序号的浅底提示条
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: C.rule },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: C.rule },
      left: { style: BorderStyle.SINGLE, size: 18, color: C.primary },
      right: { style: BorderStyle.SINGLE, size: 2, color: C.rule },
      insideHorizontal: { style: BorderStyle.NONE },
      insideVertical: { style: BorderStyle.NONE },
    },
    rows: [new TableRow({
      cantSplit: true,
      children: [new TableCell({
        width: { size: 100, type: WidthType.PERCENTAGE },
        margins: { top: 110, bottom: 110, left: 160, right: 160 },
        children: [new Paragraph({
          spacing: { before: 0, after: 0, line: 312 },
          children: [
            new TextRun({ text: "温馨提示：", bold: true, size: 24, color: C.primary, font: FONT_HAN }),
            new TextRun({ text: safeText(text, "【请填写】"), size: 24, color: C.body, font: FONT_SONG }),
          ],
        })],
      })],
    })],
  });
}

function signature() {
  const line = (text) => new Paragraph({
    alignment: AlignmentType.RIGHT,
    spacing: { before: 0, after: 60, line: 312 },
    children: [new TextRun({ text: safeText(text, "【请填写】"), size: 24, color: C.body, font: FONT_SONG })],
  });
  return [line(`填报人：${val("填报人", "【请填写】")}`), line(val("报送日期", "【请填写】"))];
}

const done = items("本周工作内容");
const issues = items("问题与需协调事项");

const children = [
  title(),
  subtitle(),
  infoTable(),
  sectionHeading("一", "本周工作内容"),
  ...(done.length
    ? done.map((t, i) => listPara(t, "list-done", i))
    : [bodyPara("【本期无填报内容】")]),
  sectionHeading("二", "下周工作计划"),
  bodyPara(val("下周工作计划", "【请填写】")),
  sectionHeading("三", "问题与需协调事项"),
  ...(issues.length
    ? issues.map((t, i) => listPara(t, "list-issue", i))
    : [bodyPara("【本期无事项】")]),
  sectionHeading("四", "温馨提示"),
  notice(val("温馨提示", "【请填写】")),
  new Paragraph({ spacing: { before: 240, after: 0, line: 312 }, children: [] }),
  ...signature(),
];

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: FONT_SONG, size: 24, color: C.body }, paragraph: { spacing: { line: 312 } } },
      heading1: {
        run: { font: FONT_HAN, size: 26, bold: true, color: C.primary },
        paragraph: { spacing: { before: 280, after: 120, line: 320 }, outlineLevel: 0 },
      },
    },
  },
  numbering: {
    config: [
      {
        reference: "list-done",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
      {
        reference: "list-issue",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 0, line: 240 },
          children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: C.meta, font: FONT_SONG })],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(BASE, "out/文书.docx"), buf);
  console.log("written", buf.length);
});