// 生成拾贝书店周报 Word 文书
// 输入：shibei_week42.json（brief 内嵌 JSON 原样落盘）
// 输出：out/文书.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Footer, AlignmentType, HeadingLevel,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType, PageNumber,
  PageOrientation, VerticalAlign,
} = require("docx");

const BASE = __dirname;
const OUT = path.join(BASE, "out");
fs.mkdirSync(OUT, { recursive: true });

const raw = JSON.parse(fs.readFileSync(path.join(BASE, "shibei_week42.json"), "utf8"));

// ---------- 字段台账（周报模板字段口径） ----------
// 必填：部门 / 填报人 / 周期 / 本周工作内容 / 下周工作计划 / 报送日期
// 选填：问题与需协调事项 / 温馨提示（备注）
const REQUIRED = ["部门", "填报人", "周期", "本周工作内容", "下周工作计划", "报送日期"];
const OPTIONAL = ["问题与需协调事项", "温馨提示"];
const KNOWN = new Set([...REQUIRED, ...OPTIONAL]);

// 归一化：字符串去首尾空白；数组剔除空白/空元素后返回列表
function normScalar(v) {
  return typeof v === "string" ? v.trim() : v;
}
function normList(v) {
  const arr = Array.isArray(v) ? v : [v];
  return arr.map(normScalar).filter((x) => typeof x === "string" && x !== "");
}

const values = {};
const dropped = [];
for (const [k, v] of Object.entries(raw)) {
  if (Array.isArray(v) || (typeof v === "string" && REQUIRED.includes(k) === false && OPTIONAL.includes(k) === false)) {
    values[k] = normList(v);
  } else {
    values[k] = normScalar(v);
  }
  if (Array.isArray(raw[k])) {
    const kept = values[k].length;
    raw[k].forEach((item, i) => {
      if (normScalar(item) === "") dropped.push({ field: k, index: i, raw: item });
    });
    if (kept === 0) values[k] = [];
  }
}

const trimmedFields = Object.entries(raw)
  .filter(([k, v]) => typeof v === "string" && v !== v.trim())
  .map(([k, v]) => ({ field: k, raw: v, normalized: v.trim() }));

const missing_required_names = REQUIRED.filter((k) => {
  const v = values[k];
  if (v === undefined || v === null) return true;
  if (Array.isArray(v)) return v.length === 0;
  return String(v).trim() === "";
});
const missing_optional = OPTIONAL.filter((k) => {
  const v = values[k];
  if (v === undefined || v === null) return true;
  if (Array.isArray(v)) return v.length === 0;
  return String(v).trim() === "";
});
const unknown_keys = Object.keys(raw).filter((k) => !KNOWN.has(k));

// ---------- 文书正文 ----------
const DEPT = values["部门"];
const TITLE = DEPT + "周报";

const CN_FONT = { ascii: "Times New Roman", eastAsia: "SimSun" };
const HEI_FONT = { ascii: "Times New Roman", eastAsia: "SimHei" };

function body(text, opts = {}) {
  return new Paragraph({
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    indent: opts.indent === false ? undefined : { firstLine: 480 },
    spacing: { line: 312, before: opts.before || 0, after: opts.after === undefined ? 60 : opts.after },
    children: [new TextRun({ text, size: 24, font: CN_FONT, color: "000000" })],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120, line: 312 },
    keepNext: true,
    children: [new TextRun({ text, bold: true, size: 28, font: HEI_FONT, color: "000000" })],
  });
}

// 单号条目（正文，悬挂缩进，不另起首行缩进）
function numberedItem(n, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 480, hanging: 480 },
    spacing: { line: 312, after: 60 },
    children: [
      new TextRun({ text: n + ". ", size: 24, font: CN_FONT, color: "000000" }),
      new TextRun({ text, size: 24, font: CN_FONT, color: "000000" }),
    ],
  });
}

const LABEL_W = 2200;
const VALUE_W = 5600;
const CELL_MARGIN = { top: 60, bottom: 60, left: 120, right: 120 };

function infoRow(label, value) {
  const b = (sz, val) => ({ style: BorderStyle.SINGLE, size: sz, color: val });
  const thin = b(4, "808080");
  return new TableRow({
    cantSplit: true,
    children: [
      new TableCell({
        width: { size: LABEL_W, type: WidthType.DXA },
        margins: CELL_MARGIN,
        verticalAlign: VerticalAlign.CENTER,
        shading: { type: ShadingType.CLEAR, color: "auto", fill: "F2F2F2" },
        borders: { top: thin, bottom: thin, left: thin, right: thin },
        children: [new Paragraph({
          spacing: { line: 312, before: 0, after: 0 },
          children: [new TextRun({ text: label, bold: true, size: 24, font: HEI_FONT, color: "000000" })],
        })],
      }),
      new TableCell({
        width: { size: VALUE_W, type: WidthType.DXA },
        margins: CELL_MARGIN,
        verticalAlign: VerticalAlign.CENTER,
        borders: { top: thin, bottom: thin, left: thin, right: thin },
        children: [new Paragraph({
          spacing: { line: 312, before: 0, after: 0 },
          children: [new TextRun({ text: value, size: 24, font: CN_FONT, color: "000000" })],
        })],
      }),
    ],
  });
}

const doc = new Document({
  creator: "拾贝书店",
  title: TITLE,
  description: values["周期"],
  styles: {
    default: {
      document: {
        run: { font: CN_FONT, size: 24, color: "000000" },
        paragraph: { spacing: { line: 312 } },
      },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838, orientation: PageOrientation.PORTRAIT },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { line: 312 },
            children: [
              new TextRun({ text: "第 ", size: 18, font: CN_FONT, color: "000000" }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, font: CN_FONT, color: "000000" }),
              new TextRun({ text: " 页", size: 18, font: CN_FONT, color: "000000" }),
            ],
          })],
        }),
      },
      children: [
        // 主标题
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 120, line: 312 },
          children: [new TextRun({ text: TITLE, bold: true, size: 44, font: HEI_FONT, color: "000000" })],
        }),
        // 副标题（周期）
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 320, line: 312 },
          children: [new TextRun({ text: values["周期"], size: 24, font: CN_FONT, color: "000000" })],
        }),

        // 抬头信息表
        new Table({
          width: { size: LABEL_W + VALUE_W, type: WidthType.DXA },
          columnWidths: [LABEL_W, VALUE_W],
          margins: CELL_MARGIN,
          rows: [
            infoRow("部门", values["部门"]),
            infoRow("填报人", values["填报人"]),
            infoRow("报送日期", values["报送日期"]),
          ],
        }),
        new Paragraph({ spacing: { before: 0, after: 0, line: 312 }, children: [] }),

        // 一、本周工作内容
        sectionHeading("一、本周工作内容"),
        ...values["本周工作内容"].map((t, i) => numberedItem(i + 1, t)),

        // 二、下周工作计划
        sectionHeading("二、下周工作计划"),
        body(values["下周工作计划"]),

        // 三、问题与需协调事项
        sectionHeading("三、问题与需协调事项"),
        ...(Array.isArray(values["问题与需协调事项"])
          ? values["问题与需协调事项"].map((t, i) => numberedItem(i + 1, t))
          : [body(values["问题与需协调事项"])]),

        // 四、温馨提示
        sectionHeading("四、温馨提示"),
        body(values["温馨提示"]),
      ],
    },
  ],
});

const docxPath = path.join(OUT, "文书.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(docxPath, buf);
  console.log("written:", docxPath, buf.length, "bytes");
  console.log("title:", TITLE);
  console.log(JSON.stringify({ missing_required_names, missing_optional, unknown_keys }, null, 2));
  console.log("dropped:", JSON.stringify(dropped));
  console.log("trimmed:", JSON.stringify(trimmedFields));
});
