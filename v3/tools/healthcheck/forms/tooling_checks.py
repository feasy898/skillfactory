# -*- coding: utf-8 -*-
"""tooling_checks.py — 工具类技能形态体检（对 hotwords / deploy-pack / speaker-mapping，
WS9 新增；target = 各资产的 package/ 目录）。

检查口径出处（写死，逐条留档；「国际通行」= skill 包 front-matter 通行口径与确定性评测
红绿纪律，「registry」= 本仓 REGISTRY ④裁 + 各资产冻结契约）：

- **国际通行（skill 包 front-matter 惯例）**：技能包根 SKILL.md 以 `---` front-matter 起
  始，`name` 与 `description` 是通行必填的两要素（name 唯一标识、description 触发语境）；
  解析口径与本仓 spec.md §3 R4 一致（行级 `key: value`，非完整 YAML，utf-8-sig 优先回退
  gbk）。
- **国际通行（CLI 可执行与确定性评测纪律）**：CLI 工具以 `--help` smoke 为最小可执行口径
  （argparse 通行约定，exit 0 + 用法文本）；评测采本仓 v3 healthcheck spec.md R6/R8 的
  确定性纪律——资产级 eval runner 绿态（自评 oracle/out oracle/out）exit 0、红态（空目录
  fail-closed）exit 1，两态缺一不可（只绿不红 = 评测器可能恒真；只红不绿 = 资产本身不过）。
- **registry（REGISTRY.md 2026-10-08 ④裁体检形态豁免注记）**：hotwords / deploy-pack /
  speaker-mapping 三件在旧 5 项 skill 口径下的失分属形态错配（该三件 SKILL.md front-matter
  只有 name/description，无 version/license/permissions），按 ④裁豁免且留档。本形态据此
  放宽为 name/description 两字段非空，**豁免注记写进每份报告 detail**（不等于免检）。

检查项（3 项，顺序即 report.json checks 顺序）：
  1. cli_executable          CLI 可执行：登记工具类的每个 CLI 入口 `python <cli> --help`
                             exit 0 且用法文本非空（cwd=package，单次确定性调用）
  2. eval_runner_red_green   eval 资产级 runner 红绿两态：<asset>/eval/runner.py 存在；
                             绿态 `python eval/runner.py oracle/out oracle/out`（cwd=asset
                             根）exit 0；红态被测根=空临时目录 exit 1（fail-closed）
  3. skill_md_fields_relaxed SKILL.md 字段完整性（放宽口径）：front-matter name+description
                             非空；detail 恒附 REGISTRY ④裁豁免注记（version/license/
                             permissions 不作要求，留档）

登记工具类（TOOL_CLASS_REGISTRY，按主 CLI 探测）：hotwords（hotwords.py）、
deploy-pack（gen_deploy.py + validate.py）、speaker-mapping（map_speakers.py）；
未登记包回退通用口径（包根顶层 *.py 全部 --help smoke，detail 注明未登记）。
"""

import json
import os
import shutil
import tempfile

from . import common

FORM = "tooling"
SKILL_MD = "SKILL.md"
EXEMPTION_NOTE = ("豁免注记（REGISTRY.md 2026-10-08 ④裁体检形态豁免）：工具类技能在旧 5 项 "
                  "skill 口径下失分属形态错配；本形态放宽为 name/description 两字段非空，"
                  "version/license/permissions 不作要求（留档备查，不等于免检）")

# 登记工具类：detect = 探测用主 CLI（存在即认定该类）；cli = 全部须 --help smoke 的入口
TOOL_CLASS_REGISTRY = (
    {"name": "hotwords", "detect": "hotwords.py", "cli": ("hotwords.py",)},
    {"name": "deploy-pack", "detect": "gen_deploy.py", "cli": ("gen_deploy.py", "validate.py")},
    {"name": "speaker-mapping", "detect": "map_speakers.py", "cli": ("map_speakers.py",)},
)

CHECK_NAMES = ("cli_executable", "eval_runner_red_green", "skill_md_fields_relaxed")

CRITERIA_NOTES = (
    "skill 包 front-matter 通行口径：SKILL.md 以 --- 块起始，name/description 为通行必填"
    "两要素；解析同本仓 v3 spec.md §3 R4（行级 key: value，非完整 YAML）。",
    "确定性评测红绿纪律：本仓 v3/tools/healthcheck/spec.md R6/R8——单次确定性调用，"
    "绿态 exit 0 + 红态 fail-closed exit 1 两态缺一不可。",
    "registry 豁免：REGISTRY.md 2026-10-08 ④裁体检形态豁免注记——hotwords/deploy-pack/"
    "speaker-mapping 三件旧 5 项失分为形态错配，放宽口径并逐报告留档豁免注记。",
)

ADVICE = {
    "cli_executable": "按 checks 明细修复 CLI（--help 应 exit 0 并打印用法；登记工具类入口清单见 forms/tooling_checks.py TOOL_CLASS_REGISTRY）。",
    "eval_runner_red_green": "建立 <asset>/eval/runner.py 并保证两态：python eval/runner.py oracle/out oracle/out → exit 0；被测根为空目录 → exit 1（fail-closed）。",
    "skill_md_fields_relaxed": "在 SKILL.md front-matter 补齐 name/description（工具类放宽口径；version/license/permissions 豁免但留档）。",
}


# ------------------------------------------------------------------ 工具类 ----

def detect_tool_class(target):
    """按主 CLI 探测登记工具类；未登记返回 (None, 顶层 *.py 清单)。"""
    for entry in TOOL_CLASS_REGISTRY:
        if os.path.isfile(os.path.join(target, entry["detect"])):
            return entry, None
    top_py = sorted(fn for fn in os.listdir(target)
                    if fn.endswith(".py") and os.path.isfile(os.path.join(target, fn)))
    return None, top_py


# ------------------------------------------------------------------ 检查项 ----

def check_cli_executable(target, entry, fallback_py):
    """① CLI 可执行：登记类每个入口 --help exit 0 且用法非空；未登记类走通用口径。"""
    if entry is None:
        if not fallback_py:
            return False, ("未识别登记工具类（%s）且包根无顶层 *.py CLI"
                           % "/".join(e["name"] for e in TOOL_CLASS_REGISTRY))
        clis, label = fallback_py, "未登记工具类（通用口径：包根顶层 *.py 逐个 --help）"
    else:
        clis, label = list(entry["cli"]), "登记工具类 %s" % entry["name"]

    fails, oks = [], []
    for cli in clis:
        if not os.path.isfile(os.path.join(target, cli)):
            fails.append("%s 不存在" % cli)
            continue
        r = common.run_cmd(["python", cli, "--help"], cwd=target, timeout=60)
        if r["timed_out"]:
            fails.append("%s --help 超时" % cli)
        elif r["returncode"] != 0:
            fails.append("%s --help exit=%s stderr: %s"
                         % (cli, r["returncode"], common.compress(r["stderr"])))
        elif not (r["stdout"] or "").strip():
            fails.append("%s --help stdout 为空（无用法文本）" % cli)
        else:
            oks.append("%s --help exit=0（%d 字节用法）" % (cli, len(r["stdout"])))
    if fails:
        return False, "CLI 可执行不过（%d/%d）: %s" % (len(fails), len(clis), "; ".join(fails))
    return True, "%s：%s" % (label, "; ".join(oks))


def check_eval_runner_red_green(target):
    """② eval 资产级 runner 红绿两态（绿 0 / 红 1，fail-closed）。"""
    asset_root = os.path.normpath(os.path.join(target, ".."))
    runner = os.path.join(asset_root, "eval", "runner.py")
    oracle_out = os.path.join(asset_root, "oracle", "out")
    if not os.path.isfile(runner):
        return False, "资产级 eval runner 缺失（%s）" % os.path.relpath(runner, asset_root)
    if not os.path.isdir(oracle_out):
        return False, "参照产物缺失（%s），无法定绿" % os.path.relpath(oracle_out, asset_root)

    green = common.run_cmd(["python", "eval/runner.py", "oracle/out", "oracle/out"],
                           cwd=asset_root, timeout=common.SUBPROC_TIMEOUT)
    red_dir = tempfile.mkdtemp(prefix="ws9-red-")
    try:
        red = common.run_cmd(["python", "eval/runner.py", red_dir, "oracle/out"],
                             cwd=asset_root, timeout=common.SUBPROC_TIMEOUT)
    finally:
        shutil.rmtree(red_dir, ignore_errors=True)

    problems = []
    if green["timed_out"]:
        problems.append("绿态超时（>%ds）" % common.SUBPROC_TIMEOUT)
    elif green["returncode"] != 0:
        problems.append("绿态 exit=%s ≠ 0（自评 oracle/out oracle/out）stderr: %s"
                        % (green["returncode"], common.compress(green["stderr"])))
    if red["timed_out"]:
        problems.append("红态超时（>%ds）" % common.SUBPROC_TIMEOUT)
    elif red["returncode"] != 1:
        problems.append("红态 exit=%s ≠ 1（空目录应 fail-closed）stdout: %s"
                        % (red["returncode"], common.compress(red["stdout"])))
    if problems:
        return False, "红绿两态不过（%d 处）: %s" % (len(problems), "; ".join(problems))
    return True, ("红绿两态成立：绿态 exit=0（python eval/runner.py oracle/out oracle/out，"
                  "stdout 摘要: %s）；红态 exit=1（被测根=空临时目录，fail-closed，stdout 摘要: %s）"
                  % (common.compress(green["stdout"]) or "<空>",
                     common.compress(red["stdout"]) or "<空>"))


def check_skill_md_fields_relaxed(target):
    """③ SKILL.md 字段完整性（工具类放宽口径 + 豁免注记恒留档）。"""
    path = os.path.join(target, SKILL_MD)
    if not os.path.isfile(path):
        return False, "包根未找到 %s｜%s" % (SKILL_MD, EXEMPTION_NOTE)
    text, err = common.read_text_flex(path)
    if text is None:
        return False, "%s 无法读取: %s｜%s" % (SKILL_MD, common.compress(err or ""), EXEMPTION_NOTE)
    fields, reason = common.parse_front_matter(text)
    if fields is None:
        return False, "%s front-matter 不过: %s｜%s" % (SKILL_MD, reason, EXEMPTION_NOTE)
    missing = [k for k in ("name", "description") if not fields.get(k)]
    if missing:
        return False, "front-matter 缺放宽口径字段: %s（已有: %s）｜%s" % (
            ", ".join(missing),
            ", ".join(k for k in ("name", "description") if fields.get(k)) or "无",
            EXEMPTION_NOTE)
    return True, ("front-matter 放宽口径字段齐备：name=%s、description 非空（%d 字符）｜%s"
                  % (fields["name"], len(fields["description"]), EXEMPTION_NOTE))


# ------------------------------------------------------------------ 组装 ----

def run_checks(target):
    """跑 tooling 形态全部检查，返回 checks（顺序 = CHECK_NAMES）。"""
    checks = []
    entry, fallback_py = detect_tool_class(target)

    ok, detail = check_cli_executable(target, entry, fallback_py)
    common.add(checks, "cli_executable", ok, detail)
    ok, detail = check_eval_runner_red_green(target)
    common.add(checks, "eval_runner_red_green", ok, detail)
    ok, detail = check_skill_md_fields_relaxed(target)
    common.add(checks, "skill_md_fields_relaxed", ok, detail)

    assert [c["name"] for c in checks] == list(CHECK_NAMES), "检查项顺序被破坏"
    return checks
