# -*- coding: utf-8 -*-
"""agent_checks.py — agent 角色包形态体检（对 v5/assets/acceptor-agent/package，WS9 新增）。

检查口径出处（写死，逐条留档；「国际通行」= 子代理定义通行三段式与 JSON Schema 习惯，
「registry」= 本仓冻结基线 v5/assets/acceptor-agent/oracle/expectations.json）：

- **国际通行（子代理/角色包定义惯例）**：一份可直接用作子代理 system prompt 的 agent
  定义，通行结构为三段式——职责（Responsibilities）/ 输出契约（Output Contract）/
  禁令（Prohibitions）；输出契约用 JSON Schema 习惯冻结字段、类型与 enum（type/enum/
  required/非空约束），示例文档（example）须能通过自身 schema 的机器校验。
- **registry（本仓冻结基线 v5/assets/acceptor-agent/oracle/expectations.json）**：
  agent_md_required_sections（职责/输出契约/禁令）、schema_required_top_fields（恰 5 顶层
  字段：verdict/deliverable_path/checks/blockers/boundary_note）、verdict_enum（PASS/FAIL）、
  check_item_required（name/passed/evidence/status）、check_status_enum（verified/judged）、
  agent_md_required_prohibition_phrases（「禁止修改」「禁止把未跑过的检查标 verified」）。
- **角色纪律（v5/assets/acceptor-agent/spec.md R1–R4）**：R1 PASS 当且仅当全 checks 过且
  blockers 空；R2 每条 check 必带 evidence、未跑禁标 verified；R3 boundary_note 必填、
  全文禁就业/收益承诺措辞；R4 缺失/矛盾 → FAIL + blocker 不猜测代答。

检查项（4 项，顺序即 report.json checks 顺序）：
  1. agent_md_sections       agent.md 三节齐备：required_sections 逐个能被标题行命中
                             （^#{1,6} 含关键词，中英括注均可）
  2. schema_fields_exact     字段恰等（集合恰等，非超集/子集）：schema/verdict.schema.json
                             顶层键集 == example-verdict.json 顶层键集 == 基线 5 字段；
                             example 每个 checks[] 项键集 == 基线 check_item_required；
                             verdict/status enum 与基线一致
  3. example_valid           example 合法：JSON 可解析，并按 schema 语义逐条校验
                             （类型/非空/min_items/enum）+ R1 推论（PASS ⇒ checks 全过
                             且 blockers 空）
  4. no_promise_wording      零承诺措辞：agent.md 基线禁令短语在文；就业/收益/薪资/
                             offer/高薪/稳赚/月入/包过/保过 等承诺关键词只允许出现在
                             边界声明或禁令句中（该行含 禁止/不得/不评/不做/不承诺/
                             承诺边界/boundary_note 之一），其余位置出现即红

实现说明：零模型调用、零第三方依赖（不引 jsonschema，schema 语义校验按基线口径内置
实现，可判定字段与 spec/expectations 一致）。
"""

import json
import os
import re

from . import common

FORM = "agent"
AGENT_MD = "agent.md"
SCHEMA_FILE = os.path.join("schema", "verdict.schema.json")
EXAMPLE_FILE = "example-verdict.json"
BASELINE_REL = ("..", "oracle", "expectations.json")

DEFAULT_SECTIONS = ("职责", "输出契约", "禁令")
DEFAULT_TOP_FIELDS = ("verdict", "deliverable_path", "checks", "blockers", "boundary_note")
DEFAULT_CHECK_ITEM = ("name", "passed", "evidence", "status")
DEFAULT_VERDICT_ENUM = ("PASS", "FAIL")
DEFAULT_STATUS_ENUM = ("verified", "judged")
DEFAULT_PROHIBITION_PHRASES = ("禁止修改", "禁止把未跑过的检查标 verified")

# 承诺类关键词（R3：全文禁就业/收益承诺措辞）；大小写不敏感匹配英文
PROMISE_KEYWORDS = ("就业", "收益", "薪资", "offer", "高薪", "稳赚", "月入", "包过", "保过")
# 承诺关键词的合法护栏（该行须含其一：本身是禁令或边界声明句）
GUARD_WORDS = ("禁止", "不得", "不评", "不做", "不承诺", "承诺边界", "boundary_note")

CHECK_NAMES = ("agent_md_sections", "schema_fields_exact", "example_valid", "no_promise_wording")

CRITERIA_NOTES = (
    "子代理定义通行三段式：职责（Responsibilities）/ 输出契约（Output Contract）/ 禁令"
    "（Prohibitions）；输出契约按 JSON Schema 习惯冻结字段与 enum。",
    "registry 冻结基线：v5/assets/acceptor-agent/oracle/expectations.json（三节名单、恰 5 顶层"
    "字段、verdict/status enum、check_item_required、禁令短语）。",
    "角色纪律：v5/assets/acceptor-agent/spec.md R1–R4（PASS 充要条件、evidence 纪律、"
    "boundary_note 必填与零承诺措辞、缺失即 FAIL）。",
)

ADVICE = {
    "agent_md_sections": "在 agent.md 补齐缺失小节标题（职责/输出契约/禁令，可带英文括注）。",
    "schema_fields_exact": "让 schema 与 example 的字段集恰等于基线 5 顶层字段（不多不少），checks[] 项键恰等 name/passed/evidence/status。",
    "example_valid": "按 checks 明细修 example-verdict.json（类型/非空/enum；PASS 须 checks 全过且 blockers 空）。",
    "no_promise_wording": "删除或改写 agent.md 中的承诺性表述；就业/收益等词只允许出现在禁令或 boundary_note 边界声明句中。",
}


# ------------------------------------------------------------------ 基线 ----

def load_baseline(target):
    """读冻结基线 <target>/../oracle/expectations.json；缺失返回 (None, 原因)。"""
    path = os.path.normpath(os.path.join(target, *BASELINE_REL))
    if not os.path.isfile(path):
        return None, "无冻结基线（%s 不存在）" % path
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, ValueError) as exc:
        return None, "冻结基线不可读: %s" % common.compress(str(exc))


def _baseline_or(baseline, key, default):
    if baseline is None:
        return list(default)
    value = baseline.get(key)
    return list(value) if value else list(default)


# ------------------------------------------------------------------ 检查项 ----

def check_agent_md_sections(target, baseline, base_note):
    """① agent.md 三节齐备。"""
    path = os.path.join(target, AGENT_MD)
    if not os.path.isfile(path):
        return False, "包根未找到 %s" % AGENT_MD
    text, err = common.read_text_flex(path)
    if text is None:
        return False, "%s 无法读取: %s" % (AGENT_MD, common.compress(err or ""))
    required = _baseline_or(baseline, "agent_md_required_sections", DEFAULT_SECTIONS)
    headings = re.findall(r"^#{1,6}\s*(.+?)\s*$", text, re.M)
    missing = [sec for sec in required
               if not any(sec in h for h in headings)]
    if missing:
        return False, "agent.md 缺小节（标题行未命中）: %s（现有标题: %s）" % (
            "; ".join(missing), " / ".join(headings) or "无")
    return True, ("agent.md 三节齐备（%s；命中标题: %s%s）"
                  % ("、".join(required),
                     " / ".join(h for h in headings if any(s in h for s in required)),
                     "" if baseline is not None else "｜%s，仅通行三段式口径" % base_note))


def check_schema_fields_exact(target, baseline, base_note):
    """② 字段恰等：schema 顶层键集 == example 顶层键集 == 基线 5 字段；item 键恰等。"""
    problems = []
    expected_top = _baseline_or(baseline, "schema_required_top_fields", DEFAULT_TOP_FIELDS)
    expected_item = _baseline_or(baseline, "check_item_required", DEFAULT_CHECK_ITEM)

    schema_path = os.path.join(target, SCHEMA_FILE)
    example_path = os.path.join(target, EXAMPLE_FILE)
    for rel, path in ((SCHEMA_FILE, schema_path), (EXAMPLE_FILE, example_path)):
        if not os.path.isfile(path):
            return False, "包根未找到 %s" % rel

    try:
        with open(schema_path, "r", encoding="utf-8-sig") as f:
            schema = json.load(f)
        with open(example_path, "r", encoding="utf-8-sig") as f:
            example = json.load(f)
    except (OSError, ValueError) as exc:
        return False, "schema/example 不是合法 JSON: %s" % common.compress(str(exc))

    schema_keys, example_keys = set(schema), set(example)
    if schema_keys != set(expected_top):
        problems.append("%s 顶层键集 %s ≠ 恰等要求 %s（缺 %s / 多 %s）"
                        % (SCHEMA_FILE, sorted(schema_keys), sorted(expected_top),
                           sorted(set(expected_top) - schema_keys),
                           sorted(schema_keys - set(expected_top))))
    if example_keys != set(expected_top):
        problems.append("%s 顶层键集 %s ≠ 恰等要求 %s（缺 %s / 多 %s）"
                        % (EXAMPLE_FILE, sorted(example_keys), sorted(expected_top),
                           sorted(set(expected_top) - example_keys),
                           sorted(example_keys - set(expected_top))))

    items = example.get("checks") if isinstance(example.get("checks"), list) else []
    for i, item in enumerate(items):
        keys = set(item) if isinstance(item, dict) else set()
        if keys != set(expected_item):
            problems.append("example checks[%d] 键集 %s ≠ 恰等要求 %s"
                            % (i, sorted(keys), sorted(expected_item)))

    def _enum_hit(field, base_key, default_enum, where):
        want = _baseline_or(baseline, base_key, default_enum)
        got = (schema.get(field) or {}).get("enum")
        if not isinstance(got, list) or set(want) != set(got):
            problems.append("%s %s enum %s ≠ 基线 %s" % (where, field, got, want))

    _enum_hit("verdict", "verdict_enum", DEFAULT_VERDICT_ENUM, SCHEMA_FILE)
    if "checks" in schema:
        # status enum 两种声明形态均识别：顶层扁平 schema["status"]["enum"]，
        # 或 checks 内嵌 schema["checks"]["status_enum"]（verdict.schema.json 实际形态）
        want = _baseline_or(baseline, "check_status_enum", DEFAULT_STATUS_ENUM)
        nested = (schema.get("checks") or {}).get("status_enum")
        flat = (schema.get("status") or {}).get("enum")
        got = nested if isinstance(nested, list) else flat
        if not isinstance(got, list) or set(want) != set(got):
            problems.append("%s checks 状态 enum %s ≠ 基线 %s" % (SCHEMA_FILE, got, want))

    if problems:
        return False, "字段恰等不过（%d 处）: %s" % (len(problems), "; ".join(problems))
    return True, ("字段恰等：schema 与 example 顶层键集恰等基线 5 字段 %s，checks[] 项键恰等 %s，"
                  "verdict/status enum 与基线一致%s"
                  % (sorted(expected_top), sorted(expected_item),
                     "" if baseline is not None else "｜%s" % base_note))


def validate_example(example, baseline):
    """example 语义校验（schema 口径内置实现）。返回问题列表（空 = 合法）。"""
    problems = []
    verdict_enum = _baseline_or(baseline, "verdict_enum", DEFAULT_VERDICT_ENUM)
    status_enum = _baseline_or(baseline, "check_status_enum", DEFAULT_STATUS_ENUM)

    verdict = example.get("verdict")
    if verdict not in verdict_enum:
        problems.append("verdict=%r 不在 enum %s" % (verdict, verdict_enum))
    path = example.get("deliverable_path")
    if not (isinstance(path, str) and path.strip()):
        problems.append("deliverable_path 须为非空字符串")
    checks = example.get("checks")
    if not (isinstance(checks, list) and len(checks) >= 1):
        problems.append("checks 须为非空数组（min_items=1）")
        checks = []
    for i, item in enumerate(checks):
        if not isinstance(item, dict):
            problems.append("checks[%d] 须为对象" % i)
            continue
        if not (isinstance(item.get("name"), str) and item["name"].strip()):
            problems.append("checks[%d].name 须为非空字符串" % i)
        if not isinstance(item.get("passed"), bool):
            problems.append("checks[%d].passed 须为布尔" % i)
        if not (isinstance(item.get("evidence"), str) and item["evidence"].strip()):
            problems.append("checks[%d].evidence 须为非空字符串（R2 证据纪律）" % i)
        if item.get("status") not in status_enum:
            problems.append("checks[%d].status=%r 不在 enum %s" % (i, item.get("status"), status_enum))
    blockers = example.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(b, str) for b in blockers):
        problems.append("blockers 须为字符串数组")
    note = example.get("boundary_note")
    if not (isinstance(note, str) and note.strip()):
        problems.append("boundary_note 须为非空字符串（R3 边界纪律）")

    # R1 推论：PASS 当且仅当 checks 全 passed 且 blockers 为空
    if verdict == "PASS":
        all_pass = bool(checks) and all(isinstance(c, dict) and c.get("passed") is True
                                        for c in checks)
        if not all_pass:
            problems.append("R1 违例：verdict=PASS 但存在未过 checks")
        if isinstance(blockers, list) and blockers:
            problems.append("R1 违例：verdict=PASS 但 blockers 非空 %s" % blockers)
    return problems


def check_example_valid(target, baseline, base_note):
    """③ example 合法：JSON 可解析 + schema 语义校验 + R1 推论。"""
    path = os.path.join(target, EXAMPLE_FILE)
    if not os.path.isfile(path):
        return False, "包根未找到 %s" % EXAMPLE_FILE
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            example = json.load(f)
    except (OSError, ValueError) as exc:
        return False, "%s 不是合法 JSON: %s" % (EXAMPLE_FILE, common.compress(str(exc)))
    if not isinstance(example, dict):
        return False, "%s 顶层须为 JSON 对象" % EXAMPLE_FILE
    problems = validate_example(example, baseline)
    if problems:
        return False, "example 校验不过（%d 处）: %s" % (len(problems), "; ".join(problems))
    blockers = example.get("blockers") or []
    return True, ("example 合法：verdict=%s，checks %d 条全带非空 evidence，blockers %s，"
                  "boundary_note 非空，R1 充要条件成立%s"
                  % (example.get("verdict"), len(example.get("checks") or []),
                     "为空" if not blockers else "= %d 项" % len(blockers),
                     "" if baseline is not None else "｜%s" % base_note))


def check_no_promise_wording(target, baseline, base_note):
    """④ 零承诺措辞：基线禁令短语在文；承诺关键词只出现在禁令/边界声明句中。"""
    path = os.path.join(target, AGENT_MD)
    if not os.path.isfile(path):
        return False, "包根未找到 %s" % AGENT_MD
    text, err = common.read_text_flex(path)
    if text is None:
        return False, "%s 无法读取: %s" % (AGENT_MD, common.compress(err or ""))
    problems, hits = [], []
    for no, line in enumerate(text.splitlines(), 1):
        lowered = line.lower()
        kws = [k for k in PROMISE_KEYWORDS if k.lower() in lowered]
        if not kws:
            continue
        if any(g in line for g in GUARD_WORDS):
            hits.append("L%d（%s，护栏: %s）" % (
                no, "/".join(kws), next(g for g in GUARD_WORDS if g in line)))
        else:
            problems.append("L%d 出现承诺关键词 %s 且无禁令/边界护栏"
                            % (no, "/".join(kws)))
    phrases = _baseline_or(baseline, "agent_md_required_prohibition_phrases",
                           DEFAULT_PROHIBITION_PHRASES)
    missing = [p for p in phrases if p not in text]
    if missing:
        problems.append("缺基线禁令短语: %s" % "; ".join(missing))
    if problems:
        return False, "零承诺措辞不过（%d 处）: %s" % (len(problems), "; ".join(problems))
    return True, ("零承诺措辞：基线禁令短语 %s 在文；承诺关键词仅出现在禁令/边界声明句（%s）%s"
                  % ("、".join(phrases), "; ".join(hits) or "全文未出现承诺关键词",
                     "" if baseline is not None else "｜%s" % base_note))


# ------------------------------------------------------------------ 组装 ----

def run_checks(target):
    """跑 agent 形态全部检查，返回 checks（顺序 = CHECK_NAMES）。"""
    checks = []
    baseline, base_err = load_baseline(target)
    base_note = base_err or "无冻结基线"

    ok, detail = check_agent_md_sections(target, baseline, base_note)
    common.add(checks, "agent_md_sections", ok, detail)
    ok, detail = check_schema_fields_exact(target, baseline, base_note)
    common.add(checks, "schema_fields_exact", ok, detail)
    ok, detail = check_example_valid(target, baseline, base_note)
    common.add(checks, "example_valid", ok, detail)
    ok, detail = check_no_promise_wording(target, baseline, base_note)
    common.add(checks, "no_promise_wording", ok, detail)

    assert [c["name"] for c in checks] == list(CHECK_NAMES), "检查项顺序被破坏"
    return checks
