# 预演（probe）：生成引擎原始输出的确定性实测

目的：在正式两遍运行前，实测 `gen_doc.py --template 会议通知` 原始产物在
同输入、不同时刻连跑两遍时的逐字节差异，定位全部不可复现源。

## 预演方法

- 输入：`fixtures/会议通知/case1.json`（与正式运行同一份，原样）
- 第 1 遍：`--outdir records/probe/run1`；间隔 3 秒后第 2 遍：`--outdir records/probe/run2`
- 解释器：`.venv/bin/python`（python-docx 1.2.0）；两遍仅输出目录不同、生成时刻不同

## 实测结果

### fields.json

两遍差异恰 1 处（第 2377 字节，第 109 行）——`outputs` 键中的产物路径
（`records/probe/run1/...` vs `records/probe/run2/...`）。
除 `outputs` 类路径键外逐字节一致；正式两遍使用同一 `--outdir`，
故该键亦同值，全文件逐字节一致（正式结论见 `run_log.json`）。

### 文书.docx

| 项 | 结果 |
|---|---|
| 文件大小 | 37200 字节，两遍相等 |
| zip 成员清单 | 17 个成员，名称与顺序完全相同 |
| 全部成员内容 | **逐字节相同**（每成员 CRC、压缩大小逐一相等，含 word/document.xml 等全部 XML 部件） |
| 差异字节总数 | 37200 字节中恰 **34 字节** |
| 差异字节取值 | 每处均为 `0x57` vs `0x59`（本次实测 17:50:46 → 17:50:50，DOS 时间秒位 23→25） |
| 差异定位 | 17 个 zip 条目 ×（本地文件头 + 中央目录）各 1 字节时间戳秒位，共 17×2=34 处 |

两遍原始 sha256（因含保存时刻时间戳而必然互不相同）：

```
89283885e50f822ccb51b292a7f341dedd972004fdb3da290390a47978bdb2e0  run1/文书.docx
8c40ae53f2040bcd5660a1a54f32d84d101af52b07ae234ac48ea66b2cdbde8d  run2/文书.docx
```

## 归因（源码级）

`python-docx 1.2.0` `docx/opc/phys_pkg.py` `_ZipPkgWriter.write` 调
`self._zipf.writestr(pack_uri.membername, blob)`（字符串文件名）；
CPython `zipfile.ZipFile.writestr` 对字符串文件名以
`ZipInfo(filename, date_time=time.localtime(time.time())[:6])` 构造条目，
把**保存时刻的本地时间**写入每个条目的 DOS 时间戳（秒粒度 2 秒）。
文档内容（全部 XML 部件）完全由输入数据推导，无任何时间/随机源。

## 处置

正式管线（`run_case.py`）在每遍生成后对 `文书.docx` 做规范化重打包：
条目顺序/名称/压缩方式/内容字节保持不变，仅将全部条目时间戳固定为
`1980-01-01 00:00:00`（可复现构建标准做法），两遍处理完全相同，
从而消除该唯一不可复现源，使两遍产物逐字节一致。
