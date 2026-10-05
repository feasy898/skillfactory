#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ofc-03/gen_oracle.py — 生成器薄包装 → harness/ws4_gen.py（判分逻辑零副本）。

用法：
    python gen_oracle.py [--seed N] [--nonce-set A|B] --out <dir>   生成实例+oracle
    python gen_oracle.py --selftest                                 BQ-8/9/10 三合一自检
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "harness")
sys.path.insert(0, HARNESS)
import ws4_gen  # noqa: E402

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(ws4_gen.main(os.path.basename(HERE), sys.argv[1:]))
