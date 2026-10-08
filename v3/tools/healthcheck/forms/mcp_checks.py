# -*- coding: utf-8 -*-
"""mcp_checks.py — MCP server 形态体检（对 v5/assets/zctl-mcp/package，WS9 新增）。

检查口径出处（写死，逐条留档；「国际通行」= MCP 官方规范，「registry」= 本仓冻结基线）：

- **国际通行（MCP 规范，modelcontextprotocol.io，Specification revision 2024-11-05）**：
  MCP stdio server 采用换行分隔 JSON-RPC 2.0；``initialize`` 应答含 ``protocolVersion``、
  ``capabilities``、``serverInfo{name, version}``；``tools/list`` 应答 ``tools[]``（每项
  name/description/inputSchema）；``tools/call`` 未知工具 → JSON-RPC -32602；未知方法
  → -32601；解析错 → -32700。zctl-mcp 实现即按此口径（package/mcp-server.mjs 头注）。
- **registry（本仓冻结基线 v5/assets/zctl-mcp/oracle/expected_tools.json）**：
  serverInfo name/version、protocolVersion、4 个只读工具的名称/顺序/inputSchema.required/
  description 关键词（description_contains），以及 forbidden_tool_names
  （zctl_reset_use / zctl_offpeak_take / zctl_offpeak_settle——变更类命令不得在 MCP 侧暴露）。
- **安全口径（上游 zctl 纪律，v5/assets/zctl-mcp/spec.md R1 + INSTALL.md 安全说明）**：
  变更类操作（reset use / offpeak take / settle）默认 dry-run 须 --yes，MCP server 侧
  直接不开放——本形态把「无变更类越权暴露」列为独立红绿项。

检查项（5 项，顺序即 report.json checks 顺序）：
  1. mcp_server_parsable     mcp-server.mjs 存在且 ``node --check`` 语法解析通过
  2. server_info_identity    initialize 实测：serverInfo name/version 与冻结基线一致
                             （无基线时降级为非空校验并在 detail 注明口径）
  3. tools_decl_match_impl   tools/list 实测 与 源码 TOOLS 声明 与 冻结基线 三方一致：
                             名称+顺序、inputSchema.required、description_contains 关键词；
                             且每个声明工具在源码 zctlArgs 有分派分支（声明=实现）
  4. no_mutation_exposure    无变更类越权暴露：forbidden_tool_names 不出现、每个工具
                             description 自带「只读」声明、源码无变更类 zctl 子命令接线
                             （"reset","use" / "offpeak","take" / "settle" / 独立 "--yes" 参数）
  5. install_md_complete     INSTALL.md 完备：Node 版本要求 / mcpServers 配置片段
                             （command+args 指向 mcp-server.mjs）/ 自检入口（eval/runner.py）/
                             安全说明（变更类不提供 MCP 入口）

实现说明：零模型调用；探针为单次确定性 stdio 调用（本模块每个 target 只 spawn 一次
node 子进程，同请求重复运行结果恒定）；mcp-server.mjs 只读工具不落盘、不改仓内文件。
"""

import json
import os
import re
import shutil
import subprocess
import threading

from . import common

FORM = "mcp"
SERVER_FILE = "mcp-server.mjs"
INSTALL_FILE = "INSTALL.md"
BASELINE_REL = ("..", "oracle", "expected_tools.json")
PROBE_TIMEOUT_SEC = 15
MUTATION_PATTERNS = (
    (r'["\']reset["\']\s*,\s*["\']use["\']', 'zctl 变更类接线 "reset","use"'),
    (r'["\']offpeak["\']\s*,\s*["\']take["\']', 'zctl 变更类接线 "offpeak","take"'),
    (r'["\']settle["\']', 'zctl 变更类接线 "settle"'),
    (r'["\']--yes["\']', '独立参数元素 "--yes"（变更确认旗标）'),
)
DEFAULT_FORBIDDEN = ("zctl_reset_use", "zctl_offpeak_take", "zctl_offpeak_settle")

CHECK_NAMES = ("mcp_server_parsable", "server_info_identity",
               "tools_decl_match_impl", "no_mutation_exposure", "install_md_complete")

CRITERIA_NOTES = (
    "MCP 官方规范 modelcontextprotocol.io（revision 2024-11-05）：JSON-RPC 2.0 换行分隔、"
    "initialize 应答 serverInfo{name,version}、tools/list、tools/call 错误码 -32602/-32601/-32700。",
    "registry 冻结基线：v5/assets/zctl-mcp/oracle/expected_tools.json（serverInfo / 4 只读工具 / "
    "inputSchema_required / description_contains / forbidden_tool_names）。",
    "安全口径：上游 zctl 纪律——变更类命令默认 dry-run 须 --yes；MCP 侧不提供变更类入口"
    "（v5/assets/zctl-mcp/spec.md R1、package/INSTALL.md 安全说明）。",
)

ADVICE = {
    "mcp_server_parsable": "修复 mcp-server.mjs 语法错误（本地复验：node --check mcp-server.mjs）；确认环境有 Node ≥18。",
    "server_info_identity": "对齐 initialize 应答的 serverInfo{name,version} 与 oracle/expected_tools.json 冻结值（zctl-mcp / 1.0.0）。",
    "tools_decl_match_impl": "让 tools/list 实测、源码 TOOLS 声明、oracle/expected_tools.json 三方一致（名称/顺序/required/描述关键词），每个声明工具补齐 zctlArgs 分派分支。",
    "no_mutation_exposure": "删除任何变更类工具或 zctl 变更类子命令接线（reset use / offpeak take / settle / --yes）；只读声明写进每个工具 description。",
    "install_md_complete": "按 checks 明细补 INSTALL.md：Node ≥18 前置、mcpServers 配置片段、eval/runner.py 自检入口、变更类不提供 MCP 入口的安全说明。",
}


# ------------------------------------------------------------------ 基线 ----

def load_baseline(target):
    """读冻结基线 <target>/../oracle/expected_tools.json；缺失返回 (None, 原因)。"""
    path = os.path.normpath(os.path.join(target, *BASELINE_REL))
    if not os.path.isfile(path):
        return None, "无冻结基线（%s 不存在）" % path
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, ValueError) as exc:
        return None, "冻结基线不可读: %s" % common.compress(str(exc))


# ------------------------------------------------------------------ 探针 ----

def _read_replies(proc, count, timeout):
    """带超时读 count 行应答（读者线程 + 期限 join；读不足即视为超时）。"""
    got = []

    def reader():
        for _ in range(count):
            line = proc.stdout.readline()
            if not line:
                break
            got.append(line.decode("utf-8", errors="replace"))

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    th.join(timeout)
    return got


def probe_server(target, server_path):
    """单次确定性 stdio 探针：initialize + tools/list，返回 (context dict)。

    context 键：init_raw / init（应答 result dict 或 None）/ tools_raw / tools（list 或 None）/
    error（整体失败原因或 None）。
    """
    ctx = {"init": None, "init_raw": "", "tools": None, "tools_raw": "", "error": None}
    node = shutil.which("node")
    if node is None:
        ctx["error"] = "环境 PATH 无 node 可执行文件，无法实测 MCP stdio 协议"
        return ctx
    try:
        proc = subprocess.Popen(
            [node, server_path], cwd=target,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        ctx["error"] = "node 子进程无法启动: %s" % exc
        return ctx
    try:
        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                   "clientInfo": {"name": "healthcheck-forms", "version": "1.0.0"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ]
        proc.stdin.write(("\n".join(requests) + "\n").encode("utf-8"))
        proc.stdin.flush()
        replies = _read_replies(proc, 2, PROBE_TIMEOUT_SEC)
    finally:
        proc.kill()
        proc.communicate()

    if len(replies) < 2:
        ctx["error"] = ("stdio 探针应答不足（收到 %d/2 行，超时 %ds 或 server 提前退出）"
                        % (len(replies), PROBE_TIMEOUT_SEC))
        if replies:
            ctx["init_raw"] = common.compress(replies[0])
            if len(replies) > 1:
                ctx["tools_raw"] = common.compress(replies[1])
        return ctx
    ctx["init_raw"] = common.compress(replies[0])
    ctx["tools_raw"] = common.compress(replies[1])
    for raw in replies:
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        result = msg.get("result")
        if msg.get("id") == 1 and isinstance(result, dict):
            ctx["init"] = result
        elif msg.get("id") == 2 and isinstance(result, dict):
            ctx["tools"] = result.get("tools")
    return ctx


# ------------------------------------------------------------------ 检查项 ----

def check_server_parsable(target):
    """① mcp-server.mjs 存在且 node --check 语法解析通过。"""
    path = os.path.join(target, SERVER_FILE)
    if not os.path.isfile(path):
        return False, "包根未找到 %s" % SERVER_FILE
    node = shutil.which("node")
    if node is None:
        return False, "环境 PATH 无 node 可执行文件，无法做语法解析检查（MCP 形态运行时要求 Node ≥18）"
    r = common.run_cmd([node, "--check", SERVER_FILE], cwd=target, timeout=30)
    if r["timed_out"]:
        return False, "node --check 超时（%s）" % r["cmd"]
    if r["returncode"] != 0:
        return False, "node --check 语法解析不过（exit=%s）stderr: %s" % (
            r["returncode"], common.compress(r["stderr"]))
    return True, "%s 通过 node --check 语法解析（node %s）" % (SERVER_FILE, _node_version(node))


def check_server_info(target, baseline, base_note, ctx):
    """② initialize 实测 serverInfo{name,version}（+protocolVersion）与基线一致。"""
    if ctx["error"] and ctx["init"] is None:
        return False, "initialize 实测失败：%s" % ctx["error"]
    init = ctx["init"]
    if not isinstance(init, dict):
        return False, "initialize 无合法应答（raw: %s）" % (ctx["init_raw"] or "<空>")
    info = init.get("serverInfo")
    if not isinstance(info, dict) or not info.get("name") or not info.get("version"):
        return False, "initialize 应答缺 serverInfo{name,version}（raw: %s）" % ctx["init_raw"]
    if baseline is None:
        return True, ("initialize 实测 serverInfo name=%s version=%s protocolVersion=%s"
                      "（%s，仅非空口径）" % (info["name"], info["version"],
                                             init.get("protocolVersion"), base_note))
    exp = baseline.get("serverInfo") or {}
    ok = (info.get("name") == exp.get("name") and info.get("version") == exp.get("version"))
    proto = baseline.get("protocolVersion")
    proto_ok = (proto is None) or (init.get("protocolVersion") == proto)
    if ok and proto_ok:
        return True, ("initialize 实测 serverInfo name=%s version=%s protocolVersion=%s"
                      " 与冻结基线一致" % (info["name"], info["version"],
                                          init.get("protocolVersion")))
    return False, ("serverInfo 与基线不一致：实测 name=%s version=%s protocol=%s，"
                   "基线 name=%s version=%s protocol=%s"
                   % (info.get("name"), info.get("version"), init.get("protocolVersion"),
                      exp.get("name"), exp.get("version"), proto))


def extract_source_tools(text):
    """源码 TOOLS 块内声明的工具名（按出现顺序）；无 TOOLS 块返回 None。"""
    m = re.search(r"const\s+TOOLS\s*=\s*\[(.*?)\n\];", text, re.S)
    if not m:
        return None
    return re.findall(r'name:\s*"([^"]+)"', m.group(1))


def check_tools_decl_match_impl(target, baseline, ctx):
    """③ tools/list 实测 × 源码 TOOLS 声明 × 冻结基线 三方一致。"""
    if ctx["error"] and ctx["tools"] is None:
        return False, "tools/list 实测失败：%s" % ctx["error"]
    live = ctx["tools"]
    if not isinstance(live, list) or not live:
        return False, "tools/list 无合法应答（raw: %s）" % (ctx["tools_raw"] or "<空>")

    server_path = os.path.join(target, SERVER_FILE)
    text, err = common.read_text_flex(server_path)
    if text is None:
        return False, "%s 无法读取: %s" % (SERVER_FILE, common.compress(err or ""))
    declared = extract_source_tools(text)
    if declared is None:
        return False, "源码未找到 const TOOLS = [...] 声明块（无法核对声明与实现）"

    live_names = [t.get("name") for t in live if isinstance(t, dict)]
    problems = []
    if live_names != declared:
        problems.append("tools/list 实测 %s ≠ 源码 TOOLS 声明 %s" % (live_names, declared))

    missing_branch = [n for n in declared
                      if ('case "%s"' % n) not in text and ("case '%s'" % n) not in text]
    if missing_branch:
        problems.append("声明工具在源码分派（zctlArgs）缺分支: %s" % ", ".join(missing_branch))

    base_tools = (baseline or {}).get("tools")
    if baseline is not None and base_tools is not None:
        base_names = [t.get("name") for t in base_tools]
        if live_names != base_names:
            problems.append("tools/list 实测 %s ≠ 冻结基线 %s" % (live_names, base_names))
        live_by = {t.get("name"): t for t in live if isinstance(t, dict)}
        for bt in base_tools:
            lt = live_by.get(bt.get("name"))
            if not isinstance(lt, dict):
                continue
            need = bt.get("inputSchema_required") or []
            got = ((lt.get("inputSchema") or {}).get("required")) or []
            if list(need) != list(got):
                problems.append("%s inputSchema.required 实测 %s ≠ 基线 %s"
                                % (bt.get("name"), got, need))
            for phrase in bt.get("description_contains") or []:
                if phrase not in (lt.get("description") or ""):
                    problems.append("%s description 缺基线关键词「%s」" % (bt.get("name"), phrase))

    if problems:
        return False, "声明与实现不一致（%d 处）: %s" % (len(problems), "; ".join(problems))
    if baseline is not None:
        return True, ("三方一致：%d 个工具 %s（tools/list 实测 = 源码 TOOLS 声明 = 冻结基线，"
                      "required/描述关键词逐项过，分派分支齐备）" % (len(live_names), live_names))
    return True, ("声明=实现一致：%d 个工具 %s（tools/list 实测 = 源码 TOOLS 声明，分派分支齐备；"
                  "无冻结基线，未做 registry 比对）" % (len(live_names), live_names))


def check_no_mutation_exposure(target, baseline, ctx):
    """④ 无变更类越权暴露：禁暴露工具名不出现、只读声明齐、无变更类 zctl 接线。"""
    live = ctx["tools"]
    if not isinstance(live, list) or not live:
        return False, "无 tools/list 实测结果，无法核对暴露面（%s）" % (ctx["error"] or "探针失败")
    text, err = common.read_text_flex(os.path.join(target, SERVER_FILE))
    if text is None:
        return False, "%s 无法读取: %s" % (SERVER_FILE, common.compress(err or ""))

    forbidden = list(DEFAULT_FORBIDDEN)
    base_forbidden = (baseline or {}).get("forbidden_tool_names")
    if base_forbidden:
        forbidden = list(base_forbidden)
    problems = []
    hit = [t.get("name") for t in live if isinstance(t, dict) and t.get("name") in forbidden]
    if hit:
        problems.append("暴露了禁暴露工具: %s" % ", ".join(hit))

    unmarked = [t.get("name") for t in live
                if isinstance(t, dict) and "只读" not in (t.get("description") or "")]
    if unmarked:
        problems.append("description 缺「只读」声明: %s" % ", ".join(unmarked))

    wired = []
    for pattern, label in MUTATION_PATTERNS:
        if re.search(pattern, text):
            wired.append(label)
    if wired:
        problems.append("源码存在变更类 zctl 接线: %s" % "; ".join(wired))

    if problems:
        return False, "存在变更类越权暴露（%d 处）: %s" % (len(problems), "; ".join(problems))
    src = "冻结基线 forbidden_tool_names=%s" % forbidden if base_forbidden \
        else "缺省禁暴露清单 %s（无冻结基线）" % forbidden
    return True, ("暴露面干净：%d 个工具全部只读声明、无禁暴露工具名、源码无变更类 zctl 接线"
                  "（核对口径：%s；模式 %s）"
                  % (len(live), src, "/".join(p for _, p in MUTATION_PATTERNS)))


def check_install_md(target):
    """⑤ INSTALL.md 完备：Node 前置 / mcpServers 片段 / 自检入口 / 安全说明。"""
    path = os.path.join(target, INSTALL_FILE)
    if not os.path.isfile(path):
        return False, "包根未找到 %s" % INSTALL_FILE
    text, err = common.read_text_flex(path)
    if text is None:
        return False, "%s 无法读取: %s" % (INSTALL_FILE, common.compress(err or ""))
    missing = []
    if not re.search(r"Node\s*≥?\s*>=?\s*\d+|Node\s*\d+", text):
        missing.append("Node 版本要求（如 Node >= 18）")
    if not ("mcpServers" in text and "command" in text and "args" in text
            and SERVER_FILE in text):
        missing.append("mcpServers 配置片段（command+args 指向 %s）" % SERVER_FILE)
    if "eval/runner.py" not in text:
        missing.append("自检入口（python eval/runner.py 及期望退出码）")
    if not ("安全" in text and ("变更类" in text or "dry-run" in text)):
        missing.append("安全说明（变更类不提供 MCP 入口 / dry-run 红线）")
    if missing:
        return False, "INSTALL.md 缺备要素（%d 项）: %s" % (len(missing), "; ".join(missing))
    return True, ("INSTALL.md 四要素齐备：Node 版本要求 / mcpServers 配置片段 / "
                  "eval/runner.py 自检入口 / 变更类安全说明")


# ------------------------------------------------------------------ 组装 ----

def run_checks(target):
    """跑 MCP 形态全部检查，返回 checks（顺序 = CHECK_NAMES）。"""
    checks = []
    baseline, base_err = load_baseline(target)
    server_path = os.path.join(target, SERVER_FILE)

    ok, detail = check_server_parsable(target)
    common.add(checks, "mcp_server_parsable", ok, detail)

    # 探针只在语法过且文件在时做一次（确定性单次调用）；否则带原因直达红项
    ctx = {"init": None, "init_raw": "", "tools": None, "tools_raw": "",
           "error": "mcp-server.mjs 缺失或语法不过，跳过 stdio 探针"}
    if os.path.isfile(server_path) and shutil.which("node"):
        ctx = probe_server(target, SERVER_FILE)

    ok, detail = check_server_info(target, baseline, base_note=base_err or "无冻结基线", ctx=ctx)
    common.add(checks, "server_info_identity", ok, detail)
    ok, detail = check_tools_decl_match_impl(target, baseline, ctx)
    common.add(checks, "tools_decl_match_impl", ok, detail)
    ok, detail = check_no_mutation_exposure(target, baseline, ctx)
    common.add(checks, "no_mutation_exposure", ok, detail)
    ok, detail = check_install_md(target)
    common.add(checks, "install_md_complete", ok, detail)

    assert [c["name"] for c in checks] == list(CHECK_NAMES), "检查项顺序被破坏"
    return checks


def _node_version(node):
    r = common.run_cmd([node, "--version"], timeout=10)
    return (r["stdout"] or "").strip() or "未知版本"
