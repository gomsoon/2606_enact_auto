#!/usr/bin/env python3

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import TextIO


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


def parse_percent(value: str) -> float:
    try:
        percent = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid percentage: {value!r}") from exc

    if percent < 0.0 or percent > 100.0:
        raise argparse.ArgumentTypeError(f"percentage must be between 0 and 100: {value!r}")
    return percent


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report gcov coverage for handwritten ENACT C sources.")
    parser.add_argument(
        "--min-lines",
        type=parse_percent,
        default=None,
        help="minimum required total line coverage percentage",
    )
    parser.add_argument(
        "--min-branches",
        type=parse_percent,
        default=None,
        help="minimum required total branch coverage percentage",
    )
    return parser.parse_args(argv)


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


def collect_coverage(
    files: list[str] | None = None,
    root: pathlib.Path = ROOT,
    error_stream: TextIO = sys.stderr,
) -> tuple[list[tuple[str, int, int, int, int]], list[int]] | None:
    selected_files = files if files is not None else FILES
    rows: list[tuple[str, int, int, int, int]] = []
    aggregate = [0, 0, 0, 0]

    for name in selected_files:
        path = root / name
        if not path.exists():
            print(f"missing coverage file: {name}", file=error_stream)
            return None
        line_hit, line_total, branch_hit, branch_total = parse_file(path)
        aggregate[0] += line_hit
        aggregate[1] += line_total
        aggregate[2] += branch_hit
        aggregate[3] += branch_total
        rows.append((name, line_hit, line_total, branch_hit, branch_total))

    return rows, aggregate


def print_coverage(rows: list[tuple[str, int, int, int, int]], aggregate: list[int]) -> None:
    print("Coverage summary (handwritten sources):")
    for name, line_hit, line_total, branch_hit, branch_total in rows:
        print(
            f"  {name:<18} "
            f"lines {line_hit:>3}/{line_total:<3} ({pct(line_hit, line_total):5.1f}%)  "
            f"branches {branch_hit:>3}/{branch_total:<3} ({pct(branch_hit, branch_total):5.1f}%)"
        )

    print(
        f"TOTAL lines {aggregate[0]}/{aggregate[1]} ({pct(aggregate[0], aggregate[1]):.1f}%)  "
        f"branches {aggregate[2]}/{aggregate[3]} ({pct(aggregate[2], aggregate[3]):.1f}%)"
    )


def check_thresholds(
    line_percent: float,
    branch_percent: float,
    min_lines: float | None,
    min_branches: float | None,
    error_stream: TextIO = sys.stderr,
    output_stream: TextIO = sys.stdout,
) -> int:
    failed = False

    if min_lines is not None and line_percent < min_lines:
        print(
            f"Coverage gate failed: lines {line_percent:.1f}% is below required {min_lines:.1f}%",
            file=error_stream,
        )
        failed = True
    if min_branches is not None and branch_percent < min_branches:
        print(
            f"Coverage gate failed: branches {branch_percent:.1f}% is below required {min_branches:.1f}%",
            file=error_stream,
        )
        failed = True

    if failed:
        return 1

    if min_lines is not None or min_branches is not None:
        gates = []
        if min_lines is not None:
            gates.append(f"lines {line_percent:.1f}% >= {min_lines:.1f}%")
        if min_branches is not None:
            gates.append(f"branches {branch_percent:.1f}% >= {min_branches:.1f}%")
        print(f"Coverage gate passed: {'; '.join(gates)}", file=output_stream)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = collect_coverage()
    if result is None:
        return 2
    coverage_rows, coverage_aggregate = result
    print_coverage(coverage_rows, coverage_aggregate)
    return check_thresholds(
        pct(coverage_aggregate[0], coverage_aggregate[1]),
        pct(coverage_aggregate[2], coverage_aggregate[3]),
        args.min_lines,
        args.min_branches,
    )


if __name__ == "__main__":
    raise SystemExit(main())
