const {
  Document, Packer, Paragraph, TextRun, Footer, PageNumber,
  AlignmentType, BorderStyle, ShadingType, Table, TableRow, TableCell,
  WidthType, VerticalAlign, TabStopType,
} = require("docx");
const fs = require("fs");
const path = require("path");

const SANS = "Noto Sans CJK SC";
const SERIF = "Noto Serif CJK SC";
const INK = "1F2933";
const MUTED = "5A6672";
const NAVY = "23405E";
const LINE = "C9D2DC";
const ZEBRA = "F2F5F9";
const WARN_BG = "FFF6E5";
const NOTE_BG = "FBF3E2";
const NOTE_BORDER = "D8B978";

const CELL_MARGIN = { top: 70, bottom: 70, left: 130, right: 130 };
const allBorders = (color, size = 4) => ({
  top: { style: BorderStyle.SINGLE, size, color },
  bottom: { style: BorderStyle.SINGLE, size, color },
  left: { style: BorderStyle.SINGLE, size, color },
  right: { style: BorderStyle.SINGLE, size, color },
});

const cell = (children, opts = {}) =>
  new TableCell({
    margins: CELL_MARGIN,
    verticalAlign: VerticalAlign.CENTER,
    borders: opts.borders || allBorders(LINE),
    shading: opts.bg
      ? { type: ShadingType.CLEAR, color: "auto", fill: opts.bg }
      : undefined,
    columnSpan: opts.span,
    children,
  });

const run = (text, o = {}) =>
  new TextRun({
    text,
    font: { ascii: o.font || SERIF, eastAsia: o.font || SERIF },
    size: o.size || 21,
    bold: o.bold || false,
    color: o.color || INK,
  });

const para = (children, o = {}) =>
  new Paragraph({
    alignment: o.align || AlignmentType.LEFT,
    spacing: { line: 312, before: o.before || 0, after: o.after === undefined ? 80 : o.after },
    indent: o.indent,
    keepNext: o.keepNext,
    children,
  });

const cellText = (text, o = {}) =>
  para([run(text, o)], { after: 0, align: o.align });

// ---------------------------------------------------------------------------
// 正文表格内容：每一格都带口径说明，避免季度数被读成本周数
// ---------------------------------------------------------------------------
const noteLine = (text) =>
  para(
    [run(text, { size: 18, color: MUTED, font: SANS })],
    { after: 0, before: 40 }
  );

const rows = [
  {
    label: "报告主体",
    value: [cellText("屿光咖啡品控组", { size: 22 })],
    src: [cellText("源数据 · 总结主体", { size: 18, color: MUTED })],
  },
  {
    label: "填报人",
    value: [
      cellText("待补充", { size: 22, bold: true, color: "8A5A00" }),
      noteLine("源数据仅给出部门，未给出个人填报人"),
    ],
    src: [cellText("需业务方填写", { size: 18, color: MUTED })],
    warn: true,
  },
  {
    label: "报告周期",
    value: [
      cellText("2026-10-05（周一）至 2026-10-11（周日）", { size: 22 }),
      noteLine("按成文日期 2026-10-09 所在自然周推算，源数据未给出周次，需核对"),
    ],
    src: [cellText("推算值 · 待确认", { size: 18, color: MUTED })],
  },
  {
    label: "本周工作完成情况",
    value: [
      cellText("【季度累计口径】", { size: 20, bold: true, color: NAVY, font: SANS }),
      para([run("完成季度杯测 36 场；处理客诉工单 58 单。")], { after: 0 }),
      noteLine("※ 上述为 2026 年第三季度（7/1—9/30）累计数，非本周数。源数据未提供本周逐项数据，故未拆分、未按周折算。"),
    ],
    src: [cellText("源数据 · 工作回顾（季度口径）", { size: 18, color: MUTED })],
  },
  {
    label: "本周主要成绩",
    value: [
      cellText("【季度累计口径】", { size: 20, bold: true, color: NAVY, font: SANS }),
      para([run("客诉 48 小时闭环率提升至 92%。")], { after: 0 }),
      noteLine("※ 该指标为第三季度末水平，非本周新增改善。"),
    ],
    src: [cellText("源数据 · 主要成绩（季度口径）", { size: 18, color: MUTED })],
  },
  {
    label: "本周存在问题",
    value: [
      para([run("偏远门店物流损耗偏高。")], { after: 0 }),
      noteLine("※ 源数据未提供本周新发现的问题，此处沿用第三季度已记录项。"),
    ],
    src: [cellText("源数据 · 存在问题", { size: 18, color: MUTED })],
  },
  {
    label: "下周工作计划",
    value: [
      para([run("引入损耗周报机制。")], { after: 0 }),
      noteLine("※ 源数据列为第三季度既定计划；若本周已启动或已完成，请据实更新。"),
    ],
    src: [cellText("源数据 · 下一步工作打算", { size: 18, color: MUTED })],
  },
  {
    label: "需要协调支持事项",
    value: [
      cellText("待补充", { size: 22, bold: true, color: "8A5A00" }),
      noteLine("源数据未涉及此项"),
    ],
    src: [cellText("需业务方填写", { size: 18, color: MUTED })],
    warn: true,
  },
  {
    label: "填报日期",
    value: [cellText("2026年10月9日", { size: 22 })],
    src: [cellText("源数据 · 成文日期", { size: 18, color: MUTED })],
  },
];

const headerRow = new TableRow({
  tableHeader: true,
  cantSplit: true,
  children: [
    cell([cellText("项目", { size: 21, bold: true, color: "FFFFFF", font: SANS })], {
      bg: NAVY, borders: allBorders(NAVY),
    }),
    cell([cellText("内容", { size: 21, bold: true, color: "FFFFFF", font: SANS })], {
      bg: NAVY, borders: allBorders(NAVY),
    }),
    cell([cellText("数据口径与来源", { size: 21, bold: true, color: "FFFFFF", font: SANS })], {
      bg: NAVY, borders: allBorders(NAVY),
    }),
  ],
});

const bodyRows = rows.map((r) =>
  new TableRow({
    cantSplit: true,
    children: [
      cell([cellText(r.label, { size: 21, bold: true, font: SANS, color: NAVY })], {
        bg: ZEBRA, borders: allBorders(LINE),
      }),
      cell(r.value, { bg: r.warn ? WARN_BG : undefined, borders: allBorders(LINE) }),
      cell(r.src, { bg: ZEBRA, borders: allBorders(LINE) }),
    ],
  })
);

const mainTable = new Table({
  width: { size: 9070, type: WidthType.DXA },
  columnWidths: [2300, 4700, 2070],
  margins: CELL_MARGIN,
  rows: [headerRow, ...bodyRows],
});

// ---------------------------------------------------------------------------
const pending = [
  "本期周报实际覆盖的起止日期（当前为按成文日期 2026-10-09 推算的 2026-10-05 至 2026-10-11；若指上一完整周则为 2026-09-28 至 2026-10-04）。",
  "本周杯测场次、本周新增客诉工单量（当前表中为第三季度累计数 36 场 / 58 单）。",
  "本周客诉 48 小时闭环率的周度读数（当前表中为第三季度末的 92%）。",
  "本周是否沿用「偏远门店物流损耗偏高」，或另有本周新增问题。",
  "本周填报人姓名。",
  "本周需要上级或其他部门协调支持的具体事项。",
];

const numberedList = pending.map((t, i) =>
  para(
    [
      run(`${i + 1}．`, { size: 21, bold: true, font: SANS, color: NAVY }),
      run(t),
    ],
    { indent: { left: 480, hanging: 480 }, after: 40 }
  )
);

const noticeBox = new Table({
  width: { size: 9070, type: WidthType.DXA },
  columnWidths: [9070],
  margins: { top: 120, bottom: 120, left: 160, right: 160 },
  rows: [
    new TableRow({
      cantSplit: true,
      children: [
        cell(
          [
            para([run("填报口径说明", { size: 21, bold: true, font: SANS, color: "8A5A00" })], { after: 60, keepNext: true }),
            para(
              [
                run(
                  "本表依据《屿光咖啡品控组 2026 年第三季度工作总结》改写为周报。源数据为季度累计口径，" +
                  "与周报的单周口径不一致，且未包含个人填报人、需协调支持事项等信息。" +
                  "凡表内标注【季度累计口径】的数值，均为 7/1—9/30 的累计数或季度末水平，不可当作本周数据阅读；" +
                  "标注「待补充」的字段，源数据确无对应内容，未作任何推测填充。" +
                  "请业务方按下方清单补齐后再行提交。"
                ),
              ],
              { align: AlignmentType.JUSTIFIED }
            ),
          ],
          { bg: NOTE_BG, borders: allBorders(NOTE_BORDER, 6) }
        ),
      ],
    }),
  ],
});

const signTable = new Table({
  width: { size: 9070, type: WidthType.DXA },
  columnWidths: [4535, 4535],
  margins: { top: 60, bottom: 60, left: 0, right: 0 },
  rows: [
    new TableRow({
      cantSplit: true,
      children: [
        cell([cellText("填报人（签字）：________________", { size: 21 })], {
          borders: { top: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE } },
        }),
        cell([cellText("日期：______ 年 ____ 月 ____ 日", { size: 21 })], {
          borders: { top: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE } },
        }),
      ],
    }),
    new TableRow({
      cantSplit: true,
      children: [
        cell([cellText("部门负责人（签字）：________________", { size: 21 })], {
          borders: { top: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE } },
        }),
        cell([cellText("日期：______ 年 ____ 月 ____ 日", { size: 21 })], {
          borders: { top: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE } },
        }),
      ],
    }),
  ],
});

const { PageBreak } = require("docx");

const sectionHeading = (text, opts = {}) =>
  new Paragraph({
    heading: undefined,
    keepNext: true,
    spacing: { before: opts.pageBreak ? 0 : 260, after: 120, line: 312 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 4 } },
    children: [
      ...(opts.pageBreak
        ? [new TextRun({ children: [new PageBreak()], size: 2, font: { ascii: SANS, eastAsia: SANS } })]
        : []),
      run(text, { size: 24, bold: true, font: SANS, color: NAVY }),
    ],
  });

const doc = new Document({
  creator: "屿光咖啡品控组",
  title: "周报",
  description: "依据 2026 年第三季度工作总结材料改写的周报，含口径标注与待补充清单",
  styles: {
    default: {
      document: {
        run: { font: { ascii: SERIF, eastAsia: SERIF }, size: 21, color: INK },
        paragraph: { spacing: { line: 312 } },
      },
    },
  },
  sections: [
    {
      properties: {
        page: {
          margin: { top: 1000, bottom: 900, left: 1418, right: 1418 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { line: 240 },
              children: [
                run("屿光咖啡品控组周报 · 第 ", { size: 18, color: MUTED, font: SANS }),
                new TextRun({ children: [PageNumber.CURRENT], size: 18, color: MUTED, font: { ascii: SANS, eastAsia: SANS } }),
                run(" 页", { size: 18, color: MUTED, font: SANS }),
              ],
            }),
          ],
        }),
      },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 50, line: 340 },
          children: [run("周　报", { size: 52, bold: true, font: SANS, color: NAVY })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200, line: 312 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 8 } },
          children: [
            run("屿光咖啡品控组　·　2026 年第 41 周（2026-10-05 至 2026-10-11）", {
              size: 21, font: SANS, color: MUTED,
            }),
          ],
        }),
        noticeBox,
        mainTable,
        sectionHeading("待补充事项清单（请填报人补齐）", { pageBreak: true }),
        para(
          [run("以下 6 项源数据中确无对应内容，未作推测填充，请填报人补齐后提交：", {})],
          { indent: { firstLine: 480 }, after: 100, keepNext: true }
        ),
        ...numberedList,
        signTable,
        para([run("")], { after: 0 }),
        new Paragraph({
          spacing: { line: 312, before: 240 },
          indent: { firstLine: 480 },
          alignment: AlignmentType.JUSTIFIED,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 6 } },
          children: [
            run(
              "补齐上述事项后，请同步删除正文表格中的【季度累计口径】与「待补充」标注，本表即可作为正式周报提交；" +
              "若周度数据尚未取得，建议改为提交第三季度工作总结，而非以季度口径材料充当周报。"
            ),
          ],
        }),
      ],
    },
  ],
});

const outDir = path.resolve(__dirname, "..", "out");
fs.mkdirSync(outDir, { recursive: true });
const outFile = path.join(outDir, "文书.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outFile, buf);
  console.log("written:", outFile, buf.length, "bytes");
});
