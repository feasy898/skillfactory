#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness/doc_consistency.py — 文档↔工具输出一致性常设门（SF-0003 缺陷③，TESTS D4/MT-2）。

被测：资产包 SKILL.md 里 apply 步骤的 stderr INFO 行示例 ↔ 工具（package/map_speakers.py）
实测 stderr 的 INFO 行。占位符归一后逐段同构才过。

归一规则（全部对称作用于两侧，无单侧放水）：
  1) 剥可选的程序名前缀 `[map_speakers.py] `（文档表格单元格引用的是消息本体，不含壳前缀）；
  2) `\\`→`/` 路径分隔符对称归一（EI-13 既有口径；Windows 下 str(Path) 会把 / 归一成 \\）；
  3) 数字占位：`共 \\d+ 行`→`共 N 行`、`替换标签 \\d+ 处`→`替换标签 X 处`、
     `未映射标签 \\d+ 种`→`未映射标签 Y 种`；
  4) 文件占位：`写出 out/\\S+（`→`写出 out/<file>（`。

工具实跑纪律：只在系统临时 scratch 目录运行（写转录稿/映射/产物全在 scratch 内），
资产树只读；oracle 零接触（TESTS 0.3-7）。

用法：
    python doc_consistency.py --asset <资产 package 目录>          # 一致 → exit 0
    python doc_consistency.py --asset <目录> --selfcheck           # 附带变异自检（MT-2 阳性对照）：
        #   临时删文档 INFO 行的两处「标签」→ 比对必须 exit 1 → 字节级复原（sha256 校验）→ 复跑比对。
退出码：0 一致（--selfcheck 下含变异阶段如预期红）/ 1 不一致或变异阶段未如预期 / 2 用法或装置错误。
"""

import argparse
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile

CANON = "INFO: 写出 out/<file>（共 N 行，替换标签 X 处，未映射标签 Y 种）"


def canonical(line):
    """占位符归一（见模块 docstring 四条规则）。返回归一后的串；不匹配 INFO 形态返回 None。"""
    if line is None:
        return None
    s = line.strip().rstrip("\r\n")
    s = re.sub(r"^\[[^\]]+\]\s*", "", s)          # 1) 剥程序名前缀
    s = s.replace("\\", "/")                       # 2) 分隔符对称归一
    s = re.sub(r"共 \d+ 行", "共 N 行", s)          # 3) 数字占位
    s = re.sub(r"替换标签 \d+ 处", "替换标签 X 处", s)
    s = re.sub(r"未映射标签 \d+ 种", "未映射标签 Y 种", s)
    s = re.sub(r"写出 out/\S+?（", "写出 out/<file>（", s)   # 4) 文件占位
    return s if "INFO: 写出" in s else None


def doc_template(skill_path):
    """取 SKILL.md 中含 `INFO: 写出` 的行（backtick 内的模板本体）。恰一行才合法。"""
    text = io.open(skill_path, encoding="utf-8", errors="strict").read()
    hits = [l for l in text.splitlines() if "INFO: 写出" in l]
    if len(hits) != 1:
        return None, "SKILL.md 含 'INFO: 写出' 的行数=%d（应为恰 1）" % len(hits)
    m = re.search(r"`([^`]*INFO: 写出[^`]*)`", hits[0])
    if not m:
        return None, "INFO 模板未包在 backtick 内: %r" % hits[0][:120]
    return m.group(1), None


def run_tool_info(asset_dir, scratch):
    """scratch 内实跑资产工具一次 apply，取 stderr 的 INFO 行。资产树只读。"""
    tool = os.path.join(asset_dir, "map_speakers.py")
    if not os.path.isfile(tool):
        return None, "资产工具不存在: %s" % tool
    t_txt = os.path.join(scratch, "T.txt")
    m_json = os.path.join(scratch, "M.json")
    o_txt = os.path.join(scratch, "out", "O.txt")
    os.makedirs(os.path.dirname(o_txt), exist_ok=True)  # package 版工具不自动建父目录（与 oracle 版差异，实测）
    with io.open(t_txt, "w", encoding="utf-8", newline="\n") as f:
        f.write("[00:00:01] SPEAKER_00: 第一句。\n[00:00:02] SPEAKER_01: 第二句。\n")
    with io.open(m_json, "w", encoding="utf-8", newline="\n") as f:
        f.write('{"SPEAKER_00": "王总"}\n')  # SPEAKER_01 留空 → 未映射标签 1 种
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(
        [sys.executable, tool, "--transcript", "T.txt", "--mapping", "M.json", "--out", "out/O.txt"],
        cwd=scratch, capture_output=True, env=env, timeout=60)
    err = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        return None, "工具退出码=%d stderr=%r" % (p.returncode, err[:200])
    infos = [l for l in err.splitlines() if "INFO: 写出" in l]
    if len(infos) != 1:
        return None, "stderr INFO 行数=%d（应为恰 1）: %r" % (len(infos), err[:300])
    return infos[0], None


def compare(asset_dir):
    """主比对：文档模板归一 == 工具实测归一 == CANON。返回 (ok, detail)。"""
    skill = os.path.join(asset_dir, "SKILL.md")
    if not os.path.isfile(skill):
        return False, "SKILL.md 不存在: %s" % skill
    tmpl, err = doc_template(skill)
    if err:
        return False, err
    with tempfile.TemporaryDirectory(prefix="doc-consistency-") as scratch:
        actual, err = run_tool_info(asset_dir, scratch)
        if err:
            return False, err
    c_t, c_a = canonical(tmpl), canonical(actual)
    if c_t != CANON:
        return False, "文档模板归一形态偏离: %r（期望 %r）" % (c_t, CANON)
    if c_a != CANON:
        return False, "工具实测归一形态偏离: %r（期望 %r）" % (c_a, CANON)
    return True, "文档模板与工具实测 stderr 占位符归一后逐段同构: %r" % c_a


def selfcheck(asset_dir):
    """变异自检（MT-2）：删「标签」×2 → 比对必须失败 → 字节复原（sha256 校验）→ 复跑必须过。"""
    skill = os.path.join(asset_dir, "SKILL.md")
    backup = open(skill, "rb").read()
    sha_before = hashlib.sha256(backup).hexdigest()
    mutated = backup.replace("替换标签 X 处，未映射标签 Y 种".encode("utf-8"),
                             "替换 X 处，未映射 Y 种".encode("utf-8"))
    if mutated == backup:
        return False, "变异未生效（找不到目标文本）"
    try:
        open(skill, "wb").write(mutated)
        ok_bad, detail_bad = compare(asset_dir)
        if ok_bad:
            return False, "变异后比对仍绿（阳性对照失败，门是恒真门）: %s" % detail_bad
    finally:
        open(skill, "wb").write(backup)
    restored = open(skill, "rb").read()
    if hashlib.sha256(restored).hexdigest() != sha_before:
        return False, "复原失败：sha256 不等（资产被变异残留污染，立即人工介入）"
    ok_again, detail = compare(asset_dir)
    if not ok_again:
        return False, "复原后比对未回绿: %s" % detail
    return True, "变异红→复原绿 双向成立；资产字节复原 sha256 校验过"


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--asset", default=None, help="资产 package 目录（含 SKILL.md 与 map_speakers.py）")
    ap.add_argument("--selfcheck", action="store_true", help="附带变异自检（临时改文档后字节复原）")
    args = ap.parse_args(argv)
    if not args.asset or not os.path.isdir(args.asset):
        print("用法: python doc_consistency.py --asset <资产 package 目录> [--selfcheck]", file=sys.stderr)
        return 2
    ok, detail = compare(args.asset)
    print("比对: %s | %s" % ("PASS" if ok else "FAIL", detail))
    if args.selfcheck:
        ok2, detail2 = selfcheck(args.asset)
        print("变异自检: %s | %s" % ("PASS" if ok2 else "FAIL", detail2))
        ok = ok and ok2
    return 0 if ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
