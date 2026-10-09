/*
 * 青蘅茶社《秋季会员茶话会》会议通知生成器（baseline rep3）
 *
 * 版式依据：GB/T 9704—2012 党政机关公文格式的常规要素（非红头）——
 *   A4，上 3.7cm / 下 3.5cm / 左 2.8cm / 右 2.6cm；
 *   标题 2 号小标宋（缺字体环境回退加粗）居中；主送顶格全角冒号；
 *   正文 3 号仿宋，固定 28 磅行距，首行缩进两字；一级条目标签 3 号黑体；
 *   西文与数字 Times New Roman；成文日期右空四字、署名居其上居中；
 *   页码「— X —」4 号居中于版心下。
 *
 * fields.json —— 字段记账（template / title / fields / summary）。
 *
 * 缺数据不编造：必填缺失以 ____ 占位；选填缺失省略条目；记账如实。
 */
const {
  Document, Packer, Paragraph, TextRun, Footer, PageNumber,
  AlignmentType, LineRuleType,
} = require("docx");
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "qingheng_teahui.json");
const OUTDIR = path.join(__dirname, "out");

const F_XBS = "STXiaoBiaoSong";   // 标题：华文小标宋（回退宋体加粗）
const F_FS = "FangSong";          // 正文：仿宋
const F_HEI = "SimHei";           // 一级条目标签：黑体
const F_SONG = "SimSun";          // 页码：宋体
const F_ASCII = "Times New Roman";// 西文 / 数字

const SZ_TITLE = 44;  // 2 号（22pt，半点单位）
const SZ_BODY = 32;   // 3 号（16pt）
const SZ_PAGE = 28;   // 4 号（14pt）
const LINE_BODY = 560;     // 固定 28 磅（twips，atLeast 规则下两种渲染引擎同为 28 磅）
const INDENT2 = 640;       // 首行缩进两字（3 号字 2×320）
const DATE_RIGHT = 1280;   // 成文日期右空四字（4×320）

const data = JSON.parse(fs.readFileSync(SRC, "utf8"));
const clean = (v) => (typeof v === "string" ? v.trim() : v);
const g = {};
for (const k of ["会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
  "参会人员", "会议议题", "联系人", "联系电话", "发文日期"]) {
  const raw = data[k];
  g[k] = raw === undefined || raw === null || String(raw).trim() === "" ? null : clean(raw);
}
const reqs = Array.isArray(data["会议要求"])
  ? data["会议要求"].map(clean).filter((s) => s && String(s).trim() !== "")
  : [];

const fontFS = { ascii: F_ASCII, eastAsia: F_FS };
const fontHEI = { ascii: F_ASCII, eastAsia: F_HEI };

// 正文段：3 号仿宋，两字缩进，28 磅行距
function body(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: INDENT2 },
    spacing: { line: LINE_BODY, lineRule: LineRuleType.AT_LEAST,
      before: opts.before || 0, after: opts.after || 0 },
    keepNext: opts.keepNext || undefined,
    keepLines: true,
    children: runs,
  });
}
const fsRun = (text, opts = {}) => new TextRun({ text, size: SZ_BODY, color: "000000", font: fontFS, ...opts });
const heiRun = (text) => new TextRun({ text, size: SZ_BODY, color: "000000", font: fontHEI });

const title = (g["召开单位"] || "____") + "关于召开" + (g["会议名称"] || "____") + "的通知";

/* ---------------- 文书.docx ---------------- */
const children = [];

// 标题：2 号小标宋居中（回退加粗），行距 atLeast 防 substituted 字体削顶
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { line: 620, lineRule: LineRuleType.AT_LEAST, before: 0, after: 440 },
  keepNext: true,
  children: [new TextRun({ text: title, size: SZ_TITLE, bold: true, color: "000000",
    font: { ascii: F_ASCII, eastAsia: F_XBS } })],
}));

// 主送对象：顶格，全角冒号
children.push(body([fsRun((g["主送对象"] || "____") + "：")], { noIndent: true, keepNext: true }));

// 导语（缘由 + 时间地点点名 + 过渡语）
const intro = "为通报秋季茶会流程安排、预告冬至茶会有关事宜，"
  + (g["召开单位"] || "____") + "定于" + (g["会议时间"] || "____")
  + "在" + (g["会议地点"] || "____") + "召开" + (g["会议名称"] || "____")
  + "。现将有关事项通知如下：";
children.push(body([fsRun(intro)], { keepNext: true }));

// 一级条目（标签黑体、值仿宋）
const itemDefs = [
  ["一、会议时间：", g["会议时间"]],
  ["二、会议地点：", g["会议地点"]],
  ["三、参会人员：", g["参会人员"]],
  ["四、会议议题：", g["会议议题"]],
];
for (const [label, value] of itemDefs) {
  children.push(body([heiRun(label), fsRun(value === null ? "____" : value)], { keepNext: true }));
}

// 五、会议要求：（一）—（N）逐条；原文末尾无标点，依次补「；」，末条补「。」
children.push(body([heiRun("五、会议要求：")], { keepNext: true }));
reqs.forEach((r, i) => {
  const tail = i === reqs.length - 1 ? "。" : "；";
  children.push(body([fsRun("（" + "一二三四五六七八九十"[i] + "）" + r + tail)], { keepNext: true }));
});

children.push(body([heiRun("六、联系人："), fsRun(g["联系人"] === null ? "____" : g["联系人"])], { keepNext: true }));
children.push(body([heiRun("七、联系电话："), fsRun(g["联系电话"] === null ? "____" : g["联系电话"])], { keepNext: true }));

// 结束语
children.push(body([fsRun("特此通知。")], { keepNext: true }));

// 落款：成文日期右空四字，署名以成文日期为准居中于其上
//   日期宽约 2080 twips（TNR 数字半宽），其半 1040，署名半宽 640 → 署名右缩进 1280+1040-640=1680
const orgWidth = ((g["召开单位"] || "____").length) * 320;
const SIGN_RIGHT = DATE_RIGHT + 1040 - orgWidth / 2;
children.push(new Paragraph({
  alignment: AlignmentType.RIGHT,
  indent: { right: Math.round(SIGN_RIGHT) },
  spacing: { line: LINE_BODY, lineRule: LineRuleType.AT_LEAST, before: 400, after: 0 },
  keepNext: true, keepLines: true,
  children: [fsRun(g["召开单位"] || "____")],
}));
children.push(new Paragraph({
  alignment: AlignmentType.RIGHT,
  indent: { right: DATE_RIGHT },
  spacing: { line: LINE_BODY, lineRule: LineRuleType.AT_LEAST, before: 0, after: 0 },
  keepLines: true,
  children: [fsRun(g["发文日期"] || "____")],
}));

const doc = new Document({
  title: title,
  creator: g["召开单位"] || "青蘅茶社",
  styles: {
    default: {
      document: {
        run: { font: fontFS, size: SZ_BODY, color: "000000" },
        paragraph: { spacing: { line: LINE_BODY, lineRule: LineRuleType.AT_LEAST } },
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
          spacing: { line: 340, lineRule: LineRuleType.AT_LEAST },
          children: [
            new TextRun({ text: "\u2014 ", size: SZ_PAGE, font: { ascii: F_ASCII, eastAsia: F_SONG } }),
            new TextRun({ children: [PageNumber.CURRENT], size: SZ_PAGE, font: { ascii: F_ASCII, eastAsia: F_SONG } }),
            new TextRun({ text: " \u2014", size: SZ_PAGE, font: { ascii: F_ASCII, eastAsia: F_SONG } }),
          ],
        })],
      }),
    },
    children,
  }],
});

/* ---------------- fields.json ---------------- */
const CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
const note = {
  "会议名称": "标题「{召开单位}关于召开{会议名称}的通知」组成部分＋导语「召开……」点名",
  "召开单位": "标题组成部分＋导语「{召开单位}定于……」点名＋文末落款署名（以成文日期为准居中排布于其上方）",
  "主送对象": "版心首行顶格主送（后加全角冒号）",
  "会议时间": "正文条目「一、会议时间：…」＋导语点名（黑体标签＋仿宋值，数字以 Times New Roman 呈现）",
  "会议地点": "正文条目「二、会议地点：…」＋导语点名（黑体标签＋仿宋值）",
  "参会人员": "正文条目「三、参会人员：…」（黑体标签＋仿宋值）",
  "会议议题": "正文条目「四、会议议题：…」（黑体标签＋仿宋值）；源数据首尾各含一个半角空格，已按公文排版规范剔除后渲染，值记剔除后文本",
  "联系人": "正文条目「六、联系人：…」（黑体标签＋仿宋值）",
  "联系电话": "正文条目「七、联系电话：…」（黑体标签＋仿宋值，数字与连字符以 Times New Roman 呈现）",
  "发文日期": "文末落款成文日期行（右空四字，署名居中于其上；依 GB/T 9704—2012 成文日期采用阿拉伯数字，与源数据一致）",
};
const REQUIRED = new Set(["会议名称", "召开单位", "主送对象", "会议时间", "会议地点", "会议议题", "发文日期"]);

const fieldNames = ["会议名称", "召开单位", "主送对象", "会议时间", "会议地点",
  "参会人员", "会议议题", "联系人", "联系电话", "发文日期"];
const fields = [];
for (const name of fieldNames) {
  const v = g[name];
  fields.push({
    "名称": name,
    "是否必填": REQUIRED.has(name),
    "状态": v === null ? "missing" : "filled",
    "值": v,
    "渲染方式": v === null ? "必填缺失以 ____ 占位" : note[name],
  });
}
fields.splice(7, 0, {
  "名称": "会议要求",
  "是否必填": false,
  "状态": reqs.length ? "filled" : "missing",
  "值": reqs.length ? reqs : null,
  "渲染方式": "正文条目「五、会议要求：」下（" + CN_NUM[0] + "）—（" + CN_NUM[Math.min(reqs.length, 10) - 1] + "）逐条列出（仿宋，首行缩进两字）；条目原文末尾无标点，按公文列表规范依次补「；」，末条补「。」",
});
const filled = fields.filter((f) => f["状态"] === "filled").length;
const fieldsJson = {
  "template": "会议通知",
  "title": title,
  "fields": fields,
  "summary": { "filled": filled, "missing": fields.length - filled, "total": fields.length },
};

/* ---------------- 写盘 ---------------- */
fs.mkdirSync(OUTDIR, { recursive: true });
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(OUTDIR, "文书.docx"), buf);
  fs.writeFileSync(path.join(OUTDIR, "fields.json"),
    JSON.stringify(fieldsJson, null, 2) + "\n");
  console.log("OK: out/文书.docx + out/fields.json");
});
