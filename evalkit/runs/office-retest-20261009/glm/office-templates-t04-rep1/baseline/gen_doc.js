// gen_doc.js — 青蘅茶社志愿组「冬季送暖协调会」会议通知生成器
// 输入: qingheng_dongji.json（含历次活动遗留的杂项键，见 JUNK_KEYS）
// 输出: out/文书.docx（公文式会议通知）+ out/fields.json（过滤杂项键后的有效字段）
// 运行: NODE_PATH=/tmp/docxgen/node_modules node gen_doc.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, Footer, PageNumber, LineRuleType,
} = require("docx");

const ROOT = __dirname;
const OUT = path.join(ROOT, "out");

// 历次活动遗留的杂项键：只存在于源数据，不进入文书与 fields.json
const JUNK_KEYS = ["Zebra", "_private", "abc", "备用3", "📋备注"];

// 有效字段按文书逻辑顺序输出
const FIELD_ORDER = [
  "会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "参会人员",
  "会议议题", "会议要求", "1号议程", "附件编号", "联系电话", "发文日期",
];

const raw = JSON.parse(fs.readFileSync(path.join(ROOT, "qingheng_dongji.json"), "utf8"));

const unexpected = Object.keys(raw).filter(k => !FIELD_ORDER.includes(k) && !JUNK_KEYS.includes(k));
if (unexpected.length) throw new Error("源数据出现未登记的键: " + unexpected.join(", "));
const missing = FIELD_ORDER.filter(k => !(k in raw));
if (missing.length) throw new Error("源数据缺少有效字段: " + missing.join(", "));

const fields = {};
for (const k of FIELD_ORDER) fields[k] = raw[k];
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, "fields.json"), JSON.stringify(fields, null, 2) + "\n", "utf8");

// ---------- 公文版式（GB/T 9704 风格，非红头） ----------
const F_BODY  = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "FangSong" };
const F_TITLE = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "STXiaoBiaoSong" }; // 缺字体时退化为宋体加粗
const F_HEI   = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "SimHei" };

const LINE = { line: 560, lineRule: LineRuleType.EXACT }; // 固定 28 磅行距
const SIZE_BODY = 32;  // 三号 16pt
const INDENT2 = { firstLine: 640 }; // 首行缩进两字（16pt×2）

const bodyP = (runs, opts = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  indent: opts.noIndent ? undefined : INDENT2,
  spacing: Object.assign({}, LINE, opts.spacing || {}),
  children: runs,
});
const t = (text, extra = {}) => new TextRun(Object.assign({ text, font: F_BODY, size: SIZE_BODY }, extra));

// 会议议程：议题为空则略，「1号议程」并入议程项
const agendaItems = [raw["会议议题"], raw["1号议程"]].filter(s => typeof s === "string" && s.trim() !== "");
const agendaText = agendaItems.join("；");

const noticeItems = [
  ["会议时间", raw["会议时间"]],
  ["会议地点", raw["会议地点"]],
  ["参会人员", raw["参会人员"]],
  ["会议议程", agendaText],
  ["联系电话", raw["联系电话"]],
].filter(([, v]) => typeof v === "string" && v.trim() !== "");

const CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];

const children = [
  // 标题（发文机关 + 事由 + 文种，语义断行）
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: Object.assign({ before: 120, after: 560 }, LINE),
    children: [
      new TextRun({ text: raw["召开单位"], font: F_TITLE, size: 44, bold: true }),
      new TextRun({ text: `关于召开${raw["会议名称"]}的通知`, font: F_TITLE, size: 44, bold: true, break: 1 }),
    ],
  }),
  // 主送对象
  bodyP([t(`${raw["主送对象"]}：`)], { noIndent: true }),
  // 缘由段
  bodyP([t(`为切实做好冬季送暖各项工作，${raw["召开单位"]}经研究，决定召开${raw["会议名称"]}。现将有关事项通知如下：`)]),
  // 通知事项（条目引导词用黑体）
  ...noticeItems.map(([label, value], i) => bodyP([
    t(`${CN_NUM[i]}、${label}：`, { font: F_HEI, bold: true }),
    t(value),
  ])),
  // 结语
  bodyP([t("特此通知。")]),
  // 附件说明（仅有编号，无附件名，如实呈现）
  bodyP([t(`附件编号：${raw["附件编号"]}`)]),
  // 落款
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 640 },
    spacing: Object.assign({ before: 560 }, LINE),
    children: [t(raw["召开单位"])],
  }),
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 640 },
    spacing: LINE,
    children: [t(raw["发文日期"])],
  }),
];

const doc = new Document({
  title: `${raw["召开单位"]}关于召开${raw["会议名称"]}的通知`,
  creator: raw["召开单位"],
  styles: {
    default: {
      document: {
        run: { font: F_BODY, size: SIZE_BODY, color: "000000" },
        paragraph: { spacing: LINE },
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
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { line: 280, lineRule: LineRuleType.EXACT },
          children: [
            new TextRun({ text: "\u2014 ", font: F_BODY, size: 28 }),
            new TextRun({ children: [PageNumber.CURRENT], font: F_BODY, size: 28 }),
            new TextRun({ text: " \u2014", font: F_BODY, size: 28 }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(OUT, "文书.docx"), buf);
  console.log("OK out/文书.docx out/fields.json");
}).catch(err => { console.error(err); process.exit(1); });
