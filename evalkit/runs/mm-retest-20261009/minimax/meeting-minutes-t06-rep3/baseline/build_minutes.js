const {
  Document, Packer, Paragraph, TextRun, Footer, PageNumber,
  AlignmentType, HeadingLevel, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, VerticalAlign,
} = require("/tmp/node_modules/docx");
const fs = require("fs");
const path = require("path");

// ---------- Fonts (local-first: Noto CJK stands in for SimHei / SimSun) ----------
const HEI = "Noto Sans CJK SC";   // 黑体 substitute (headings)
const SONG = "Noto Serif CJK SC"; // 宋体 substitute (body)
const TNR = "Times New Roman";

const INK = "000000";
const GRAY_LABEL = "404040";

const OUT_DIR = path.resolve(__dirname, "out");
fs.mkdirSync(OUT_DIR, { recursive: true });

// ---------- Helpers ----------
const safeText = (v, ph) =>
  v === undefined || v === null || v === "" || String(v) === "NaN" || String(v) === "undefined"
    ? ph || "【待补充】"
    : String(v);

const LQ = "\u201c";
const RQ = "\u201d";

function bodyPara(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: opts.noIndent ? 0 : 480 },
    spacing: { line: 312, before: opts.before ?? 0, after: opts.after ?? 120 },
    children: [new TextRun({ text: safeText(text), size: 24, color: INK, font: { ascii: TNR, eastAsia: SONG } })],
  });
}

function notePara(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 480 },
    spacing: { line: 312, before: 0, after: 120 },
    children: [new TextRun({ text: safeText(text), size: 21, color: INK, font: { ascii: TNR, eastAsia: SONG } })],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { line: 312, before: 320, after: 160 },
    children: [new TextRun({ text: safeText(text), bold: true, size: 28, color: INK, font: { ascii: TNR, eastAsia: HEI } })],
  });
}

function docTitle(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { line: 312, lineRule: "atLeast", before: 0, after: 320 },
    children: [new TextRun({ text: safeText(text), bold: true, size: 36, color: INK, font: { ascii: TNR, eastAsia: HEI } })],
  });
}

function cellPara(text, { bold = false, align = AlignmentType.LEFT, size = 21, shading } = {}) {
  return new Paragraph({
    alignment: align,
    spacing: { line: 312, before: 40, after: 40 },
    children: [new TextRun({
      text: safeText(text),
      bold,
      size,
      color: INK,
      font: { ascii: TNR, eastAsia: bold ? HEI : SONG },
    })],
    ...(shading ? { shading: { type: ShadingType.CLEAR, fill: shading, color: "auto" } } : {}),
  });
}

function mkCell(text, widthPct, opts = {}) {
  return new TableCell({
    width: { size: widthPct, type: WidthType.PERCENTAGE },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 108, right: 108 },
    children: [cellPara(text, opts)],
  });
}

function basicTable(pairs) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
      insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
    },
    rows: pairs.map(([k, v]) =>
      new TableRow({
        cantSplit: true,
        children: [
          mkCell(k, 24, { bold: true, shading: "F2F2F2" }),
          mkCell(v, 76),
        ],
      })
    ),
  });
}

function gridTable(widths, header, rows) {
  const cell = (t, w, i) =>
    new TableCell({
      width: { size: w, type: WidthType.PERCENTAGE },
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 60, bottom: 60, left: 108, right: 108 },
      children: [cellPara(t, i === 0 ? { bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" } : { align: i === 0 ? AlignmentType.CENTER : AlignmentType.LEFT })],
    });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "808080" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
      insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "B0B0B0" },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        cantSplit: true,
        children: header.map((t, i) => cell(t, widths[i], i)),
      }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, widths[i], i)) })),
    ],
  });
}

// ---------- Content ----------
const decided = [
  ["（一）晨会时间", "晨会自本次会议后固定于每周二上午召开，具体钟点另行确定。"],
  ["（二）工装夹具制作", "工装夹具先按现行图纸制作，不作修改。原会议以举手方式征求同意，转写稿未记录表决结果，表决情况待补。"],
  ["（三）淡季房价", "淡季房价方案于本次会议当场议定，工作日执行一口价。管家苏莞此前提出的改日群内投票方案，与本条结论的先后关系待确认。"],
];

const actionRows = [
  ["1", "物料清单梳理与核对", "小盛（管家苏莞委托）", "原话为" + LQ + "就这两天弄完" + RQ + "，未指明具体日期"],
  ["2", "腊味礼盒包装重新选型", "未明确（管家苏莞提出）", "须于出样前确定，具体日期未指明"],
];

const openItems = [
  ["（一）压胶工序延期风险", "布草房郁南提出，压胶工序仍是延期风险最大的环节，床罩已返工两次。本次会议未形成处置意见，亦未指定责任人。"],
  ["（二）洗烘设备保修单据", "布草房郁南提出，洗烘设备保修单据的存放位置不明。本次会议未明确归档位置与责任人。"],
  ["（三）淡季房价方案表决方式", "管家苏莞提出改日在群内发起投票，掌柜岑晏随后当场议定工作日一口价。是否仍需群内投票及二者的效力关系，待确认。"],
];

const children = [
  docTitle("泊棠民宿淡季工作会会议纪要"),
  basicTable([
    ["会议名称", "泊棠民宿淡季工作会"],
    ["会议时间", "19:00 至 19:09（转写稿未记录具体日期，待补充）"],
    ["会议地点", "待补充"],
    ["主持人", "掌柜 岑晏"],
    ["参会人员", "岑晏（掌柜）、苏莞（管家）、郁南（布草房）"],
    ["相关人员", "小盛（受物料清单梳理事项委托，转写稿未载明其是否在场）"],
    ["会议议题", "淡季经营及相关事项"],
    ["记录人", "待补充"],
  ]),

  h1("一、会议议定事项"),
  ...decided.map(([, t]) => bodyPara(t)),

  h1("二、会议待办事项"),
  gridTable([8, 34, 26, 32], ["序号", "事项", "负责人", "完成时限"], actionRows),
  bodyPara("上述时限系转写稿原话，未指明具体日期，请责任人确认后回填。", { before: 160 }),

  h1("三、待明确事项"),
  ...openItems.map(([, t]) => bodyPara(t)),

  h1("四、记录说明"),
  bodyPara("本纪要依据会议现场转写稿整理，已删除口语赘词、重复表述与语气词，各条含义与原话一致，未作实质性增删。"),
  bodyPara("转写稿未记录的信息（会议具体日期、会议地点、记录人、表决结果、部分责任人与具体时限等），一律标注为" + "“待补充”" + "或" + "“未明确”" + "，未作推定，亦未以文件名推断具体日期。"),
];

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: { ascii: TNR, eastAsia: SONG }, size: 24, color: INK }, paragraph: { spacing: { line: 312 } } },
      heading1: { run: { font: { ascii: TNR, eastAsia: HEI }, size: 28, bold: true, color: INK } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: "— ", size: 21, color: GRAY_LABEL, font: { ascii: TNR, eastAsia: SONG } }),
                new TextRun({ children: [PageNumber.CURRENT], size: 21, color: GRAY_LABEL, font: { ascii: TNR, eastAsia: SONG } }),
                new TextRun({ text: " —", size: 21, color: GRAY_LABEL, font: { ascii: TNR, eastAsia: SONG } }),
              ],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

const outPath = path.join(OUT_DIR, "纪要.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log("WROTE " + outPath + " (" + buf.length + " bytes)");
});
