# -*- coding: utf-8 -*-
"""common.py — WS9 分形态体检共享件（报告组装 / 子进程 / 读文件 / 评级）。

只增不改：本文件是 WS9 新增模块的内部共享层，不 import、不修改旧
``package/healthcheck.py`` / ``oracle/healthcheck.py`` 的任何逻辑；仅按
spec.md §3 R4/R6/R8/R9/R10 的冻结口径复刻同构行为，保证分形态产物与
skill 形态产物可被同一套习惯消费（schema 同构、评级规则一致）。

同构点（与 spec.md/contract.md 逐条对齐）：
- 评级规则 = R8 写死：失败数 0→A / 1→B / ≥2→C；skip 不计失败（分形态检查目前无 skip 态，保留口径）。
- report.json = R9 同构：tool / target / generated_at（唯一非确定性字段）/
  summary{total,pass,fail} / rating / checks[{name,pass,detail}]；
  UTF-8、ensure_ascii=False、indent=2、结尾换行；form 形态额外带 ``form`` 字段。
- REPORT.md = R10 同构：机器锚点行「评级：**X**」（正则 ``评级：\\*\\*([ABC])\\*\\*``）
  不变；标题换成形态名；额外附「检查口径出处」节（各形态模块的 CRITERIA_NOTES）。
- 退出码 = R11 同口径：0 = 报告已写出（红绿都 0）；2 = 参数/目标目录无效。
"""

import json
import os
import subprocess
from datetime import datetime

TOOL_ID = "healthcheck-forms.py 1.0.0"   # 与旧 TOOL_ID 区分，形态后缀由入口拼接
SUMMARY_LIMIT = 400                       # R6 摘要口径：空白压缩后截尾长度
SUBPROC_TIMEOUT = 120                     # 分形态子进程缺省超时（秒）


# ------------------------------------------------------------------ 文本 ----

def compress(text, limit=SUMMARY_LIMIT):
    """R6 摘要口径：空白压缩为单空格并截尾，保证报告 detail 单行可读。"""
    text = " ".join((text or "").split())
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def read_text_flex(path):
    """R4 编码口径：utf-8-sig 优先，解码失败回退 gbk，再失败返回 (None, 原因)。"""
    with open(path, "rb") as f:
        data = f.read()
    last = None
    for enc in ("utf-8-sig", "gbk"):
        try:
            return data.decode(enc), None
        except UnicodeDecodeError as exc:
            last = exc
    return None, str(last)


def parse_front_matter(text):
    """R4 行级 front-matter 解析（非完整 YAML）：返回 (fields|None, 失败原因|None)。

    与 skill 形态 R4 同口径：块以首行 ``---`` 起始、至下一个 ``---`` 行闭合；
    块内逐行匹配 ``key: value``（首个冒号切分，缩进行视为嵌套内容不收）。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "front-matter 块缺失（首行不是 ---）"
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields, None
        if ":" in line and not line[:1].isspace():
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return None, "front-matter 块未闭合（缺少结束 ---）"


# ---------------------------------------------------------------- 子进程 ----

def run_cmd(cmd, cwd=None, timeout=SUBPROC_TIMEOUT, env_extra=None):
    """跑单条命令，返回 dict(cmd, returncode, stdout, stderr, timed_out)。

    单次确定性调用（不重试掩蔽，spec.md §4 边界同口径）；超时/异常只记录不抛出。
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if env_extra:
        env.update(env_extra)
    disp = " ".join(str(c) for c in cmd)
    try:
        proc = subprocess.run(
            [str(c) for c in cmd], cwd=cwd, env=env, timeout=timeout,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        return {"cmd": disp, "returncode": None, "timed_out": True,
                "stdout": to_text(exc.stdout), "stderr": to_text(exc.stderr)}
    except OSError as exc:
        return {"cmd": disp, "returncode": None, "timed_out": False,
                "stdout": "", "stderr": str(exc)}
    return {"cmd": disp, "returncode": proc.returncode, "timed_out": False,
            "stdout": proc.stdout or "", "stderr": proc.stderr or ""}


def to_text(data):
    """subprocess 输出（bytes/str/None）转安全文本。"""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


# ------------------------------------------------------------------ 评级 ----

def rate(num_fail):
    """R8 评级规则（写死）：A=0 失败 / B=1 / C=≥2；skip 不计失败。"""
    if num_fail == 0:
        return "A"
    if num_fail == 1:
        return "B"
    return "C"


# ------------------------------------------------------------------ 产物 ----

def build_form_report(form, target, checks, advice, criteria_notes, out_dir):
    """组装并写出分形态 report.json + REPORT.md（R9/R10 同构），返回 report dict。

    - form           形态名（mcp / agent / tooling），写入 tool 字段后缀与 form 字段
    - advice         {检查名: 建议文案}（REPORT.md 建议节逐失败项引用）
    - criteria_notes [口径出处文案]（REPORT.md「检查口径出处」节逐条落盘）
    """
    total = len(checks)
    n_pass = sum(1 for c in checks if c["pass"])
    n_fail = total - n_pass
    rating = rate(n_fail)
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    tool_id = "%s (%s 形态)" % (TOOL_ID, form)

    report = {
        "tool": tool_id,
        "form": form,
        "target": os.path.abspath(target),
        "generated_at": generated_at,   # 唯一非确定性字段（R9/R12 同口径）
        "summary": {"total": total, "pass": n_pass, "fail": n_fail},
        "rating": rating,
        "checks": checks,
    }
    json_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

    lines = ["# %s 形态体检报告（分形态 Healthcheck）" % form.upper(), ""]
    lines.append("- 目标包：`%s`" % report["target"])
    lines.append("- 生成时间：%s（%s）" % (generated_at, tool_id))
    lines.append("- 评级：**%s**（A=0 失败 / B=1 失败 / C=≥2 失败）" % rating)
    lines.append("- 汇总：%d 项检查，%d 通过 / %d 失败" % (total, n_pass, n_fail))
    lines.append("")
    lines.append("| 检查项 | 结果 | 说明 |")
    lines.append("| --- | --- | --- |")
    for c in checks:
        verdict = "✅ PASS" if c["pass"] else "❌ FAIL"
        lines.append("| %s | %s | %s |" % (c["name"], verdict, c["detail"].replace("|", "\\|")))
    lines.append("")
    lines.append("## 检查口径出处")
    lines.append("")
    for note in criteria_notes:
        lines.append("- %s" % note)
    lines.append("")
    lines.append("## 建议")
    lines.append("")
    if rating == "A":
        lines.append("评级 A：无失败项，%s 形态口径全绿。" % form)
    elif rating == "B":
        lines.append("评级 B：仅 1 项失败，建议修复下述红项后重跑体检。")
    else:
        lines.append("评级 C：失败项 ≥2，分发/回写台账前必须完成整改。")
    for c in checks:
        if not c["pass"] and c["name"] in advice:
            lines.append("- **%s**：%s" % (c["name"], advice[c["name"]]))
    lines.append("")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json_text)
    with open(os.path.join(out_dir, "REPORT.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return report


def add(checks, name, ok, detail):
    """追加一条检查结果（pass 恒转 bool，防外部真值泄漏）。"""
    checks.append({"name": name, "pass": bool(ok), "detail": detail})


def summary_line(report, out_dir):
    """stdout 摘要行（评级 / 通过数 / 输出目录），供入口打印。"""
    return ("体检完成：%s 形态评级 %s（%d 项检查，%d 通过 / %d 失败）→ %s"
            % (report["form"], report["rating"], report["summary"]["total"],
               report["summary"]["pass"], report["summary"]["fail"],
               os.path.abspath(out_dir)))
