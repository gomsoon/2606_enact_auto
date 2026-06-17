#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import os
import pty
import select
import subprocess
import sys
import time


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


def expect_tty_line(source: str, expected_stdout: str) -> None:
    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[bytes] | None = None
    output = ""

    try:
        proc = subprocess.Popen(
            [str(BIN)],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1

        os.write(master_fd, source.encode())
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and expected_stdout not in output:
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if not readable:
                continue
            chunk = os.read(master_fd, 4096)
            if not chunk:
                break
            output += chunk.decode(errors="replace").replace("\r\n", "\n")

        if expected_stdout not in output:
            raise AssertionError(
                f"expected tty output containing {expected_stdout!r} for {source!r}, got {output!r}"
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


def expect_tty_fragments(source: str, expected_fragments: list[str]) -> None:
    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[bytes] | None = None
    output = ""
    fragment_index = 0
    search_from = 0

    try:
        proc = subprocess.Popen(
            [str(BIN)],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1

        os.write(master_fd, source.encode())
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and fragment_index < len(expected_fragments):
            readable, _, _ = select.select([master_fd], [], [], 0.1)
            if not readable:
                continue
            chunk = os.read(master_fd, 4096)
            if not chunk:
                break
            output += chunk.decode(errors="replace").replace("\r\n", "\n")

            while fragment_index < len(expected_fragments):
                found = output.find(expected_fragments[fragment_index], search_from)
                if found < 0:
                    break
                search_from = found + len(expected_fragments[fragment_index])
                fragment_index += 1

        if fragment_index < len(expected_fragments):
            raise AssertionError(
                f"expected tty fragments {expected_fragments!r} for {source!r}, got {output!r}"
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

    long_comment = "%" + ("comment" * 240) + "\n(8+2)/5."
    huge_integer = ("9" * 512) + "."
    long_identifier = ("abc_" * 80) + "z."
    load_dir = ROOT / "build" / "load_cases"
    load_dir.mkdir(parents=True, exist_ok=True)

    def write_load_case(name: str, source: str) -> str:
        path = load_dir / name
        path.write_text(source, encoding="utf-8")
        return path.as_posix()

    load_defs_path = write_load_case(
        "defs.en",
        "loaded_x:=7.\nloaded_inc(n):=n+1.\nloaded_inc(loaded_x).",
    )
    load_empty_path = write_load_case("empty.en", "   % empty load file\n  ")
    load_dot_string_path = write_load_case("dot_string.en", "loaded_s:=\"a.b\".\nloaded_s.")
    load_nested_inner_path = write_load_case("nested_inner.en", "inner_value:=3.\ninner_value+4.")
    load_nested_outer_path = write_load_case(
        "nested_outer.en",
        f"load \"{load_nested_inner_path}\".\ninner_value+5.",
    )
    load_parse_error_path = write_load_case("parse_error.en", "bad_load:=1.\nbad_load")
    load_eval_error_path = write_load_case("eval_error.en", "loaded_before_failure:=9.\nmissing.")
    load_tty_path = write_load_case("tty.en", "tty_loaded:=5.\ntty_loaded+1.")
    load_atom_path = write_load_case("atom.en", "loaded_atom:='from_file.\nloaded_atom.")
    load_newline_path = write_load_case("newline.en", "loaded_newline:=5\nloaded_newline+2\n")

    slice_008_token_cases = [
        ("f(x):=x+1.", "TOK_IDENTIFIER TOK_LPAREN TOK_IDENTIFIER TOK_RPAREN TOK_ASSIGN TOK_IDENTIFIER TOK_PLUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("f(99).", "TOK_IDENTIFIER TOK_LPAREN TOK_INT_LITERAL TOK_RPAREN TOK_DOT TOK_EOF\n"),
    ]

    slice_008_boundary_success_cases = [
        ("f(x):=x+1; f(99).", "100\n"),
        ("double(x):=x*2; double(3)+1.", "7\n"),
        ('id(x):=x; id("hi").', "\"hi\"\n"),
        ("not_fn(x):=not x; not_fn(false).", "true\n"),
        ("x:=10; f(y):=x+y; f(1).", "11\n"),
        ("x:=10; f(y):=x+y; x:=20; f(1).", "11\n"),
        ("f(x):=(y:=x+1; y); f(2).", "3\n"),
        ("f(x):=x where x:=1; f(99).", "1\n"),
        ("f(x):=x+1.", "<function>\n"),
        ("f(x):=x; y:=f; y(4).", "4\n"),
        ("apply(f):=f(3); inc(x):=x+1; apply(inc).", "4\n"),
        ("make_adder(x):=add(y):=x+y; add2:=make_adder(2); add2(5).", "7\n"),
        ("f(x):=(x:=2; x); x:=1; f(0); x.", "1\n"),
    ]

    slice_008_robustness_failure_cases = [
        ("f(1).", "ENACT_ERR_NAME_UNBOUND"),
        ("1(2).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("true(1).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("f(x):=x+1; f(true).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("f().", "ENACT_ERR_NAME_UNBOUND"),
        ("f(1):=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x):=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(f)(x):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f((x)):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x):=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x):=x; f().", "ENACT_ERR_ARITY_MISMATCH"),
        ("f(x):=x; f(1.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("f(x):=f(x,1); f(1).", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_009_token_cases = [
        ("add(x,y):=x+y.", "TOK_IDENTIFIER TOK_LPAREN TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER TOK_RPAREN TOK_ASSIGN TOK_IDENTIFIER TOK_PLUS TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("add(2,3).", "TOK_IDENTIFIER TOK_LPAREN TOK_INT_LITERAL TOK_COMMA TOK_INT_LITERAL TOK_RPAREN TOK_DOT TOK_EOF\n"),
    ]

    slice_009_boundary_success_cases = [
        ("add(x,y):=x+y; add(2,3).", "5\n"),
        ("mix(a,b,c):=a*b+c; mix(2,3,4).", "10\n"),
        ('first(a,b):=a; first("left","right").', "\"left\"\n"),
        ("both(a,b):=a and b; both(true,false).", "false\n"),
        ("inc(x):=x+1; inc(4).", "5\n"),
        ("x:=10; addx(a,b):=x+a+b; x:=20; addx(1,2).", "13\n"),
        ("apply2(f,x,y):=f(x,y); add(a,b):=a+b; apply2(add,2,3).", "5\n"),
        ("make(a):=sum(b,c):=a+b+c; s:=make(1); s(2,3).", "6\n"),
        ("pick(a,b):=b; x:=0; pick(x:=1,x:=2); x.", "2\n"),
        ("f(a,b):=(a:=9; b:=8; a+b); a:=1; b:=2; f(3,4); a+b.", "3\n"),
    ]

    slice_009_robustness_failure_cases = [
        ("add(x,y):=x+y; add(1,2,3).", "ENACT_ERR_ARITY_MISMATCH"),
        ("inc(x):=x+1; inc(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("one(x):=x; one(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f().", "ENACT_ERR_NAME_UNBOUND"),
        ("add(,1).", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("add(1,).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x,x):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x,1):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f((x),y):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1(2,3).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("add(x,y):=x+y; add(true,1).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("ignore(a,b):=a; ignore(1,1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("f(x,y):=f(x,y,1); f(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("add(1,2.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
    ]

    slice_010_token_cases = [
        ("x::x+1.", "TOK_IDENTIFIER TOK_LAMBDA TOK_IDENTIFIER TOK_PLUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("(x,y)::x+y.", "TOK_LPAREN TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER TOK_RPAREN TOK_LAMBDA TOK_IDENTIFIER TOK_PLUS TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
    ]

    slice_010_boundary_success_cases = [
        ("(x::x+1)(4).", "5\n"),
        ("inc:=x::x+1; inc(4).", "5\n"),
        ("add:=(x,y)::x+y; add(2,3).", "5\n"),
        ("((x,y)::x*y)(3,4).", "12\n"),
        ('id:=x::x; id("hi").', "\"hi\"\n"),
        ("both:=(a,b)::a and b; both(true,false).", "false\n"),
        ("x:=10; f:=y::x+y; x:=20; f(1).", "11\n"),
        ("apply:=(f,x)::f(x); inc:=x::x+1; apply(inc,3).", "4\n"),
        ("apply:=(f,x)::f(x); apply(x::x+1,3).", "4\n"),
        ("make:=a::(b,c)::a+b+c; s:=make(1); s(2,3).", "6\n"),
        ("adder:=x::y::x+y; adder(2)(3).", "5\n"),
        ("f:=x::(y:=x+1; y); f(2).", "3\n"),
        ("x::x+1.", "<function>\n"),
    ]

    slice_010_robustness_failure_cases = [
        ("x::.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1::1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x,)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(,x)::x.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("(x,x)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x,1)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("((x),y)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f:=x::x; f().", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=x::x; f(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("ignore:=(x,y)::x; ignore(1,1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("f:=x::f(x); f(1).", "ENACT_ERR_NAME_UNBOUND"),
    ]

    slice_011_boundary_success_cases = [
        ("add(x,y):=x+y; add(1)(4).", "5\n"),
        ("add(x,y):=x+y; inc:=add(1); inc(4).", "5\n"),
        ("add:=(x,y)::x+y; add(1)(4).", "5\n"),
        ("tri:=(a,b,c)::a+b+c; tri(1)(2)(3).", "6\n"),
        ("tri:=(a,b,c)::a+b+c; add1:=tri(1); add1(2,3).", "6\n"),
        ("tri:=(a,b,c)::a+b+c; add3:=tri(1,2); add3(3).", "6\n"),
        ('choose:=(a,b)::a; left:=choose("left"); left("right").', "\"left\"\n"),
        ("both:=(a,b)::a and b; t:=both(true); t(false).", "false\n"),
        ("x:=10; addx:=(a,b)::x+a+b; p:=addx(1); x:=20; p(2).", "13\n"),
        ("apply:=(f,x)::f(x); add:=(a,b)::a+b; apply(add(2),3).", "5\n"),
        ("add:=(x,y)::x+y; add(1).", "<function>\n"),
        ("make:=a::(b,c)::a+b+c; s:=make(1)(2); s(3).", "6\n"),
        ("add:=(x,y)::x+y; x:=0; p:=add(x:=2); p(3); x.", "2\n"),
    ]

    slice_011_robustness_failure_cases = [
        ("add:=(x,y)::x+y; add(1,2,3).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=(x,y)::x+y; f(1,2,3).", "ENACT_ERR_ARITY_MISMATCH"),
        ("one:=x::x; one(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("ignore:=(a,b)::a; ignore(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("add:=(a,b)::a+b; p:=add(true); p(1).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1(2).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("f().", "ENACT_ERR_NAME_UNBOUND"),
        ("f:=x::f(x); f(1).", "ENACT_ERR_NAME_UNBOUND"),
    ]

    slice_012_boundary_success_cases = [
        ("inc(x):=x+1; inc 4.", "5\n"),
        ("add(x,y):=x+y; add 2 3.", "5\n"),
        ("tri(a,b,c):=a+b+c; tri 1 2 3.", "6\n"),
        ("inc:=x::x+1; inc 4.", "5\n"),
        ("apply(f,x):=f x; inc(y):=y+1; apply inc 3.", "4\n"),
        ("add(x,y):=x+y; (add 1) 4.", "5\n"),
        ("add x:=x+1; add 4.", "5\n"),
        ("add x y:=x+y; add 2 3.", "5\n"),
        ("x:=10; addx a b:=x+a+b; x:=20; addx 1 2.", "13\n"),
        ('id(x):=x; id "hi".', "\"hi\"\n"),
        ("both(a,b):=a and b; both true false.", "false\n"),
        ("add(x,y):=x+y; add 1.", "<function>\n"),
        ("add(x,y):=x+y; add (1+2) 3.", "6\n"),
        ("add(x,y):=x+y; add 1 2+3.", "6\n"),
    ]

    slice_012_robustness_failure_cases = [
        ("1 2.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("true 1.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("inc(x):=x+1; inc true.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("one(x):=x; one 1 2.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("ignore(a,b):=a; ignore (1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("add(x,y):=x+y; add 1+2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("f 1:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f x x:=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f x:=f(x,1); f 1.", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_013_token_cases = [
        ("nil.", "TOK_NIL TOK_DOT TOK_EOF\n"),
        ("1:nil.", "TOK_INT_LITERAL TOK_CONS TOK_NIL TOK_DOT TOK_EOF\n"),
    ]

    slice_013_boundary_success_cases = [
        ("nil.", "nil\n"),
        ("1:nil.", "1:nil\n"),
        ("1:2:nil.", "1:2:nil\n"),
        ('"a":true:nil.', "\"a\":true:nil\n"),
        ("(1:nil):nil.", "(1:nil):nil\n"),
        ("xs:=1:2:nil; xs.", "1:2:nil\n"),
        ("xs:=2:nil; 1:xs.", "1:2:nil\n"),
        ("1+2:nil.", "3:nil\n"),
        ("1:2:nil == 1:2:nil.", "true\n"),
        ("1:nil != 2:nil.", "true\n"),
        ("id(x):=x; id (1:nil).", "1:nil\n"),
        ("xs:=1:nil; f:=x::xs; xs:=2:nil; f 0.", "1:nil\n"),
        ("f:=x::x; f:nil.", "<function>:nil\n"),
    ]

    slice_013_robustness_failure_cases = [
        ("1:2.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("1:true.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("1:(x::x).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("nil+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("nil<nil.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("nil==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("1:.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        (":nil.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("nilx.", "ENACT_ERR_NAME_UNBOUND"),
    ]

    slice_014_boundary_success_cases = [
        ("hd(1:nil).", "1\n"),
        ("tl(1:2:nil).", "2:nil\n"),
        ("tl(1:nil).", "nil\n"),
        ('hd("a":nil).', "\"a\"\n"),
        ("hd((1:nil):nil).", "1:nil\n"),
        ("f:=hd; f(1:nil).", "1\n"),
        ("apply(f,x):=f x; apply(hd, 1:nil).", "1\n"),
        ("id(x):=x; id(hd)(1:nil).", "1\n"),
        ("make(f):=x::f x; first:=make(hd); first(1:nil).", "1\n"),
        ("hd:=x::x; hd 4.", "4\n"),
        ("hd == hd.", "true\n"),
        ("hd != tl.", "true\n"),
        ("hd.", "<function>\n"),
        ("tl.", "<function>\n"),
    ]

    slice_014_robustness_failure_cases = [
        ("hd nil.", "ENACT_ERR_LIST_EMPTY"),
        ("tl nil.", "ENACT_ERR_LIST_EMPTY"),
        ("hd 1.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("tl true.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd().", "ENACT_ERR_ARITY_MISMATCH"),
        ("hd(1:nil,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("hd(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("not hd.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1:hd.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_015_boundary_success_cases = [
        ("size nil.", "0\n"),
        ("size(1:nil).", "1\n"),
        ("size(1:2:3:nil).", "3\n"),
        ("size((1:nil):2:nil).", "2\n"),
        ("append(nil, 1:nil).", "1:nil\n"),
        ("append(1:nil, nil).", "1:nil\n"),
        ("append(1:2:nil, 3:4:nil).", "1:2:3:4:nil\n"),
        ('append("a":nil, "b":nil).', "\"a\":\"b\":nil\n"),
        ("append((1:nil):nil, 2:nil).", "(1:nil):2:nil\n"),
        ("hd(append(1:2:nil, 3:nil)).", "1\n"),
        ("tl(append(1:nil, 2:3:nil)).", "2:3:nil\n"),
        ("f:=append; f(1:nil, 2:nil).", "1:2:nil\n"),
        ("apply(f,x,y):=f(x,y); apply(append, 1:nil, 2:nil).", "1:2:nil\n"),
        ("measure(f,x):=f x; measure(size, 1:2:nil).", "2\n"),
        ("append(1:2:nil, 3:nil) == 1:2:3:nil.", "true\n"),
    ]

    slice_015_robustness_failure_cases = [
        ("size 1.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("size true.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(1, nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(nil, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(1:nil, 2:nil, 3:nil).", "ENACT_ERR_ARITY_MISMATCH"),
        ("size(1:nil, 2:nil).", "ENACT_ERR_ARITY_MISMATCH"),
        ("append(1/0, nil).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("append(nil, 1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("size(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("append(1:nil, 2:nil)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_016_boundary_success_cases = [
        ("append(1:nil).", "<function>\n"),
        ("append(1:nil)(2:nil).", "1:2:nil\n"),
        ("p:=append(1:nil); p(2:nil).", "1:2:nil\n"),
        ("append(nil)(1:nil).", "1:nil\n"),
        ("append(1:nil) nil.", "1:nil\n"),
        ("(append(1:nil)) (2:nil).", "1:2:nil\n"),
        ("apply(f,x):=f x; apply(append(1:nil), 2:nil).", "1:2:nil\n"),
        ("make(f):=x::f x; append1:=make(append(1:nil)); append1(2:nil).", "1:2:nil\n"),
        ("xs:=1:nil; p:=append(xs); xs:=2:nil; p(3:nil).", "1:3:nil\n"),
        ('append("a":nil)("b":nil).', "\"a\":\"b\":nil\n"),
        ("append(1:nil) == append(1:nil).", "false\n"),
        ("q:=append(1:nil); r:=q; q==r.", "true\n"),
        ("append 1:nil.", "<function>:nil\n"),
    ]

    slice_016_robustness_failure_cases = [
        ("append(1)(nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(1:nil)(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(1:nil)(2:nil, 3:nil).", "ENACT_ERR_ARITY_MISMATCH"),
        ("append(1:nil)(1/0, nil).", "ENACT_ERR_ARITY_MISMATCH"),
        ("size(1:nil, 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("append(1:nil)(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("append(1:nil)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not append(1:nil).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("1:append(1:nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(1:nil)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_017_token_cases = [
        ("(1,2).", "TOK_LPAREN TOK_INT_LITERAL TOK_COMMA TOK_INT_LITERAL TOK_RPAREN TOK_DOT TOK_EOF\n"),
        ("(1,2,3).", "TOK_LPAREN TOK_INT_LITERAL TOK_COMMA TOK_INT_LITERAL TOK_COMMA TOK_INT_LITERAL TOK_RPAREN TOK_DOT TOK_EOF\n"),
    ]

    slice_017_boundary_success_cases = [
        ("(1,2).", "1:2:nil\n"),
        ("(1,2,3).", "1:2:3:nil\n"),
        ('("a",true,3).', "\"a\":true:3:nil\n"),
        ("((1,2),3).", "(1:2:nil):3:nil\n"),
        ("(1+2,3*4).", "3:12:nil\n"),
        ("x:=0; (x:=1,x+1).", "1:2:nil\n"),
        ("xs:=(1,2); xs.", "1:2:nil\n"),
        ("size((1,2,3)).", "3\n"),
        ("hd((1,2,3)).", "1\n"),
        ("tl((1,2,3)).", "2:3:nil\n"),
        ("append((1,2),(3,4)).", "1:2:3:4:nil\n"),
        ("append((1,2))((3,4)).", "1:2:3:4:nil\n"),
        ("(1,2)==1:2:nil.", "true\n"),
        ("id(x):=x; id((1,2)).", "1:2:nil\n"),
        ("make(x):=y::(x,y); make(1)(2).", "1:2:nil\n"),
    ]

    slice_017_robustness_failure_cases = [
        ("(1,).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(,1).", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("(1,,2).", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("(1,2.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("(1,2,).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("size(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("hd((1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("(1,2)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not (1,2).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("(1,2)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_018_boundary_success_cases = [
        ("map(x::x+1, nil).", "nil\n"),
        ("map(x::x+1, (1,2,3)).", "2:3:4:nil\n"),
        ("inc(x):=x+1; map(inc, (1,2,3)).", "2:3:4:nil\n"),
        ('map(x::x, ("a","b")).', "\"a\":\"b\":nil\n"),
        ("map(x::not x, (true,false,true)).", "false:true:false:nil\n"),
        ("map(hd, ((1,2),(3,4))).", "1:3:nil\n"),
        ("map(tl, ((1,2),(3,4))).", "(2:nil):(4:nil):nil\n"),
        ("map(size, ((1,2),(3,4,5))).", "2:3:nil\n"),
        ("map(append(0:nil), ((1,2),(3,4))).", "(0:1:2:nil):(0:3:4:nil):nil\n"),
        ("map(map(x::x+1), ((1,2),(3,4))).", "(2:3:nil):(4:5:nil):nil\n"),
        ("map(append, ((1,2),(3,4))).", "<function>:<function>:nil\n"),
        ("m:=map(x::x+1); m((1,2)).", "2:3:nil\n"),
        ("apply(f,x):=f x; apply(map(x::x+1), (1,2)).", "2:3:nil\n"),
        ("n:=1; f:=x::x+n; p:=map(f); n:=10; p((1,2)).", "2:3:nil\n"),
        ("map(x::x+1).", "<function>\n"),
    ]

    slice_018_robustness_failure_cases = [
        ("map(1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(1, nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(x::x+1, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(x::x+1, (true,2)).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("map(hd, (nil,(1,2))).", "ENACT_ERR_LIST_EMPTY"),
        ("map(size, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(x::x+1, (1,2), 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("map(x::x+1, nil, 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("map(x::x, (1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("map(x::x+1, (1,2))+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not map(x::x, (true,false)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(x::x, (1,2))==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_019_boundary_success_cases = [
        ("filter(x::x>1, nil).", "nil\n"),
        ("filter(x::x>1, (1,2,3)).", "2:3:nil\n"),
        ("filter(x::true, (1,2,3)).", "1:2:3:nil\n"),
        ("filter(x::false, (1,2,3)).", "nil\n"),
        ("filter(x::x==\"a\", (\"a\",\"b\",\"a\")).", "\"a\":\"a\":nil\n"),
        ("filter(x::size(x)>2, ((1,2),(3,4,5),nil)).", "(3:4:5:nil):nil\n"),
        ("size(filter(x::true, (1,2,3))).", "3\n"),
        ("size(filter(x::false, (1,2,3))).", "0\n"),
        ("p:=filter(x::x>1); p((1,2,3)).", "2:3:nil\n"),
        ("apply(f,x):=f x; apply(filter(x::x>1), (1,2,3)).", "2:3:nil\n"),
        ("map(x::x*2, filter(x::x>1, (1,2,3))).", "4:6:nil\n"),
        ("all(x::x>0, nil).", "true\n"),
        ("all(x::x>0, (1,2,3)).", "true\n"),
        ("all(x::x>1, (1,2,3)).", "false\n"),
        ("all(x::not x, (false,false)).", "true\n"),
        ("all(hd, ((true:nil),(true,false))).", "true\n"),
        ("q:=all(x::x>0); q((1,2)).", "true\n"),
        ("all(x::x<2 and 1/0==0, (2,0)).", "false\n"),
        ("filter(x::x>1).", "<function>\n"),
        ("all(x::x>1).", "<function>\n"),
    ]

    slice_019_robustness_failure_cases = [
        ("filter(1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("all(1, nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("filter(x::x>1, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("all(x::x>1, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("filter(x::x+1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("all(x::x+1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("filter(hd, ((1:nil),(2:nil))).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("all(size, ((1:nil),(2:nil))).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("filter(x::x>1, (1,2), 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("all(x::x>1, nil, 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("filter(x::x, (1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("all(x::x, (1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("filter(x::x<2 and 1/0==0, (2,0)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("filter(x::x>1, (1,2))+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not filter(x::x>1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("filter(x::x>1, (1,2))==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_020_boundary_success_cases = [
        ("reduce((acc,x)::acc+x, 0, nil).", "0\n"),
        ("reduce((acc,x)::acc+x, 0, (1,2,3)).", "6\n"),
        ("reduce((acc,x)::acc*x, 1, (2,3,4)).", "24\n"),
        ("reduce((acc,x)::acc+1, 0, (10,20,30)).", "3\n"),
        ("reduce((acc,x)::x, 0, (1,2,3)).", "3\n"),
        ("reduce((acc,x)::x:acc, nil, (1,2,3)).", "3:2:1:nil\n"),
        ("reduce(append, nil, ((1,2),(3,4),nil)).", "1:2:3:4:nil\n"),
        ("reduce((acc,x)::acc and x, true, (true,true,false)).", "false\n"),
        ("reduce((acc,x)::acc or x, false, (false,true,false)).", "true\n"),
        ("reduce((acc,x)::acc==x, true, (true,true,true)).", "true\n"),
        ("reduce((acc,x)::x, \"\", (\"a\",\"b\")).", "\"b\"\n"),
        ("reduce((acc,x)::x, 99, 42:nil).", "42\n"),
        ("r:=reduce((acc,x)::acc+x); r(0,(1,2)).", "3\n"),
        ("r:=reduce((acc,x)::acc+x,0); r((1,2)).", "3\n"),
        ("apply(f,z,xs):=f(z,xs); apply(reduce((acc,x)::acc+x),0,(1,2)).", "3\n"),
        ("map(x::x*2, reduce((acc,x)::x:acc, nil, (1,2,3))).", "6:4:2:nil\n"),
        ("reduce((acc,x)::acc+x, 0, filter(x::x>1, (1,2,3))).", "5\n"),
        ("all(x::x>0, reduce((acc,x)::x:acc, nil, (1,2,3))).", "true\n"),
        ("f:=reduce((acc,x)::(y::acc(y)+x), y::y, (1,2)); f(10).", "13\n"),
        ("reduce((acc,x)::acc+x).", "<function>\n"),
    ]

    slice_020_robustness_failure_cases = [
        ("reduce(1, 0, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("reduce(1, 0, nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("reduce((acc,x)::acc+x, 0, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("reduce((acc,x)::acc+x, 0, (1,true)).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("reduce(x::x, 0, (1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(hd, nil, ((1:nil),(2:nil))).", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce((acc,x)::acc+x, 0, (1,2), 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce((acc,x)::acc+x, 0, nil, 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce((acc,x)::acc+x, 0, (1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("reduce((acc,x)::1/0, 0, (1,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("reduce((acc,x)::acc+x, true, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("reduce((acc,x)::acc+x, 0, (true,2)).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("reduce((acc,x)::x:acc, nil, (1,2))+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not reduce((acc,x)::x:acc, nil, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("reduce((acc,x)::x:acc, nil, (1,2))==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("reduce(append, nil, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_021_boundary_success_cases = [
        ("atom(1).", "true\n"),
        ("atom(-1).", "true\n"),
        ("atom(true).", "true\n"),
        ("atom(false).", "true\n"),
        ("atom(\"x\").", "true\n"),
        ("atom(nil).", "true\n"),
        ("atom(1:nil).", "false\n"),
        ("atom((1,2)).", "false\n"),
        ("atom((1:nil):nil).", "false\n"),
        ("atom(x::x).", "true\n"),
        ("f:=x::x; atom(f).", "true\n"),
        ("atom(hd).", "true\n"),
        ("atom(append(1:nil)).", "true\n"),
        ("atom(reduce((acc,x)::acc+x)).", "true\n"),
        ("map(atom, (1,true,\"x\",nil,(1,2),x::x)).", "true:true:true:true:false:true:nil\n"),
        ("size(filter(atom, (1,nil,(1,2),\"x\"))).", "3\n"),
        ("all(atom, (1,true,\"x\",nil,x::x)).", "true\n"),
        ("all(atom, (1,(2,3))).", "false\n"),
        ("reduce((acc,x)::acc+1, 0, filter(atom, (1,nil,(2,3),x::x))).", "3\n"),
        ("atom(atom).", "true\n"),
    ]

    slice_021_robustness_failure_cases = [
        ("atom(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("atom(nil,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("atom(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("atom(missing).", "ENACT_ERR_NAME_UNBOUND"),
        ("atom((1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("atom(1)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1+atom(1).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("atom(1)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("1:atom(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("atom(1)(2).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("atom(1)<atom(2).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("atom(1):nil + 1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_022_boundary_success_cases = [
        ("fact(n):=1 if n==0 else n*fact(n-1); fact(5).", "120\n"),
        ("nfib(n):=1 if n<2 else nfib(n-1)+nfib(n-2); nfib(5).", "8\n"),
        ("sumdown(n):=0 if n==0 else n+sumdown(n-1); sumdown(5).", "15\n"),
        ("len(xs):=0 if atom(xs) else 1+len(tl(xs)); len((1,2,3)).", "3\n"),
        ("reverse(xs):=nil if atom(xs) else append(reverse(tl(xs)), hd(xs):nil); reverse((1,2,3)).", "3:2:1:nil\n"),
        ("sum(a,b):=b if a==0 else sum(a-1,b+a); sum(3,0).", "6\n"),
        ("sum(a,b):=b if a==0 else sum(a-1,b+a); sum(3)(0).", "6\n"),
        ("sum(a,b):=b if a==0 else sum(a-1,b+a); add3:=sum(3); add3(0).", "6\n"),
        ("apply(f,x):=f(x); fact(n):=1 if n==0 else n*fact(n-1); apply(fact,4).", "24\n"),
        ("step:=2; count(n):=0 if n==0 else step+count(n-1); step:=10; count(3).", "6\n"),
        ("make(start):=loop(n):=start if n==0 else loop(n-1)+1; c:=make(10); c(3).", "13\n"),
        ("f(n):=1 if n==0 else f(n-1)+1; old:=f; f(n):=100; old(3).", "4\n"),
        ("f(n):=f if n==0 else f(n-1); f(2)==f.", "true\n"),
        ("fact(n):=1 if n==0 else n*fact(n-1); atom(fact).", "true\n"),
        ("down n:=0 if n==0 else down(n-1)+1; down 4.", "4\n"),
        ("fact(n):=1 if n==0 else n*fact(n-1); map(x::fact(x), (0,1,4)).", "1:1:24:nil\n"),
    ]

    slice_022_robustness_failure_cases = [
        ("f:=x::f(x); f(1).", "ENACT_ERR_NAME_UNBOUND"),
        ("f(x):=f(x,1); f(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f(x,y):=f(x,y,1); f(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f x:=f(x,1); f 1.", "ENACT_ERR_ARITY_MISMATCH"),
        ("fact(n):=1 if n==0 else n*fact(n-1); fact(true).", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("fact(n):=1 if n==0 else n*fact(n-1); fact(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("bad(n):=1 if n==0 else true+bad(n-1); bad(1).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("bad(xs):=hd(xs) if atom(xs) else bad(tl(xs)); bad(nil).", "ENACT_ERR_LIST_EMPTY"),
        ("f(f):=0 if f==0 else f(f-1); f(1).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1); even(2).", "ENACT_ERR_NAME_UNBOUND"),
        ("sum(a,b):=sum(a,b,1); sum(1)(2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f(n):=f(n-1); f(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_023_token_cases = [
        ("().", "TOK_LPAREN TOK_RPAREN TOK_DOT TOK_EOF\n"),
        ("99:().", "TOK_INT_LITERAL TOK_CONS TOK_LPAREN TOK_RPAREN TOK_DOT TOK_EOF\n"),
        ("list 99.", "TOK_IDENTIFIER TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_023_boundary_success_cases = [
        ("().", "nil\n"),
        ("99:().", "99:nil\n"),
        ("1:2:().", "1:2:nil\n"),
        ("list 99.", "99:nil\n"),
        ("list(99).", "99:nil\n"),
        ("list true.", "true:nil\n"),
        ("list nil.", "(nil):nil\n"),
        ("list((1,2)).", "(1:2:nil):nil\n"),
        ("size(()).", "0\n"),
        ("atom(()).", "true\n"),
        ("hd(list 5).", "5\n"),
        ("tl(list 5).", "nil\n"),
        ("append((), list 1).", "1:nil\n"),
        ("append(99:(), list 100).", "99:100:nil\n"),
        ("1:list 2.", "1:2:nil\n"),
        ("map(list, (1,2)).", "(1:nil):(2:nil):nil\n"),
        ("reduce(append, (), map(list, (1,2))).", "1:2:nil\n"),
        ("xs:=(); xs==nil.", "true\n"),
        ("list:=x::x; list 4.", "4\n"),
    ]

    slice_023_robustness_failure_cases = [
        ("list().", "ENACT_ERR_ARITY_MISMATCH"),
        ("size().", "ENACT_ERR_ARITY_MISMATCH"),
        ("list(1,2).", "ENACT_ERR_ARITY_MISMATCH"),
        ("list(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("list(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("list missing.", "ENACT_ERR_NAME_UNBOUND"),
        ("list 1+2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not list true.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("list 1==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("list 1<list 2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(()).", "ENACT_ERR_LIST_EMPTY"),
        ("tl(()).", "ENACT_ERR_LIST_EMPTY"),
        ("():1.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("list:=1; list 2.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_024_token_cases = [
        ("fix.", "TOK_FIX TOK_DOT TOK_EOF\n"),
        ("fixer.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("f fix (f(x):=x).", "TOK_IDENTIFIER TOK_FIX TOK_LPAREN TOK_IDENTIFIER TOK_LPAREN TOK_IDENTIFIER TOK_RPAREN TOK_ASSIGN TOK_IDENTIFIER TOK_RPAREN TOK_DOT TOK_EOF\n"),
    ]

    slice_024_boundary_success_cases = [
        ("fact fix (fact(n):=1 if n==0 else n*fact(n-1)); fact(5).", "120\n"),
        ("fact fix (fact:=n::1 if n==0 else n*fact(n-1)); fact(5).", "120\n"),
        ("nfib fix (nfib(n):=1 if n<2 else nfib(n-1)+nfib(n-2)); nfib(5).", "8\n"),
        ("len fix (len(xs):=0 if atom(xs) else 1+len(tl(xs))); len((1,2,3)).", "3\n"),
        ("reverse fix (reverse(xs):=nil if atom(xs) else append(reverse(tl(xs)), hd(xs):nil)); reverse((1,2,3)).", "3:2:1:nil\n"),
        ("(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); even(4).", "true\n"),
        ("(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); odd(4).", "false\n"),
        ("(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); map(even, (0,1,2,3)).", "true:false:true:false:nil\n"),
        ("(f,g) fix (f(n):=0 if n==0 else g(n-1)+1; g(n):=0 if n==0 else f(n-1)+1); f(3).", "3\n"),
        ("sum fix (sum(a,b):=b if a==0 else sum(a-1,b+a)); sum(3)(0).", "6\n"),
        ("sum fix (sum(a,b):=b if a==0 else sum(a-1,b+a)); add3:=sum(3); add3(0).", "6\n"),
        ("apply(f,x):=f x; fact fix (fact(n):=1 if n==0 else n*fact(n-1)); apply(fact,4).", "24\n"),
        ("step:=2; count fix (count(n):=0 if n==0 else step+count(n-1)); step:=10; count(3).", "6\n"),
        ("f fix (f(n):=1 if n==0 else f(n-1)+1); old:=f; f(n):=100; old(3).", "4\n"),
        ("(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); saved:=even; even(n):=false; odd(n):=false; saved(2).", "true\n"),
        ("make(start):=(loop fix (loop(n):=start if n==0 else loop(n-1)+1)); c:=make(10); c(3).", "13\n"),
        ("self fix (self(n):=self if n==0 else self(n-1)); self(2)==self.", "true\n"),
        ("fact fix (fact(n):=1 if n==0 else n*fact(n-1)); atom(fact).", "true\n"),
        ("fact fix (fact(n):=1 if n==0 else n*fact(n-1)); map(x::fact(x), (0,1,4)).", "1:1:24:nil\n"),
        ("(left,right) fix (left(x):=right(x); right(x):=x+1); left(4).", "5\n"),
    ]

    slice_024_robustness_failure_cases = [
        ("fix.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(f,f) fix (f(n):=n).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(even,odd) fix (even(n):=true).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(even,odd) fix (even(n):=true; extra(n):=false).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x fix (x:=1).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("f fix (1).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f fix (g(n):=n); f(1).", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f fix (f(n):=f(n,1)); f(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("(even,odd) fix (even(n):=odd(n,1); odd(n):=false); even(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("fact fix (fact(n):=1 if n==0 else n*fact(n-1)); fact(true).", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("bad fix (bad(n):=1 if n==0 else true+bad(n-1)); bad(1).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("fact fix (fact(n):=1 if n==0 else n*fact(n-1)); fact(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=x::f(x); f(1).", "ENACT_ERR_NAME_UNBOUND"),
        ("f fix (f:=x::f(x,1)); f(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f fix (f(n):=f(n-1)); f(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f fix (f(n):=f(n-1)); f(true).", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("f fix (f(n):=hd(()) if n==0 else f(n-1)); f(0).", "ENACT_ERR_LIST_EMPTY"),
    ]

    slice_025_boundary_success_cases = [
        ("member(1,nil).", "false\n"),
        ("member(1,(1,2,3)).", "true\n"),
        ("member(3,(1,2,3)).", "true\n"),
        ("member(4,(1,2,3)).", "false\n"),
        ("member(\"b\",(\"a\",\"b\")).", "true\n"),
        ("member((1,2),((1,2),(3,4))).", "true\n"),
        ("f:=x::x; member(f,list f).", "true\n"),
        ("member(hd,list hd).", "true\n"),
        ("remove(1,nil).", "nil\n"),
        ("remove(1,(1,2,3)).", "2:3:nil\n"),
        ("remove(2,(1,2,3)).", "1:3:nil\n"),
        ("remove(4,(1,2,3)).", "1:2:3:nil\n"),
        ("remove(1,(1,1,2)).", "1:2:nil\n"),
        ("difference(nil,(1,2)).", "nil\n"),
        ("difference((1,2),nil).", "1:2:nil\n"),
        ("difference((1,2,3),(2,4)).", "1:3:nil\n"),
        ("difference((\"a\",\"b\"),list \"b\").", "\"a\":nil\n"),
        ("intersection(nil,(1,2)).", "nil\n"),
        ("intersection((1,2),nil).", "nil\n"),
        ("intersection((1,2,3),(2,3,4)).", "2:3:nil\n"),
        ("intersection(((1,2),(3,4)),list((3,4))).", "(3:4:nil):nil\n"),
        ("union(nil,nil).", "nil\n"),
        ("union(nil,(2,3)).", "2:3:nil\n"),
        ("union((1,2),nil).", "1:2:nil\n"),
        ("union((3,2,1),(5,4,3)).", "2:1:5:4:3:nil\n"),
        ("union((1,2),(2,3)).", "1:2:3:nil\n"),
        ("add12:=union((1,2)); add12((2,3)).", "1:2:3:nil\n"),
        ("reduce(union,nil,((1,2),(2,3),(3,4))).", "1:2:3:4:nil\n"),
        ("filter(member(2),((1,2),(3,4),(2,5))).", "(1:2:nil):(2:5:nil):nil\n"),
        ("map(remove(2),((1,2),(2,3),(4,5))).", "(1:nil):(3:nil):(4:5:nil):nil\n"),
        ("all(member(2),((1,2),(2,3))).", "true\n"),
        ("all(member(2),((1,2),(3,4))).", "false\n"),
        ("size(union((1,2),(2,3))).", "3\n"),
    ]

    slice_025_robustness_failure_cases = [
        ("member(1,1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove(1,true).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(1,nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(nil,1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(1,nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(nil,1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(1,nil).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(nil,1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("member(1,nil,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("remove(1,nil,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("union(nil,nil,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("member(1/0,nil).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("member(1,1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("remove(missing,nil).", "ENACT_ERR_NAME_UNBOUND"),
        ("member(1,(1,2))+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("union(nil,nil)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("true and difference(nil,nil).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("m:=member(1); m(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("r:=remove(1); r(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("u:=union(nil); u(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("d:=difference(nil); d(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("i:=intersection(nil); i(1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove(1,nil)(2).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_026_token_cases = [
        ("then.", "TOK_THEN TOK_DOT TOK_EOF\n"),
        ("thenish.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("true then 1 else 2.", "TOK_TRUE TOK_THEN TOK_INT_LITERAL TOK_ELSE TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_026_boundary_success_cases = [
        ("true then 1 else 2.", "1\n"),
        ("false then 1 else 2.", "2\n"),
        ("1==1 then 10 else 20.", "10\n"),
        ("1==2 then 10 else 20.", "20\n"),
        ("true and false then 1 else 2.", "2\n"),
        ("true or 1/0==0 then 1 else 2.", "1\n"),
        ("false then 1/0 else 2.", "2\n"),
        ("true then 1 else 1/0.", "1\n"),
        ("false then 1 else true then 2 else 3.", "2\n"),
        ("true then false then 1 else 2 else 3.", "2\n"),
        ("(false then true else false) then 1 else 2.", "2\n"),
        ("fact(n):=n==0 then 1 else n*fact(n-1); fact(5).", "120\n"),
        ("nfib(n):=n<2 then 1 else nfib(n-1)+nfib(n-2)+1; nfib(5).", "15\n"),
        ("reverse(x):=x==nil then nil else append(reverse(tl x),(hd x):()); reverse((1,2,3)).", "3:2:1:nil\n"),
        ("x:=true; x then \"yes\" else \"no\".", "\"yes\"\n"),
        ("f:=x::x>0 then x else -x; f(-3).", "3\n"),
        ("map(x::x==0 then 0 else x+1,(0,1,2)).", "0:2:3:nil\n"),
        ("filter(x::x mod 2==0 then true else false,(1,2,3,4)).", "2:4:nil\n"),
        ("all(x::x<5 then true else false,(1,2,3)).", "true\n"),
        ("reduce((acc,x)::x==0 then acc else acc+x,0,(1,0,2)).", "3\n"),
        ("x where x:=true then 1 else 2.", "1\n"),
        ("true then (x:=1; x) else 0.", "1\n"),
        ("false then 0 else (x:=2; x).", "2\n"),
        ("fact fix (fact(n):=n==0 then 1 else n*fact(n-1)); fact(5).", "120\n"),
        ("(even,odd) fix (even(n):=n==0 then true else odd(n-1); odd(n):=n==0 then false else even(n-1)); even(4).", "true\n"),
        ("true then 1 if false else 2 else 3.", "2\n"),
        ("true then union((1,2),(2,3)) else nil.", "1:2:3:nil\n"),
        ("member(2,(1,2)) then remove(2,(1,2)) else nil.", "1:nil\n"),
        ("condition:=x::x>0 then \"positive\" else \"nonpositive\"; condition(0).", "\"nonpositive\"\n"),
        ("thenValue:=7; thenValue.", "7\n"),
    ]

    slice_026_robustness_failure_cases = [
        ("then.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then else 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("then 1 else 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 else.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 else else 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 else 2 else 3.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 else 2 then 3.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 if true else 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1 then 2 else 3.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("\"x\" then 1 else 2.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("(1/0)==0 then 1 else 2.", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("true then missing else 2.", "ENACT_ERR_NAME_UNBOUND"),
        ("false then 1 else missing.", "ENACT_ERR_NAME_UNBOUND"),
        ("true then true+1 else 2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("false then 1 else false+2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("false then 1 else 2 == false.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("false then 1 else 2(3).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("not (true then 1 else 2).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("true then (1:nil)+1 else 2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("then:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true then 1 else 2", "ENACT_ERR_PARSE_MISSING_DOT"),
    ]

    slice_027_token_cases = [
        ("f().", "TOK_IDENTIFIER TOK_LPAREN TOK_RPAREN TOK_DOT TOK_EOF\n"),
        ("f():=1.", "TOK_IDENTIFIER TOK_LPAREN TOK_RPAREN TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("()::1.", "TOK_LPAREN TOK_RPAREN TOK_LAMBDA TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_027_boundary_success_cases = [
        ("f():=1; f().", "1\n"),
        ("f():=true; f().", "true\n"),
        ('f():="hi"; f().', "\"hi\"\n"),
        ("f():=nil; f().", "nil\n"),
        ("f():=(1,2); f().", "1:2:nil\n"),
        ("f():=x::x+1; f()(2).", "3\n"),
        ("make():=x::x+1; inc:=make(); inc(4).", "5\n"),
        ("x:=1; f():=x; x:=2; f().", "1\n"),
        ("f():=(x:=1; x); f().", "1\n"),
        ("(()::7)().", "7\n"),
        ("f:=()::7; f().", "7\n"),
        ("apply0(f):=f(); thunk():=5; apply0(thunk).", "5\n"),
        ("fact fix (fact():=1); fact().", "1\n"),
        ("(a,b) fix (a():=1; b():=a()+1); b().", "2\n"),
        ("cond():=true; cond() then 1 else 2.", "1\n"),
        ("f():=1; f()+2.", "3\n"),
        ("f():=1; f()==1.", "true\n"),
        ("f():=1; list(f()).", "1:nil\n"),
        ("f():=1; atom(f).", "true\n"),
        ("f():=1; atom(f()).", "true\n"),
        ("f():=1; map(x::f(),(1,2,3)).", "1:1:1:nil\n"),
        ("f():=1; reduce((acc,x)::acc+f(),0,(1,2,3)).", "3\n"),
        ("f():=1; f.", "<function>\n"),
        ("()::1.", "<function>\n"),
    ]

    slice_027_robustness_failure_cases = [
        ("f().", "ENACT_ERR_NAME_UNBOUND"),
        ("1().", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("true().", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("()().", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("f(x):=x; f().", "ENACT_ERR_ARITY_MISMATCH"),
        ("f():=1; f(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f():=1; f(1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f():=1; f(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=x::x; f().", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=()::1; f(1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("size().", "ENACT_ERR_ARITY_MISMATCH"),
        ("list().", "ENACT_ERR_ARITY_MISMATCH"),
        ("append().", "ENACT_ERR_ARITY_MISMATCH"),
        ("hd().", "ENACT_ERR_ARITY_MISMATCH"),
        ("map().", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce().", "ENACT_ERR_ARITY_MISMATCH"),
        ("(()::1)(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("(()::1)(1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("f(x)():=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f()(x):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(()):=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("():=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(()::missing)().", "ENACT_ERR_NAME_UNBOUND"),
        ("(()::1)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("map(()::1,(1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_028_boundary_success_cases = [
        ("unitset(1).", "1:nil\n"),
        ("unitset true.", "true:nil\n"),
        ('unitset("a").', "\"a\":nil\n"),
        ("unitset nil.", "(nil):nil\n"),
        ("unitset((1,2)).", "(1:2:nil):nil\n"),
        ("member(1,unitset(1)).", "true\n"),
        ("member(2,unitset(1)).", "false\n"),
        ("hd(unitset(3)).", "3\n"),
        ("tl(unitset(3)).", "nil\n"),
        ("size(unitset(3)).", "1\n"),
        ("unitset(1)==list(1).", "true\n"),
        ("union(unitset(1),unitset(2)).", "1:2:nil\n"),
        ("difference(unitset(1),unitset(1)).", "nil\n"),
        ("intersection(unitset(1),unitset(1)).", "1:nil\n"),
        ("reduce(union,nil,map(unitset,(1,2))).", "1:2:nil\n"),
        ("filter(member(2),map(unitset,(1,2,3))).", "(2:nil):nil\n"),
        ("all(x::size(x)==1,map(unitset,(1,2))).", "true\n"),
        ("map(hd,map(unitset,(1,2))).", "1:2:nil\n"),
        ("f:=unitset; f(4).", "4:nil\n"),
        ("unitset(hd).", "<function>:nil\n"),
        ("f:=x::x+1; unitset(f).", "<function>:nil\n"),
        ("unitset:=x::x; unitset(5).", "5\n"),
    ]

    slice_028_robustness_failure_cases = [
        ("unitset().", "ENACT_ERR_ARITY_MISMATCH"),
        ("unitset(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("unitset(1/0).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("unitset(missing).", "ENACT_ERR_NAME_UNBOUND"),
        ("unitset(1)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not unitset(true).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("unitset(1)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("unitset(1):1.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("unitset(1)(2).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("unitset:=1; unitset 2.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("filter(unitset,(1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("all(unitset,(1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("reduce(unitset,nil,(1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
        ("unitset(1)<unitset(2).", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_029_boundary_success_cases = [
        ("version().", "\"enact-auto 0.1.0\"\n"),
        ("version.", "<function>\n"),
        ("version()==version().", "true\n"),
        ("list(version()).", "\"enact-auto 0.1.0\":nil\n"),
        ("apply0(f):=f(); apply0(version).", "\"enact-auto 0.1.0\"\n"),
        ("f:=version(); f.", "\"enact-auto 0.1.0\"\n"),
        ("unitset(version()).", "\"enact-auto 0.1.0\":nil\n"),
        ("isObject(1).", "false\n"),
        ("isObject(true).", "false\n"),
        ('isObject("x").', "false\n"),
        ("isObject(nil).", "false\n"),
        ("isObject((1,2)).", "false\n"),
        ("isObject(x::x).", "false\n"),
        ("isObject(hd).", "false\n"),
        ("isObject(append(nil)).", "false\n"),
        ("isObject(version()).", "false\n"),
        ("isObject(unitset(1)).", "false\n"),
        ("not isObject(1).", "true\n"),
        ("map(isObject,(1,true,\"x\",nil,(1,2),x::x,hd,append(nil))).", "false:false:false:false:false:false:false:false:nil\n"),
        ("filter(isObject,(1,true,\"x\",nil,(1,2))).", "nil\n"),
        ("all(x::not isObject(x),(1,true,\"x\",nil,(1,2))).", "true\n"),
        ("isObject:=x::true; isObject(1).", "true\n"),
    ]

    slice_029_robustness_failure_cases = [
        ("version(1).", "ENACT_ERR_ARITY_MISMATCH"),
        ("version(1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("isObject().", "ENACT_ERR_ARITY_MISMATCH"),
        ("isObject(1,1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("version()+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not version().", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("version()==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("version()().", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("isObject(1)+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("isObject(1)==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("map(version,(1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
        ("filter(version,(1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(version,nil,(1,2)).", "ENACT_ERR_ARITY_MISMATCH"),
        ("isObject:=1; isObject 2.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("version:=1; version().", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_030_boundary_tty_cases = [
        ("x:=1.\nx+2.\n", ["1\n", "3\n"]),
        ("x:=1.\nx:=x+4.\nx.\n", ["1\n", "5\n", "5\n"]),
        ("base:=10.\nadd_base(y):=base+y.\nbase:=20.\nadd_base(1).\n", ["10\n", "<function>\n", "20\n", "11\n"]),
        ("fact(n):=n==0 then 1 else n*fact(n-1).\nfact(5).\n", ["<function>\n", "120\n"]),
        ("add(x,y):=x+y.\ninc:=add(1).\ninc(4).\n", ["<function>\n", "<function>\n", "5\n"]),
        ("version().\nisObject(1).\n", ["\"enact-auto 0.1.0\"\n", "false\n"]),
        ("version:=()::\"local\".\nversion().\n", ["<function>\n", "\"local\"\n"]),
        ("x:=1.\nx where x:=2.\nx.\n", ["1\n", "2\n", "1\n"]),
        ("xs:=(1,2,3).\nmap(x::x+1,xs).\nreduce((a,x)::a+x,0,xs).\n", ["1:2:3:nil\n", "2:3:4:nil\n", "6\n"]),
    ]

    slice_030_robustness_tty_cases = [
        ("x:=5.\nmissing.\nx.\n", ["5\n", "ENACT_ERR_NAME_UNBOUND", "5\n"]),
        ("x:=7.\n(.\nx.\n", ["7\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN", "7\n"]),
        ("x:=2.\nx+true.\nx+1.\n", ["2\n", "ENACT_ERR_TYPE_EXPECTED_INT", "3\n"]),
        ("hd:=1.\nhd(1:nil).\nhd.\n", ["1\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION", "1\n"]),
        ("x:=1.\ny:=missing.\ny.\nx.\n", ["1\n", "ENACT_ERR_NAME_UNBOUND", "ENACT_ERR_NAME_UNBOUND", "1\n"]),
        ("inc(x):=x+1.\ninc(true).\ninc(2).\n", ["<function>\n", "ENACT_ERR_TYPE_EXPECTED_INT", "3\n"]),
        ("x:=1.\nf():=9.\nf(x:=2).\nx.\n", ["1\n", "<function>\n", "ENACT_ERR_ARITY_MISMATCH", "1\n"]),
    ]

    slice_031_boundary_success_cases = [
        ("", ""),
        ("% comment only\n", ""),
        ("x:=1.\nx+2.", "1\n3\n"),
        ("% boot\nx:=1.\n% middle\nx:=x+1.\nx.", "1\n2\n2\n"),
        ("base:=10.\nadd_base(y):=base+y.\nbase:=20.\nadd_base(1).", "10\n<function>\n20\n11\n"),
        ("fact(n):=n==0 then 1 else n*fact(n-1).\nfact(5).", "<function>\n120\n"),
        ("add(x,y):=x+y.\ninc:=add(1).\ninc(4).", "<function>\n<function>\n5\n"),
        ("s:=\"a.b\".\ns.", "\"a.b\"\n\"a.b\"\n"),
        ("x:=1 % . ignored inside comment\n.\nx+1.", "1\n2\n"),
        ("xs:=(\"a.b\",\"c.d\").\nsize(xs).", "\"a.b\":\"c.d\":nil\n2\n"),
        ("xs:=(1,2,3).\nmap(x::x+1,xs).\nreduce((a,x)::a+x,0,xs).", "1:2:3:nil\n2:3:4:nil\n6\n"),
        ("version().\nisObject(version()).", "\"enact-auto 0.1.0\"\nfalse\n"),
        ("x:=1.\nx+1.\n% trailing comment\n", "1\n2\n"),
    ]

    slice_031_robustness_failure_cases = [
        ("x:=1.\nmissing.", "ENACT_ERR_NAME_UNBOUND"),
        ("x:=1.\n(.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("x:=1.\nx+true.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("x:=1.\nx", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("x:=1.\ny:=missing.\nx.", "ENACT_ERR_NAME_UNBOUND"),
        ("x:=1.\nf():=9.\nf(x:=2).\nx.", "ENACT_ERR_ARITY_MISMATCH"),
        ("hd:=1.\nhd(1:nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_032_boundary_success_cases = [
        ("exists(x::x>0, nil).", "false\n"),
        ("exists(x::x>0, (1,2,3)).", "true\n"),
        ("exists(x::x>2, (1,2,3)).", "true\n"),
        ("exists(x::x>3, (1,2,3)).", "false\n"),
        ("exists(x::not x, (true,false)).", "true\n"),
        ("exists(hd, ((false:nil),(true:nil))).", "true\n"),
        ("exists(hd, ((false:nil),(false:nil))).", "false\n"),
        ("exists(hd, ((true:nil),nil)).", "true\n"),
        ("q:=exists(x::x>1); q((1,2)).", "true\n"),
        ("apply(f,x):=f x; apply(exists(x::x>1), (1,2)).", "true\n"),
        ("exists(member(2), map(unitset,(1,2,3))).", "true\n"),
        ("exists(x::x==\"b\", (\"a\",\"b\",\"c\")).", "true\n"),
        ("exists(x::size(x)==0, ((1,2),nil,(3,4))).", "true\n"),
        ("exists(x::x==1, (1,true)).", "true\n"),
        ("all(x::not exists(member(x), map(unitset,(1,2))), (3,4)).", "true\n"),
        ("filter(x::exists(member(x), map(unitset,(1,3))), (1,2,3)).", "1:3:nil\n"),
        ("exists(x::x>1).", "<function>\n"),
        ("exists:=x::true; exists(1).", "true\n"),
    ]

    slice_032_robustness_failure_cases = [
        ("exists(1, nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("exists(x::x>1, 1).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("exists(x::x+1, (1,2)).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("exists(size, ((1:nil),(2:nil))).", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("exists(x::x>1, nil, 1/0).", "ENACT_ERR_ARITY_MISMATCH"),
        ("exists(x::x, (1/0,2)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("exists(x::x==1, (2,true)).", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("exists(x::x<2 and 1/0==0, (2,0)).", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("exists(x::false, (1,2))+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("exists(x::false, (1,2))==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("exists:=1; exists(x::true,nil).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(exists(x::true),(1,2)).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("exists(hd, ((false:nil),nil)).", "ENACT_ERR_LIST_EMPTY"),
    ]

    slice_033_token_cases = [
        ("load \"x\".", "TOK_LOAD TOK_STRING_LITERAL TOK_DOT TOK_EOF\n"),
        ("loader.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
    ]

    slice_033_boundary_success_cases = [
        (f"load \"{load_empty_path}\".", ""),
        (f"load \"{load_defs_path}\".", "7\n<function>\n8\n"),
        (f"load \"{load_defs_path}\".\nloaded_x+1.", "7\n<function>\n8\n8\n"),
        (f"prefix:=2.\nload \"{load_defs_path}\".\nprefix+loaded_x.", "2\n7\n<function>\n8\n9\n"),
        (f"load \"{load_dot_string_path}\".", "\"a.b\"\n\"a.b\"\n"),
        (f"load \"{load_nested_outer_path}\".", "3\n7\n8\n"),
        (f"load \"{load_empty_path}\".\n1+1.", "2\n"),
        ("loader:=5.\nloader.", "5\n5\n"),
    ]

    slice_033_robustness_failure_cases = [
        ("load.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("load 1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("load(\"x\").", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("load \"missing/enact/file\".", "ENACT_ERR_LOAD_FILE"),
        ("load \"bad\\q\".", "ENACT_ERR_LEX_BAD_STRING"),
        ("load \"unterminated.", "ENACT_ERR_LEX_BAD_STRING"),
        (f"load \"{load_parse_error_path}\".", "ENACT_ERR_PARSE_MISSING_DOT"),
        (f"load \"{load_eval_error_path}\".", "ENACT_ERR_NAME_UNBOUND"),
        ("load:=x::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x:=1; load \"missing/enact/file\".", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
    ]

    slice_033_boundary_tty_cases = [
        (f"load \"{load_tty_path}\".\ntty_loaded+2.\n", ["5\n", "6\n", "7\n"]),
    ]

    slice_033_robustness_tty_cases = [
        (f"x:=1.\nload \"missing/enact/file\".\nx.\n", ["1\n", "ENACT_ERR_LOAD_FILE", "1\n"]),
    ]

    slice_034_token_cases = [
        ("'hello.", "TOK_ATOM_LITERAL TOK_DOT TOK_EOF\n"),
        ("'_x123.", "TOK_ATOM_LITERAL TOK_DOT TOK_EOF\n"),
        ("'true.", "TOK_ATOM_LITERAL TOK_DOT TOK_EOF\n"),
        ("'load.", "TOK_ATOM_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_034_boundary_success_cases = [
        ("'hello.", "'hello\n"),
        ("'_x123.", "'_x123\n"),
        ("'true.", "'true\n"),
        ("atom('hello).", "true\n"),
        ("'hello=='hello.", "true\n"),
        ("'hello!='world.", "true\n"),
        ("x:='hello; x.", "'hello\n"),
        ("'hello:nil.", "'hello:nil\n"),
        ("('a,'b).", "'a:'b:nil\n"),
        ("list 'hello.", "'hello:nil\n"),
        ("member('a,('b,'a)).", "true\n"),
        ("remove('a,('a,'b,'a)).", "'b:'a:nil\n"),
        ("map(atom,('a,\"a\",(1,2))).", "true:true:false:nil\n"),
        ("filter(x::x!='skip,('keep,'skip,'also)).", "'keep:'also:nil\n"),
        ("exists(member('a), map(unitset,('b,'a))).", "true\n"),
        ("quote(x):='x; quote(1).", "'x\n"),
        (f"load \"{load_atom_path}\".\nloaded_atom.", "'from_file\n'from_file\n'from_file\n"),
    ]

    slice_034_robustness_failure_cases = [
        ("'.", "ENACT_ERR_LEX_INVALID_CHAR"),
        ("'1.", "ENACT_ERR_LEX_INVALID_CHAR"),
        ("'hello+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1+'hello.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not 'hello.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("'hello==\"hello\".", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("'hello<1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("'hello(1).", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("1:'tail.", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd('x).", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("'hello where 'x:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
    ]

    slice_035_token_cases = [
        ("class Node < Object.", "TOK_CLASS TOK_IDENTIFIER TOK_LT TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("new Object.", "TOK_NEW TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("obj with x:=1.", "TOK_IDENTIFIER TOK_WITH TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("classy newer within self.", "TOK_IDENTIFIER TOK_IDENTIFIER TOK_IDENTIFIER TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("'class 'new 'with.", "TOK_ATOM_LITERAL TOK_ATOM_LITERAL TOK_ATOM_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_035_boundary_success_cases = [
        ("classy:=1; classy.", "1\n"),
        ("newer:=2; newer.", "2\n"),
        ("within:=3; within.", "3\n"),
        ("self:=4; self.", "4\n"),
        ("('class,'new,'with).", "'class:'new:'with:nil\n"),
    ]

    slice_035_robustness_failure_cases = [
        ("class.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node Object.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("new(Object).", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("new.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("with x:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("new:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("with:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
    ]

    slice_036_boundary_success_cases = [
        ("1+2\n", "3\n"),
        ("x:=1\nx+2\n", "1\n3\n"),
        ("x:=1.\nx+2\n", "1\n3\n"),
        ("1+2\n\n3+4\n", "3\n7\n"),
        ("1 % comment with .\n2\n", "1\n2\n"),
        ("(1,\n2)\n", "1:2:nil\n"),
        ("add(x,y):=x+y\nadd(2,3)\n", "<function>\n5\n"),
        (f"load \"{load_newline_path}\"\nloaded_newline+1\n", "5\n7\n6\n"),
        ("'line_atom\n", "'line_atom\n"),
        ("list 99\n", "99:nil\n"),
    ]

    slice_036_robustness_failure_cases = [
        ("1+\n2\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x:=1\nmissing\nx\n", "ENACT_ERR_NAME_UNBOUND"),
        ("load \"missing/enact/file\"\n", "ENACT_ERR_LOAD_FILE"),
        ("load\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1\n2+true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("(1,2\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("\"unterminated\n1\n", "ENACT_ERR_LEX_BAD_STRING"),
        ("x:=1\nx", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("with x:=1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
    ]

    slice_036_boundary_tty_cases = [
        ("tty_nl:=8\ntty_nl+1\n", ["8\n", "9\n"]),
    ]

    slice_036_robustness_tty_cases = [
        ("tty_recover:=3\nmissing\n_:=tty_recover+1\n", ["3\n", "ENACT_ERR_NAME_UNBOUND", "4\n"]),
    ]

    slice_037_boundary_success_cases = [
        ("Object\n", "<class Object>\n"),
        ("new Object\n", "<object Object>\n"),
        ("isObject(new Object)\n", "true\n"),
        ("isObject(Object)\n", "false\n"),
        ("atom(new Object)\n", "true\n"),
        ("Object==Object\n", "true\n"),
        ("o:=new Object\no\n", "<object Object>\n<object Object>\n"),
        ("o:=new Object\no==o\n", "<object Object>\ntrue\n"),
        ("new Object == new Object\n", "false\n"),
        ("list(new Object)\n", "<object Object>:nil\n"),
        ("C:=Object\nnew C\n", "<class Object>\n<object Object>\n"),
        ("map(isObject,(new Object,Object,1))\n", "true:false:false:nil\n"),
    ]

    slice_037_robustness_failure_cases = [
        ("new missing\n", "ENACT_ERR_NAME_UNBOUND"),
        ("Object:=1\nnew Object\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("new 1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("new(Object)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("new Object()\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("new Object + 1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not new Object\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("new Object < new Object\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("new Object(1)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("1:new Object\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("new Object == Object\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_038_boundary_success_cases = [
        ("class Node < Object\n", "<class Node>\n"),
        ("class Node < Object\nNode\n", "<class Node>\n<class Node>\n"),
        ("class Node < Object\nnew Node\n", "<class Node>\n<object Node>\n"),
        ("class Node < Object\nisObject(new Node)\n", "<class Node>\ntrue\n"),
        ("Base:=Object\nclass Node < Base\nnew Node\n", "<class Object>\n<class Node>\n<object Node>\n"),
        ("class Node < Object\nNode==Node\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nNode==Object\n", "<class Node>\nfalse\n"),
        ("class Node < Object\nlist(new Node)\n", "<class Node>\n<object Node>:nil\n"),
        ("class Node < Object\nmap(isObject,(new Node,Object,Node))\n", "<class Node>\ntrue:false:false:nil\n"),
        ("class Node < Object\nC:=Node\nnew C\n", "<class Node>\n<class Node>\n<object Node>\n"),
        ("class Node < Object\nclass Leaf < Node\nnew Leaf\n", "<class Node>\n<class Leaf>\n<object Leaf>\n"),
        ("class Node < Object\natom(Node)\n", "<class Node>\ntrue\n"),
    ]

    slice_038_robustness_failure_cases = [
        ("class Node < Missing\n", "ENACT_ERR_NAME_UNBOUND"),
        ("Base:=1\nclass Node < Base\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("class Node Object\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class < Object\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < 1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object + 1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nnew Missing\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class Node < Object\nnew Node + 1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nnot Node\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class Node < Object\nhd(Node)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("class Node < Object\nNode==new Node\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("class Node < Object\nNode(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_039_token_cases = [
        ("obj.value.", "TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("new Node with value:=1.", "TOK_NEW TOK_IDENTIFIER TOK_WITH TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_039_boundary_success_cases = [
        ("class Node < Object\nn:=new Node with value:=1\nn.value\n", "<class Node>\n<object Node>\n1\n"),
        ("class Node < Object\nn:=new Node with x:=1 with y:=2\nn.x+n.y\n", "<class Node>\n<object Node>\n3\n"),
        ("class Node < Object\nn:=new Node with value:=1+2\nn.value\n", "<class Node>\n<object Node>\n3\n"),
        ("class Node < Object\nn:=new Node with child:=new Node\nisObject(n.child)\n", "<class Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nf:=new Node with inc:=x::x+1\nf.inc(4)\n", "<class Node>\n<object Node>\n5\n"),
        ("class Node < Object\n(new Node with value:=3).value\n", "<class Node>\n3\n"),
        ("class Node < Object\n(new Node with x:=1 with x:=2).x\n", "<class Node>\n2\n"),
        ("class Node < Object\nn:=new Node with items:=(1,2)\nn.items\n", "<class Node>\n<object Node>\n1:2:nil\n"),
        ("class Node < Object\nn:=new Node with cls:=Node\nn.cls==Node\n", "<class Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nn:=new Node with value:=7\nn.value.\n", "<class Node>\n<object Node>\n7\n"),
        ("class Node < Object\nmap(x::x.value,(new Node with value:=1,new Node with value:=2))\n", "<class Node>\n1:2:nil\n"),
        ("class Node < Object\nn:=new Node with value:=5\nlist(n.value)\n", "<class Node>\n<object Node>\n5:nil\n"),
    ]

    slice_039_robustness_failure_cases = [
        ("obj with x:=1\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class Node < Object\n(new Node).missing\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("1.x\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nNode.x\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nnew Node with x:=missing\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class Node < Object\nnew Node with x:=1.x\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nnew Node with :=1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nnew Node with x\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nnew Node with x:=1 + true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nn:=new Node with x:=1\nn.y\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class Node < Object\nn:=new Node with x:=1\nn.x + true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nn:=new Node with x:=1\nn.x()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_040_boundary_success_cases = [
        ("classof(new Object)\n", "<class Object>\n"),
        ("classof(new Object)==Object\n", "true\n"),
        ("class Node < Object\nclassof(new Node)\n", "<class Node>\n<class Node>\n"),
        ("class Node < Object\nclassof(new Node)==Node\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nclassof(new Node)==Object\n", "<class Node>\nfalse\n"),
        ("class Node < Object\nn:=new Node\nclassof(n)==Node\n", "<class Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nn:=new Node with child:=new Node\nclassof(n.child)==Node\n", "<class Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nclass Leaf < Node\nclassof(new Leaf)==Leaf\n", "<class Node>\n<class Leaf>\ntrue\n"),
        ("class Node < Object\nclass Leaf < Node\nmap(classof,(new Node,new Leaf))\n", "<class Node>\n<class Leaf>\n<class Node>:<class Leaf>:nil\n"),
        ("class Node < Object\n(x::classof(x))(new Node)\n", "<class Node>\n<class Node>\n"),
        ("class Node < Object\nlist(classof(new Node))\n", "<class Node>\n<class Node>:nil\n"),
        ("class Node < Object\nn:=new Node with cls:=classof(new Node)\nn.cls==Node\n", "<class Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nC:=Node\nclassof(new C)==Node\n", "<class Node>\n<class Node>\ntrue\n"),
        ("class Node < Object\nall(x::classof(x)==Node,(new Node,new Node))\n", "<class Node>\ntrue\n"),
    ]

    slice_040_robustness_failure_cases = [
        ("classof()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classof(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classof(1)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof(true)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ('classof("x")\n', "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof(nil)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof(Object)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nclassof(Node)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("classof(hd)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nclassof(new Node)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_041_token_cases = [
        ("obj.x:=1.", "TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("obj.child.x:=2.", "TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ]

    slice_041_boundary_success_cases = [
        ("class Node < Object\nn:=new Node with x:=1\nn.x:=2\nn.x\n", "<class Node>\n<object Node>\n2\n2\n"),
        ("class Node < Object\nn:=new Node\nn.x:=1\nn.x\n", "<class Node>\n<object Node>\n1\n1\n"),
        ("class Node < Object\nn:=new Node\n(n.x:=2)+3\nn.x\n", "<class Node>\n<object Node>\n5\n2\n"),
        ("class Node < Object\nn:=new Node with x:=1\nn.x:=n.x+1\nn.x\n", "<class Node>\n<object Node>\n2\n2\n"),
        ("class Node < Object\nn:=new Node with child:=new Node\nn.child.x:=7\nn.child.x\n", "<class Node>\n<object Node>\n7\n7\n"),
        ("class Node < Object\nn:=new Node\nn.child:=new Node\nclassof(n.child)==Node\n", "<class Node>\n<object Node>\n<object Node>\ntrue\n"),
        ("class Node < Object\nn:=new Node\nn.f:=x::x+1\nn.f(4)\n", "<class Node>\n<object Node>\n<function>\n5\n"),
        ("class Node < Object\nn:=new Node\nn.cls:=Node\nn.cls==Node\n", "<class Node>\n<object Node>\n<class Node>\ntrue\n"),
        ("class Node < Object\nn:=new Node\nn.items:=(1,2)\nn.items\n", "<class Node>\n<object Node>\n1:2:nil\n1:2:nil\n"),
        ("class Node < Object\nn:=new Node\nn.x:=1; n.x:=n.x+2; n.x\n", "<class Node>\n<object Node>\n3\n"),
        ("class Node < Object\nn:=new Node\nsetx(o,v):=o.x:=v\nsetx(n,8)\nn.x\n", "<class Node>\n<object Node>\n<function>\n8\n8\n"),
        ("class Node < Object\nmap(x::x.value:=x.value+1,(new Node with value:=1,new Node with value:=2))\n", "<class Node>\n2:3:nil\n"),
        ("class Node < Object\n(n:=new Node).x:=9\nn.x\n", "<class Node>\n9\n9\n"),
        ("class Node < Object\nn:=new Node\nn.x:=1\nclassof(n)==Node\n", "<class Node>\n<object Node>\n1\ntrue\n"),
    ]

    slice_041_robustness_failure_cases = [
        ("1.x:=2\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("1.x:=missing\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nNode.x:=2\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("missing.x:=1\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class Node < Object\nn:=new Node\nn.x:=missing\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class Node < Object\nn:=new Node\nn.x:=1+true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nn:=new Node\nn.x:=1.y\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nn:=new Node\nn.x:=1\nn.x()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("class Node < Object\nn:=new Node\nnot (n.x:=1)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class Node < Object\nn:=new Node\nn.x(1):=2\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nn:=new Node\nn.:=1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nn:=new Node\nn.x:=\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
    ]

    slice_042_token_cases = [
        ("Node.get():=self.x.", "TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_LPAREN TOK_RPAREN TOK_ASSIGN TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("Node.set(x):=self.x:=x.", "TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_LPAREN TOK_IDENTIFIER TOK_RPAREN TOK_ASSIGN TOK_IDENTIFIER TOK_ATTR_DOT TOK_IDENTIFIER TOK_ASSIGN TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
    ]

    slice_042_boundary_success_cases = [
        ("class Node < Object\nNode.get():=self.x\n(new Node with x:=3).get()\n", "<class Node>\n<function>\n3\n"),
        ("class Node < Object\nNode.set(v):=self.x:=v\nn:=new Node\nn.set(7)\nn.x\n", "<class Node>\n<function>\n<object Node>\n7\n7\n"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(2,3)\n", "<class Node>\n<function>\n5\n"),
        ("class Node < Object\nNode.className():=classof(self)==Node\n(new Node).className()\n", "<class Node>\n<function>\ntrue\n"),
        ("class Node < Object\nNode.inc():=self.x:=self.x+1\nn:=new Node with x:=1\nn.inc()\nn.inc()\nn.x\n", "<class Node>\n<function>\n<object Node>\n2\n3\n3\n"),
        ("class Node < Object\nNode.make():=self.child:=new Node\nn:=new Node\nclassof(n.make())==Node\nclassof(n.child)==Node\n", "<class Node>\n<function>\n<object Node>\ntrue\ntrue\n"),
        ("class Node < Object\nbase:=10\nNode.addBase(x):=base+x\nbase:=20\n(new Node).addBase(1)\n", "<class Node>\n10\n<function>\n20\n11\n"),
        ("class Node < Object\nC:=Node\nC.get():=self.x\n(new Node with x:=5).get()\n", "<class Node>\n<class Node>\n<function>\n5\n"),
        ("class Node < Object\nNode.value():=1\nNode.value():=2\n(new Node).value()\n", "<class Node>\n<function>\n<function>\n2\n"),
        ("class Node < Object\nNode.value():=1\nn:=new Node\nn.value:=x::x+10\nn.value(5)\n", "<class Node>\n<function>\n<object Node>\n<function>\n15\n"),
        ("class Node < Object\nNode.value():=1\nmap(x::x.value(),(new Node,new Node))\n", "<class Node>\n<function>\n1:1:nil\n"),
        ("class Node < Object\nNode.id(x):=x\nlist((new Node).id(Node))\n", "<class Node>\n<function>\n<class Node>:nil\n"),
        ("class Node < Object\nNode.store(v):=self.saved:=v\nn:=new Node\nn.store((1,2))\nn.saved\n", "<class Node>\n<function>\n<object Node>\n1:2:nil\n1:2:nil\n"),
        ("class Node < Object\nNode.getSelf():=self\nn:=new Node\nn.getSelf()==n\n", "<class Node>\n<function>\n<object Node>\ntrue\n"),
        ("class Node < Object\nNode.zero():=0\nf:=new Node\nf.zero()\n", "<class Node>\n<function>\n<object Node>\n0\n"),
        ("class Node < Object\nNode.apply(f,x):=f(x)\n(new Node).apply(x::x+1,4)\n", "<class Node>\n<function>\n5\n"),
    ]

    slice_042_robustness_failure_cases = [
        ("class Node < Object\n(new Node).missing()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class Node < Object\nNode.get():=self.x\n(new Node).get(1)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1,1/0,3)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nn:=new Node\nn.get():=1\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("1.get()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nNode.get():=self.x\nNode.get()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nNode.get():=self.x\n(new Node).get()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class Node < Object\nNode.bad():=self.x+true\n(new Node with x:=1).bad()\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.bad(self):=self\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nNode.bad(x,x):=x\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nNode.bad(1):=1\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class Node < Object\nNode.value():=1\nn:=new Node\nn.value:=1\nn.value()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_043_boundary_success_cases = [
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\n(new Leaf).value()\n", "<class Node>\n<function>\n<class Leaf>\n1\n"),
        ("class Node < Object\nNode.get():=self.x\nclass Leaf < Node\n(new Leaf with x:=4).get()\n", "<class Node>\n<function>\n<class Leaf>\n4\n"),
        ("class Node < Object\nNode.add(a,b):=a+b\nclass Leaf < Node\n(new Leaf).add(2,3)\n", "<class Node>\n<function>\n<class Leaf>\n5\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nLeaf.value():=2\n(new Leaf).value()\n", "<class Node>\n<function>\n<class Leaf>\n<function>\n2\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nLeaf.value():=2\n(new Node).value()\n", "<class Node>\n<function>\n<class Leaf>\n<function>\n1\n"),
        ("class A < Object\nclass B < A\nclass C < B\nA.id():=classof(self)==C\n(new C).id()\n", "<class A>\n<class B>\n<class C>\n<function>\ntrue\n"),
        ("class Node < Object\nclass Leaf < Node\nNode.isLeaf():=classof(self)==Leaf\n(new Leaf).isLeaf()\n", "<class Node>\n<class Leaf>\n<function>\ntrue\n"),
        ("class Node < Object\nNode.value():=self.x\nclass Leaf < Node\nmap(x::x.value(),(new Leaf with x:=1,new Leaf with x:=2))\n", "<class Node>\n<function>\n<class Leaf>\n1:2:nil\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nn:=new Leaf\nn.value:=x::x+10\nn.value(5)\n", "<class Node>\n<function>\n<class Leaf>\n<object Leaf>\n<function>\n15\n"),
        ("class Node < Object\nbase:=10\nNode.addBase(x):=base+x\nclass Leaf < Node\nbase:=20\n(new Leaf).addBase(1)\n", "<class Node>\n10\n<function>\n<class Leaf>\n20\n11\n"),
        ("Object.root():=1\nclass Node < Object\n(new Node).root()\n", "<function>\n<class Node>\n1\n"),
    ]

    slice_043_robustness_failure_cases = [
        ("class Node < Object\nclass Leaf < Node\n(new Leaf).missing()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\n(new Leaf).value(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.bad():=self.x+true\nclass Leaf < Node\n(new Leaf with x:=1).bad()\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nn:=new Leaf\nn.value:=1\nn.value()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nLeaf.value(x):=x\n(new Leaf).value()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("Object.root():=1\nclass Node < Object\nNode.root(x):=x\n(new Node).root()\n", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_044_boundary_success_cases = [
        ("attrs(new Object)\n", "nil\n"),
        ("class Node < Object\nattrs(new Node)\n", "<class Node>\nnil\n"),
        ("class Node < Object\nattrs(new Node with x:=1)\n", "<class Node>\n'x:nil\n"),
        ("class Node < Object\nattrs(new Node with x:=1 with y:=2)\n", "<class Node>\n'x:'y:nil\n"),
        ("class Node < Object\nattrs(new Node with x:=1 with y:=2 with x:=3)\n", "<class Node>\n'x:'y:nil\n"),
        ("class Node < Object\nn:=new Node\nn.x:=1\nattrs(n)\n", "<class Node>\n<object Node>\n1\n'x:nil\n"),
        ("class Node < Object\nn:=new Node with child:=(new Node with value:=7)\nattrs(n.child)\n", "<class Node>\n<object Node>\n'value:nil\n"),
        ("class Node < Object\nmember('x,attrs(new Node with x:=1))\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nsize(attrs(new Node with x:=1 with y:=2))\n", "<class Node>\n2\n"),
        ("class Node < Object\nmap(attrs,(new Node with x:=1,new Node with y:=2))\n", "<class Node>\n('x:nil):('y:nil):nil\n"),
        ("class Node < Object\nall(x::member('x,attrs(x)),(new Node with x:=1,new Node with x:=2))\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nNode.value():=1\nattrs(new Node)\n", "<class Node>\n<function>\nnil\n"),
        ("class Node < Object\nclass Leaf < Node\nattrs(new Leaf with x:=1)\n", "<class Node>\n<class Leaf>\n'x:nil\n"),
        ("f:=attrs\nclass Node < Object\nf(new Node with x:=1)\n", "<function>\n<class Node>\n'x:nil\n"),
        ("attrs:=x::nil\nattrs(new Object)\n", "<function>\nnil\n"),
    ]

    slice_044_robustness_failure_cases = [
        ("attrs()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("attrs(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("attrs(1)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(true)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ('attrs("x")\n', "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(nil)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(Object)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(hd)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(new Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not attrs(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("attrs:=1\nattrs(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    token_cases = [
        ("-1.", "TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1-2.", "TOK_INT_LITERAL TOK_MINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1*-2.", "TOK_INT_LITERAL TOK_STAR TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1--2.", "TOK_INT_LITERAL TOK_MINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("--1.", "TOK_UMINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("true.", "TOK_TRUE TOK_DOT TOK_EOF\n"),
        ("false.", "TOK_FALSE TOK_DOT TOK_EOF\n"),
        ("1==2.", "TOK_INT_LITERAL TOK_EQEQ TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1==-2.", "TOK_INT_LITERAL TOK_EQEQ TOK_UMINUS TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1!=2.", "TOK_INT_LITERAL TOK_NEQ TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1<2.", "TOK_INT_LITERAL TOK_LT TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1>2.", "TOK_INT_LITERAL TOK_GT TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1<=2.", "TOK_INT_LITERAL TOK_LTE TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("1>=2.", "TOK_INT_LITERAL TOK_GTE TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("7 mod 3.", "TOK_INT_LITERAL TOK_MOD TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("x.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("_x.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("foo_bar123.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("modern.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("wherever.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("trueValue.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("and_then.", "TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("x:=1.", "TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ("x:=1; x.", "TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_SEMI TOK_IDENTIFIER TOK_DOT TOK_EOF\n"),
        ("x where x:=1.", "TOK_IDENTIFIER TOK_WHERE TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        ('"".', "TOK_STRING_LITERAL TOK_DOT TOK_EOF\n"),
        ('"hello\\n".', "TOK_STRING_LITERAL TOK_DOT TOK_EOF\n"),
        ("true and false.", "TOK_TRUE TOK_AND TOK_FALSE TOK_DOT TOK_EOF\n"),
        ("not false.", "TOK_NOT TOK_FALSE TOK_DOT TOK_EOF\n"),
        ("1 if true else 2.", "TOK_INT_LITERAL TOK_IF TOK_TRUE TOK_ELSE TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        (" \t\n(8+2)/5.", "TOK_LPAREN TOK_INT_LITERAL TOK_PLUS TOK_INT_LITERAL TOK_RPAREN TOK_SLASH TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
        (long_comment, "TOK_LPAREN TOK_INT_LITERAL TOK_PLUS TOK_INT_LITERAL TOK_RPAREN TOK_SLASH TOK_INT_LITERAL TOK_DOT TOK_EOF\n"),
    ] + slice_008_token_cases + slice_009_token_cases + slice_010_token_cases + slice_013_token_cases + slice_017_token_cases + slice_023_token_cases + slice_024_token_cases + slice_026_token_cases + slice_027_token_cases + slice_033_token_cases + slice_034_token_cases + slice_035_token_cases + slice_039_token_cases + slice_041_token_cases + slice_042_token_cases

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
        ("7 mod 3.", "1\n"),
        ("-7 mod 3.", "-1\n"),
        ("7 mod -3.", "1\n"),
        ("-7 mod -3.", "-1\n"),
        ("8 mod 3*2.", "4\n"),
        ("8 mod (3*2).", "2\n"),
        ("1+8 mod 3.", "3\n"),
        ("8/3 mod 2.", "0\n"),
        ("2*3 mod 4.", "2\n"),
        ("2147483647.", "2147483647\n"),
        ("-2147483648.", "-2147483648\n"),
        ("46340*46340.", "2147395600\n"),
        ("true.", "true\n"),
        ("false.", "false\n"),
        ("1==1.", "true\n"),
        ("1==0.", "false\n"),
        ("0==0.", "true\n"),
        ("-1==-1.", "true\n"),
        ("(1+2)==3.", "true\n"),
        ("2147483647==2147483647.", "true\n"),
        ("-2147483648==-2147483648.", "true\n"),
        ("true==true.", "true\n"),
        ("false==false.", "true\n"),
        ("true==false.", "false\n"),
        ("1!=2.", "true\n"),
        ("1!=1.", "false\n"),
        ("true!=false.", "true\n"),
        ("true!=true.", "false\n"),
        ('""=="".', "true\n"),
        ('"a"=="a".', "true\n"),
        ('"a"=="b".', "false\n"),
        ('"a"!="b".', "true\n"),
        ('"a"!="a".', "false\n"),
        ("0<1.", "true\n"),
        ("1<0.", "false\n"),
        ("1<=1.", "true\n"),
        ("1<=0.", "false\n"),
        ("3>2.", "true\n"),
        ("2>3.", "false\n"),
        ("3>=3.", "true\n"),
        ("3>=4.", "false\n"),
        ("2147483647>=2147483647.", "true\n"),
        ("-2147483648<=-2147483648.", "true\n"),
        ("-1<0.", "true\n"),
        ("0>-1.", "true\n"),
        ("1+2<4.", "true\n"),
        ("not 1<2.", "false\n"),
        ("1 if 2>=2 else 3.", "1\n"),
        ("not true.", "false\n"),
        ("not false.", "true\n"),
        ("not not true.", "true\n"),
        ("true and true.", "true\n"),
        ("true and false.", "false\n"),
        ("false or false.", "false\n"),
        ("false or true.", "true\n"),
        ("not false and true.", "true\n"),
        ("false and 1/0==0.", "false\n"),
        ("true or 1/0==0.", "true\n"),
        ("1 if true else 2.", "1\n"),
        ("1 if false else 2.", "2\n"),
        ("1 if 1==1 else 2.", "1\n"),
        ("1 if false else 2 if true else 3.", "2\n"),
        ("1 if true else false.", "1\n"),
        ("1 if false else false.", "false\n"),
        ("((true)).", "true\n"),
        ('"".', "\"\"\n"),
        ('"hello".', "\"hello\"\n"),
        ('"hello world".', "\"hello world\"\n"),
        ('"line\\n".', "\"line\\n\"\n"),
        ('"tab\\tend".', "\"tab\\tend\"\n"),
        ('"quote: \\"".', "\"quote: \\\"\"\n"),
        ('"slash: \\\\".', '"slash: \\\\"\n'),
        ('1 if false else "fallback".', "\"fallback\"\n"),
        ("x:=1.", "1\n"),
        ("x:=1; x.", "1\n"),
        ("x:=1; x+2.", "3\n"),
        ("x:=true; x and false.", "false\n"),
        ("x:=1; x:=2; x.", "2\n"),
        ("x:=1; y:=x+2; y.", "3\n"),
        ("x:=1 if true else 2; x.", "1\n"),
        ("(x:=1; x)+2.", "3\n"),
        ("x:=y:=1; x+y.", "2\n"),
        ("x:=1; y:=2; x<y.", "true\n"),
        ('x:="hi"; x.', "\"hi\"\n"),
        ('x:="hi"; y:=x; y.', "\"hi\"\n"),
        ('x:="a"; x=="a".', "true\n"),
        ("x where x:=1.", "1\n"),
        ("x+2 where x:=1.", "3\n"),
        ("x==1 where x:=1.", "true\n"),
        ("x where x:=(1 if true else 2).", "1\n"),
        ('x where x:="hi".', "\"hi\"\n"),
        ("x+1 where x:=7 mod 3.", "2\n"),
        ("x:=10; (x where x:=1); x.", "10\n"),
        ("x:=10; ((x:=20) where y:=1); x.", "10\n"),
        ("x + (y where y:=2) where x:=1.", "3\n"),
        ("1 if x where x:=true else 2.", "1\n"),
        ("true and x where x:=true.", "true\n"),
        ("x:=1; (x where x:=2); x.", "1\n"),
    ] + slice_008_boundary_success_cases + slice_009_boundary_success_cases + slice_010_boundary_success_cases + slice_011_boundary_success_cases + slice_012_boundary_success_cases + slice_013_boundary_success_cases + slice_014_boundary_success_cases + slice_015_boundary_success_cases + slice_016_boundary_success_cases + slice_017_boundary_success_cases + slice_018_boundary_success_cases + slice_019_boundary_success_cases + slice_020_boundary_success_cases + slice_021_boundary_success_cases + slice_022_boundary_success_cases + slice_023_boundary_success_cases + slice_024_boundary_success_cases + slice_025_boundary_success_cases + slice_026_boundary_success_cases + slice_027_boundary_success_cases + slice_028_boundary_success_cases + slice_029_boundary_success_cases + slice_031_boundary_success_cases + slice_032_boundary_success_cases + slice_033_boundary_success_cases + slice_034_boundary_success_cases + slice_035_boundary_success_cases + slice_036_boundary_success_cases + slice_037_boundary_success_cases + slice_038_boundary_success_cases + slice_039_boundary_success_cases + slice_040_boundary_success_cases + slice_041_boundary_success_cases + slice_042_boundary_success_cases + slice_043_boundary_success_cases + slice_044_boundary_success_cases

    failure_cases = [
        ("1", "ENACT_ERR_PARSE_MISSING_DOT"),
        (".", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("-.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1+.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1++2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1//2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("-2147483648 mod -1.", "ENACT_ERR_INT_OVERFLOW"),
        ("1 mod 0.", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("a.", "ENACT_ERR_NAME_UNBOUND"),
        ("true", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("==.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1==.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1==2", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("1==2==3.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("<.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("<1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1<.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1<2<3.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1!=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1<=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1>=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true!=1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("true<false.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1<true.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("x.", "ENACT_ERR_NAME_UNBOUND"),
        ("_x.", "ENACT_ERR_NAME_UNBOUND"),
        ("x1.", "ENACT_ERR_NAME_UNBOUND"),
        ("foo_bar123.", "ENACT_ERR_NAME_UNBOUND"),
        ("trueValue.", "ENACT_ERR_NAME_UNBOUND"),
        ("and_then.", "ENACT_ERR_NAME_UNBOUND"),
        ("modern.", "ENACT_ERR_NAME_UNBOUND"),
        ("wherever.", "ENACT_ERR_NAME_UNBOUND"),
        ("x+1.", "ENACT_ERR_NAME_UNBOUND"),
        ("1+x.", "ENACT_ERR_NAME_UNBOUND"),
        ("x==1.", "ENACT_ERR_NAME_UNBOUND"),
        ("1 if flag else 2.", "ENACT_ERR_NAME_UNBOUND"),
        ("x", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("1abc.", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("trueValue", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("_.", "ENACT_ERR_NAME_UNBOUND"),
        (long_identifier, "ENACT_ERR_NAME_UNBOUND"),
        ("not.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("and true.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true and.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("or false.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("false or.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1 and true.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("1 or false.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("1 if true.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1 if else 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1 if 1 else 2.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("1 if true else.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true==1.", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("true+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1+false.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ('"unterminated.', "ENACT_ERR_LEX_BAD_STRING"),
        ('"bad\\q".', "ENACT_ERR_LEX_BAD_STRING"),
        ('"line\nbreak".', "ENACT_ERR_LEX_BAD_STRING"),
        ('"x"+1.', "ENACT_ERR_TYPE_EXPECTED_INT"),
        ('1+"x".', "ENACT_ERR_TYPE_EXPECTED_INT"),
        ('1 if "x" else 2.', "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ('"x"<"y".', "ENACT_ERR_TYPE_EXPECTED_INT"),
        ('"x"==1.', "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("mod 2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("2 mod.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("true mod 2.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("2 mod false.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("where x:=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x where x:=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x where :=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x where 1:=2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x where x:=1", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("(x where x:=1); x.", "ENACT_ERR_NAME_UNBOUND"),
        ("x where y:=1.", "ENACT_ERR_NAME_UNBOUND"),
        ("x where x:=y.", "ENACT_ERR_NAME_UNBOUND"),
        ("x+1 where x:=true.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("1 if x where x:=1 else 2.", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("=.", "ENACT_ERR_LEX_BARE_EQUALS"),
        ("x:=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        (":=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("1:=2.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x:=1;.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        (";x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x; .", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("x:=true; x+1.", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("x:=y.", "ENACT_ERR_NAME_UNBOUND"),
        ("x+1; x:=2.", "ENACT_ERR_NAME_UNBOUND"),
        ("x:=1; y.", "ENACT_ERR_NAME_UNBOUND"),
    ] + slice_008_robustness_failure_cases + slice_009_robustness_failure_cases + slice_010_robustness_failure_cases + slice_011_robustness_failure_cases + slice_012_robustness_failure_cases + slice_013_robustness_failure_cases + slice_014_robustness_failure_cases + slice_015_robustness_failure_cases + slice_016_robustness_failure_cases + slice_017_robustness_failure_cases + slice_018_robustness_failure_cases + slice_019_robustness_failure_cases + slice_020_robustness_failure_cases + slice_021_robustness_failure_cases + slice_022_robustness_failure_cases + slice_023_robustness_failure_cases + slice_024_robustness_failure_cases + slice_025_robustness_failure_cases + slice_026_robustness_failure_cases + slice_027_robustness_failure_cases + slice_028_robustness_failure_cases + slice_029_robustness_failure_cases + slice_031_robustness_failure_cases + slice_032_robustness_failure_cases + slice_033_robustness_failure_cases + slice_034_robustness_failure_cases + slice_035_robustness_failure_cases + slice_036_robustness_failure_cases + slice_037_robustness_failure_cases + slice_038_robustness_failure_cases + slice_039_robustness_failure_cases + slice_040_robustness_failure_cases + slice_041_robustness_failure_cases + slice_042_robustness_failure_cases + slice_043_robustness_failure_cases + slice_044_robustness_failure_cases

    token_failure_cases = [
        ("$x.", "ENACT_ERR_LEX_INVALID_CHAR"),
        (huge_integer, "ENACT_ERR_LEX_BAD_INTEGER"),
        ('"bad\\q".', "ENACT_ERR_LEX_BAD_STRING"),
        ("=", "ENACT_ERR_LEX_BARE_EQUALS"),
    ]

    for source, expected in token_cases:
        expect_tokens(source, expected)

    for source, expected_code in token_failure_cases:
        expect_token_failure(source, expected_code)

    for source, expected in success_cases:
        expect_success(source, expected)

    for source, expected_code in failure_cases:
        expect_failure(source, expected_code)

    expect_tty_line("1+2.\n", "3\n")

    for source, expected_fragments in slice_030_boundary_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    for source, expected_fragments in slice_033_boundary_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    for source, expected_fragments in slice_036_boundary_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    for source, expected_fragments in slice_030_robustness_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    for source, expected_fragments in slice_033_robustness_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    for source, expected_fragments in slice_036_robustness_tty_cases:
        expect_tty_fragments(source, expected_fragments)

    total = len(token_cases) + len(token_failure_cases) + len(success_cases) + len(failure_cases)
    total += 1 + len(slice_030_boundary_tty_cases) + len(slice_030_robustness_tty_cases)
    total += len(slice_033_boundary_tty_cases) + len(slice_033_robustness_tty_cases)
    total += len(slice_036_boundary_tty_cases) + len(slice_036_robustness_tty_cases)
    print(f"passed {total} checks")
    print(f"slice 008 boundary regression checks: {len(slice_008_token_cases) + len(slice_008_boundary_success_cases)}")
    print(f"slice 008 robustness regression checks: {len(slice_008_robustness_failure_cases)}")
    print(f"slice 009 boundary regression checks: {len(slice_009_token_cases) + len(slice_009_boundary_success_cases)}")
    print(f"slice 009 robustness regression checks: {len(slice_009_robustness_failure_cases)}")
    print(f"slice 010 boundary regression checks: {len(slice_010_token_cases) + len(slice_010_boundary_success_cases)}")
    print(f"slice 010 robustness regression checks: {len(slice_010_robustness_failure_cases)}")
    print(f"slice 011 boundary regression checks: {len(slice_011_boundary_success_cases)}")
    print(f"slice 011 robustness regression checks: {len(slice_011_robustness_failure_cases)}")
    print(f"slice 012 boundary regression checks: {len(slice_012_boundary_success_cases)}")
    print(f"slice 012 robustness regression checks: {len(slice_012_robustness_failure_cases)}")
    print(f"slice 013 boundary regression checks: {len(slice_013_token_cases) + len(slice_013_boundary_success_cases)}")
    print(f"slice 013 robustness regression checks: {len(slice_013_robustness_failure_cases)}")
    print(f"slice 014 boundary regression checks: {len(slice_014_boundary_success_cases)}")
    print(f"slice 014 robustness regression checks: {len(slice_014_robustness_failure_cases)}")
    print(f"slice 015 boundary regression checks: {len(slice_015_boundary_success_cases)}")
    print(f"slice 015 robustness regression checks: {len(slice_015_robustness_failure_cases)}")
    print(f"slice 016 boundary regression checks: {len(slice_016_boundary_success_cases)}")
    print(f"slice 016 robustness regression checks: {len(slice_016_robustness_failure_cases)}")
    print(f"slice 017 boundary regression checks: {len(slice_017_token_cases) + len(slice_017_boundary_success_cases)}")
    print(f"slice 017 robustness regression checks: {len(slice_017_robustness_failure_cases)}")
    print(f"slice 018 boundary regression checks: {len(slice_018_boundary_success_cases)}")
    print(f"slice 018 robustness regression checks: {len(slice_018_robustness_failure_cases)}")
    print(f"slice 019 boundary regression checks: {len(slice_019_boundary_success_cases)}")
    print(f"slice 019 robustness regression checks: {len(slice_019_robustness_failure_cases)}")
    print(f"slice 020 boundary regression checks: {len(slice_020_boundary_success_cases)}")
    print(f"slice 020 robustness regression checks: {len(slice_020_robustness_failure_cases)}")
    print(f"slice 021 boundary regression checks: {len(slice_021_boundary_success_cases)}")
    print(f"slice 021 robustness regression checks: {len(slice_021_robustness_failure_cases)}")
    print(f"slice 022 boundary regression checks: {len(slice_022_boundary_success_cases)}")
    print(f"slice 022 robustness regression checks: {len(slice_022_robustness_failure_cases)}")
    print(f"slice 023 boundary regression checks: {len(slice_023_token_cases) + len(slice_023_boundary_success_cases)}")
    print(f"slice 023 robustness regression checks: {len(slice_023_robustness_failure_cases)}")
    print(f"slice 024 boundary regression checks: {len(slice_024_token_cases) + len(slice_024_boundary_success_cases)}")
    print(f"slice 024 robustness regression checks: {len(slice_024_robustness_failure_cases)}")
    print(f"slice 025 boundary regression checks: {len(slice_025_boundary_success_cases)}")
    print(f"slice 025 robustness regression checks: {len(slice_025_robustness_failure_cases)}")
    print(f"slice 026 boundary regression checks: {len(slice_026_token_cases) + len(slice_026_boundary_success_cases)}")
    print(f"slice 026 robustness regression checks: {len(slice_026_robustness_failure_cases)}")
    print(f"slice 027 boundary regression checks: {len(slice_027_token_cases) + len(slice_027_boundary_success_cases)}")
    print(f"slice 027 robustness regression checks: {len(slice_027_robustness_failure_cases)}")
    print(f"slice 028 boundary regression checks: {len(slice_028_boundary_success_cases)}")
    print(f"slice 028 robustness regression checks: {len(slice_028_robustness_failure_cases)}")
    print(f"slice 029 boundary regression checks: {len(slice_029_boundary_success_cases)}")
    print(f"slice 029 robustness regression checks: {len(slice_029_robustness_failure_cases)}")
    print(f"slice 030 boundary regression checks: {len(slice_030_boundary_tty_cases)}")
    print(f"slice 030 robustness regression checks: {len(slice_030_robustness_tty_cases)}")
    print(f"slice 031 boundary regression checks: {len(slice_031_boundary_success_cases)}")
    print(f"slice 031 robustness regression checks: {len(slice_031_robustness_failure_cases)}")
    print(f"slice 032 boundary regression checks: {len(slice_032_boundary_success_cases)}")
    print(f"slice 032 robustness regression checks: {len(slice_032_robustness_failure_cases)}")
    print(f"slice 033 boundary regression checks: {len(slice_033_token_cases) + len(slice_033_boundary_success_cases) + len(slice_033_boundary_tty_cases)}")
    print(f"slice 033 robustness regression checks: {len(slice_033_robustness_failure_cases) + len(slice_033_robustness_tty_cases)}")
    print(f"slice 034 boundary regression checks: {len(slice_034_token_cases) + len(slice_034_boundary_success_cases)}")
    print(f"slice 034 robustness regression checks: {len(slice_034_robustness_failure_cases)}")
    print(f"slice 035 boundary regression checks: {len(slice_035_token_cases) + len(slice_035_boundary_success_cases)}")
    print(f"slice 035 robustness regression checks: {len(slice_035_robustness_failure_cases)}")
    print(f"slice 036 boundary regression checks: {len(slice_036_boundary_success_cases) + len(slice_036_boundary_tty_cases)}")
    print(f"slice 036 robustness regression checks: {len(slice_036_robustness_failure_cases) + len(slice_036_robustness_tty_cases)}")
    print(f"slice 037 boundary regression checks: {len(slice_037_boundary_success_cases)}")
    print(f"slice 037 robustness regression checks: {len(slice_037_robustness_failure_cases)}")
    print(f"slice 038 boundary regression checks: {len(slice_038_boundary_success_cases)}")
    print(f"slice 038 robustness regression checks: {len(slice_038_robustness_failure_cases)}")
    print(f"slice 039 boundary regression checks: {len(slice_039_token_cases) + len(slice_039_boundary_success_cases)}")
    print(f"slice 039 robustness regression checks: {len(slice_039_robustness_failure_cases)}")
    print(f"slice 040 boundary regression checks: {len(slice_040_boundary_success_cases)}")
    print(f"slice 040 robustness regression checks: {len(slice_040_robustness_failure_cases)}")
    print(f"slice 041 boundary regression checks: {len(slice_041_token_cases) + len(slice_041_boundary_success_cases)}")
    print(f"slice 041 robustness regression checks: {len(slice_041_robustness_failure_cases)}")
    print(f"slice 042 boundary regression checks: {len(slice_042_token_cases) + len(slice_042_boundary_success_cases)}")
    print(f"slice 042 robustness regression checks: {len(slice_042_robustness_failure_cases)}")
    print(f"slice 043 boundary regression checks: {len(slice_043_boundary_success_cases)}")
    print(f"slice 043 robustness regression checks: {len(slice_043_robustness_failure_cases)}")
    print(f"slice 044 boundary regression checks: {len(slice_044_boundary_success_cases)}")
    print(f"slice 044 robustness regression checks: {len(slice_044_robustness_failure_cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
