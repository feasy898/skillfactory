# office-templates ab4-invalid-input-rejection · baseline 臂

本臂自研一个文书生成入口，并对其施加四组非法输入 + 一组合法对照组 + 一组必填缺失补测，
逐组留证到 `run_log.json`。本臂未挂载任何技能包（见上级 `arms_manifest.json` 的
`baseline_has_skill: false`），入口完全由 `gen.py` 自行实现。

## 复现方式

```bash
python3 run_cases.py        # 从干净态跑完六组用例，写出 run_log.json，退出码 0 表示全通过
```

若要清空重跑：`rm -rf out .scratch run_log.json && python3 run_cases.py`。

## 生成入口

```
python3 gen.py --template <模板名> --data <JSON 数据文件> [--outdir <输出根目录，默认 out>]
```

* 可用模板：周报、月报、会议纪要。**「证书」不在登记表内**，用作模板名非法探针。
* 成功：退出码 0，产物 `out/<模板名>/<数据文件名>/文书.docx` 与 `fields.json`。
* 非法输入：退出码 **2**，中文错误信息走 stderr，**在校验全部通过前不碰文件系统**。
* 字段缺失**不算非法**：缺失字段按「（未填写）」占位，正常出文书、退出码 0。

拒绝的四类输入依次是：模板名非法 → 数据文件不存在/非普通文件 → JSON 解析失败 →
JSON 顶层非对象。`fields.json` 落盘走「写同目录临时文件 + `os.replace`」，
因此中途失败也不会留下半成品。

## 产物布局

```
brief.md                      任务书（给定）
gen.py                        生成入口（自研）
run_cases.py                  用例执行器
fixtures/周报/case1.json      合法对照组输入（给定）
invalid_inputs/
  not-json.txt                ③ 输入，内容「不是JSON」
  top-level-array.json        ④ 输入，内容 ["数组", "非对象"]
extra_inputs/
  missing-required.json       补测输入：缺 周期/下周工作计划/问题与需协调事项
run_log.json                  逐组留证（命令/退出码/stderr 摘要/残留检查/判定）
out/周报/case1/文书.docx       合法对照组产物
out/周报/case1/fields.json    合法对照组产物
```

② 号输入（`invalid_inputs/does-not-exist.json`）刻意不存在于盘上，因此没有对应文件。

## 残留检查口径

执行器在每次调用前后对臂目录做递归快照，取差集作为「本次调用创建的路径」。
`fixtures/`、`invalid_inputs/`、`extra_inputs/` 与脚本自身视为执行前既有，不计入残留；
`.scratch/` 计入，这样补测组的产物能被看见。四组非法输入的差集均为空集。

补测组（必填缺失）用 `--outdir .scratch/missing-required` 改写出图位置，
以免在任务书约定的 `out/周报/case1/` 之外留下多余目录；该目录在记录进 `run_log.json`
之后由执行器删除（`summary.scratch_cleaned` 为证）。

## 本轮结论

`run_log.json` 的 `summary` 六项全绿：四组非法输入全部退出码 2、全部有中文 stderr、
全部零残留；合法对照组退出码 0 且 `文书.docx`（37,024 字节、可被 zipfile 打开、
正文七个字段齐全）与 `fields.json` 两产物齐备；必填缺失未被误拒，缺失字段占位落盘。

## 环境说明

依赖 `python-docx`。`gen.py` 在 `import docx` 失败时会自动把
`~/.local/lib/python3.*/site-packages` 追加进 `sys.path` 后重试，
因此在 user site 被禁用的 venv 解释器（`/home/pan-ding/venvs/ml/bin/python3`）下也能跑；
`/usr/bin/python3` 则原生可用。`run_log.json` 的 `interpreter` 字段记录了实际使用的解释器路径。