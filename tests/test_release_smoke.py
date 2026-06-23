#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "enact"
SMOKE_DIR = ROOT / "tests" / "smoke"


@dataclass(frozen=True)
class SmokeCase:
    name: str
    script: str
    expected_stdout: str


@dataclass(frozen=True)
class SmokeFailureCase:
    name: str
    script: str
    expected_stdout: str
    expected_error_code: str


SUCCESS_CASES = [
    SmokeCase(
        "functional fixture executes from stdin",
        "functional.en",
        "<function>\n<function>\n<function>\n1:2:3:4:nil\n120\n12\n10\n",
    ),
    SmokeCase(
        "object fixture executes from stdin",
        "object.en",
        "<class Tree>\n<function>\n<class Leaf>\n<object Tree>\n<object Leaf>\n"
        "true\n13\n20\n23\n<class Leaf>:<class Tree>:<class Object>:nil\n",
    ),
    SmokeCase(
        "collection fixture executes from stdin",
        "collections.en",
        "set(1:2:3:nil)\nbag(1:1:2:nil)\n3\n3\n"
        "set(2:3:4:nil)\nbag(2:2:3:nil)\ntrue:false:nil\n",
    ),
    SmokeCase(
        "load fixture evaluates definitions into caller session",
        "load_main.en",
        "40\n<function>\n40:41:nil\n42\n",
    ),
    SmokeCase(
        "nested load fixture respects bye command",
        "load_nested_outer.en",
        "7\n42\n8\n",
    ),
]

FAILURE_CASES = [
    SmokeFailureCase(
        "missing load target fails release smoke",
        "missing_load.en",
        "",
        "ENACT_ERR_LOAD_FILE",
    ),
    SmokeFailureCase(
        "malformed script reports parse failure",
        "bad_parse.en",
        "1\n",
        "ENACT_ERR_PARSE_UNEXPECTED_TOKEN",
    ),
    SmokeFailureCase(
        "runtime name failure preserves earlier output",
        "bad_runtime.en",
        "1\n",
        "ENACT_ERR_NAME_UNBOUND",
    ),
    SmokeFailureCase(
        "loaded runtime failure propagates to caller",
        "load_bad_runtime.en",
        "9\n",
        "ENACT_ERR_NAME_UNBOUND",
    ),
]


def run_fixture(script_name: str) -> subprocess.CompletedProcess[str]:
    script = SMOKE_DIR / script_name
    if not script.exists():
        raise AssertionError(f"missing smoke fixture: {script}")
    with script.open(encoding="utf-8") as stdin:
        return subprocess.run(
            [str(BIN)],
            stdin=stdin,
            text=True,
            capture_output=True,
            check=False,
            cwd=ROOT,
        )


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def expect_success(case: SmokeCase, counts: dict[str, int]) -> None:
    proc = run_fixture(case.script)
    require(
        proc.returncode == 0,
        f"{case.name}: expected success, got returncode={proc.returncode}, stderr={proc.stderr!r}",
        counts,
        "boundary",
    )
    if proc.stdout != case.expected_stdout:
        raise AssertionError(
            f"{case.name}: stdout mismatch for {case.script}: "
            f"expected {case.expected_stdout!r}, got {proc.stdout!r}"
        )
    if proc.stderr:
        raise AssertionError(f"{case.name}: unexpected stderr for {case.script}: {proc.stderr!r}")


def expect_failure(case: SmokeFailureCase, counts: dict[str, int]) -> None:
    proc = run_fixture(case.script)
    require(
        proc.returncode != 0 and case.expected_error_code in proc.stderr,
        f"{case.name}: expected {case.expected_error_code}, got "
        f"returncode={proc.returncode}, stderr={proc.stderr!r}",
        counts,
        "robustness",
    )
    if proc.stdout != case.expected_stdout:
        raise AssertionError(
            f"{case.name}: stdout mismatch for {case.script}: "
            f"expected {case.expected_stdout!r}, got {proc.stdout!r}"
        )


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    counts = {"boundary": 0, "robustness": 0}

    for case in SUCCESS_CASES:
        expect_success(case, counts)
    for case in FAILURE_CASES:
        expect_failure(case, counts)

    print(
        "release smoke tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
