#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "enact"


def run_eval(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(BIN)], input=source, text=True, capture_output=True, check=False)


def run_tokens(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(BIN), "--tokens"], input=source, text=True, capture_output=True, check=False)


def expect_success(source: str, expected_stdout: str) -> None:
    proc = run_eval(source)
    if proc.returncode != 0:
        raise AssertionError(
            f"expected success for {source!r}, got returncode={proc.returncode}, stderr={proc.stderr!r}"
        )
    if proc.stdout != expected_stdout:
        raise AssertionError(
            f"stdout mismatch for {source!r}: expected {expected_stdout!r}, got {proc.stdout!r}"
        )
    if proc.stderr:
        raise AssertionError(f"unexpected stderr for {source!r}: {proc.stderr!r}")


def expect_failure(source: str, expected_code: str) -> None:
    proc = run_eval(source)
    if proc.returncode == 0:
        raise AssertionError(f"expected failure for {source!r}, got success with stdout={proc.stdout!r}")
    if expected_code not in proc.stderr:
        raise AssertionError(
            f"expected error code {expected_code!r} for {source!r}, got stderr={proc.stderr!r}"
        )


def expect_tokens(source: str, expected_stdout: str) -> None:
    proc = run_tokens(source)
    if proc.returncode != 0:
        raise AssertionError(
            f"expected token dump success for {source!r}, got returncode={proc.returncode}, stderr={proc.stderr!r}"
        )
    if proc.stdout != expected_stdout:
        raise AssertionError(
            f"token stdout mismatch for {source!r}: expected {expected_stdout!r}, got {proc.stdout!r}"
        )


def expect_token_failure(source: str, expected_code: str) -> None:
    proc = run_tokens(source)
    if proc.returncode == 0:
        raise AssertionError(f"expected token dump failure for {source!r}, got success with stdout={proc.stdout!r}")
    if expected_code not in proc.stderr:
        raise AssertionError(
            f"expected token error code {expected_code!r} for {source!r}, got stderr={proc.stderr!r}"
        )


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    long_comment = "%" + ("comment" * 240) + "\n(8+2)/5."
    huge_integer = ("9" * 512) + "."

    token_cases = [
        ("-1.", "TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1-2.", "TOK_INT_LITERAL TOK_MINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1*-2.", "TOK_INT_LITERAL TOK_STAR TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1--2.", "TOK_INT_LITERAL TOK_MINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("--1.", "TOK_UMINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        (" \t\n(8+2)/5.", "TOK_LPAREN TOK_INT_LITERAL TOK_PLUS TOK_INT_LITERAL TOK_RPAREN TOK_SLASH TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        (long_comment, "TOK_LPAREN TOK_INT_LITERAL TOK_PLUS TOK_INT_LITERAL TOK_RPAREN TOK_SLASH TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    success_cases = [
        ("1+2.", "3\n"),
        ("1+2*3.", "7\n"),
        ("(1+2)*3.", "9\n"),
        ("1+2*3+4*5+6.", "33\n"),
        ("-4+10.", "6\n"),
        ("1*-2.", "-2\n"),
        ("1--2.", "3\n"),
        ("--1.", "1\n"),
        ("-(1+2).", "-3\n"),
        ("8/2.", "4\n"),
        ("7/-3.", "-2\n"),
        ("2147483647.", "2147483647\n"),
        ("-2147483648.", "-2147483648\n"),
        ("46340*46340.", "2147395600\n"),
    ]

    failure_cases = [
        ("", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("1", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("% comment only\n", "ENACT_ERR_PARSE_MISSING_DOT"),
        (".", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("-.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1+.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1++2.", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("1//2.", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("(1+2.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("1+2).", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("1/0.", "ENACT_ERR_DIVIDE_BY_ZERO"),
        (huge_integer, "ENACT_ERR_LEX_BAD_INTEGER"),
        ("2147483648.", "ENACT_ERR_INT_OVERFLOW"),
        ("-2147483649.", "ENACT_ERR_INT_OVERFLOW"),
        ("2147483647+1.", "ENACT_ERR_INT_OVERFLOW"),
        ("-2147483648-1.", "ENACT_ERR_INT_OVERFLOW"),
        ("46341*46341.", "ENACT_ERR_INT_OVERFLOW"),
        ("-2147483648/-1.", "ENACT_ERR_INT_OVERFLOW"),
        ("a.", "ENACT_ERR_LEX_INVALID_CHAR"),
    ]

    token_failure_cases = [
        ("a.", "ENACT_ERR_LEX_INVALID_CHAR"),
        (huge_integer, "ENACT_ERR_LEX_BAD_INTEGER"),
    ]

    for source, expected in token_cases:
        expect_tokens(source, expected)

    for source, expected_code in token_failure_cases:
        expect_token_failure(source, expected_code)

    for source, expected in success_cases:
        expect_success(source, expected)

    for source, expected_code in failure_cases:
        expect_failure(source, expected_code)

    total = len(token_cases) + len(token_failure_cases) + len(success_cases) + len(failure_cases)
    print(f"passed {total} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
