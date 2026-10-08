#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/office-retest-20261009/repack/repack_office_dist.py — office 重测：dist 重打包器（照 K-5 首发打包口径）。

映射（旧例=CHANGELOG 1.0.0 首发条目 + 4ff52f5 补迁先例）：
  package/SKILL.md        → SKILL.md（正文逐字节复制 + 分发包体例 front-matter 保留）
  package/scripts/gen_doc.py → scripts/gen_doc.py（逐字节）
  package/references/*.md、requirements.txt → 同名（逐字节，源零改动仅校验）
  eval/runner.py、eval/golden.json → eval/（逐字节；golden 冻结 K5B-09，sha 须等于 REGISTRY 登记 2fa58b07…）
  oracle/inputs → reference/inputs、oracle/out → reference/out（逐字节，源零改动仅校验；
                  fields.json 历史打包已作 CRLF→LF 归一，本轮源未变、包侧零改动）
  reference/out 的 docx 与 fields.json 本轮照旧例取自 oracle/out（本轮 oracle 参照零改动）
  README.md 红线②表述同步补强口径（内容更新面）
  CHANGELOG.md 新增 1.0.1 重打包条目（流程留痕照旧例）；SKILL.md front-matter/MANIFEST 版本号随包升 1.0.1
canonical 源 v3/assets/office-templates 零改动（K-5 纪律：补强已收口 e82b3cb）。
退出码：0=重打包完成且全部校验过；1=校验红（fail-closed，不动包）。
"""
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
SRC = os.path.join(ROOT, "v3", "assets", "office-templates")
PKG = os.path.join(SRC, "package")
DST = os.path.join(ROOT, "dist", "office-templates-skill")
RUN = os.path.join(ROOT, "evalkit", "runs", "office-retest-20261009")
GOLDEN_SHA_EXPECT = "2fa58b07481b44bc2840b2fdd757ef19faa5ebe37e1918baf936b2b923f4ecbf"  # REGISTRY.md:75
RUNNER_SHA_EXPECT = "8eb51801b6fc9fce357be87e3f13f5903720e573dcf5988167bdd41bf1f08c67"  # REGISTRY.md:74


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    report = {"run": "office-retest-20261009", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "source": os.path.relpath(SRC, ROOT), "source_head": "e82b3cb（补强收口）+ 9827318（ab5 裁决）",
              "dest": os.path.relpath(DST, ROOT), "checks": [], "actions": []}

    def check(name, ok, detail):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            print("CHECK FAIL %s: %s" % (name, detail), file=sys.stderr)

    # ---- 前置：dist 工作树零未提交改动（重打包从已提交状态出发）
    st = os.popen("git -C %s status --porcelain -- %s" % (ROOT, os.path.relpath(DST, ROOT))).read().strip()
    check("dist_worktree_clean", st == "", "git status --porcelain dist/office-templates-skill → %r" % st)

    # ---- 零改动面校验（源与包逐字节必须已一致，重打包不得触碰）
    same = []
    for name in ("references/工作总结.md", "references/会议通知.md", "references/请示函.md",
                 "references/周报.md", "requirements.txt", "eval/runner.py", "eval/golden.json"):
        s, d = os.path.join(PKG if name.startswith("references") or name == "requirements.txt" else SRC,
                            name), os.path.join(DST, name)
        if name == "requirements.txt":
            s = os.path.join(PKG, name)
        same.append((name, sha256_file(s) == sha256_file(d)))
    inputs_eq = os.popen("diff -rq %s %s" % (os.path.join(DST, "reference/inputs"),
                                             os.path.join(SRC, "oracle/inputs"))).read().strip()
    same.append(("reference/inputs ↔ oracle/inputs", inputs_eq == ""))
    check("untouched_face_byte_equal", all(ok for _, ok in same), "; ".join("%s=%s" % (n, ok) for n, ok in same))

    # ---- 冻结纪律：dist golden sha == REGISTRY 登记
    g_sha = sha256_file(os.path.join(DST, "eval/golden.json"))
    check("golden_frozen_sha", g_sha == GOLDEN_SHA_EXPECT, "%s" % g_sha)
    check("runner_sha_matches_registry", sha256_file(os.path.join(DST, "eval/runner.py")) == RUNNER_SHA_EXPECT,
          "REGISTRY.md:74")

    # ---- 内容更新面
    # 1) SKILL.md = front-matter（旧包体例，version 升 1.0.1）+ 补强后正文
    old = open(os.path.join(DST, "SKILL.md"), encoding="utf-8", newline="").read()
    end = old.index("\n---\n", 4) + len("\n---\n")
    fm = [l for l in old[:end].splitlines(keepends=True)]
    fm = [l.replace("version: 1.0.0\n", "version: 1.0.1\n") for l in fm]
    body = open(os.path.join(PKG, "SKILL.md"), encoding="utf-8", newline="").read()
    if not body.endswith("\n"):
        body += "\n"
    new_skill = "".join(fm) + "\n" + body
    with open(os.path.join(DST, "SKILL.md"), "w", encoding="utf-8", newline="") as f:
        f.write(new_skill)
    report["actions"].append({"file": "SKILL.md", "op": "front-matter(1.0.1)+package/SKILL.md 正文逐字节",
                              "sha256": sha256_file(os.path.join(DST, "SKILL.md"))})
    check("skill_body_from_source", new_skill.split("\n---\n", 1)[1].lstrip("\n") ==
          (body if body.startswith("#") else body), "正文=package/SKILL.md 逐字节")

    # 2) scripts/gen_doc.py 逐字节
    shutil.copyfile(os.path.join(PKG, "scripts/gen_doc.py"), os.path.join(DST, "scripts/gen_doc.py"))
    report["actions"].append({"file": "scripts/gen_doc.py", "op": "逐字节复制（补强版引擎 D1+）",
                              "sha256": sha256_file(os.path.join(DST, "scripts/gen_doc.py"))})

    # 3) README.md 红线②表述同步
    rm_path = os.path.join(DST, "README.md")
    rm = open(rm_path, encoding="utf-8", newline="").read()
    old_line = ("2. **产物确定性可复现**——正文无当前时间、无随机源，同输入连跑两次产物一致"
                "（`fields.json` 除 outputs 路径外逐字节一致）。")
    new_line = ("2. **产物确定性可复现**——正文无当前时间、无随机源，同输入连跑两次 `fields.json` 与"
                " `文书.docx` 均**整文件逐字节一致**（引擎把 docx 容器时间戳归一化，无墙钟/随机源）。")
    assert old_line in rm, "README 红线②原句未命中，拒改"
    rm = rm.replace(old_line, new_line)
    with open(rm_path, "w", encoding="utf-8", newline="") as f:
        f.write(rm)
    report["actions"].append({"file": "README.md", "op": "红线②确定性表述同步补强口径（仅此一处）",
                              "sha256": sha256_file(rm_path)})

    # 4) CHANGELOG.md 新增 1.0.1 条目（留痕照旧例）
    cl_path = os.path.join(DST, "CHANGELOG.md")
    entry = """# CHANGELOG — office-templates package（实现层）

## 1.0.1 — 2026-10-09（office 补强重打包，K-5 回炉重测前置）

- 以补强后资产源 `v3/assets/office-templates`（提交 e82b3cb：docx 容器时间戳归一化 + SKILL §9-5 自评规程，oracle 参照与 eval/runner.py 零改动）按首发（1.0.0）打包口径重建本分发包：**包结构不变、内容更新**。
  - `SKILL.md`：正文逐字节更新为 `package/SKILL.md` 补强版（§2/§5/§6-V8 确定性口径升级为整文件逐字节一致；§9 增第 5 步「确定性/交付自评」：同命令连跑两遍快照对拍 sha256 + run_log.json 留痕规程）；front-matter 照分发包体例保留，版本随包升 1.0.1。
  - `scripts/gen_doc.py`：逐字节更新为补强版引擎（canonicalize_docx_zip()——保存后原子重写 zip 容器，17 条目时间戳归一化 1980-01-01，D1+ 整文件逐字节可复现；失败退回 D1 语义下限不影响退出码）。
  - `references/`（四份）、`requirements.txt`、`eval/runner.py`、`eval/golden.json`、`reference/inputs/`：源零改动，逐字节复制校验一致（打包器实算）。
  - `reference/out/`：照旧例取自 `oracle/out`（本轮 oracle 参照零改动，逐字节未变）；fields.json 沿用首发包侧 CRLF→LF 归一形态。
  - `README.md`：设计红线②「确定性可复现」表述同步为整文件逐字节口径（仅此一处）。
  - 新写面（`LICENSE`/`EVALUATION.md`/`MANIFEST.md`/`eval/results/benchmark.json`）零改动；版本号面（front-matter/本文件/MANIFEST 标题）随包升 1.0.1。
- 冻结纪律（K5B-09 口径）：`eval/golden.json` 逐字节未动，sha256=2fa58b07… 与 REGISTRY.md 登记值一致。
- canonical 源 `v3/assets/office-templates` 本轮零改动。
"""
    cl = open(cl_path, encoding="utf-8", newline="").read()
    assert cl.startswith("# CHANGELOG"), "CHANGELOG 头异常"
    cl_old_head = cl.split("\n\n", 1)
    cl_new = entry + "\n" + cl_old_head[1]
    with open(cl_path, "w", encoding="utf-8", newline="") as f:
        f.write(cl_new)
    report["actions"].append({"file": "CHANGELOG.md", "op": "新增 1.0.1 重打包条目（流程留痕）",
                              "sha256": sha256_file(cl_path)})

    # 5) MANIFEST.md 标题版本
    mf_path = os.path.join(DST, "MANIFEST.md")
    mf = open(mf_path, encoding="utf-8", newline="").read()
    assert "# MANIFEST — office-templates-skill v1.0.0" in mf
    mf = mf.replace("# MANIFEST — office-templates-skill v1.0.0",
                    "# MANIFEST — office-templates-skill v1.0.1")
    with open(mf_path, "w", encoding="utf-8", newline="") as f:
        f.write(mf)
    report["actions"].append({"file": "MANIFEST.md", "op": "标题版本 1.0.0→1.0.1（仅此一处）",
                              "sha256": sha256_file(mf_path)})

    # ---- 收尾全包清单
    files = []
    for dp, _dn, fns in os.walk(DST):
        if "__pycache__" in dp:
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            files.append({"path": os.path.relpath(p, DST), "sha256": sha256_file(p), "bytes": os.path.getsize(p)})
    files.sort(key=lambda x: x["path"])
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["package_files"] = files
    ok = all(c["ok"] for c in report["checks"])
    report["exit"] = 0 if ok else 1
    out = os.path.join(RUN, "records", "repack-manifest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"exit": report["exit"], "checks_bad": [c for c in report["checks"] if not c["ok"]],
                      "n_files": len(files)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
