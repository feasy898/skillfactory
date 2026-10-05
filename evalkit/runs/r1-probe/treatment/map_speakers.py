#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""map_speakers.py — diarization 转写稿说话人标签映射工具（仅标准库）。

用法：
  发现（扫描）模式：
    python map_speakers.py --discover --transcript T.txt [--out draft.json]
  应用（替换）模式：
    python map_speakers.py --transcript T.txt --mapping M.json --out O.txt

安全特性：
  - 只替换行首（可带时间戳前缀 `[..]`）的 ASCII 标签 span；时间戳段、冒号
    （半角/全角）、空白、正文、行数、行尾风格（CRLF/LF）全部与输入逐字节一致；
  - 行中出现的 `SPEAKER_xx:`（标签不在行首）不识别、不替换；
  - 未映射标签（含映射值为空串 ""）原样保留并汇总告警，绝不猜名替换；
  - 映射键在转写稿中未出现时告警；
  - 确定性输出：无网络、无随机数、无时间戳，同输入重跑逐字节一致。

已知限制：英文冒号行（如 `Note: ...`）也会命中标签正则；标签 token 仅支持
ASCII（SPEAKER_00、Agent_A 等）；一行只识别行首一个标签。

退出码：
  0 = 成功（含有告警但成功的情况）
  1 = 映射文件不是合法 JSON / 顶层不是对象 / 键值不是字符串
  2 = 输入文件不存在 / 命令行参数错误
"""

import argparse
import json
import re
import sys

# 全角冒号 U+FF1A 的 UTF-8 字节（识别时与半角冒号同等对待，替换时逐字节保留）
FULLWIDTH_COLON = "\uff1a".encode("utf-8")

# 行首标签正则（字节级）：可选时间戳前缀 `[..]` + 空白，随后 ASCII 标签 token，
# 紧跟半角或全角冒号。只替换 group(2) 这个标签 span。
LABEL_RE = re.compile(
    rb"^(\[[^\]]*\][ \t]*)?([A-Za-z_][A-Za-z0-9_]*)(:|"
    + re.escape(FULLWIDTH_COLON)
    + rb")"
)


def emit(msg):
    """向 stderr 写一行 UTF-8 消息（绕过文本层，保证重定向存档为 UTF-8）。"""
    sys.stderr.buffer.write((msg + "\n").encode("utf-8"))
    sys.stderr.buffer.flush()


def die(code, msg):
    emit(msg)
    sys.exit(code)


def read_file(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        die(2, "ERROR: 输入文件不存在: %s" % path)
    except OSError as e:
        die(2, "ERROR: 无法读取输入文件 %s（%s）" % (path, e))


def load_mapping(path):
    """读入映射 JSON；不是合法 JSON / 顶层非对象 / 键值非字符串时退出码 1。"""
    raw = read_file(path)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        die(1, "ERROR: 映射文件不是合法 JSON: %s（%s）" % (path, e))
    if not isinstance(obj, dict):
        die(1, "ERROR: 映射文件顶层必须是 JSON 对象: %s" % path)
    for k, v in obj.items():
        if not isinstance(k, str) or not isinstance(v, str):
            die(1, "ERROR: 映射文件的键与值必须是字符串: %s" % path)
    return obj


def split_lines(data):
    """按行切分并保留每行的行尾（LF/CRLF 原样保留，写出时拼回逐字节一致）。"""
    return data.splitlines(keepends=True)


def scan(data):
    """扫描转写稿：返回 (行列表, 标签首次出现顺序, 标签->条数, 带标签发言总数)。"""
    lines = split_lines(data)
    order = []
    counts = {}
    total = 0
    for line in lines:
        m = LABEL_RE.match(line)
        if m:
            label = m.group(2).decode("ascii")
            total += 1
            if label not in counts:
                order.append(label)
                counts[label] = 0
            counts[label] += 1
    return lines, order, counts, total


def cmd_discover(args):
    data = read_file(args.transcript)
    lines, order, counts, total = scan(data)
    result = {
        "transcript": args.transcript,
        "total_utterances": total,
        "speakers": [{"label": lb, "utterances": counts[lb]} for lb in order],
        "draft_mapping": {lb: "" for lb in order},
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        try:
            with open(args.out, "wb") as f:
                f.write(text.encode("utf-8"))
        except OSError as e:
            die(2, "ERROR: 无法写出 %s（%s）" % (args.out, e))
        emit(
            "INFO: 写出 %s（共 %d 行，替换 0 处，未映射 %d 种）"
            % (args.out, len(lines), len(order))
        )
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    sys.exit(0)


def cmd_apply(args):
    data = read_file(args.transcript)
    mapping = load_mapping(args.mapping)

    lines = split_lines(data)
    out_lines = []
    present = {}            # 标签 -> 出现条数（含未映射）
    unmapped = {}           # 未映射标签 -> 出现条数（映射表没填或填了空串）
    unmapped_order = []     # 未映射标签首次出现顺序
    replaced = 0
    for line in lines:
        m = LABEL_RE.match(line)
        if m:
            label = m.group(2).decode("ascii")
            present[label] = present.get(label, 0) + 1
            name = mapping.get(label, "")
            if name:
                # 只替换标签 span：前缀（时间戳+空白）与冒号起的内容逐字节不动
                out_lines.append(
                    line[: m.start(2)] + name.encode("utf-8") + line[m.end(2):]
                )
                replaced += 1
            else:
                out_lines.append(line)
                if label not in unmapped:
                    unmapped_order.append(label)
                    unmapped[label] = 0
                unmapped[label] += 1
        else:
            out_lines.append(line)

    for lb in unmapped_order:
        emit(
            'WARNING: 未映射说话人标签 "%s"，出现 %d 次，已原样保留'
            % (lb, unmapped[lb])
        )
    for key in mapping:
        if key not in present:
            emit('WARNING: 映射键 "%s" 在转写稿中未出现' % key)

    try:
        with open(args.out, "wb") as f:
            f.write(b"".join(out_lines))
    except OSError as e:
        die(2, "ERROR: 无法写出 %s（%s）" % (args.out, e))
    emit(
        "INFO: 写出 %s（共 %d 行，替换 %d 处，未映射 %d 种）"
        % (args.out, len(lines), replaced, len(unmapped_order))
    )
    sys.exit(0)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="map_speakers.py",
        description="diarization 转写稿说话人标签映射：--discover 扫描出草稿，"
        "或用 --mapping 把行首标签替换为人名（只换标签 span，其余逐字节不动）",
    )
    p.add_argument("--discover", action="store_true",
                   help="扫描模式：统计标签并产出草稿映射 JSON")
    p.add_argument("--transcript", required=True, help="转写稿路径（UTF-8 文本）")
    p.add_argument("--mapping", help="标签→人名 JSON 映射表（apply 模式必填）")
    p.add_argument("--out",
                   help="输出路径（apply 必填；discover 省略时打印到 stdout）")
    args = p.parse_args(argv)

    if args.discover:
        if args.mapping:
            p.error("--discover 模式不接受 --mapping")
        cmd_discover(args)
    else:
        if not args.mapping:
            p.error("apply 模式需要 --mapping")
        if not args.out:
            p.error("apply 模式需要 --out")
        cmd_apply(args)


if __name__ == "__main__":
    main()
