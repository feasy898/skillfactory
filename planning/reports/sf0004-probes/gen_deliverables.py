"""SF-0004 deliverable generator: decision.json + decision report.

Every verdict is COMPUTED from the raw probe evidence (p-a-*.json / p-b0-*.json / p-k*.json),
never hardcoded: self-reported verdicts are not truth (acceptance appendix).

The DT-v1 block is copied programmatically out of the planner-owned acceptance file so
D2 byte-fidelity is structural rather than a hand transcription.
"""
import json
import os
import re
import sqlite3
import time

PR = r"D:\new-workspace\agent-asset\planning\reports"
PROBE = os.path.join(PR, "sf0004-probes")
ACCEPT = r"D:\workspace\local-plane\projects\skillfactory\tests\visible\SF-0004-accept.md"
DB = os.path.join(os.environ["USERPROFILE"], ".zcode", "cli", "db", "db.sqlite")
JSONOUT = os.path.join(PR, "SF-0004-decision.json")
REPORT = os.path.join(PR, "SF-0004-single-family-decision.md")
GLM_LANDING = "account:bigmodel-individual-coding-plan/GLM-5.3"

TARGET_MODEL = "Minimax-M3.1-Flash-Preview"
TARGET_PROVIDER = "minimax"


def load(p):
    with open(os.path.join(PROBE, p), encoding="utf-8") as f:
        return json.load(f)


def w_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


ctl = load("p-a-ctl.json")
trt = load("p-a-trt-trt-1-m1.json")
ctl2 = load("p-a-ctl2.json")
k1 = load("p-k1-step.json")
k2 = load("p-k2-broker.json")
b0a = load("p-b0-prior.json")
b0b = load("p-b0-static.json")
b0c = load("p-b0-catalog.json")
prereg = load("a0-prereg.json")

# ---------- A verdict, recomputed from raw evidence ----------
ctl_infra_ok = (ctl["exit_code"] == 0 and ctl["db"]["available"]
                and ctl["db"]["session_row_found"] and ctl["db"]["directory_match"] is True
                and ctl["db"]["model_usage_rows"] > 0)
ctl_landed_glm = ctl["db"]["model_id_verbatim"] == "GLM-5.3" and "bigmodel" in \
    (ctl["db"]["provider_id_verbatim"] or "").lower()
trt_success = bool(trt["success_shape"])
restore_ok = bool(ctl2["success_shape"]) and ctl2["db"]["model_id_verbatim"] == "GLM-5.3"

if not ctl_infra_ok:
    a_verdict, a_reason = "Undetermined", "A-ctl infra failure (db unreadable or spawn failure)"
elif trt_success and restore_ok:
    a_verdict, a_reason = "Viable", "A-trt success shape met AND A-restore returned to GLM-5.3"
elif prereg["candidates"] and all(c.get("planned", "").startswith("SKIP") for c in prereg["candidates"]):
    a_verdict, a_reason = "NotViable", "every preregistered mechanism exhausted, no landing moved"
else:
    a_verdict, a_reason = "Undetermined", "no successful treatment and no exhausted enumeration"

# ---------- B verdict, recomputed ----------
b0a_ran = b0a.get("runs_total") is not None
b0b_ran = b0b.get("perActorCwdFieldFound") is not None
b0c_ran = b0c.get("available") is not None
b1_constructed = False
if not (b0a_ran and b0b_ran and b0c_ran):
    b_verdict, b_reason = "NotViable", "a B0 gate failed to produce its required evidence"
elif not b1_constructed:
    b_verdict, b_reason = ("Undetermined",
                           "B0 all ran; B1 not constructed (activation table: B1 is not run when "
                           "a_verdict=Viable; independently not constructable because B0c "
                           "reports the model catalog is unavailable in the executing session)")
else:
    b_verdict, b_reason = "Viable", "B1 three assertions passed"

# ---------- DT-v1 evaluation ----------
DT = {("Viable", "Viable"): "D1", ("Viable", "NotViable"): "D1", ("Viable", "Undetermined"): "D1",
      ("NotViable", "Viable"): "D2", ("NotViable", "NotViable"): "D3",
      ("NotViable", "Undetermined"): "D4",
      ("Undetermined", "Viable"): "D5", ("Undetermined", "NotViable"): "D5",
      ("Undetermined", "Undetermined"): "D5"}
decision = DT[(a_verdict, b_verdict)]
assert len(DT) == 9, "DT-v1 table must cover 3x3 with no default cell"

# ---------- probe sessions + budget ----------
con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
cur = con.cursor()
sessions, total_tok, fam_count = [], 0, {}
kimi_sid = None
m = re.search(r'"session_id"\s*:\s*"([^"]+)"',
              open(os.path.join(PROBE, "p-k1-stream.jsonl"), encoding="utf-8",
                   errors="replace").read())
if m:
    kimi_sid = m.group(1)

for label, ev, channel in (("A-ctl", ctl, "zcode-headless-glm"),
                           ("A-trt-1-m1", trt, "zcode-headless-minimax-pinned"),
                           ("A-ctl2", ctl2, "zcode-headless-glm")):
    sid = ev["session_id"]
    row = cur.execute("select id from session where id=?", (sid,)).fetchone()
    it, ot = ev["db"]["input_tokens"], ev["db"]["output_tokens"]
    total_tok += it + ot
    fam = ("glm" if (ev["db"]["model_id_verbatim"] or "").startswith("GLM")
           else "minimax" if (ev["db"]["model_id_verbatim"] or "").lower().startswith("minimax")
           else "other")
    fam_count[fam] = fam_count.get(fam, 0) + 1
    sessions.append({"session_id": sid, "channel": channel, "probe_not_arm": True,
                     "ts": ev["ts"], "db_queryable": True, "found_in_db": bool(row),
                     "model_id_verbatim": ev["db"]["model_id_verbatim"],
                     "provider_id_verbatim": ev["db"]["provider_id_verbatim"],
                     "input_tokens": it, "output_tokens": ot})
con.close()
fam_count["step"] = 1  # K1 kimi head, no db accounting

probe_sessions = sessions + [{
    "session_id": kimi_sid, "channel": "kimi-cli-step-head", "probe_not_arm": True,
    "ts": k1["ts"], "db_queryable": False, "found_in_db": False,
    "db_query_note": "kimi CLI performs no db accounting (card-carried device fact); this "
                     "session therefore cannot appear in the session table. Recorded as an "
                     "explicit deviation rather than silently dropped.",
    "model_id_verbatim": None, "input_tokens": None, "output_tokens": None}]

model_call_rows = 4  # 3 zcode + 1 kimi (K2 skipped, no call made)

# ---------- coverage ----------
coverage_families = ["GLM-5.3 @ account:bigmodel-individual-coding-plan (headless default)",
                     "MiniMax-M3.1-Flash-Preview @ minimax (headless under M1 env override)"]

decision_doc = {
    "schema": "sf0004-decision/v1",
    "table_id": "SF-0004-DT-v1",
    "evalbench_version_at_decision": "v6-mvp-0.2",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "executor": "worker-minimax-v5 (minimax family)",

    "a_verdict": a_verdict,
    "a_verdict_reason": a_reason,
    "b_verdict": b_verdict,
    "b_verdict_reason": b_reason,
    "decision": decision,

    "a_probe": {
        "target_model_id": TARGET_MODEL,
        "ctl_session_id": ctl["session_id"],
        "ctl_model_id": ctl["db"]["model_id_verbatim"],
        "ctl_provider_id": ctl["db"]["provider_id_verbatim"],
        "trt_sessions": [trt["session_id"]],
        "mechanisms_enumerated": [{"id": c["id"], "mechanism": c["mechanism"],
                                   "disposition": c["planned"],
                                   "skip_reason": c.get("skip_reason", "")}
                                  for c in prereg["candidates"]],
        "mechanisms_executed": ["M1-paired-provider-config-env"],
        "landing_moved": bool(trt["db"]["model_id_verbatim"] == TARGET_MODEL),
        "restore_check": {"session_id": ctl2["session_id"],
                          "model_id_verbatim": ctl2["db"]["model_id_verbatim"],
                          "returned_to_glm": ctl2["db"]["model_id_verbatim"] == "GLM-5.3"},
        "mechanism_detail": {
            "M1": "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE + ZCODE_PERSONAL_PROVIDER_CONFIG_FILE "
                  "both pointed at derived copies under $PROBE/secret-scratch; the personal "
                  "copy set config.defaultModelSelection={providerId:'minimax', "
                  "modelId:'Minimax-M3.1-Flash-Preview'} and reordered providerOrder. "
                  "Static precondition discovered this card: resolveNodeProviderRuntimePaths "
                  "THROWS unless both variables are set, so the single-variable form the card "
                  "sketched would have failed at startup. No global file was touched.",
        },
    },

    "k_facts": {"step_head": k1["status"], "broker_head": "skipped_no_token",
                "step_head_note": "kimi 2.1.1 --output-format stream-json emits only "
                                  "system.version / assistant content / session.resume_hint; "
                                  "it carries no model identifier at all, so the landing is "
                                  "unobservable. exit 0 and the PONG reply prove the channel "
                                  "works; they do NOT identify the model.",
                "broker_note": k2["reason"]},

    "b_probe": {"gate1_catalog_available": b0c["available"],
                "gate1_classification": b0c["classification"],
                "gate2_schema_facts": {"dwf_actor_has_cwd_column": b0b["dwf_actor_has_cwd_column"],
                                       "perActorCwdFieldFound": b0b["perActorCwdFieldFound"],
                                       "declared_token_set": b0b["declared_token_set"],
                                       "token_hits": b0b["token_hits"]},
                "gate2_historical_prior": {"runs_total": b0a["runs_total"],
                                           "runs_with_ge2_actors": b0a["runs_with_ge2_actors"],
                                           "max_distinct_directory_per_run":
                                               b0a["max_distinct_directory_per_run"],
                                           "runs_with_distinct_gt1": b0a["runs_with_distinct_gt1"],
                                           "history_silent": b0a["history_silent"]},
                "gate3_executed": b1_constructed,
                "gate3_actors": [],
                "gate3_not_run_reason": b_reason},

    "sf_channel": {
        "glm": GLM_LANDING + " -- zcode headless default landing, db-verbatim in A-ctl and A-ctl2",
        "minimax": "minimax/" + TARGET_MODEL + " -- zcode headless landing under the M1 "
                   "env-scoped override, db-verbatim in A-trt-1-m1",
        "stepfun_zcode": "not_reached_this_round",
        "stepfun_zcode_note": "no zcode headless step-family pin was attempted; the M1 mechanism "
                              "was demonstrated on the minimax family only. Whether the same "
                              "mechanism reaches the step family via new-provider is UNTESTED.",
        "stepfun_kimi_head": "unobservable -- channel works (exit 0, correct reply) but kimi "
                             "2.1.1 stream-json carries no model id field",
        "coverage_claim_basis": "2 families proven at the db level on ONE channel (zcode "
                                "headless process-driven): GLM-5.3 by default and minimax only "
                                "under the env-scoped paired provider-config override. The kimi "
                                "step head is NOT counted (unobservable landing) and the broker "
                                "head was NOT exercised (no injected token).",
    },

    "probe_sessions": probe_sessions,
    "token_present": bool(any(v for v in k2["token_env_names_checked"].values())),

    "budget": {
        "model_call_rows": model_call_rows, "model_call_cap": 7,
        "per_family_counts": fam_count, "per_family_cap": 2,
        "db_backed_total_tokens": total_tok, "total_token_cap": 200000,
        "max_single_session_input_tokens": max(s["input_tokens"] for s in sessions),
        "per_session_input_cap": 8192,
        "per_session_cap_respected": max(s["input_tokens"] for s in sessions) <= 8192,
        "cap_conflict": "The card's per-session input cap of 8192 is unreachable on the zcode "
                        "headless channel: a PONG-level prompt costs ~23k input tokens of CLI "
                        "system prompt (23140 / 22718 / 23143 across A-ctl / A-trt / A-ctl2, "
                        "single attempt each). The aggregate cap (200000) is respected with "
                        "large margin. Registered as a caliber conflict, not silently passed.",
    },

    "rejected": [
        {"branch": "B (workflow per-actor cwd, PLAN §9.1 R-2)",
         "verdict": b_verdict,
         "falsified_mechanism": "per-actor cwd is absent from the recorded schema AND from the "
                                "implementation: PRAGMA dwf_actor has no cwd column, and 10 "
                                "declared per-actor directory tokens (actor_cwd, actorCwd, "
                                "perActorCwd, per_actor_cwd, actorWorkingDirectory, "
                                "actor_working_directory, actorDir, actor_dir, actorPath, "
                                "actor_path) produce 0 hits in the 14.8MB vendor bundle. "
                                "Historically 458 runs (319 of them multi-actor) yield "
                                "max 1 distinct directory per run and 0 runs with more than one.",
         "evidence_ref": "p-b0-static.json"},
        {"branch": "B historical prior", "verdict": b_verdict,
         "falsified_mechanism": "not 'untested' but zero-prior: dwf_actor joined to session and "
                                "grouped by run_id gives max_distinct_directory_per_run == 1 "
                                "across the entire live db.",
         "evidence_ref": "p-b0-prior.json"},
        {"branch": "C (accept single family)",
         "verdict": "NotViable",
         "falsified_mechanism": "falsified by A's measured success rather than by its own "
                                "evidence: the env-scoped paired provider-config override moved "
                                "the headless landing verbatim to " + TARGET_MODEL + " and the "
                                "mechanism restored cleanly to GLM-5.3, so the single-family "
                                "constraint has a working env-scoped remedy and 'accept single "
                                "family' is no longer forced.",
         "evidence_ref": "p-a-trt-trt-1-m1.json"},
        {"branch": "C quality-track unjudgeable registration",
         "verdict": "NotApplicable",
         "falsified_mechanism": "C's three fixed literals and followup-card draft are bound to "
                                "decision==D3; DT-v1 evaluated to D1, so C was not run. Skipped "
                                "explicitly rather than silently.",
         "evidence_ref": "a0-prereg.json"},
    ],

    "negative_space": [
        "O-5 four-family matrix is NOT established. Measured coverage is exactly 2 families on "
        "1 channel (zcode headless): GLM-5.3 by default, MiniMax-M3.1-Flash-Preview only under "
        "the M1 env-scoped override. Step family via zcode headless is untested; the kimi step "
        "head is unobservable; the broker head was not exercised (no injected token).",
        "R-3 step-channel normalizer is NOT validated. kimi 2.1.1 stream-json carries no model "
        "identifier, so a transcript normalizer has no ground truth to normalize against. K1 is "
        "registered 'unobservable', which is neither a pass nor a fail.",
        "O-7 cross-family judging is NOT proven on this machine. With the judged set at "
        "{GLM, minimax}, a judge would have to come from a third family; no third family is "
        "reachable with an observable landing, so the quality track stays unjudgeable.",
        "The M1 mechanism was demonstrated for the minimax family ONLY. Whether it reaches the "
        "step family (new-provider) or any other provider entry is untested.",
        "A-arm budget cap conflict: per-session input tokens exceeded the card's 8192 cap on "
        "every zcode session because of the CLI system prompt; the aggregate cap held.",
        "B1 was never constructed, so b_verdict is Undetermined. The static and historical "
        "negatives for branch B are strong but are NOT a functional falsification; a reviewer "
        "should treat 'branch B is dead' as an inference, not a measurement.",
    ],

    "ws4": {
        "startable": True,
        "glm_pin_changed": False,
        "glm_landing": GLM_LANDING,
        "matrix_shape": "two-family-headless-reachable (GLM default + minimax under M1 override)",
        "quality_track": "unjudgeable",
        "planner_confirm_required": True,
        "unblock_notes": "WS4 is startable per DT-v1 table two row D1, but ONLY after planner "
                         "records the matrix family-composition clause (one journal line). No "
                         "second evalbench bump is forced: the GLM arm five-tuple is unchanged "
                         "and its measured landing is verbatim " + GLM_LANDING + ". Any NEW "
                         "family is added as an incremental registration under baseline/<family>/ "
                         "(baseline/ is currently empty, so nothing is voided).",
    },

    "quality_track": {
        "verdict": "unjudgeable",
        "score": None,
        "ws4_matrix_field": "unjudgeable",
        "required_value": "must stay null; never 0, never omitted",
        "reason_ref": "p-k1-step.json",
        "reason_ref_note": "the only third-family candidate (kimi step head) cannot identify its "
                           "own landing, so no family outside {GLM, minimax} is available to "
                           "judge; O-7 is therefore unsatisfiable this round and the score is "
                           "null by construction, not by omission.",
        "claim_boundary": "This round's quality track is unjudgeable: O-7 requires the judging "
                         "family to have no intersection with the round's tested set, and no "
                         "such family was shown reachable with an observable landing on this "
                         "machine before work started. Therefore no quality score, no "
                         "cross-family conclusion, and no claim that asset quality has been "
                         "validated across families. Artifact-track and process-track "
                         "conclusions are unaffected by this limit.",
    },

    "executor_note": "Executed by worker-minimax-v5 (minimax family). The decision is computed "
                     "from raw probe evidence by gen_deliverables.py and independently "
                     "recomputed from the same evidence by verify_sf0004.py; a mismatch is exit "
                     "1. Complex-reasoning items flagged for stronger-model review: (1) "
                     "classifying branch B as effectively dead on static+historical evidence "
                     "without a functional B1 attempt; (2) the D1 matrix_shape wording, which "
                     "DT-v1 table two does not fix for D1.",
}

w_json(JSONOUT, decision_doc)

# ---------------- report ----------------
with open(ACCEPT, encoding="utf-8") as f:
    accept_txt = f.read()
block = re.search(r"<!-- DT-v1:BEGIN -->(.*?)<!-- DT-v1:END -->", accept_txt, re.S).group(1).rstrip("\n")
# The markers are part of the block contract: D2 locates the block by them, so they must
# travel with the copied content into the report.
block = "<!-- DT-v1:BEGIN -->\n" + block + "\n<!-- DT-v1:END -->"

R = f"""# SF-0004 · headless 单族限制技术决断（{decision}）

> 执行：worker-minimax-v5（minimax 族）· 2026-10-04
> 判据：`tests/visible/SF-0004-accept.md`（planner 所有，worker 零写权限）
> 汇总器：`python D:\\new-workspace\\agent-asset\\planning\\reports\\sf0004-probes\\verify_sf0004.py`
> 结论由冻结表 DT-v1 从门值算出；本报告不预设胜负，**本卡是决断不是验收结论**。

## 0. 一句话结论

**headless 单族限制可解，且不需要新凭据、不改任何全局文件**：zcode headless 只要同时给出
`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` 与 `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` 指向**派生副本**，
落点即可逐字钉到非 GLM 族（实测 `{TARGET_MODEL}` @ `minimax`），撤除机制后干净回到
`GLM-5.3`。故 **{a_verdict}={a_verdict}** → DT-v1 求值 **{decision}**。

## 1. 结论码与门值

| 门 | 取值 | 依据（原始证据） |
|---|---|---|
| a_verdict | **{a_verdict}** | {a_reason} |
| b_verdict | **{b_verdict}** | {b_reason} |
| decision | **{decision}** | DT-v1 表一求值（A=Viable 短路，B 列不阻断） |
| K1 step 头 | **{k1["status"]}** | kimi 2.1.1 stream-json 无 model id 字段 |
| K2 broker 头 | **skipped_no_token** | 进程环境未注入 vault 短期 token（仅扫变量名，未读值） |

## 2. DT-v1 冻结决断表（逐字内嵌，自验收文件程序化抄录，非手打）

{block}

## 3. A 支证据：枚举 → 可读性 → 落点比对

预登记 5 条机制（`a0-prereg.json`，**实跑集合 ⊆ 预登记集合**，P1 绿）。两条在花掉模型调用
之前就被静态证伪：

- **M2 `ZCODE_ENABLED_AGENT_PROVIDERS`**：schema 是 `m.array(zO).transform(()=>[...qpe])`，
  transform 直接丢弃入参、恒返回 `["glm"]`。机制**构造上即死**，0 调用。
- **M5 探针 cwd 级配置发现**：provider 配置自 `environmentConfigRoot`（`~/.zcode/v2`）解析，
  bundle 内无 cwd 相对发现路径。（SF-0001 的 cwd 相对发现属于 **skills**，不迁移到 provider。）

实跑 **M1**，并在此补上卡文没有的一条**硬前置**：

> `resolveNodeProviderRuntimePaths` 在只给一个变量时**抛错**——`ZCode Built-in 与 Personal
> Provider Config 路径必须同时提供`。卡文草拟的单变量形态会在启动即失败。必须成对注入。

| 臂 | 机制 | exit | session.directory==臂目录 | model_usage 可 join | model_id 逐字 | provider_id 逐字 |
|---|---|---|---|---|---|---|
| A-ctl | 裸 headless | {ctl["exit_code"]} | {str(ctl["db"]["directory_match"]).lower()} | {str(ctl["db"]["model_usage_rows"] > 0).lower()} | `{ctl["db"]["model_id_verbatim"]}` | `{ctl["db"]["provider_id_verbatim"]}` |
| A-trt-1 | M1 成对 env | {trt["exit_code"]} | {str(trt["db"]["directory_match"]).lower()} | {str(trt["db"]["model_usage_rows"] > 0).lower()} | `{trt["db"]["model_id_verbatim"]}` | `{trt["db"]["provider_id_verbatim"]}` |
| A-ctl2 | 机制撤除后裸跑 | {ctl2["exit_code"]} | {str(ctl2["db"]["directory_match"]).lower()} | {str(ctl2["db"]["model_usage_rows"] > 0).lower()} | `{ctl2["db"]["model_id_verbatim"]}` | `{ctl2["db"]["provider_id_verbatim"]}` |

- 落点比对：A-trt 逐字命中预登记目标串 `{TARGET_MODEL}`（**大小写敏感**，与 db 字面一致；
  db 中另存在 `MiniMax-M3.1-Flash-Preview` 仅 16 行的另一拼法，本卡未混用）。
- 装置阳性对照成立：A-ctl 装置本身可用（不是 infra 故障），故 A 分支的结论不是探针不可判。
- 复原复核通过：派生副本已删（`scratch_purged=true`，并断言目录不存在）后裸跑逐字回 GLM-5.3，
  说明机制**不破坏既有 GLM 钉版**。
- A-trt 与 A-ctl 时间差 ≤3600s（同分钟内）。

## 4. B 支证据（B0 逐门）

| 门 | 结果 | 事实 |
|---|---|---|
| B0a 历史先验 | **history_silent={str(b0a["history_silent"]).lower()}** | {b0a["runs_total"]} runs（其中 {b0a["runs_with_ge2_actors"]} 个多 actor），max distinct directory = **{b0a["max_distinct_directory_per_run"]}**，>1 的 run = **{b0a["runs_with_distinct_gt1"]}**。口径= `dwf_actor JOIN session GROUP BY run_id count(distinct directory)`，未用时间窗近似 |
| B0b 静态普查 | **perActorCwdFieldFound={str(b0b["perActorCwdFieldFound"]).lower()}** | `dwf_actor` 无 `cwd` 列；10 个声明 token 在 14.8MB bundle 中命中 0 |
| B0c 宿主目录 | **available={str(b0c["available"]).lower()}** | `{b0c["classification"]}`：worker 会话无 ListModels 等价工具，kimi 2.1.1 无 model 枚举子命令 |
| B1 | **not_run** | 激活真值表：A=Viable 时 B1 不跑；独立地，因 B0c 目录不可用亦不可构造 |

**b_verdict 取 Undetermined 的理由**：B1 从未构造，故 B 支**没有功能层证伪**。B0b/B0a 的
静态与历史反证很强，但把「B 支已死」当成**实测**是过宽的结论——本卡拒绝这么写。

## 5. 落选理由留痕

- **B 支**：机制层反证已列（schema 无列 + bundle 零 token + 458 run 零先验），但 verdict 仍记
  `Undetermined`，证据 `p-b0-static.json` / `p-b0-prior.json`。
- **C 支（接受单族）**：被 A 支实测成功**证伪**——单族约束有 env-scoped 解法，不必接受单族。
  C 的三句固定字面 + followup 草案绑在 `decision==D3`，本轮 DT-v1 求值为 D1，故**显式跳过**
  而非静默不跑（激活真值表要求 skip 必须有显式行 + 理由）。
- **M2 / M5**：静态证伪，0 模型调用，已在 `a0-prereg.json` 与本报告登记。

## 6. 跨族覆盖面与宽度上限（措辞不得宽于证据）

- **实测覆盖面 = 2 族，且只在 1 条通道（zcode headless 进程驱动）上**：
  `GLM-5.3` @ `{GLM_LANDING}`（默认）+ `{TARGET_MODEL}` @ `minimax`（**仅在 M1 env 覆盖下**）。
- **不并入**：kimi step 头（落点 unobservable）；kimi broker 头（未注入 token，未跑）。
- **不声称**：四族矩阵成立；step 族经 zcode headless 可钉（未测）；资产质量已跨族验证。

## 7. 对 WS4 的影响

- **startable = true**，但**前置**：planner 在开卡前须显式确认矩阵族构成条款（一行 journal，
  未确认不开工）——这是 DT-v1 表二 D1 行的硬条件。
- **pin 契约不变**：GLM 臂五元组不变，实测落点逐字 `{GLM_LANDING}`，**不触发第二次 bump**。
  新增族按增量登记进 `baseline/<family>/`（`baseline/` 现为空，无存量可作废）。
- **质量轨 unjudgeable**：`score` 恒 `null`（不许填 0、不许省略键）。原因是被测集已占满
  {{GLM, minimax}} 两族，而本机没有第三个**落点可观测**的族可当异族裁判（O-7 不满足）。
- D1 行另注：若 WS4 首轮 ≥2 族且裁判异族可满足才出分，否则**仍 unjudgeable**。

WS4-PRE: done-gate={decision}-resolved; pin=unchanged-no-second-bump; glm_landing={GLM_LANDING}; quality=unjudgeable-pending-planner-family-composition-confirmation

## 8. Negative space（本卡**没有**证明的）

""" + "\n".join("- " + s for s in decision_doc["negative_space"]) + f"""

## 9. 凭据与记账留痕

- **密钥/token 零落盘**：探针只用 env 注入的派生副本（内容在 `secret-scratch`，用后即删并断言
  不存在）；证据只登记 `token_present` 布尔与配置 sha256，**任何 api/access 值都未进入任何产物或回显**。
- **全局配置零改动**：`~/.zcode/cli/config.json`、`~/.zcode/v2/provider_config.json`、
  `~/.kimi-code/config.toml` 三者 sha256 收工前后**逐字节相等**（G5 绿），未使用 try/finally 临时改协议。
- **evalkit 零写入**：全树 os.walk 开工/收工差分 = ∅（含 `runs/`），freeze 16 文件前后全对，
  oracle 树 31 文件 sha256 前后一致。
- **afp-clone 零改动**：`git status --porcelain` 开工/收工差分 = ∅，与六封存区路径交集 = ∅。
- **记账污染留痕**：全部探针 session 在 `decision.json.probe_sessions` 标 `probe_not_arm=true`
  （`model_usage` 是通道事实表与限流率门的数据源，不许当臂数字引用）。
- **预算**：model_call 行 {model_call_rows}/7；每族 ≤2；db 侧 token 合计 {total_tok:,}/200,000。
  **单会话 input 上限 8192 未达成**（zcode headless 的 CLI 系统提示本身约 23k，PONG 级提示亦然：
  23140 / 22718 / 23143），按口径冲突登记，见下节。

## 10. 口径说明（不改判据、只留证据）

1. **单会话 input token 上限不可达**：卡文硬上限 8192 与 zcode headless 装置现实冲突。
   三个 session 的 input 分别为 23140 / 22718 / 23143，均为单次尝试，差额即 CLI 系统提示。
   处置：判据不改、证据全留、**不静默放行**；`decision.json.budget.per_session_cap_respected=false`
   由汇总器如实判红，裁不裁由 planner 定。
2. **kimi session 不可 db 查**：验收 D8 要求 probe_sessions 逐条可在 `$DB session 表查到`，
   但卡载事实已写明「kimi CLI 无 db 记账」。处置：该 session 以 `db_queryable=false` + 理由显式
   登记，不静默丢弃；汇总器只对 `db_queryable=true` 的条目做查表断言。
3. **db 行数与卡载数字的漂移**：卡文 dwf_run 471 / dwf_actor 2817 / GLM-5.3 24139 /
   GLM-5.3-Flash 110471；实测（活库，会话持续写入）476 / 2834 / 24224 / 110582。方向一致、
   属自然增长，结论不受影响。
4. **db 文件大小**：卡文 3.59GB，实测 3.35GB（3,354,674,176 字节级取整差异），不影响任何判据。

## 11. 未尽事项

1. **B 支未被功能证伪**：若 planner 要把「B 死」当结论用，需另开卡提供有模型目录的宿主会话复测
   门 3，或接受本卡的静态+历史推断（**建议强模型复核**）。
2. **M1 只在 minimax 族验证过**：能否钉到 step 族（new-provider）未测，是 WS4 族构成的直接输入。
3. **配置文档化另开卡**：M1 的成对 env 契约（必须成对、单给即抛错）需写进 evalkit 文档，
   否则下一个跑批的人会踩同一个坑。
4. **per-session token 上限**待 planner 裁定：改判据（放宽到 32k 级）或改探针装置（不可行，
   系统提示不可裁剪），本卡不代拍。
5. **未 commit / 未 push**（红线 6 + ESC-008）：全部改动留在工作树，提交批次由 planner 统一定夺。

## 12. 执行记录（PROTOCOL §3 四要素）

- **做了什么**：P 组 4 门预检（0 模型）→ A0 预登记 5 机制 → A 组 3 调用（ctl / trt-M1 / 复原）
  → K 组 1 调用 + 1 跳过行 → B 组 3 个零成本门 → 收尾三守卫 + G6/G7 → 汇总器复算。
- **关键发现**：① `resolveNodeProviderRuntimePaths` 单变量即抛错，卡文草拟形态不可用；
  ② `ZCODE_ENABLED_AGENT_PROVIDERS` 被 schema transform 吞掉，机制构造上即死；
  ③ personal v2 配置 `defaultModelSelection` 为 null——这正是 headless 回落到 builtin GLM 的结构性原因；
  ④ zcode headless 的 input 下限约 23k，与卡文 8192 上限冲突。
- **卡在哪**：B1 不可构造（无模型目录宿主）；K2 无注入 token；单会话 token 上限超限待裁。
- **下一步（命令级）**：planner 复跑
  `python D:\\new-workspace\\agent-asset\\planning\\reports\\sf0004-probes\\verify_sf0004.py`
  （exit 0 = 全绿；本卡因单会话 token 上限判红一项，见 §10.1），并抽验
  `p-a-trt-trt-1-m1.json` / `p-a-ctl2.json` 原始证据与 WS4-PRE 行对账。
"""

with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
    f.write(R)

print(json.dumps({"decision": decision, "a_verdict": a_verdict, "b_verdict": b_verdict,
                  "report": REPORT, "json": JSONOUT,
                  "total_db_tokens": total_tok,
                  "ws4_pre_occurrences": R.count("WS4-PRE:")}, ensure_ascii=False, indent=2))
