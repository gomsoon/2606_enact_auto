#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import os
import pty
import select
import subprocess
import sys
import time
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "enact"
WORK_DIR = ROOT / "build" / "coverage_ratchet"
TTY_POLL_SECONDS = 0.05
TTY_DRAIN_SECONDS = 0.08


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


@dataclass(frozen=True)
class TtyCase:
    name: str
    source: str
    expected_fragments: list[str]
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
            FailureCase(
                "load command requires command whitespace",
                'load"missing"\n',
                "ENACT_ERR_PARSE_UNEXPECTED_TOKEN: unexpected token at offset 4\n",
                "robustness",
            ),
            FailureCase(
                "load command requires a string literal path",
                "load 1\n",
                "ENACT_ERR_PARSE_UNEXPECTED_TOKEN: unexpected token at offset 5\n",
                "robustness",
            ),
            FailureCase(
                "load command reports missing terminator at eof",
                'load "missing"',
                "ENACT_ERR_PARSE_MISSING_DOT: missing terminating '.' at offset 14\n",
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


def normalize_tty_output(chunk: bytes) -> str:
    return chunk.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def read_tty_available(master_fd: int, timeout: float) -> str:
    output = ""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        wait = max(0.0, min(TTY_POLL_SECONDS, deadline - time.monotonic()))
        readable, _, _ = select.select([master_fd], [], [], wait)
        if not readable:
            continue
        try:
            chunk = os.read(master_fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        output += normalize_tty_output(chunk)

    return output


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


def expect_tty_tokens(case: TtyCase, counts: dict[str, int]) -> None:
    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[bytes] | None = None
    output = ""
    fragment_index = 0
    search_from = 0

    try:
        proc = subprocess.Popen(
            [str(BIN), "--tokens"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            cwd=ROOT,
        )
        os.close(slave_fd)
        slave_fd = -1

        os.write(master_fd, case.source.encode())
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and fragment_index < len(case.expected_fragments):
            output += read_tty_available(master_fd, TTY_DRAIN_SECONDS)
            while fragment_index < len(case.expected_fragments):
                found = output.find(case.expected_fragments[fragment_index], search_from)
                if found < 0:
                    break
                search_from = found + len(case.expected_fragments[fragment_index])
                fragment_index += 1

        require(
            fragment_index == len(case.expected_fragments),
            f"{case.name}: expected tty fragments {case.expected_fragments!r}, got {output!r}",
            counts,
            case.kind,
        )
    finally:
        if slave_fd >= 0:
            os.close(slave_fd)
        if proc is not None and proc.poll() is None:
            try:
                os.write(master_fd, b"\x04")
                proc.wait(timeout=1.0)
            except (OSError, subprocess.TimeoutExpired):
                proc.terminate()
                proc.wait(timeout=1.0)
        os.close(master_fd)


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    success_cases, failure_cases = setup_fixtures()
    tty_cases = [
        TtyCase(
            "tty token mode dumps a complete expression line",
            "1+2.\n",
            ["TOK_INT_LITERAL", "TOK_PLUS", "TOK_INT_LITERAL", "TOK_DOT", "TOK_EOF"],
            "boundary",
        ),
        TtyCase(
            "tty token mode reports an error and keeps reading",
            "$\n3.\n",
            ["ENACT_ERR_LEX_INVALID_CHAR", "TOK_INT_LITERAL", "TOK_DOT", "TOK_EOF"],
            "robustness",
        ),
    ]
    counts = {"boundary": 0, "robustness": 0}

    for case in success_cases:
        expect_success(case, counts)
    for case in failure_cases:
        expect_failure(case, counts)
    for case in tty_cases:
        expect_tty_tokens(case, counts)

    print(
        "coverage ratchet tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
