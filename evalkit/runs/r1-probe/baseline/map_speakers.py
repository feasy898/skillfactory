#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会议转写稿说话人标签映射 / 扫描工具（仅标准库）。

用法：
    python map_speakers.py map      <转写稿> <映射表.json> <输出.txt>
    python map_speakers.py discover <转写稿> <输出.json>

map 模式：把转写稿行首的 SPEAKER_xx 标签换成映射表里的姓名，其余字节
（时间戳、冒号、空白、正文、行数、行尾风格）与输入完全一致；映射表里
没有的标签原样保留并告警，绝不猜名。

discover 模式：扫描转写稿中的说话人标签，产出 JSON 草稿，含 transcript /
total_utterances / speakers（按首次出现顺序）/ draft_mapping（各标签映射
到空字符串）四个字段。

诊断信息全部走 stderr：WARNING 逐条告警，每次成功写出追加一行 INFO 汇总。

退出码：0 成功（含有告警但成功）；1 映射文件不是合法 JSON（或不是
键值均为字符串的 JSON 对象）；2 输入文件不存在或命令行参数错误。
"""

import json
import re
import sys

EXIT_OK = 0
EXIT_BAD_MAPPING = 1
EXIT_BAD_ARGS = 2

USAGE = (
    "用法:\n"
    "  python map_speakers.py map <转写稿> <映射表.json> <输出.txt>\n"
    "  python map_speakers.py discover <转写稿> <输出.json>"
)

# 行首标签：可选前导空白 + 可选 [时间戳] 段 + SPEAKER_编号 + 冒号。
# 只捕获标签段本身，时间戳/空白/冒号原样保留；正文中的 SPEAKER_xx 不受影响。
LABEL_LINE_RE = re.compile(
    rb"^([ \t]*(?:\[[^\]\r\n]*\][ \t]*)?)(SPEAKER_[0-9]+)(?=[ \t]*:)"
)


def stderr_write(text):
    sys.stderr.write(text + "\n")


def info(msg):
    stderr_write("INFO: " + msg)


def warn(msg):
    stderr_write("WARNING: " + msg)


def fail(msg, code):
    stderr_write("ERROR: " + msg)
    return code


def split_terminator(line):
    """把一行拆成（正文, 行尾符），行尾符逐字节保留原样。"""
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n") or line.endswith(b"\r"):
        return line[:-1], line[-1:]
    return line, b""


def read_transcript(path):
    with open(path, "rb") as f:
        return f.read()


def scan_labels(raw):
    """返回（按首次出现顺序的标签列表, 标签->出现次数, 总行数）。"""
    order = []
    counts = {}
    for line in raw.splitlines(keepends=True):
        body, _ = split_terminator(line)
        m = LABEL_LINE_RE.match(body)
        if not m:
            continue
        label = m.group(2).decode("ascii")
        if label not in counts:
            counts[label] = 0
            order.append(label)
        counts[label] += 1
    return order, counts


def load_mapping(path):
    """读入映射表；返回 (mapping, 错误说明, 退出码)。

    读不到文件按「输入文件不存在」处理（退出码 2），
    内容不是合法 JSON / 合法映射表才是退出码 1。
    """
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        return None, "无法读取映射文件 %s: %s" % (path, e.strerror or e), EXIT_BAD_ARGS
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as e:
        return None, "映射文件 %s 不是合法 JSON: %s" % (path, e), EXIT_BAD_MAPPING
    if not isinstance(obj, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in obj.items()
    ):
        return None, (
            "映射文件 %s 不是合法映射表：顶层必须是 JSON 对象，"
            "且键与值均为字符串" % path
        ), EXIT_BAD_MAPPING
    return obj, None, EXIT_OK


def cmd_map(transcript_path, mapping_path, out_path):
    try:
        raw = read_transcript(transcript_path)
    except OSError as e:
        return fail(
            "输入转写稿不存在或无法读取 %s: %s"
            % (transcript_path, e.strerror or e),
            EXIT_BAD_ARGS,
        )

    mapping, err, code = load_mapping(mapping_path)
    if mapping is None:
        return fail(err, code)

    lines = raw.splitlines(keepends=True)
    out_parts = []
    replaced = 0
    order, counts = [], {}
    for line in lines:
        body, term = split_terminator(line)
        m = LABEL_LINE_RE.match(body)
        if m:
            label = m.group(2).decode("ascii")
            if label not in counts:
                counts[label] = 0
                order.append(label)
            counts[label] += 1
            if label in mapping:
                body = body[: m.start(2)] + mapping[label].encode("utf-8") + body[m.end(2):]
                replaced += 1
        out_parts.append(body + term)

    try:
        with open(out_path, "wb") as f:
            f.write(b"".join(out_parts))
    except OSError as e:
        return fail(
            "无法写出 %s: %s" % (out_path, e.strerror or e), EXIT_BAD_ARGS
        )

    unmapped = [label for label in order if label not in mapping]
    for label in unmapped:
        warn('未映射说话人标签 "%s"，出现 %d 次' % (label, counts[label]))
    for key in mapping:
        if key not in counts:
            warn('映射键 "%s" 在转写稿中未出现' % key)
    info(
        "写出 %s（共 %d 行，替换 %d 处，未映射 %d 种）"
        % (out_path, len(lines), replaced, len(unmapped))
    )
    return EXIT_OK


def cmd_discover(transcript_path, out_path):
    try:
        raw = read_transcript(transcript_path)
    except OSError as e:
        return fail(
            "输入转写稿不存在或无法读取 %s: %s"
            % (transcript_path, e.strerror or e),
            EXIT_BAD_ARGS,
        )

    lines = raw.splitlines(keepends=True)
    order, counts = scan_labels(raw)
    result = {
        "transcript": transcript_path,
        "total_utterances": sum(counts.values()),
        "speakers": [
            {"label": label, "utterances": counts[label]} for label in order
        ],
        "draft_mapping": {label: "" for label in order},
    }
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    try:
        with open(out_path, "wb") as f:
            f.write(payload)
    except OSError as e:
        return fail(
            "无法写出 %s: %s" % (out_path, e.strerror or e), EXIT_BAD_ARGS
        )

    info(
        "写出 %s（共 %d 行，发现说话人 %d 种，发言 %d 条）"
        % (out_path, len(lines), len(order), sum(counts.values()))
    )
    return EXIT_OK


def main(argv):
    # 归一化诊断输出编码，保证重定向到文件时内容始终是 UTF-8
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    if len(argv) >= 2 and argv[1] == "map":
        if len(argv) != 5:
            return fail("参数错误，需要 3 个参数。\n" + USAGE, EXIT_BAD_ARGS)
        return cmd_map(argv[2], argv[3], argv[4])
    if len(argv) >= 2 and argv[1] == "discover":
        if len(argv) != 4:
            return fail("参数错误，需要 2 个参数。\n" + USAGE, EXIT_BAD_ARGS)
        return cmd_discover(argv[2], argv[3])
    return fail("参数错误。\n" + USAGE, EXIT_BAD_ARGS)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
