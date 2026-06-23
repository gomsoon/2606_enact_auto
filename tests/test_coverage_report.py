#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import io
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
COVERAGE_REPORT = ROOT / "tools" / "coverage_report.py"


def load_coverage_module():
    spec = importlib.util.spec_from_file_location("coverage_report", COVERAGE_REPORT)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load coverage_report module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def require_raises(func, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    try:
        func()
    except Exception:
        return
    raise AssertionError(label)


def main() -> int:
    coverage = load_coverage_module()
    counts = {"boundary": 0, "robustness": 0}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        sample = tmp / "sample.c.gcov"
        sample.write_text(
            "\n".join(
                [
                    "        -:    0:Source:sample.c",
                    "        1:    1:int main(void) {",
                    "    #####:    2:    return 0;",
                    "        -:    3:}",
                    "branch  0 taken 1",
                    "branch  1 never executed",
                ]
            )
            + "\n"
        )

        require(
            coverage.parse_file(sample) == (1, 2, 1, 2),
            "sample gcov parse counts lines and branches",
            counts,
            "boundary",
        )
        rows, aggregate = coverage.collect_coverage(["sample.c.gcov"], tmp)
        require(
            rows == [("sample.c.gcov", 1, 2, 1, 2)] and aggregate == [1, 2, 1, 2],
            "coverage aggregation returns rows and totals",
            counts,
            "boundary",
        )
        require(
            coverage.collect_coverage(["missing.c.gcov"], tmp, io.StringIO()) is None,
            "missing gcov file reports collection failure",
            counts,
            "robustness",
        )

    require(coverage.pct(0, 0) == 0.0, "empty percentage is zero", counts, "boundary")
    require(coverage.parse_percent("0") == 0.0, "zero threshold accepted", counts, "boundary")
    require(coverage.parse_percent("100") == 100.0, "full threshold accepted", counts, "boundary")

    require_raises(lambda: coverage.parse_percent("-0.1"), "negative threshold rejected", counts, "robustness")
    require_raises(lambda: coverage.parse_percent("100.1"), "over-full threshold rejected", counts, "robustness")
    require_raises(lambda: coverage.parse_percent("nope"), "non-numeric threshold rejected", counts, "robustness")

    require(
        coverage.check_thresholds(81.4, 73.9, 81.0, 73.0, io.StringIO(), io.StringIO()) == 0,
        "baseline threshold passes",
        counts,
        "boundary",
    )
    require(
        coverage.check_thresholds(81.4, 73.9, 82.0, 73.0, io.StringIO()) == 1,
        "line threshold failure returns non-zero",
        counts,
        "robustness",
    )
    require(
        coverage.check_thresholds(81.4, 73.9, 81.0, 74.0, io.StringIO()) == 1,
        "branch threshold failure returns non-zero",
        counts,
        "robustness",
    )

    print(
        "coverage report tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
