#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runs/sf0008-k5b/s8_arms.py — SF-0008 三包 K5B 欠账补齐：臂批编排器（随卡证据）。

范围（登记文件 round-plan.json/budget.json 为准）：
  mm     v2/evalbench-v02 8 任务（t1..t8）× 2 臂 × n=2 = 32 臂调用
  office dist golden.json 5 ab_tasks × 2 臂 × n=2   = 20 臂调用
  hot    dist golden.json 5 ab_tasks × 2 臂 × n=3   = 30 臂调用（复检轮）
  按族分配（round-plan.arm_allocation）：任务级奇偶轮换，glm=46 / minimax=36。
  treatment 挂 dist 顶层 canonical 包的**可交付面过滤副本**（禁 reference/、eval/、
  EVALUATION.md 进臂——A-12 同款「任何臂不得带参照物」；canonical 源零改动）。
钉版机制照抄 sf0006-c（layers 全绿）：glm=M4、minimax=M2；两臂 prompt 逐字相同；
glm 落点漂移 → redline 停全批（B-01/SF-0004 DT-v1）。
预算：budget.json 台账态（spawn 前 pending、事后 db join 回填；只增不改历史行）；
  每臂 rate_limited 退避重试 ≤1；超额进程不计入结果。

用法：
  python s8_arms.py prep      # 零模型：过滤资产+包构建+单元树+隔离断言+全局sha开工快照
  python s8_arms.py canary    # 金丝雀：仅 glm/hot-templates/ab-001（2 个正式臂调用）
  python s8_arms.py run       # 余量全批（幂等续跑：已有权威 records 的臂跳过）
  python s8_arms.py close     # 收工：freeze verify + 全局 sha 收工比对（零模型）
退出码：0 成功 / 1 有臂级失败或断言红 / 2 用法或装置错误。
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = "/home/pan-ding/workspace/skill工厂/skillfactory"
RUN = os.path.join(ROOT, "evalkit", "runs", "sf0008-k5b")
EVALKIT = os.path.join(ROOT, "evalkit")
VPY = os.path.join(ROOT, ".venv-dev", "bin", "python")
DB = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
PERSONAL_SRC = os.path.expanduser("~/.zcode/v2/provider_config.json")
CRED_SRC = os.path.expanduser("~/.zcode/v2/credentials.json")
BUILTIN_SRC = "/opt/ZCode/resources/config/provider/zcode-builtin.json"
GLOBAL_SHA_FILES = [os.path.expanduser("~/.zcode/cli/config.json"),
                    os.path.expanduser("~/.zcode/v2/provider_config.json"),
                    os.path.expanduser("~/.zcode/v2/credentials.json")]
SCRATCH = "/tmp/sf0008-k5b-pin-scratch"

PKGS = {
    "meeting-minutes": {"dist": "meeting-minutes-skill", "n": 2},
    "office-templates": {"dist": "office-templates-skill", "n": 2},
    "hot-templates": {"dist": "hot-templates-skill", "n": 3},
}
MOUNTABLE = ["SKILL.md", "references", "scripts", "requirements.txt"]
FAMILIES = ["glm", "minimax"]
REPS = {pkg: list(range(1, spec["n"] + 1)) for pkg, spec in PKGS.items()}
FAMILY_TIMEOUT = {"minimax": 1200, "glm": 1800}
TARGET = {
    "glm": {"provider": "account:bigmodel-individual-coding-plan", "model": "GLM-5.3",
            "reasoning": "max"},
    "minimax": {"provider": "minimax", "model": "Minimax-M3.1-Flash-Preview",
                "reasoning": "enabled"},
}
CAP_ARMS = 82
RETRY_CAP_PER_ARM = 1
ENV_PROVIDER_KEYS = ("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
                     "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
                     "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE")
PROMPT = ("Read the file brief.md in the current working directory and complete the task it "
          "describes. Work autonomously end to end; do not ask questions. Leave all deliverables "
          "in place when you are finished.")

LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
STOP = threading.Event()
THREAD_ERROR = {"glm": None, "minimax": None}
PROGRESS = os.path.join(RUN, "progress.log")
QUEUE = {"items": [], "idx": 0}
SCRATCH_ENV = {}
BUDGET_LOCK = threading.Lock()


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    with LOG_LOCK:
        with open(PROGRESS, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    print(line, flush=True)


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_arm = load_mod("run_arm", os.path.join(EVALKIT, "harness", "run_arm.py"))
pull_telemetry = run_arm.pull_telemetry
make_arms = load_mod("make_arms", os.path.join(EVALKIT, "harness", "make_arms.py"))
classify_mod = load_mod("classify", os.path.join(EVALKIT, "evaluators", "classify.py"))


def plan_allocation():
    rp = json.load(open(os.path.join(RUN, "round-plan.json"), encoding="utf-8"))
    fam_of = {}
    for p in rp["arm_allocation"]["per_package"]:
        pkg = p["pkg"]
        for t in p["glm_tasks"]:
            fam_of[(pkg, t)] = "glm"
        for t in p["minimax_tasks"]:
            fam_of[(pkg, t)] = "minimax"
    return rp, fam_of


def tasks_of(pkg):
    if pkg == "meeting-minutes":
        d = json.load(open(os.path.join(ROOT, "v2/evalbench-v02/meeting-minutes/tasks.json"),
                           encoding="utf-8"))
        return [(t["id"], t["instruction"]) for t in d]
    d = json.load(open(os.path.join(ROOT, "dist", PKGS[pkg]["dist"], "eval/golden.json"),
                       encoding="utf-8"))
    return [(t["id"], t) for t in d["ab_tasks"]]


# ---------------------------------------------------------------- office 臂任务书（oracle 剥离改写， faithful 子集）
OFFICE_BRIEFS = {
 "ab1-standard-four-templates": {
   "inputs": [("周报","case1"),("请示函","case1"),("会议通知","case1"),("工作总结","case1")],
   "text": ("把 fixtures/ 目录下四类模板的 case1 数据 JSON（周报、请示函、会议通知、工作总结各一份，字段全部齐全）分别生成为公文产物。\n"
            "命令行契约：--template <周报|请示函|会议通知|工作总结> --data <数据json路径> --outdir <输出目录>，每次调用在该目录下生成 文书.docx 与 fields.json 两个产物。\n"
            "产物写入 out/<模板>/case1/（四类各一个单元目录，每目录恰含 文书.docx 与 fields.json）。\n"
            "风格要求：GB/T 9704 公文风格（A4 版面）。缺数据不编造：必填缺失以____占位、选填缺失留空或省略，并在 fields.json 中如实记账。\n"
            "fields.json 顶层需含 title、fields 明细（每个字段：名称、是否必填、状态、值/渲染方式）与 summary（filled/missing/total 计数）。\n"
            "实现方式不限（可自行编写脚本后调用）。完成后确认四个单元目录与产物齐全。")},
 "ab2-boundary-missing-required": {
   "inputs": [("请示函","case2"),("会议通知","case2")],
   "text": ("处理两份含缺失字段的边界数据：fixtures/请示函/case2.json（主送机关关键缺失、请示事项为空字符串、联系电话/成文日期选填缺失）与 "
            "fixtures/会议通知/case2.json（会议名称缺失、会议地点空字符串、会议议题/会议要求/联系人/联系电话选填缺失、含模板外键「备注」）。\n"
            "命令行契约：--template <请示函|会议通知> --data <数据json路径> --outdir <输出目录>，每次调用生成 文书.docx 与 fields.json。\n"
            "产物写入 out/<模板>/case2/（两个单元目录，每目录恰含两产物）。\n"
            "核心行为要求（缺数据不编造、如实记账）：必填缺失以____占位渲染且程序正常结束（退出码 0）；选填缺失留空或省略、不得误记为必填；"
            "模板外键记入 unknown_keys 类记账；fields.json 的 missing_required/选填 missing/unknown_keys 名单必须与输入的缺失事实一致；版式不因缺数据而破坏（称谓顶格、落款右对齐）。\n"
            "实现方式不限。完成后确认两个单元目录与产物齐全。")},
 "ab3-empty-and-string-lists": {
   "inputs": [("周报","case2"),("工作总结","case2")],
   "text": ("处理两份列表字段边界数据：fixtures/周报/case2.json（周期为空字符串、本周工作内容为空数组、问题与需协调事项选填缺失）与 "
            "fixtures/工作总结/case2.json（总结主体缺失、主要成绩为空数组、工作回顾为字符串型列表、存在问题与成文日期选填缺失）。\n"
            "命令行契约：--template <周报|工作总结> --data <数据json路径> --outdir <输出目录>，每次调用生成 文书.docx 与 fields.json。\n"
            "产物写入 out/<模板>/case2/（两个单元目录，每目录恰含两产物）。\n"
            "核心行为要求：空列表按必填缺失处理——渲染占位条目（如「1．____」）并在 fields.json 记占位语义；字符串型列表按单项化处理——渲染为单项条目且 fields.json 中该字段值为单元素数组；"
            "选填小节缺失整节省略（正文不出现该节头）但 fields.json 仍记 missing（required=false）；必填缺失以____占位（如标题「____工作周报」「____2026年9月工作总结」）；小节编号「一、二、三、」条目编号「1．2．3．」规范；落款右对齐不因空日期/缺主体破坏。\n"
            "实现方式不限。完成后确认两个单元目录与产物齐全。")},
 "ab4-invalid-input-rejection": {
   "inputs": [("周报","case1")],
   "text": ("非法输入拒绝行为测试：对你的生成入口分别施加四组非法输入——① --template 证书（模板名非法）② --data 指向不存在的文件 ③ --data 指向内容为「不是JSON」的文件（JSON 解析失败）④ --data 指向内容为 [\"数组\",\"非对象\"] 的文件（顶层非对象）；另以 fixtures/周报/case1.json 作合法对照组。\n"
            "逐组记录到 run_log.json：完整命令、退出码、stderr 摘要、产物残留检查（该次调用是否创建了输出目录/写出了 文书.docx 或 fields.json 等任何文件）。\n"
            "核心行为要求：四组非法输入应以非零退出码（约定值 2）拒绝、stderr 有中文错误信息、且零产物残留（不创建输出目录、不写半成品）；合法对照组退出码 0 并在 out/周报/case1/ 生成 文书.docx 与 fields.json 两产物；含必填缺失的输入不算非法（不得把缺失当错误拒绝）。\n"
            "产物布局：run_log.json（逐组记录）+ out/周报/case1/（合法对照组产物）。")},
 "ab5-determinism-layout-selfeval": {
   "inputs": [("会议通知","case1")],
   "text": ("确定性自评：用完全相同的输入 fixtures/会议通知/case1.json 连续运行生成两遍到同一输出目录 out/会议通知/case1（第二遍覆盖复写第一遍）。\n"
            "每遍后记录该目录下 文书.docx 与 fields.json 的 sha256 到 run_log.json（标注第几遍），并对两遍产物做逐字节对比，把对比结论（一致/不一致及差异说明）写入 run_log.json。\n"
            "核心行为要求：同输入连跑两遍产物逐字节一致（fields.json 除 outputs 类路径键外逐字节一致；docx 解析后的段落文本/对齐/缩进/字体/行距完全一致，无当前时间、随机内容等不可复现源）；输出目录恰含两产物。\n"
            "命令行契约：--template 会议通知 --data <数据json路径> --outdir out/会议通知/case1，每次调用生成 文书.docx 与 fields.json。实现方式不限。")},
}

HOT_RUNLOG = ("把本次任务中每一次生成调用的记录（输入参数、退出码、stderr 摘要、产生的文件清单）写入 run_log.json，与产物同级放在工作目录下。\n")


def build_packs():
    """构建三包臂任务包：brief.md（两臂逐字同）+ fixtures/。office 为 oracle 剥离改写（原 golden 冻结零改动）。"""
    made = []
    # mm
    for tid, instr in tasks_of("meeting-minutes"):
        pd = os.path.join(RUN, "packs", "meeting-minutes-%s" % tid)
        if os.path.isdir(pd):
            made.append(pd); continue
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)  # make_arms 要求 fixtures/ 在位（本任务输入内嵌于 brief，fixtures 空目录）
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(instr.replace("<outdir>", "out") + "\n")
        made.append(pd)
    # office
    for tid, t in tasks_of("office-templates"):
        spec = OFFICE_BRIEFS[tid]
        pd = os.path.join(RUN, "packs", "office-templates-%s" % tid)
        if os.path.isdir(pd):
            made.append(pd); continue
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)
        src_in = os.path.join(ROOT, "dist", "office-templates-skill", "reference", "inputs")
        lines = ["# SF-0008 office 臂任务（%s）" % tid, ""]
        for tpl, case in spec["inputs"]:
            dst = os.path.join(pd, "fixtures", tpl)
            os.makedirs(dst, exist_ok=True)
            shutil.copyfile(os.path.join(src_in, tpl, "%s.json" % case),
                            os.path.join(dst, "%s.json" % case))
        lines.append(spec["text"])
        lines.append("（注：本任务书为 golden.json ab 任务在「禁止参照物进臂」约束下的忠实改写；输入数据原样来自冻结任务集。）")
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        made.append(pd)
    # hot
    for tid, t in tasks_of("hot-templates"):
        pd = os.path.join(RUN, "packs", "hot-templates-%s" % tid)
        if os.path.isdir(pd):
            made.append(pd); continue
        os.makedirs(os.path.join(pd, "fixtures"), exist_ok=True)  # make_arms 要求（输入自含于 brief，fixtures 空目录）
        txt = t["instruction"].replace("<outdir>", "out")
        if tid == "ab-005":
            txt = txt + "\n" + HOT_RUNLOG
        with open(os.path.join(pd, "brief.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(txt + "\n")
        made.append(pd)
    return made


def build_filtered_assets():
    """canonical 顶层包 → 可交付面过滤副本（MOUNTABLE 白名单）；源零改动，登记文件清单与 sha256。"""
    manifest = {}
    for pkg, spec in PKGS.items():
        src = os.path.join(ROOT, "dist", spec["dist"])
        dst = os.path.join(RUN, "assets", spec["dist"])
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        files = []
        for item in MOUNTABLE:
            s = os.path.join(src, item)
            if not os.path.exists(s):
                raise RuntimeError("canonical 包缺可挂载面 %s: %s" % (item, s))
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
                for dp, _dn, fns in os.walk(d):
                    for fn in fns:
                        files.append(os.path.relpath(os.path.join(dp, fn), dst))
            else:
                shutil.copyfile(s, d)
                files.append(item)
        files.sort()
        manifest[spec["dist"]] = {
            "source": os.path.relpath(src, ROOT),
            "source_untouched": True,
            "filter_whitelist": MOUNTABLE,
            "excluded": ["reference", "eval", "EVALUATION.md", "CHANGELOG.md",
                         "README.md", "MANIFEST.md", "LICENSE"],
            "files": files,
            "file_sha256": {f: sha256_file(os.path.join(dst, f)) for f in files},
        }
    write_json(os.path.join(RUN, "records", "mount-manifest.json"), manifest)
    return manifest


def mount_name(pkg):
    """treatment 臂内技能挂载名 = SKILL.md frontmatter name（make_arms skill_name_of 口径）。"""
    sk = os.path.join(RUN, "assets", PKGS[pkg]["dist"], "SKILL.md")
    m = re.search(r"^name:\s*(\S+)", open(sk, encoding="utf-8").read(), re.M)
    return m.group(1) if m else PKGS[pkg]["dist"]


def unit_dir(fam, pkg, task, rep):
    return os.path.join(RUN, fam, "%s-%s-rep%d" % (pkg, task, rep))


def arm_dir_of(fam, pkg, task, rep, arm):
    return os.path.join(unit_dir(fam, pkg, task, rep), arm)


# ---------------------------------------------------------------- M2/M4 scratch（照抄 sf0006-c）
def derive_personal(fam_scratch, family):
    t = TARGET[family]
    with open(PERSONAL_SRC, "r", encoding="utf-8") as f:
        personal = json.load(f)
    cfg = personal.setdefault("config", {})
    cfg["defaultModelSelection"] = {"providerId": t["provider"], "modelId": t["model"],
                                    "options": {"reasoningLevel": t["reasoning"]}}
    cfg["providerOrder"] = [t["provider"]] + [p for p in cfg.get("providerOrder", [])
                                              if p != t["provider"]]
    path = os.path.join(fam_scratch, "provider_config.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(personal, f, ensure_ascii=False, indent=2)
    return path


def derive_data_dir(fam_scratch, family):
    t = TARGET[family]
    with open(CRED_SRC, "r", encoding="utf-8") as f:
        creds = json.load(f)
    ident_key = "account-provider:%s:identity" % t["provider"]
    if ident_key in creds:
        return None, "identity 条目已存在（探针口径：无需注入，M4 短路）"
    api_keys = [k for k in creds
                if k.startswith("account-provider:coding-plan:%s:account:" % t["provider"])
                and k.endswith(":api-key")]
    if not api_keys:
        return None, "无 api-key 条目可解析 identity，M4 不可行"
    account_identity = api_keys[0].split(":account:")[-1][:-len(":api-key")]
    if not account_identity:
        return None, "api-key 条目名中 identity 段为空"
    creds[ident_key] = account_identity
    v2 = os.path.join(fam_scratch, "zcode-data", ".zcode", "v2")
    os.makedirs(v2, exist_ok=True)
    path = os.path.join(v2, "credentials.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(path, 0o600)
    note = ("注入明文 identity 条目 %s（值=<%d chars>）；其余 %d 条原样拷贝"
            % (ident_key, len(account_identity), len(creds) - 1))
    return os.path.join(fam_scratch, "zcode-data"), note


def build_family_scratch(family):
    fam_scratch = os.path.join(SCRATCH, family)
    os.makedirs(fam_scratch, exist_ok=True)
    builtin_path = os.path.join(fam_scratch, "zcode-builtin.json")
    shutil.copyfile(BUILTIN_SRC, builtin_path)
    personal_path = derive_personal(fam_scratch, family)
    extra_env = {"ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": builtin_path,
                 "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": personal_path}
    m4_note = None
    if TARGET[family]["provider"] == "account:bigmodel-individual-coding-plan":
        data_dir, m4_note = derive_data_dir(fam_scratch, family)
        if data_dir is None:
            raise RuntimeError("M4 不可行: " + m4_note)
        extra_env["ZCODE_DATA_BASE_DIR"] = data_dir
    return {"extra_env": extra_env, "m4_note": m4_note}


# ---------------------------------------------------------------- run（照抄 sf0006-c 机制）
def looks_rate_limited(text, tele):
    for r in (tele.get("model_usage") or []):
        if "rate_limited" in str(r.get("status") or ""):
            return True
    return bool(re.search(r"rate[_ ]?limit", text, re.I))


def dominant_row(rows):
    return sorted(rows, key=lambda r: (r.get("n") or 0), reverse=True)[0] if rows else None


def run_once(arm_dir, family):
    arm_dir = os.path.abspath(arm_dir)
    timeout = FAMILY_TIMEOUT[family]
    cmd = [shutil.which("node") or "/home/pan-ding/.local/bin/node",
           "/opt/ZCode/resources/glm/zcode.cjs",
           "-p", PROMPT, "--cwd", arm_dir.replace("\\", "/"), "--json"]
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    for k in ENV_PROVIDER_KEYS:
        env.pop(k, None)
    env.pop("ZCODE_DATA_BASE_DIR", None)
    env.update(SCRATCH_ENV[family])
    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env,
                              shell=False, cwd=arm_dir)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, out, err, timed_out = -1, (exc.stdout or b""), (exc.stderr or b""), True
    wall_ms = int((time.time() - t0) * 1000)
    text = out.decode("utf-8", errors="replace")
    errtext = err.decode("utf-8", errors="replace")
    m = re.search(r'"sessionId"\s*:\s*"([^"]+)"', text)
    session_id = m.group(1) if m else None
    time.sleep(2)
    tele = pull_telemetry(DB, session_id, arm_dir)
    if session_id and not (tele.get("model_usage") or []):
        for root, _dirs, files in os.walk(SCRATCH):
            for fn in files:
                if fn.endswith(".sqlite"):
                    cand = pull_telemetry(os.path.join(root, fn), session_id, arm_dir)
                    if cand.get("session"):
                        tele = dict(cand, db_path_fallback=os.path.join(root, fn))
                        break
            if tele.get("session"):
                break
    rows = tele.get("model_usage") or []
    dom = dominant_row(rows)
    return {
        "family": family, "arm": os.path.basename(arm_dir),
        "mechanism": "m4" if family == "glm" else "m2",
        "command_shape": ["node", "zcode.cjs", "-p", "<PROMPT 逐字同 run_arm.py>", "--cwd",
                          arm_dir, "--json"],
        "exit_code": rc, "timed_out": timed_out, "wall_ms": wall_ms,
        "started_at_ms": int(t0 * 1000), "session_id": session_id,
        "directory_matches_arm": tele.get("directory_matches_arm"),
        "session_directory": (tele.get("session") or {}).get("directory"),
        "db_source": "global" if not tele.get("db_path_fallback") else "scratch-fallback",
        "model_id_observed": dom.get("model_id") if dom else None,
        "provider_id_observed": dom.get("provider_id") if dom else None,
        "variant_observed": dom.get("variant") if dom else None,
        "model_usage_rows": len(rows), "model_usage": rows,
        "input_tokens": sum((r.get("it") or 0) for r in rows),
        "output_tokens": sum((r.get("ot") or 0) for r in rows),
        "stdout_bytes": len(out), "stderr_bytes": len(err),
        "stderr_head": errtext[:2000], "stdout_tail": text[-1500:],
        "_raw_stdout": text, "_raw_stderr": errtext,
    }


def budget_append(entry):
    with BUDGET_LOCK:
        p = os.path.join(RUN, "budget.json")
        b = json.load(open(p, encoding="utf-8"))
        b.setdefault("ledger_entries", [])
        entry["slot"] = len(b["ledger_entries"]) + 1
        b["ledger_entries"].append(entry)
        if entry.get("kind") == "arm" and entry.get("status") == "pending":
            b["arm_calls"]["counted_so_far"] = b["arm_calls"].get("counted_so_far", 0) + 1
        if entry.get("kind") == "rate_limited-retry":
            b["retry_policy"]["used"] = b["retry_policy"].get("used", 0) + 1
        write_json(p, b)
        return entry["slot"]


def budget_reserved_arms():
    """占位即计数（pending+done+no-model-call），与 C 层口径一致：防并发超预算。
    装置 bug/无效尝试条目（skipped_harness_bug、rate_limited_attempt1_invalid）不占额度。"""
    p = os.path.join(RUN, "budget.json")
    b = json.load(open(p, encoding="utf-8"))
    return sum(1 for e in b.get("ledger_entries", [])
               if e.get("kind") == "arm"
               and e.get("status") in ("pending", "done", "no-model-call"))


def budget_update(slot, **kw):
    with BUDGET_LOCK:
        p = os.path.join(RUN, "budget.json")
        b = json.load(open(p, encoding="utf-8"))
        for e in b["ledger_entries"]:
            if e.get("slot") == slot:
                e.update(kw)
                break
        write_json(p, b)


def persist_arm(fam, pkg, task, rep, arm, rec, asset_dist):
    ad = arm_dir_of(fam, pkg, task, rep, arm)
    rec_dir = os.path.join(ad, "records")
    pin = {
        "arm": arm, "run_label": "rep%d" % rep, "run_id": "sf0008-k5b",
        "model_id": rec["model_id_observed"] or "UNOBSERVED",
        "provider_base_url": rec["provider_id_observed"] or "UNOBSERVED",
        "cli_runtime": "zcode-app-cli 3.14.4 (embedded) / zcode-runtime 0.16.9",
        "date": time.strftime("%Y-%m-%d"),
        "reasoning_variant": rec["variant_observed"]
                             or ("max" if fam == "glm" else "enabled"),
        "asset_mount": (os.path.join(ad, ".zcode", "skills", mount_name(pkg))
                        if arm == "treatment" else None),
        "family": fam, "mechanism": rec["mechanism"],
        "pkg": pkg, "task": task, "rep": rep,
        "note": ("SF-0008 K5B 实测钉版：model_id/provider_base_url 抄 db model_usage join 落点"
                 "（逐字大小写敏感）；机制 glm=M4、minimax=M2（照 sf0006-c）"),
    }
    write_json(os.path.join(rec_dir, "model_pin.json"), pin)
    arm_run = {k: v for k, v in rec.items() if not k.startswith("_")}
    write_json(os.path.join(rec_dir, "arm_run.json"), arm_run)
    write_json(os.path.join(rec_dir, "telemetry.json"),
               {"available": True, "session_id": rec["session_id"],
                "session": {"directory": rec["session_directory"]},
                "directory_matches_arm": rec["directory_matches_arm"],
                "db_source": rec["db_source"], "model_usage": rec["model_usage"]})
    stripped = rec["_raw_stdout"].lstrip()
    sname = "transcript_stdout.json" if stripped.startswith("{") else "transcript_stdout.cli-error.txt"
    with open(os.path.join(rec_dir, sname), "w", encoding="utf-8", newline="\n") as f:
        f.write(rec["_raw_stdout"])
    with open(os.path.join(rec_dir, "transcript_stderr.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(rec["_raw_stderr"])
    return pin


def classify_arm(rec, retried):
    events = []
    if rec["timed_out"]:
        events.append({"kind": "arm_timeout", "detail": "wall_ms=%d" % rec["wall_ms"]})
    elif rec["session_id"] is None and rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "no session / no model_usage"})
    elif rec["model_usage_rows"] == 0:
        events.append({"kind": "harness_crash", "detail": "session without model_usage"})
    if retried:
        events.append({"kind": "rate_limited", "detail": "退避重试 1 次后重跑"})
    r = classify_mod.classify_run(events, arm_id=rec["arm"])
    return {"bucket": r["arm_verdict"],
            "buckets_detail": [b["bucket"] for b in r["buckets"]] or ["measured_failure"],
            "classify_module": "evalkit/evaluators/classify.py classify_run（装置原函数实跑）",
            "events_in": events}


def family_worker(fam, fam_queue, redline):
    try:
        _family_worker(fam, fam_queue, redline)
    except Exception as exc:
        import traceback
        THREAD_ERROR[fam] = traceback.format_exc()[-1500:]
        log("WORKER CRASH %s: %s" % (fam, exc))
        STOP.set()


def _family_worker(fam, fam_queue, redline):
    for (pkg, task, rep) in fam_queue:
        if STOP.is_set():
            return
        for arm in ("baseline", "treatment"):
            if STOP.is_set():
                return
            if os.path.isfile(os.path.join(arm_dir_of(fam, pkg, task, rep, arm), "records",
                                           "arm_run.json")):
                log("SKIP 已完成臂 %s/%s-%s-rep%d/%s" % (fam, pkg, task, rep, arm))
                continue
            with LOCK:
                if budget_reserved_arms() >= CAP_ARMS or STOP.is_set():
                    STOP.set()
                    return
                slot = budget_append({"arm": "%s/%s-%s-rep%d/%s" % (fam, pkg, task, rep, arm),
                                      "kind": "arm", "pkg": pkg, "task": task, "family": fam,
                                      "rep": rep,
                                      "ts_intent": time.strftime("%H:%M:%S"), "status": "pending"})
            ad = arm_dir_of(fam, pkg, task, rep, arm)
            rec = None
            try:
                rec = run_once(ad, fam)
            except Exception as exc:   # 装置级异常：如实标 failed，不留悬置 pending
                import traceback
                budget_update(slot, status="failed_harness_exception",
                              error=type(exc).__name__ + ":" + str(exc)[:200])
                write_json(os.path.join(RUN, "attempts",
                                        "%s-%s-%s-rep%d-%s.harness-exception.json"
                                        % (fam, pkg, task, rep, arm)),
                           {"error": traceback.format_exc()[-2000:]})
                STOP.set()
                return
            retried = False
            failed = (rec["exit_code"] != 0 or rec["timed_out"]
                      or not rec["session_id"] or rec["model_usage_rows"] == 0)
            rl = failed and looks_rate_limited(rec["_raw_stdout"] + rec["_raw_stderr"], rec)
            if rl:
                att1 = {k: v for k, v in rec.items() if not k.startswith("_")}
                att1["attempt"] = 1
                write_json(os.path.join(RUN, "attempts", "%s-%s-%s-rep%d-%s.attempt1.json"
                                        % (fam, pkg, task, rep, arm)), att1)
                log("rate_limited 退避 30s 后重试 1 次：%s/%s-%s-rep%d/%s" % (fam, pkg, task, rep, arm))
                time.sleep(30)
                rslot = budget_append({"arm": "%s/%s-%s-rep%d/%s" % (fam, pkg, task, rep, arm),
                                       "kind": "rate_limited-retry", "pkg": pkg, "task": task,
                                       "family": fam, "rep": rep,
                                       "ts_intent": time.strftime("%H:%M:%S"), "status": "pending"})
                rec = run_once(ad, fam)
                rec["attempt"] = 2
                rec["rate_limited_retry"] = True
                retried = True
                budget_update(rslot, status="done" if rec["model_usage_rows"] else "no-model-call",
                              exit_code=rec["exit_code"], session_id=rec["session_id"])
            pin = persist_arm(fam, pkg, task, rep, arm, rec, PKGS[pkg]["dist"])
            observed = rec["model_usage_rows"] > 0
            t = TARGET[fam]
            pin_ok = (rec["model_id_observed"] == t["model"]
                      and rec["provider_id_observed"] == t["provider"])
            summary = {k: v for k, v in rec.items() if not k.startswith("_")}
            summary.update({"pin_verdict": "pass" if pin_ok else "drift" if observed else "unobserved",
                            "attempted": True, "retried": retried,
                            "classify": classify_arm(rec, retried),
                            "pkg": pkg, "task": task, "rep": rep, "slot": slot})
            write_json(os.path.join(RUN, "records", "arms",
                                    "%s-%s-%s-rep%d-%s.json" % (fam, pkg, task, rep, arm)), summary)
            budget_update(slot, status="done" if observed else "no-model-call",
                          exit_code=rec["exit_code"], session_id=rec["session_id"],
                          observed={"model_id": rec["model_id_observed"],
                                    "provider_id": rec["provider_id_observed"],
                                    "variant": rec["variant_observed"]},
                          pin_verdict=summary["pin_verdict"])
            if fam == "glm" and observed and not pin_ok:
                redline["event"] = True
                redline["detail"] = ("glm 臂落点漂移（B-01 红线）：observed %s @ %s ≠ %s @ %s，停全批"
                                     % (rec["model_id_observed"], rec["provider_id_observed"],
                                        t["model"], t["provider"]))
                STOP.set()
                return
            log("ARM done %s/%s-%s-rep%d/%s exit=%d tokens=%d+%d pin=%s"
                % (fam, pkg, task, rep, arm, rec["exit_code"], rec["input_tokens"],
                   rec["output_tokens"], summary["pin_verdict"]))


def budget_counted():
    p = os.path.join(RUN, "budget.json")
    b = json.load(open(p, encoding="utf-8"))
    return sum(1 for e in b.get("ledger_entries", [])
               if e.get("kind") == "arm" and e.get("status") in ("done", "no-model-call"))


def global_sha(tag):
    lines = ["# SF-0008 全局配置 sha256（%s，%s）" % (tag, time.strftime("%Y-%m-%dT%H:%M:%S%z"))]
    for p in GLOBAL_SHA_FILES:
        lines.append("%s  %s" % (sha256_file(p), p))
    with open(os.path.join(RUN, "precheck", "global-sha-%s.txt" % tag), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- stages
def stage_prep():
    fails = []
    rp, fam_of = plan_allocation()
    global_sha("opening")
    fr = subprocess.run([sys.executable, os.path.join(EVALKIT, "harness", "freeze_device.py"),
                         "verify", "--evalkit", EVALKIT], capture_output=True)
    with open(os.path.join(RUN, "precheck", "freeze-verify-opening.out"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("exit=%d\n%s" % (fr.returncode, fr.stdout.decode("utf-8", "replace")))
    if fr.returncode != 0:
        fails.append("freeze verify 开工非 0")
    build_filtered_assets()
    packs = build_packs()
    log("packs: %d" % len(packs))

    # 单元树（make_arms：fixtures+brief 两臂同、treatment 挂 .zcode/skills/<name>）；幂等：已有单元只验证
    units = 0
    for pkg, spec in PKGS.items():
        asset = os.path.join(RUN, "assets", spec["dist"])
        for tid, _ in tasks_of(pkg):
            fam = fam_of[(pkg, tid)]
            for rep in REPS[pkg]:
                ud = unit_dir(fam, pkg, tid, rep)
                if os.path.isdir(ud):
                    units += 1
                    continue
                rc = make_arms.main(["--pack", os.path.join(RUN, "packs", "%s-%s" % (pkg, tid)),
                                     "--run-id", "%s/%s-%s-rep%d" % (fam, pkg, tid, rep),
                                     "--asset-skill", asset, "--out", RUN])
                if rc != 0:
                    fails.append("make_arms %s %s-%s-rep%d exit=%d" % (fam, pkg, tid, rep, rc))
                    continue
                units += 1
                # 隔离断言（A-12 同款）：任何臂树禁 reference|oracle；baseline 禁 .zcode；
                # brief.md 两臂逐字同
                for arm in ("baseline", "treatment"):
                    ad = arm_dir_of(fam, pkg, tid, rep, arm)
                    for ban in ("reference", "oracle"):
                        for dp, dns, _fns in os.walk(ad):
                            if os.path.basename(dp) == ban:
                                fails.append("臂含 %s/: %s" % (ban, dp))
                    if not os.path.isfile(os.path.join(ad, "brief.md")):
                        fails.append("臂缺 brief.md: %s" % ad)
                b1 = os.path.join(arm_dir_of(fam, pkg, tid, rep, "baseline"), "brief.md")
                b2 = os.path.join(arm_dir_of(fam, pkg, tid, rep, "treatment"), "brief.md")
                if sha256_file(b1) != sha256_file(b2):
                    fails.append("两臂 brief.md 不同: %s-%s-rep%d" % (pkg, tid, rep))
                if os.path.isdir(os.path.join(arm_dir_of(fam, pkg, tid, rep, "baseline"),
                                              ".zcode")):
                    fails.append("baseline 臂含 .zcode: %s-%s-rep%d" % (pkg, tid, rep))
                if not os.path.isdir(os.path.join(arm_dir_of(fam, pkg, tid, rep, "treatment"),
                                                  ".zcode", "skills", mount_name(pkg))):
                    fails.append("treatment 臂缺技能挂载: %s-%s-rep%d" % (pkg, tid, rep))
    if fails:
        print("PREP FAIL:\n" + "\n".join(fails), file=sys.stderr)
        write_json(os.path.join(RUN, "records", "prep-fails.json"), {"fails": fails})
        return 1
    n_units = sum(len(tasks_of(p)) * PKGS[p]["n"] for p in PKGS)
    write_json(os.path.join(RUN, "records", "prep-summary.json"),
               {"units": n_units, "arm_calls_planned": 2 * sum(
                   len(tasks_of(p)) * PKGS[p]["n"] for p in PKGS),
                "allocation": {("%s|%s" % k): v for k, v in fam_of.items()},
                "opened_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    log("PREP 完成：%d 单元（%d 臂目录），隔离断言全过" % (n_units, 2 * n_units))
    return 0


def build_queue(fam_of, only_canary=False):
    q = {"glm": [], "minimax": []}
    # 金丝雀先跑最轻的 hot ab-001（glm 族）
    order_pkgs = ["hot-templates", "meeting-minutes", "office-templates"]
    for pkg in order_pkgs:
        for tid, _ in tasks_of(pkg):
            fam = fam_of[(pkg, tid)]
            for rep in REPS[pkg]:
                q[fam].append((pkg, tid, rep))
    if only_canary:
        q = {"glm": [q["glm"][0]], "minimax": []}
    return q


def stage_run(only_canary=False):
    global SCRATCH_ENV
    rp, fam_of = plan_allocation()
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    for fam in FAMILIES:
        SCRATCH_ENV[fam] = build_family_scratch(fam)["extra_env"]
    write_json(os.path.join(RUN, "records", "scratch-env-names.json"),
               {f: sorted(SCRATCH_ENV[f].keys()) for f in FAMILIES})
    q = build_queue(fam_of, only_canary)
    redline = {"event": False, "detail": None}
    th = threading.Thread(target=family_worker, args=("glm", q["glm"], redline))
    th2 = threading.Thread(target=family_worker, args=("minimax", q["minimax"], redline))
    th.start(); th2.start(); th.join(); th2.join()
    write_json(os.path.join(RUN, "records", "run-stage-summary.json"),
               {"redline_event": redline["event"], "redline_detail": redline["detail"],
               "thread_errors": {k: v for k, v in THREAD_ERROR.items() if v},
               "counted_arms": budget_counted(),
               "closed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "canary": only_canary})
    log("RUN 阶段结束：counted=%d redline=%s thread_error=%s"
        % (budget_counted(), redline["event"], [k for k, v in THREAD_ERROR.items() if v]))
    if redline["event"] or any(THREAD_ERROR.values()):
        return 1
    return 0


def stage_close():
    r = subprocess.run([sys.executable, os.path.join(EVALKIT, "harness", "freeze_device.py"),
                        "verify", "--evalkit", EVALKIT], capture_output=True)
    with open(os.path.join(RUN, "precheck", "freeze-verify-closing.out"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("exit=%d\n%s" % (r.returncode, r.stdout.decode("utf-8", "replace")))
    log("freeze verify closing exit=%d" % r.returncode)
    global_sha("closing")
    a = open(os.path.join(RUN, "precheck", "global-sha-opening.txt"), encoding="utf-8").read()
    b = open(os.path.join(RUN, "precheck", "global-sha-closing.txt"), encoding="utf-8").read()
    same = all(l.split("  ")[0] in b for l in a.splitlines() if "  " in l)
    log("全局配置 sha 开工/收工逐字节一致=%s" % same)
    write_json(os.path.join(RUN, "precheck", "b03-global-sha-equal.json"),
               {"byte_identical": bool(same)})
    return 0 if (r.returncode == 0 and same) else 1


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("prep", "canary", "run", "close"):
        print(__doc__, file=sys.stderr)
        return 2
    os.makedirs(os.path.join(RUN, "records"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "attempts"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "precheck"), exist_ok=True)
    return {"prep": stage_prep, "canary": lambda: stage_run(True),
            "run": lambda: stage_run(False), "close": stage_close}[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
