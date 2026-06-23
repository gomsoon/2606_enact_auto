#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "enact"
WORK_DIR = ROOT / "build" / "coverage_ratchet"


@dataclass(frozen=True)
class EvalCase:
    name: str
    source: str
    expected_stdout: str
    kind: str


@dataclass(frozen=True)
class FailureCase:
    name: str
    source: str
    expected_stderr: str
    kind: str


def enact_string_literal(value: str) -> str:
    escaped = []
    for ch in value:
        if ch == "\\":
            escaped.append("\\\\")
        elif ch == '"':
            escaped.append('\\"')
        elif ch == "\n":
            escaped.append("\\n")
        elif ch == "\r":
            escaped.append("\\r")
        elif ch == "\t":
            escaped.append("\\t")
        else:
            escaped.append(ch)
    return '"' + "".join(escaped) + '"'


def write_fixture(name: str, source: str) -> pathlib.Path:
    path = WORK_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def setup_fixtures() -> tuple[list[EvalCase], list[FailureCase]]:
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    large_source = "%" + ("large-load-comment" * 80) + "\nratchet_large:=21\nratchet_large*2\n"
    large_path = write_fixture("large.en", large_source)

    escaped_paths = [
        write_fixture("tab\tname.en", "tab_escape:=10\ntab_escape+1\n"),
        write_fixture("line\nname.en", "newline_escape:=20\nnewline_escape+1\n"),
        write_fixture("carriage\rname.en", "carriage_escape:=30\ncarriage_escape+1\n"),
        write_fixture('slash\\quote".en', "quote_escape:=40\nquote_escape+1\n"),
    ]
    escaped_loads = "".join(f"load {enact_string_literal(path.relative_to(ROOT).as_posix())}\n" for path in escaped_paths)

    return (
        [
            EvalCase(
                "large load fixture grows file reader",
                f"load {enact_string_literal(large_path.relative_to(ROOT).as_posix())}\n",
                "21\n42\n",
                "boundary",
            ),
            EvalCase(
                "load command decodes filename escapes",
                escaped_loads,
                "10\n11\n20\n21\n30\n31\n40\n41\n",
                "boundary",
            ),
            EvalCase(
                "string printing escapes carriage return",
                '"line\\rreturn"\n',
                '"line\\rreturn"\n',
                "boundary",
            ),
        ],
        [
            FailureCase(
                "load command rejects bad escape",
                'load "bad\\q"\n',
                "ENACT_ERR_LEX_BAD_STRING: invalid string literal at offset 9\n",
                "robustness",
            ),
            FailureCase(
                "load command rejects literal newline in path",
                'load "bad\nname"\n',
                "ENACT_ERR_LEX_BAD_STRING: invalid string literal at offset 9\n",
                "robustness",
            ),
            FailureCase(
                "load command rejects trailing expression",
                'load "missing" extra\n',
                "ENACT_ERR_PARSE_UNEXPECTED_TOKEN: unexpected token at offset 15\n",
                "robustness",
            ),
        ],
    )


def run_source(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN)],
        input=source,
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
    )


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def expect_success(case: EvalCase, counts: dict[str, int]) -> None:
    proc = run_source(case.source)
    require(
        proc.returncode == 0,
        f"{case.name}: expected success, got returncode={proc.returncode}, stderr={proc.stderr!r}",
        counts,
        case.kind,
    )
    if proc.stdout != case.expected_stdout:
        raise AssertionError(
            f"{case.name}: stdout mismatch: expected {case.expected_stdout!r}, got {proc.stdout!r}"
        )
    if proc.stderr:
        raise AssertionError(f"{case.name}: unexpected stderr: {proc.stderr!r}")


def expect_failure(case: FailureCase, counts: dict[str, int]) -> None:
    proc = run_source(case.source)
    require(
        proc.returncode != 0,
        f"{case.name}: expected failure, got stdout={proc.stdout!r}",
        counts,
        case.kind,
    )
    if proc.stdout:
        raise AssertionError(f"{case.name}: unexpected stdout: {proc.stdout!r}")
    if proc.stderr != case.expected_stderr:
        raise AssertionError(
            f"{case.name}: stderr mismatch: expected {case.expected_stderr!r}, got {proc.stderr!r}"
        )


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    success_cases, failure_cases = setup_fixtures()
    counts = {"boundary": 0, "robustness": 0}

    for case in success_cases:
        expect_success(case, counts)
    for case in failure_cases:
        expect_failure(case, counts)

    print(
        "coverage ratchet tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
