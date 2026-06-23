#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "enact"


@dataclass(frozen=True)
class DiagnosticCase:
    name: str
    source: str
    expected_stdout: str
    expected_stderr: str
    kind: str


DIAGNOSTIC_CASES = [
    DiagnosticCase(
        "invalid character includes offset",
        "$x.\n",
        "",
        "ENACT_ERR_LEX_INVALID_CHAR: invalid character at offset 0\n",
        "boundary",
    ),
    DiagnosticCase(
        "bad string includes offset",
        '"bad\\q".\n',
        "",
        "ENACT_ERR_LEX_BAD_STRING: invalid string literal at offset 0\n",
        "boundary",
    ),
    DiagnosticCase(
        "bare equals keeps compatibility hint",
        "=.\n",
        "",
        "ENACT_ERR_LEX_BARE_EQUALS: bare '=' is not supported; use '==' at offset 0\n",
        "boundary",
    ),
    DiagnosticCase(
        "unexpected token includes offset",
        "1+.\n",
        "",
        "ENACT_ERR_PARSE_UNEXPECTED_TOKEN: unexpected token at offset 2\n",
        "boundary",
    ),
    DiagnosticCase(
        "missing final terminator reports EOF offset",
        "1",
        "",
        "ENACT_ERR_PARSE_MISSING_DOT: missing terminating '.' at offset 1\n",
        "boundary",
    ),
    DiagnosticCase(
        "unmatched parenthesis includes offset",
        "(1+2.\n",
        "",
        "ENACT_ERR_PARSE_UNMATCHED_PAREN: mismatched parentheses at offset 4\n",
        "boundary",
    ),
    DiagnosticCase(
        "divide by zero has stable runtime message",
        "1/0.\n",
        "",
        "ENACT_ERR_DIVIDE_BY_ZERO: division by zero\n",
        "robustness",
    ),
    DiagnosticCase(
        "integer type error has stable runtime message",
        "1+true.\n",
        "",
        "ENACT_ERR_TYPE_EXPECTED_INT: integer value required\n",
        "robustness",
    ),
    DiagnosticCase(
        "non-callable call has stable runtime message",
        "1(2).\n",
        "",
        "ENACT_ERR_TYPE_EXPECTED_FUNCTION: function value required\n",
        "robustness",
    ),
    DiagnosticCase(
        "arity mismatch has stable runtime message",
        "hd(1:nil,2:nil).\n",
        "",
        "ENACT_ERR_ARITY_MISMATCH: function arity mismatch\n",
        "robustness",
    ),
    DiagnosticCase(
        "unbound name has stable runtime message",
        "missing_name\n",
        "",
        "ENACT_ERR_NAME_UNBOUND: unbound identifier\n",
        "robustness",
    ),
    DiagnosticCase(
        "load failure has stable command message",
        'load "tests/smoke/missing_fixture.en"\n',
        "",
        "ENACT_ERR_LOAD_FILE: could not load file\n",
        "robustness",
    ),
    DiagnosticCase(
        "unbound attribute has stable object message",
        "(new Object).missing\n",
        "",
        "ENACT_ERR_ATTRIBUTE_UNBOUND: unbound attribute\n",
        "robustness",
    ),
    DiagnosticCase(
        "super outside method has stable context message",
        "super.missing()\n",
        "",
        "ENACT_ERR_INVALID_SUPER_CONTEXT: super method access requires an active method context\n",
        "robustness",
    ),
    DiagnosticCase(
        "inconsistent linearization preserves earlier stdout",
        "class X < Object\n"
        "class Y < Object\n"
        "class A < (X,Y)\n"
        "class B < (Y,X)\n"
        "class C < (A,B)\n"
        "(new C).missing\n",
        "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n",
        "ENACT_ERR_INCONSISTENT_LINEARIZATION: inconsistent class linearization\n",
        "robustness",
    ),
]


def run_case(case: DiagnosticCase) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN)],
        input=case.source,
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def expect_diagnostic(case: DiagnosticCase, counts: dict[str, int]) -> None:
    proc = run_case(case)
    require(
        proc.returncode != 0,
        f"{case.name}: expected non-zero return code, got stdout={proc.stdout!r}",
        counts,
        case.kind,
    )
    if proc.stdout != case.expected_stdout:
        raise AssertionError(
            f"{case.name}: stdout mismatch: expected {case.expected_stdout!r}, got {proc.stdout!r}"
        )
    if proc.stderr != case.expected_stderr:
        raise AssertionError(
            f"{case.name}: stderr mismatch: expected {case.expected_stderr!r}, got {proc.stderr!r}"
        )


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    counts = {"boundary": 0, "robustness": 0}

    for case in DIAGNOSTIC_CASES:
        expect_diagnostic(case, counts)

    print(
        "error diagnostic golden tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
