// gen_doc.js — 青蘅茶社志愿组「冬季送暖协调会」会议通知生成器（模板字段驱动）
// 输入: qingheng_dongji.json（源数据，含历次活动遗留的杂项键）
// 输出: out/文书.docx（公文式会议通知，非红头）+ out/fields.json（字段台账 + 计数汇总）
// 运行: NODE_PATH=/tmp/docxgen/node_modules node gen_doc.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, Footer, PageNumber, LineRuleType,
} = require("docx");

const ROOT = __dirname;
const OUT = path.join(ROOT, "out");

// ---------- 会议通知模板字段（11 个；required 之外均为选填） ----------
// empty 取值含义（选填字段无值时的渲染语义）：
//   留空     → 标签保留，值渲染为空字符串
//   整节省略 → 不渲染节头与任何条目
const TEMPLATE_FIELDS = [
  { name: "会议名称", required: true, where: "标题及缘由段" },
  { name: "召开单位", required: true, where: "缘由段及落款" },
  { name: "主送对象", required: true, where: "主送行" },
  { name: "会议时间", required: true, where: "正文条目" },
  { name: "会议地点", required: true, where: "正文条目" },
  { name: "参会人员", required: true, where: "正文条目" },
  { name: "会议议题", required: false, where: "正文条目", empty: "留空" },
  { name: "会议要求", required: false, where: "正文条目", empty: "整节省略", list: true },
  { name: "联系人",   required: false, where: "正文条目", empty: "留空" },
  { name: "联系电话", required: false, where: "正文条目" },
  { name: "发文日期", required: true, where: "落款日期" },
];

const raw = JSON.parse(fs.readFileSync(path.join(ROOT, "qingheng_dongji.json"), "utf8"));

const has = (k) => Object.prototype.hasOwnProperty.call(raw, k);
const isEmptyValue = (v) =>
  v === null || v === undefined ||
  (typeof v === "string" && v.trim() === "") ||
  (Array.isArray(v) && v.length === 0);

// ---------- 字段台账 ----------
const records = TEMPLATE_FIELDS.map((f) => {
  const present = has(f.name);
  const value = present ? raw[f.name] : null;
  const filled = present && !isEmptyValue(value);
  const rec = {
    name: f.name,
    required: !!f.required,
    present_in_data: present,
    status: filled ? "filled" : "missing",
  };
  if (present) rec.value = value;
  if (filled) {
    rec.rendered_as = f.where;
  } else if (!present) {
    rec.missing_reason = "数据中无此键";
    rec.rendered_as = f.empty === "整节省略" ? "整节省略（不渲染节头与条目）" : "留空（渲染为空字符串）";
  } else if (Array.isArray(value)) {
    rec.missing_reason = "空数组（按缺失处理）";
    rec.rendered_as = "整节省略（不渲染节头与条目）";
  } else {
    rec.missing_reason = "空字符串（按缺失处理）";
    rec.rendered_as = "留空（渲染为空字符串）";
  }
  return rec;
});

// 杂项键 = 源数据中不属于模板字段的键，按 Unicode 码点序排列（Python sorted() 口径）
const codepointCompare = (a, b) => {
  const A = Array.from(a), B = Array.from(b);
  const n = Math.min(A.length, B.length);
  for (let i = 0; i < n; i++) {
    const d = A[i].codePointAt(0) - B[i].codePointAt(0);
    if (d !== 0) return d;
  }
  return A.length - B.length;
};
const templateNames = new Set(TEMPLATE_FIELDS.map((f) => f.name));
const unknownKeys = Object.keys(raw).filter((k) => !templateNames.has(k)).sort(codepointCompare);

const filledRecs = records.filter((r) => r.status === "filled");
const missingRecs = records.filter((r) => r.status === "missing");
const missingRequiredNames = missingRecs.filter((r) => r.required).map((r) => r.name);

// 计数口径自检
if (records.length !== 11 || filledRecs.length !== 8 || missingRecs.length !== 3 ||
    missingRequiredNames.length !== 0) {
  throw new Error("计数自检失败: " + JSON.stringify({
    total: records.length, filled: filledRecs.length, missing: missingRecs.length,
  }));
}

const title = `关于召开${raw["会议名称"]}的通知`;

const ledger = {
  template: "会议通知",
  data_file: "qingheng_dongji.json",
  document: "文书.docx",
  title,
  fields: records,
  summary: {
    total: records.length,
    filled: filledRecs.length,
    missing: missingRecs.length,
    missing_required: missingRequiredNames.length,
    missing_required_names: missingRequiredNames,
    unknown_count: unknownKeys.length,
    unknown_keys: unknownKeys,
    unknown_sort: "Unicode 码点序（Python sorted() 口径）",
  },
};

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, "fields.json"), JSON.stringify(ledger, null, 2) + "\n", "utf8");

// ---------- 公文版式（非红头，参照 GB/T 9704 字体与行距） ----------
const F_BODY  = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "FangSong" };
const F_TITLE = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "STXiaoBiaoSong" }; // 缺字体时退化为宋体加粗
const F_HEI   = { ascii: "Times New Roman", hAnsi: "Times New Roman", eastAsia: "SimHei" };

const LINE = { line: 560, lineRule: LineRuleType.EXACT }; // 固定 28 磅行距
const SIZE_BODY = 32;  // 三号 16pt
const INDENT2 = { firstLine: 640 }; // 首行缩进两字（16pt × 2）

const DOC_TEXTS = []; // 供泄入自检
const t = (text, extra = {}) => {
  DOC_TEXTS.push(text);
  return new TextRun(Object.assign({ text, font: F_BODY, size: SIZE_BODY }, extra));
};

const bodyP = (runs, opts = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  indent: opts.noIndent ? undefined : INDENT2,
  spacing: Object.assign({}, LINE, opts.spacing || {}),
  children: runs,
});

// 正文条目：按模板顺序渲染 7 个条目型字段；空值按 empty 语义处理
const ITEM_FIELDS = ["会议时间", "会议地点", "参会人员", "会议议题", "会议要求", "联系人", "联系电话"];
const CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
const itemParas = [];
let n = 0;
for (const name of ITEM_FIELDS) {
  const f = TEMPLATE_FIELDS.find((x) => x.name === name);
  const v = has(name) ? raw[name] : null;
  if (isEmptyValue(v)) {
    if (f.empty === "整节省略") continue; // 空数组：整节省略，不占条目序号
    itemParas.push(bodyP([t(`${CN_NUM[n]}、${name}：`, { font: F_HEI })])); // 留空：标签保留
    n += 1;
    continue;
  }
  if (Array.isArray(v)) { // 列表字段有值时：节头 + 逐条子项
    itemParas.push(bodyP([t(`${CN_NUM[n]}、${name}：`, { font: F_HEI })]));
    n += 1;
    v.forEach((s, i) => itemParas.push(bodyP([t(`（${CN_NUM[i]}）${s}`)])));
    continue;
  }
  itemParas.push(bodyP([t(`${CN_NUM[n]}、${name}：`, { font: F_HEI }), t(String(v))]));
  n += 1;
}

const children = [
  // 标题（发文机关事由文种式，语义完整不断行）
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: Object.assign({ before: 0, after: 560 }, LINE),
    children: [new TextRun({ text: title, font: F_TITLE, size: 44, bold: true })],
  }),
  // 主送对象
  bodyP([t(`${raw["主送对象"]}：`)], { noIndent: true }),
  // 缘由段
  bodyP([t(`为统筹做好冬季送暖活动各项筹备工作，${raw["召开单位"]}经研究，决定召开${raw["会议名称"]}。现将有关事项通知如下：`)]),
  // 通知事项
  ...itemParas,
  // 结语
  bodyP([t("特此通知。")]),
  // 落款：单位 + 成文日期（右空两字）
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

// ---------- 泄入自检：杂项键名/值与被省略节不得进入文书 ----------
const allText = DOC_TEXTS.join("\n");
for (const k of unknownKeys) {
  if (allText.includes(k)) throw new Error(`杂项键名泄入文书: ${k}`);
  const v = raw[k];
  if (typeof v === "string" && v !== "" && allText.includes(v)) throw new Error(`杂项键值泄入文书: ${v}`);
}
if (allText.includes("会议要求")) throw new Error("「会议要求」空数组应整节省略");

const doc = new Document({
  title,
  creator: raw["召开单位"],
  description: "会议通知（模板字段驱动生成）",
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
        margin: { top: 2098, bottom: 1984, left: 1588, right: 1474 }, // GB/T 9704 版心
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
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

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(OUT, "文书.docx"), buf);
  console.log(`OK out/文书.docx (${buf.length} bytes)`);
  const s = ledger.summary;
  console.log(`OK out/fields.json total=${s.total} filled=${s.filled} missing=${s.missing} missing_required=${s.missing_required} unknown=${s.unknown_count}`);
  console.log(`unknown_keys = ${JSON.stringify(s.unknown_keys)}`);
});
