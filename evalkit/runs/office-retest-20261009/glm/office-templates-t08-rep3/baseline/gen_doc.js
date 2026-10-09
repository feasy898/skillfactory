// 工作总结 文书生成（GB/T 9704 红头格式）
// 数据源: data/工作总结/case1-overflow.json -> out/文书.docx + out/fields.json
const {
  Document, Packer, Paragraph, TextRun,
  AlignmentType, HeadingLevel, BorderStyle,
} = require("/tmp/docxwork/node_modules/docx");
const fs = require("fs");
const path = require("path");

const BASE = __dirname;
const dataPath = path.join(BASE, "data", "工作总结", "case1-overflow.json");
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

// undefined/null/空串防线（common-rules 强制）
function safeText(v, ph) {
  if (v === undefined || v === null || v === "" || String(v) === "NaN" || String(v) === "undefined") {
    return ph || "【待填写】";
  }
  return String(v);
}

// —— 字段取值（忠实数据，不编造） ——
const org = safeText(data["总结主体"], "【总结主体】");
const period = safeText(data["总结时段"], "【总结时段】");
const review = Array.isArray(data["工作回顾"]) ? data["工作回顾"] : [];
const achievements = Array.isArray(data["主要成绩"]) ? data["主要成绩"] : [];
const problems = Array.isArray(data["存在问题"]) ? data["存在问题"] : [];
const plans = Array.isArray(data["下一步工作打算"]) ? data["下一步工作打算"] : [];
const dateStr = safeText(data["成文日期"], "【成文日期】");

// —— 公共构件 ——
const F_BODY = { ascii: "Times New Roman", eastAsia: "FangSong" };   // 仿宋三号
const F_HEI = { ascii: "Times New Roman", eastAsia: "SimHei" };      // 黑体三号
const F_SONG = { ascii: "Times New Roman", eastAsia: "SimSun" };     // 小标宋替代：宋体加粗

// 正文段（仿宋三号，两字缩进，两端对齐，固定 28 磅行距）
function body(text, extra = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 640 },
    spacing: { line: 560, lineRule: "exact", ...(extra.spacing || {}) },
    children: [new TextRun({ text, font: F_BODY, size: 32, color: "000000" })],
  });
}

// 一级标题（黑体三号，左空二字）
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    indent: { firstLine: 640 },
    spacing: { before: 0, after: 0, line: 560, lineRule: "exact" },
    children: [new TextRun({ text, font: F_HEI, size: 32, bold: true, color: "000000" })],
  });
}

// 列表项成段（多条时用（一）（二）…，单条直接成段；句末补句号）
function items(paras) {
  if (paras.length <= 1) {
    return paras.length === 1 ? [body(paras[0].replace(/。?$/, "。"))] : [];
  }
  const cn = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
  return paras.map((p, i) => body(`（${cn[i]}）${p.replace(/。?$/, "。")}`));
}

const children = [
  // 红头：发文机关标志（红色小标宋，居中）
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 100, line: 640, lineRule: "atLeast" },
    children: [new TextRun({ text: `${org}文件`, font: F_SONG, size: 52, bold: true, color: "FF0000" })],
  }),
  // 红色分隔线（段落下边框实现，禁用字符线）
  new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: "FF0000" } },
    spacing: { before: 0, after: 480, line: 60, lineRule: "exact" },
    children: [],
  }),
  // 标题（二号小标宋替代：宋体加粗，居中）
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 360, after: 480, line: 720, lineRule: "atLeast" },
    children: [new TextRun({ text: `${org}${period.replace(/\s+/g, "")}工作总结`, font: F_SONG, size: 44, bold: true, color: "000000" })],
  }),
  // 导语（不新增事实，仅衔接）
  body(`${period.replace(/\s+/g, "")}，${org}围绕网关灰度切换推进各项工作，现将本月工作情况总结如下：`),
  // 一、工作回顾
  h1("一、工作回顾"),
  ...items(review),
  // 二、主要成绩
  h1("二、主要成绩"),
  ...items(achievements),
  // 三、存在问题
  h1("三、存在问题"),
  ...items(problems),
  // 四、下一步工作打算
  h1("四、下一步工作打算"),
  ...items(plans),
  // 落款：署名 + 成文日期（右对齐，署名相对日期居中）
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 880 },
    spacing: { before: 1120, line: 560, lineRule: "exact" },
    children: [new TextRun({ text: org, font: F_BODY, size: 32, color: "000000" })],
  }),
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 640 },
    spacing: { line: 560, lineRule: "exact" },
    children: [new TextRun({ text: dateStr, font: F_BODY, size: 32, color: "000000" })],
  }),
  // 盖章位置预留（不伪造公章印迹，仅标注盖章处）
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    indent: { right: 640 },
    spacing: { before: 240, line: 560, lineRule: "exact" },
    children: [new TextRun({ text: "（此处加盖公章）", font: F_BODY, size: 32, color: "000000" })],
  }),
];

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: F_BODY, size: 32, color: "000000" },
        paragraph: { spacing: { line: 560, lineRule: "exact" } },
      },
      heading1: {
        run: { font: F_HEI, size: 32, bold: true, color: "000000" },
        paragraph: { spacing: { before: 0, after: 0, line: 560, lineRule: "exact" } },
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
      children,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const outDocx = path.join(BASE, "out", "文书.docx");
  fs.writeFileSync(outDocx, buf);
  console.log("WROTE", outDocx, buf.length, "bytes");
});

// 台账 fields.json：数据字段原样 + 用户新增「审批人」「密级」（值未提供，留空待填）
const ledger = {
  ...data,
  "审批人": "",
  "密级": "",
};
const outFields = path.join(BASE, "out", "fields.json");
fs.writeFileSync(outFields, JSON.stringify(ledger, null, 2) + "\n", "utf8");
console.log("WROTE", outFields);
