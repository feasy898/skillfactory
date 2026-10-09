// 青蘅茶社志愿组 冬季送暖协调会 会议通知生成
// 输入：qingheng_dongji.json（含历次活动遗留杂项键）
// 输出：out/文书.docx + out/fields.json
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Footer,
  AlignmentType, PageNumber,
} = require("docx");

const BASE = __dirname;
const OUT_DIR = path.join(BASE, "out");
const src = JSON.parse(fs.readFileSync(path.join(BASE, "qingheng_dongji.json"), "utf8"));

// ---------- 字段清洗 ----------
// 历次活动遗留的杂项键：不进入文书、不进入 fields.json
const junkKeys = ["Zebra", "_private", "abc", "备用3", "📋备注"];

// 议题聚合：主字段（字符串，可为空）+ 编号议程键（1号议程、2号议程…）
const agenda = [];
if (typeof src["会议议题"] === "string" && src["会议议题"].trim()) {
  agenda.push(src["会议议题"].trim());
}
for (let i = 1; src[`${i}号议程`] != null; i++) {
  const v = String(src[`${i}号议程`]).trim();
  if (v) agenda.push(v);
}
// 会议要求为空数组：整节省略，不渲染空段

const fields = {
  "会议名称": src["会议名称"],
  "召开单位": src["召开单位"],
  "主送对象": src["主送对象"],
  "会议时间": src["会议时间"],
  "会议地点": src["会议地点"],
  "参会人员": src["参会人员"],
  ...(agenda.length ? { "会议议题": agenda } : {}),
  "联系电话": src["联系电话"],
  "附件编号": src["附件编号"],
  "发文日期": src["发文日期"],
};

// ---------- 版式常量（GB/T 9704 公文口径）----------
const F_BODY = { ascii: "Times New Roman", eastAsia: "FangSong" };
const F_TITLE = { ascii: "Times New Roman", eastAsia: "SimSun" }; // 小标宋缺失时退化为宋体加粗
const SZ_BODY = 32;   // 三号 16pt
const SZ_TITLE = 44;  // 二号 22pt
const SZ_PAGE = 28;   // 四号 14pt
const LINE = { line: 560, lineRule: "exact" }; // 固定 28pt 行距
const INDENT2 = { firstLine: 640 };            // 三号字两字符缩进

function bodyRun(text, extra = {}) {
  return new TextRun({ text, size: SZ_BODY, font: F_BODY, color: "000000", ...extra });
}
function bodyPara(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    indent: opts.indent,
    children: [bodyRun(text)],
  });
}

// ---------- 正文事项 ----------
const cnNum = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
const items = [
  `会议时间：${fields["会议时间"]}`,
  `会议地点：${fields["会议地点"]}`,
  `参会人员：${fields["参会人员"]}`,
  ...(agenda.length ? [`会议议题：${agenda.join("；")}`] : []),
  `联系电话：${fields["联系电话"]}`,
];

// ---------- 文书 ----------
const doc = new Document({
  creator: fields["召开单位"],
  title: `${fields["召开单位"]}关于召开${fields["会议名称"]}的通知`,
  description: "会议通知",
  styles: {
    default: {
      document: {
        run: { font: F_BODY, size: SZ_BODY, color: "000000" },
        paragraph: { spacing: LINE },
      },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 2098, bottom: 1984, left: 1588, right: 1474 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "— ", size: SZ_PAGE, font: F_BODY, color: "000000" }),
            new TextRun({ children: [PageNumber.CURRENT], size: SZ_PAGE, font: F_BODY, color: "000000" }),
            new TextRun({ text: " —", size: SZ_PAGE, font: F_BODY, color: "000000" }),
          ],
        })],
      }),
    },
    children: [
      // 标题（超一行，按语义断行：发文机关 / 事由+文种）
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 120, after: 560, ...LINE },
        children: [
          new TextRun({ text: fields["召开单位"], bold: true, size: SZ_TITLE, font: F_TITLE, color: "000000" }),
          new TextRun({
            text: `关于召开${fields["会议名称"]}的通知`,
            bold: true, size: SZ_TITLE, font: F_TITLE, color: "000000", break: 1,
          }),
        ],
      }),
      // 主送对象
      bodyPara(`${fields["主送对象"]}：`, { align: AlignmentType.LEFT }),
      // 缘由与引语
      bodyPara(
        `为做好冬季送暖活动各项筹备与协调工作，经研究，决定召开${fields["会议名称"]}。现将有关事项通知如下：`,
        { indent: INDENT2 },
      ),
      // 事项条目
      ...items.map((t, i) => bodyPara(`${cnNum[i]}、${t}`, { indent: INDENT2 })),
      // 结束语
      bodyPara("特此通知。", { indent: INDENT2 }),
      // 附件编号（正文之后、落款之前）
      bodyPara(`附件编号：${fields["附件编号"]}`, { indent: INDENT2 }),
      // 落款：署名右空二字，成文日期与之右对齐
      bodyPara(fields["召开单位"], { align: AlignmentType.RIGHT, indent: { right: 640 } }),
      bodyPara(fields["发文日期"], { align: AlignmentType.RIGHT, indent: { right: 640 } }),
    ],
  }],
});

// ---------- 落盘 ----------
fs.mkdirSync(OUT_DIR, { recursive: true });
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(OUT_DIR, "文书.docx"), buf);
  fs.writeFileSync(path.join(OUT_DIR, "fields.json"), JSON.stringify(fields, null, 2) + "\n", "utf8");
  console.log("OK out/文书.docx + out/fields.json");
  console.log("议题来源键: 会议议题=\"" + String(src["会议议题"]) + "\" + 编号议程x" +
    agenda.length + " →", JSON.stringify(agenda));
  console.log("已剔除杂项键:", junkKeys.join(", "));
  console.log("会议要求为空，整节省略");
});
