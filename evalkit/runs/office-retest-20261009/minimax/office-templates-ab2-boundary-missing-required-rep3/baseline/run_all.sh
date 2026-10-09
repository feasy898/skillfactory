#!/usr/bin/env bash
# 渲染两个单元目录的产物（每个目录恰含 文书.docx 与 fields.json）
set -euo pipefail
cd "$(dirname "$0")"
for t in 请示函 会议通知; do
  python3 gen_doc.py --template "$t" --data "fixtures/$t/case2.json" --outdir "out/$t/case2"
done