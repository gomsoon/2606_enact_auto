#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]

FILES = [
    "ast.c.gcov",
    "function.c.gcov",
    "object.c.gcov",
    "builtin.c.gcov",
    "value.c.gcov",
    "diag.c.gcov",
    "runtime_stats.c.gcov",
    "env.c.gcov",
    "parser_state.c.gcov",
    "eval.c.gcov",
    "api.c.gcov",
    "scan.c.gcov",
    "main.c.gcov",
]


def parse_file(path: pathlib.Path) -> tuple[int, int, int, int]:
    line_total = 0
    line_hit = 0
    branch_total = 0
    branch_hit = 0

    for raw_line in path.read_text().splitlines():
        line_match = re.match(r"^\s*([0-9]+|#####|-)\:(\s*[0-9]+)\:", raw_line)
        if line_match:
            count = line_match.group(1)
            if count != "-":
                line_total += 1
                if count != "#####":
                    line_hit += 1

        branch_match = re.search(r"branch\s+\d+\s+taken\s+([0-9]+)|branch\s+\d+\s+never executed", raw_line)
        if branch_match:
            branch_total += 1
            if "never executed" not in raw_line and int(branch_match.group(1)) > 0:
                branch_hit += 1

    return line_hit, line_total, branch_hit, branch_total


def pct(hit: int, total: int) -> float:
    return 0.0 if total == 0 else hit * 100.0 / total


def main() -> int:
    aggregate = [0, 0, 0, 0]

    print("Coverage summary (handwritten sources):")
    for name in FILES:
        path = ROOT / name
        if not path.exists():
            print(f"missing coverage file: {name}", file=sys.stderr)
            return 2
        line_hit, line_total, branch_hit, branch_total = parse_file(path)
        aggregate[0] += line_hit
        aggregate[1] += line_total
        aggregate[2] += branch_hit
        aggregate[3] += branch_total
        print(
            f"  {name:<18} "
            f"lines {line_hit:>3}/{line_total:<3} ({pct(line_hit, line_total):5.1f}%)  "
            f"branches {branch_hit:>3}/{branch_total:<3} ({pct(branch_hit, branch_total):5.1f}%)"
        )

    print(
        f"TOTAL lines {aggregate[0]}/{aggregate[1]} ({pct(aggregate[0], aggregate[1]):.1f}%)  "
        f"branches {aggregate[2]}/{aggregate[3]} ({pct(aggregate[2], aggregate[3]):.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
