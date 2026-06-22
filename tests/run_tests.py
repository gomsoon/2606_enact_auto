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

    slice_045_boundary_success_cases = [
        ("supers(Object)\n", "nil\n"),
        ("supers(Object)==nil\n", "true\n"),
        ("class Node < Object\nsupers(Node)\n", "<class Node>\n<class Object>:nil\n"),
        ("class Node < Object\nhd(supers(Node))==Object\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nsize(supers(Node))\n", "<class Node>\n1\n"),
        ("size(supers(Object))\n", "0\n"),
        ("class Node < Object\nmember(Object,supers(Node))\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nlist(hd(supers(Node)))\n", "<class Node>\n<class Object>:nil\n"),
        ("class Node < Object\nC:=Node\nsupers(C)==supers(Node)\n", "<class Node>\n<class Node>\ntrue\n"),
        ("class Node < Object\nclass Leaf < Node\nsupers(Leaf)\n", "<class Node>\n<class Leaf>\n<class Node>:nil\n"),
        ("class Node < Object\nclass Leaf < Node\nhd(supers(Leaf))==Node\n", "<class Node>\n<class Leaf>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nmember(Object,supers(C))\n", "<class A>\n<class B>\n<class C>\nfalse\n"),
        ("class Node < Object\nclass Leaf < Node\nmap(size,map(supers,(Object,Node,Leaf)))\n", "<class Node>\n<class Leaf>\n0:1:1:nil\n"),
        ("class Node < Object\nclass Leaf < Node\nfilter(x::size(supers(x))==1,(Object,Node,Leaf))\n", "<class Node>\n<class Leaf>\n<class Node>:<class Leaf>:nil\n"),
        ("class Node < Object\nclass Leaf < Node\nsupers(classof(new Leaf))\n", "<class Node>\n<class Leaf>\n<class Node>:nil\n"),
        ("f:=supers\nclass Node < Object\nf(Node)\n", "<function>\n<class Node>\n<class Object>:nil\n"),
        ("supers:=x::nil\nclass Node < Object\nsupers(Node)\n", "<function>\n<class Node>\nnil\n"),
    ]

    slice_045_robustness_failure_cases = [
        ("supers()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("supers(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("supers(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('supers("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers(hd)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("supers(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not supers(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("supers:=1\nsupers(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_046_boundary_success_cases = [
        ("superiors(Object)\n", "nil\n"),
        ("superiors(Object)==nil\n", "true\n"),
        ("class Node < Object\nsuperiors(Node)\n", "<class Node>\n<class Object>:nil\n"),
        ("class Node < Object\nhd(superiors(Node))==Object\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nsize(superiors(Node))\n", "<class Node>\n1\n"),
        ("size(superiors(Object))\n", "0\n"),
        ("class Node < Object\nmember(Object,superiors(Node))\n", "<class Node>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nsuperiors(C)\n", "<class A>\n<class B>\n<class C>\n<class B>:<class A>:<class Object>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nsupers(C)\n", "<class A>\n<class B>\n<class C>\n<class B>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nsize(superiors(C))\n", "<class A>\n<class B>\n<class C>\n3\n"),
        ("class A < Object\nclass B < A\nclass C < B\nhd(superiors(C))==B\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nmember(Object,superiors(C))\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nmember(C,superiors(C))\n", "<class A>\n<class B>\n<class C>\nfalse\n"),
        ("class Node < Object\nclass Leaf < Node\nmap(size,map(superiors,(Object,Node,Leaf)))\n", "<class Node>\n<class Leaf>\n0:1:2:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nfilter(x::member(Object,superiors(x)),(Object,A,B,C))\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class C>:nil\n"),
        ("class Node < Object\nclass Leaf < Node\nsuperiors(classof(new Leaf))\n", "<class Node>\n<class Leaf>\n<class Node>:<class Object>:nil\n"),
        ("f:=superiors\nclass Node < Object\nf(Node)\n", "<function>\n<class Node>\n<class Object>:nil\n"),
        ("superiors:=x::nil\nclass Node < Object\nsuperiors(Node)\n", "<function>\n<class Node>\nnil\n"),
    ]

    slice_046_robustness_failure_cases = [
        ("superiors()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('superiors("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(hd)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not superiors(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("superiors:=1\nsuperiors(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_047_boundary_success_cases = [
        ("methods(Object)\n", "nil\n"),
        ("methods(Object)==nil\n", "true\n"),
        ("class Node < Object\nmethods(Node)\n", "<class Node>\nnil\n"),
        ("class Node < Object\nNode.get():=1\nmethods(Node)\n", "<class Node>\n<function>\n'get:nil\n"),
        (
            "class Node < Object\nNode.get():=1\nNode.set(v):=v\nmethods(Node)\n",
            "<class Node>\n<function>\n<function>\n'get:'set:nil\n",
        ),
        (
            "class Node < Object\nNode.value():=1\nNode.value():=2\nmethods(Node)\n",
            "<class Node>\n<function>\n<function>\n'value:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nmethods(Leaf)\n",
            "<class Node>\n<function>\n<class Leaf>\nnil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nLeaf.set(v):=v\nmethods(Leaf)\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n'set:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\n(new Leaf).get()\nmethods(Leaf)\n",
            "<class Node>\n<function>\n<class Leaf>\n1\nnil\n",
        ),
        ("class Node < Object\nNode.get():=1\nmember('get,methods(Node))\n", "<class Node>\n<function>\ntrue\n"),
        (
            "class Node < Object\nNode.get():=1\nNode.set(v):=v\nsize(methods(Node))\n",
            "<class Node>\n<function>\n<function>\n2\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nLeaf.set(v):=v\nmap(size,map(methods,(Object,Node,Leaf)))\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n0:1:1:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nLeaf.set(v):=v\nfilter(x::member('get,methods(x)),(Object,Node,Leaf))\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n<class Node>:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nmethods(classof(new Node))\n",
            "<class Node>\n<function>\n'get:nil\n",
        ),
        ("f:=methods\nclass Node < Object\nNode.get():=1\nf(Node)\n", "<function>\n<class Node>\n<function>\n'get:nil\n"),
        ("methods:=x::nil\nclass Node < Object\nNode.get():=1\nmethods(Node)\n", "<function>\n<class Node>\n<function>\nnil\n"),
    ]

    slice_047_robustness_failure_cases = [
        ("methods()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methods(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methods(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('methods("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods(hd)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methods(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not methods(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("methods:=1\nmethods(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_048_boundary_success_cases = [
        ("classes(Object)\n", "<class Object>:nil\n"),
        ("hd(classes(Object))==Object\n", "true\n"),
        ("tl(classes(Object))==nil\n", "true\n"),
        ("size(classes(Object))\n", "1\n"),
        ("class Node < Object\nclasses(Node)\n", "<class Node>\n<class Node>:<class Object>:nil\n"),
        ("class Node < Object\nhd(classes(Node))==Node\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nhd(tl(classes(Node)))==Object\n", "<class Node>\ntrue\n"),
        (
            "class A < Object\nclass B < A\nclass C < B\nclasses(C)\n",
            "<class A>\n<class B>\n<class C>\n<class C>:<class B>:<class A>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < B\nsize(classes(C))\n",
            "<class A>\n<class B>\n<class C>\n4\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < B\nmember(C,classes(C))\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < B\nmember(C,superiors(C))\n",
            "<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        ("class Node < Object\nclasses(Node)==append(list(Node),superiors(Node))\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nclass Leaf < Node\nmap(size,map(classes,(Object,Node,Leaf)))\n", "<class Node>\n<class Leaf>\n1:2:3:nil\n"),
        (
            "class A < Object\nclass B < A\nclass C < B\nfilter(x::member(A,classes(x)),(Object,A,B,C))\n",
            "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class C>:nil\n",
        ),
        ("class Node < Object\nclass Leaf < Node\nclasses(classof(new Leaf))\n", "<class Node>\n<class Leaf>\n<class Leaf>:<class Node>:<class Object>:nil\n"),
        ("f:=classes\nclass Node < Object\nf(Node)\n", "<function>\n<class Node>\n<class Node>:<class Object>:nil\n"),
        ("classes:=x::nil\nclass Node < Object\nclasses(Node)\n", "<function>\n<class Node>\nnil\n"),
    ]

    slice_048_robustness_failure_cases = [
        ("classes()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('classes("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(hd)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not classes(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("classes:=1\nclasses(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_049_boundary_success_cases = [
        ("supers(Object)\n", "nil\n"),
        ("class Node < Object\nsupers(Node)\n", "<class Node>\n<class Object>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nsupers(C)\n", "<class A>\n<class B>\n<class C>\n<class B>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nsuperiors(C)\n", "<class A>\n<class B>\n<class C>\n<class B>:<class A>:<class Object>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nclasses(C)\n", "<class A>\n<class B>\n<class C>\n<class C>:<class B>:<class A>:<class Object>:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nhd(superiors(C))==B\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nclasses(C)==append(list(C),superiors(C))\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < A\nclass C < B\nmap(size,map(supers,(Object,A,B,C)))\n", "<class A>\n<class B>\n<class C>\n0:1:1:1:nil\n"),
        ("class A < Object\nclass B < A\nclass C < B\nmap(size,map(classes,(Object,A,B,C)))\n", "<class A>\n<class B>\n<class C>\n1:2:3:4:nil\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\n(new Leaf).value()\n", "<class Node>\n<function>\n<class Leaf>\n1\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nLeaf.value():=2\n(new Leaf).value()\n", "<class Node>\n<function>\n<class Leaf>\n<function>\n2\n"),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nmethods(Leaf)\n", "<class Node>\n<function>\n<class Leaf>\nnil\n"),
        ("class Node < Object\nattrs(new Node with x:=1)\n", "<class Node>\n'x:nil\n"),
        ("f:=supers\nclass Node < Object\nf(Node)\n", "<function>\n<class Node>\n<class Object>:nil\n"),
        ("class Node < Object\nclass Leaf < Node\nclassof(new Leaf)==Leaf\n", "<class Node>\n<class Leaf>\ntrue\n"),
    ]

    slice_049_robustness_failure_cases = [
        ("supers()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("supers(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("superiors(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("classes(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not classes(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("supers:=1\nsupers(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("classes:=1\nclasses(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_050_token_cases = [
        ("class C < (A,B).", "TOK_CLASS TOK_IDENTIFIER TOK_LT TOK_LPAREN TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER TOK_RPAREN TOK_DOT TOK_EOF\n"),
        (
            "class C < (A,B,D).",
            "TOK_CLASS TOK_IDENTIFIER TOK_LT TOK_LPAREN TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER TOK_RPAREN TOK_DOT TOK_EOF\n",
        ),
    ]

    slice_050_boundary_success_cases = [
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsupers(C)\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nhd(supers(C))==A\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nhd(tl(supers(C)))==B\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsize(supers(C))\n", "<class A>\n<class B>\n<class C>\n2\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nclassof(new C)==C\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class A < Object\nclass B < Object\nB.b():=2\nclass C < (A,B)\n(new C).b()\n",
            "<class A>\n<class B>\n<function>\n<class C>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\nC.v():=3\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n3\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.w():=2\nclass C < (A,B)\nmethods(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\nnil\n",
        ),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsuperiors(C)\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(C)\n", "<class A>\n<class B>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nmap(size,map(supers,(Object,A,B,C)))\n", "<class A>\n<class B>\n<class C>\n0:1:1:2:nil\n"),
        (
            "class A < Object\nclass B < Object\nclass C < Object\nclass D < (A,B,C)\nsupers(D)\n",
            "<class A>\n<class B>\n<class C>\n<class D>\n<class A>:<class B>:<class C>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nX:=A\nclass C < (X,B)\nsupers(C)\n",
            "<class A>\n<class B>\n<class A>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        ("class A < Object\nclass C < (A,A)\nsupers(C)==(A,A)\n", "<class A>\n<class C>\ntrue\n"),
    ]

    slice_050_robustness_failure_cases = [
        ("class C < ()\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class C < (Object)\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class C < (Object,)\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class C < (,Object)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("class C < Object,Object\n", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("class C < (Object,Object\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("class C < (Object,true)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("class C < (Object,1)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("class C < (Object,'x)\n", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("class C < (Object,Missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("x:=1\nclass C < (Object,x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
    ]

    slice_051_boundary_success_cases = [
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsuperiors(C)\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(C)\n", "<class A>\n<class B>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsize(superiors(C))\n", "<class A>\n<class B>\n<class C>\n3\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nhd(tl(superiors(C)))==B\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(C)==append(list(C),superiors(C))\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nmember(C,superiors(C))\n", "<class A>\n<class B>\n<class C>\nfalse\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nmap(size,map(superiors,(Object,A,B,C)))\n", "<class A>\n<class B>\n<class C>\n0:1:1:3:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nmap(size,map(classes,(Object,A,B,C)))\n", "<class A>\n<class B>\n<class C>\n1:2:2:4:nil\n"),
        (
            "class Top < Object\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nsuperiors(Leaf)\n",
            "<class Top>\n<class Left>\n<class Right>\n<class Leaf>\n<class Left>:<class Right>:<class Top>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < Object\nclass D < (B,C)\nclasses(D)\n",
            "<class A>\n<class B>\n<class C>\n<class D>\n<class D>:<class B>:<class A>:<class C>:<class Object>:nil\n",
        ),
        ("class A < Object\nclass C < (A,A)\nsuperiors(C)\n", "<class A>\n<class C>\n<class A>:<class Object>:nil\n"),
        ("class A < Object\nclass C < (A,A)\nclasses(C)\n", "<class A>\n<class C>\n<class C>:<class A>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsupers(C)\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nsuperiors(classof(new C))\n", "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nX:=A\nclass C < (X,B)\nclasses(C)\n", "<class A>\n<class B>\n<class A>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nfilter(x::member(B,superiors(x)),(Object,A,B,C))\n", "<class A>\n<class B>\n<class C>\n<class C>:nil\n"),
        ("f:=classes\nclass A < Object\nclass B < Object\nclass C < (A,B)\nf(C)\n", "<function>\n<class A>\n<class B>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n"),
    ]

    slice_051_robustness_failure_cases = [
        ("superiors()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not classes(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("superiors:=1\nsuperiors(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("classes:=1\nclasses(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_052_boundary_success_cases = [
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class A < Object\nclass B < Object\nB.v():=2\nclass C < (A,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<class C>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\nC.v():=3\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n3\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nclass C < (A,B)\nn:=new C\nn.v:=x::x+10\nn.v(5)\n",
            "<class A>\n<class B>\n<function>\n<class C>\n<object C>\n<function>\n15\n",
        ),
        (
            "Object.v():=0\nclass A < Object\nclass B < A\nclass C < Object\nC.v():=3\nclass D < (B,C)\n(new D).v()\n",
            "<function>\n<class A>\n<class B>\n<class C>\n<function>\n<class D>\n3\n",
        ),
        (
            "class A < Object\nA.v():=1\nclass B < A\nclass C < Object\nC.v():=3\nclass D < (B,C)\n(new D).v()\n",
            "<class A>\n<function>\n<class B>\n<class C>\n<function>\n<class D>\n1\n",
        ),
        (
            "class Top < Object\nTop.v():=10\nclass Left < Top\nclass Right < Top\nRight.v():=20\nclass Leaf < (Left,Right)\n(new Leaf).v()\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<function>\n<class Leaf>\n20\n",
        ),
        (
            "class Top < Object\nTop.v():=10\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\n(new Leaf).v()\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<class Leaf>\n10\n",
        ),
        (
            "class Top < Object\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nclasses(classof(new Leaf))\n",
            "<class Top>\n<class Left>\n<class Right>\n<class Leaf>\n<class Leaf>:<class Left>:<class Right>:<class Top>:<class Object>:nil\n",
        ),
        (
            "class Top < Object\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nTop.v():=classof(self)==Leaf\n(new Leaf).v()\n",
            "<class Top>\n<class Left>\n<class Right>\n<class Leaf>\n<function>\ntrue\n",
        ),
        (
            "class A < Object\nA.v():=1\nclass C < (A,A)\n(new C).v()\n",
            "<class A>\n<function>\n<class C>\n1\n",
        ),
        (
            "class A < Object\nclass B < Object\nX:=A\nX.v():=1\nB.v():=2\nclass C < (X,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<class A>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "Object.root():=0\nclass A < Object\nclass B < Object\nclass C < (A,B)\n(new C).root()\n",
            "<function>\n<class A>\n<class B>\n<class C>\n0\n",
        ),
        (
            "Object.v():=0\nclass A < Object\nclass B < A\nclass C < Object\nC.v():=3\nclass D < (B,C)\nmap(x::x.v(),(new D,new C))\n",
            "<function>\n<class A>\n<class B>\n<class C>\n<function>\n<class D>\n3:3:nil\n",
        ),
        (
            "Object.v():=0\nclass A < Object\nclass B < A\nclass C < Object\nC.v():=3\nclass D < (B,C)\nD.v():=4\n(new D).v()\n",
            "<function>\n<class A>\n<class B>\n<class C>\n<function>\n<class D>\n<function>\n4\n",
        ),
        (
            "class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\nmethods(C)\n",
            "<class A>\n<function>\n<class B>\n<class C>\nnil\n",
        ),
        (
            "class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\nclasses(classof(new C))==classes(C)\n",
            "<class A>\n<function>\n<class B>\n<class C>\ntrue\n",
        ),
    ]

    slice_052_robustness_failure_cases = [
        ("class A < Object\nclass B < Object\nclass C < (A,B)\n(new C).missing()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nclass B < Object\nA.v(x):=x\nB.v():=2\nclass C < (A,B)\n(new C).v()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("Object.v():=0\nclass A < Object\nclass B < A\nclass C < Object\nC.v():=1+true\nclass D < (B,C)\n(new D).v()\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\nn:=new C\nn.v:=1\nn.v()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\nC.v()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("1.v()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class A < Object\nclass B < Object\nA.v():=1\nclass C < (A,B)\n(new C).v(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nclass B < Object\nA.v(x):=x\nclass C < (A,B)\n(new C).v(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("Object.v(x):=x\nclass A < Object\nclass B < Object\nclass C < (A,B)\n(new C).v()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nA.v():=self.missing\nclass B < Object\nclass C < (A,B)\n(new C).v()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\nnot (new C).v()\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class A < Object\nA.v():=1\nclass B < Object\nclass C < (A,B)\n(new C).v()+true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_053_boundary_success_cases = [
        ("OK(Object)\n", "true\n"),
        ("class A < Object\nOK(A)\n", "<class A>\ntrue\n"),
        ("class A < Object\nclass B < Object\nclass C < (A,B)\nOK(C)\n", "<class A>\n<class B>\n<class C>\ntrue\n"),
        (
            "class Top < Object\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nOK(Leaf)\n",
            "<class Top>\n<class Left>\n<class Right>\n<class Leaf>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < Object\nclass D < (B,C)\nOK(D)\n",
            "<class A>\n<class B>\n<class C>\n<class D>\ntrue\n",
        ),
        ("class A < Object\nclass C < (A,A)\nOK(C)\n", "<class A>\n<class C>\ntrue\n"),
        ("class A < Object\nX:=A\nclass C < (A,X)\nOK(C)\n", "<class A>\n<class A>\n<class C>\ntrue\n"),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nOK(C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nOK(classof(new C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nmap(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\ntrue:true:false:nil\n",
        ),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nfilter(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nall(OK,(Object,A,B,C))\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nall(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            "class X < Object\nclass Y < Object\nclass A < (X,Y)\nclass B < (Y,X)\nclass C < (A,B)\nOK(C) then 1 else 2\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n2\n",
        ),
        ("f:=OK\nclass A < Object\nf(A)\n", "<function>\n<class A>\ntrue\n"),
        ("OK\n", "<function>\n"),
        ("OK:=x::not x\nOK(false)\n", "<function>\ntrue\n"),
    ]

    slice_053_robustness_failure_cases = [
        ("OK()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("OK(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("OK(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK(OK)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("OK(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(OK(Object))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("OK(Object)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("OK:=1\nOK(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    inconsistent_mro_prefix = (
        "class X < Object\n"
        "class Y < Object\n"
        "class A < (X,Y)\n"
        "class B < (Y,X)\n"
        "class C < (A,B)\n"
    )

    slice_054_boundary_success_cases = [
        (inconsistent_mro_prefix + "OK(C)\n", "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n"),
        (
            inconsistent_mro_prefix + "OK(classof(new C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            inconsistent_mro_prefix + "supers(C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            inconsistent_mro_prefix + "methods(C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nnil\n",
        ),
        (
            inconsistent_mro_prefix + "classof(new C)==C\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            inconsistent_mro_prefix + "attrs(new C with x:=1)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n'x:nil\n",
        ),
        (
            inconsistent_mro_prefix + "n:=new C\nn.v:=x::x+1\nn.v(2)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<object C>\n<function>\n3\n",
        ),
        (
            inconsistent_mro_prefix + "map(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\ntrue:true:false:nil\n",
        ),
        (
            inconsistent_mro_prefix + "filter(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            inconsistent_mro_prefix + "all(OK,(A,B,C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            inconsistent_mro_prefix + "OK(C) then 1 else 2\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(C)\n",
            "<class A>\n<class B>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
    ]

    slice_054_robustness_failure_cases = [
        (inconsistent_mro_prefix + "classes(C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "superiors(C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "classes(classof(new C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "superiors(classof(new C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "OK(C)\nsize(classes(C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "hd(superiors(C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "map(classes,(A,B,C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "filter(x::size(classes(x))>0,(A,C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "Object.v():=0\n(new C).v()\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.v():=1\nB.v():=2\n(new C).v()\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "class D < C\nclasses(D)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "class D < C\nObject.v():=0\n(new D).v()\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_055_boundary_success_cases = [
        ("Set\n", "<class Set>\n"),
        ("Bag\n", "<class Bag>\n"),
        ("supers(Set)\n", "<class Object>:nil\n"),
        ("supers(Bag)\n", "<class Object>:nil\n"),
        ("classes(Set)\n", "<class Set>:<class Object>:nil\n"),
        ("classes(Bag)\n", "<class Bag>:<class Object>:nil\n"),
        ("set()\n", "set()\n"),
        ("bag()\n", "bag()\n"),
        ("classof(set())==Set\n", "true\n"),
        ("classof(bag())==Bag\n", "true\n"),
        ("isObject(set()) and isObject(bag())\n", "true\n"),
        ("attrs(set())\n", "nil\n"),
        ("attrs(bag())\n", "nil\n"),
        ("f:=set\nf()\n", "<function>\nset()\n"),
        ("map(classof,(set(),bag()))\n", "<class Set>:<class Bag>:nil\n"),
        ("class EmptySet < Set\nsupers(EmptySet)\n", "<class EmptySet>\n<class Set>:nil\n"),
    ]

    slice_055_robustness_failure_cases = [
        ("set(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("bag(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("bag(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("Set:=1\nset()\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("Bag:=true\nbag()\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("new set\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("classof(Set)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("attrs(Bag)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("set()+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not bag()\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set:=1\nset()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_056_boundary_success_cases = [
        ("size(set())\n", "0\n"),
        ("size(bag())\n", "0\n"),
        ("member(1,set())\n", "false\n"),
        ("member(1,bag())\n", "false\n"),
        ("size(new Set)\n", "0\n"),
        ("size(new Bag)\n", "0\n"),
        ("member('x,new Set)\n", "false\n"),
        ("member(\"x\",new Bag)\n", "false\n"),
        ("s:=set()\nattrs(s)==nil\n", "set()\ntrue\n"),
        ("b:=bag()\nattrs(b)==nil\n", "bag()\ntrue\n"),
        ("map(size,(set(),bag(),nil))\n", "0:0:0:nil\n"),
        ("map(member(1),(set(),bag(),nil))\n", "false:false:false:nil\n"),
        ("all(x::size(x)==0,(set(),bag(),nil))\n", "true\n"),
        ("m:=member(1)\nm(set())\n", "<function>\nfalse\n"),
        ("class EmptySet < Set\nsize(new EmptySet)\n", "<class EmptySet>\n0\n"),
        ("class EmptyBag < Bag\nmember(1,new EmptyBag)\n", "<class EmptyBag>\nfalse\n"),
        ("size(set())==size(bag())\n", "true\n"),
        ("s:=set()\nmember(s,list(s))\n", "set()\ntrue\n"),
    ]

    slice_056_robustness_failure_cases = [
        ("size(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("member(1,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("size(Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("member(1,Bag)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("size(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("member(1,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("member(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("1:set()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(set(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(set(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(size,set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("size:=1\nsize(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_057_boundary_success_cases = [
        ("size(insert(1,set()))\n", "1\n"),
        ("member(1,insert(1,set()))\n", "true\n"),
        ("member(2,insert(1,set()))\n", "false\n"),
        ("size(insert(1,insert(1,set())))\n", "1\n"),
        ("size(insert(1,insert(1,bag())))\n", "2\n"),
        ("member(1,insert(1,bag()))\n", "true\n"),
        ("s:=set()\nt:=insert(1,s)\nsize(s)\nsize(t)\n", "set()\nset(1:nil)\n0\n1\n"),
        ("classof(insert(1,set()))==Set\n", "true\n"),
        ("class EmptySet < Set\nclassof(insert(1,new EmptySet))==EmptySet\n", "<class EmptySet>\ntrue\n"),
        ("class EmptySet < Set\nsize(insert(1,new EmptySet))\n", "<class EmptySet>\n1\n"),
        ("class EmptyBag < Bag\nsize(insert(1,insert(1,new EmptyBag)))\n", "<class EmptyBag>\n2\n"),
        ("attrs(insert(1,set() with tag:=true))\n", "'tag:nil\n"),
        ("map(size,(insert(1,set()),insert(1,insert(1,bag()))))\n", "1:2:nil\n"),
        ("f:=insert(1)\nsize(f(set()))\n", "<function>\n1\n"),
        ("map(insert(1),(set(),bag()))\n", "set(1:nil):bag(1:nil):nil\n"),
        ("all(member(1),map(insert(1),(set(),bag())))\n", "true\n"),
        ("x:=insert(\"a\",set())\nmember(\"a\",x)\n", "set(\"a\":nil)\ntrue\n"),
        ("size(insert(set(),set()))\n", "1\n"),
    ]

    slice_057_robustness_failure_cases = [
        ("insert()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("insert(1,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("insert(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("insert(1,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("insert(1,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("insert(1,nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("insert(1,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("insert(1,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("insert(1,insert(2,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not insert(1,bag())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(insert(1,set()),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(insert(1,set()),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("insert:=1\ninsert(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(insert(1),(1,nil))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_058_boundary_success_cases = [
        ("size(remove(1,set()))\n", "0\n"),
        ("size(remove(1,insert(1,set())))\n", "0\n"),
        ("member(1,remove(1,insert(1,set())))\n", "false\n"),
        ("size(remove(2,insert(1,set())))\n", "1\n"),
        ("member(1,remove(1,insert(1,bag())))\n", "false\n"),
        ("size(remove(1,insert(1,insert(1,bag()))))\n", "1\n"),
        ("member(1,remove(1,insert(1,insert(1,bag()))))\n", "true\n"),
        ("s:=insert(1,set())\nt:=remove(1,s)\nsize(s)\nsize(t)\n", "set(1:nil)\nset()\n1\n0\n"),
        ("classof(remove(1,insert(1,set())))==Set\n", "true\n"),
        ("class EmptySet < Set\nclassof(remove(1,insert(1,new EmptySet)))==EmptySet\n", "<class EmptySet>\ntrue\n"),
        ("class EmptySet < Set\nsize(remove(1,insert(1,new EmptySet)))\n", "<class EmptySet>\n0\n"),
        ("class EmptyBag < Bag\nsize(remove(1,insert(1,insert(1,new EmptyBag))))\n", "<class EmptyBag>\n1\n"),
        ("attrs(remove(1,insert(1,set() with tag:=true)))\n", "'tag:nil\n"),
        ("map(size,(remove(1,insert(1,set())),remove(1,insert(1,insert(1,bag())))))\n", "0:1:nil\n"),
        ("f:=remove(1)\nsize(f(insert(1,set())))\n", "<function>\n0\n"),
        ("map(remove(1),(insert(1,set()),insert(1,insert(1,bag()))))\n", "set():bag(1:nil):nil\n"),
        ("x:=remove(\"a\",insert(\"a\",set()))\nmember(\"a\",x)\n", "set()\nfalse\n"),
        ("s:=set()\nt:=insert(s,set())\nsize(remove(s,t))\n", "set()\nset(set():nil)\n0\n"),
    ]

    slice_058_robustness_failure_cases = [
        ("remove()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("remove(1,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("remove(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("remove(1,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("remove(1,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove(1,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove(1,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove(1,remove(1,insert(1,set())))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not remove(1,bag())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(remove(1,insert(1,set())))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(remove(1,insert(1,set())),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(remove(1,insert(1,set())),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(remove(1,insert(1,set())),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(remove(1,insert(1,set())),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("remove:=1\nremove(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(remove(1),(1,nil))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_059_boundary_success_cases = [
        ("all(x::true,set())\n", "true\n"),
        ("exists(x::true,set())\n", "false\n"),
        ("all(x::true,bag())\n", "true\n"),
        ("exists(x::true,bag())\n", "false\n"),
        ("all(x::x>0,insert(1,insert(2,set())))\n", "true\n"),
        ("exists(x::x==2,insert(1,insert(2,set())))\n", "true\n"),
        ("all(x::x==1,insert(2,insert(1,set())))\n", "false\n"),
        ("exists(x::x==3,insert(2,insert(1,set())))\n", "false\n"),
        ("all(x::x==1,insert(1,insert(1,bag())))\n", "true\n"),
        ("exists(x::x==1,remove(1,insert(1,insert(1,bag()))))\n", "true\n"),
        ("p:=all(x::x>0)\np(insert(1,set()))\n", "<function>\ntrue\n"),
        ("p:=exists(x::x==1)\np(insert(1,bag()))\n", "<function>\ntrue\n"),
        ("map(all(x::x>0),(insert(1,set()),insert(1,bag()),set()))\n", "true:true:true:nil\n"),
        ("map(exists(x::x==1),(insert(1,set()),insert(2,set()),bag()))\n", "true:false:false:nil\n"),
        ("class PositiveSet < Set\nall(x::x>0,insert(1,new PositiveSet))\n", "<class PositiveSet>\ntrue\n"),
        ("class HitBag < Bag\nexists(x::x==1,insert(1,new HitBag))\n", "<class HitBag>\ntrue\n"),
        ("o:=new Object\nexists(x::x==o,insert(o,set()))\n", "<object Object>\ntrue\n"),
        ("all(x::x>0,remove(1,insert(1,set())))\n", "true\n"),
    ]

    slice_059_robustness_failure_cases = [
        ("all()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("exists()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("all(x::true,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("exists(x::true,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("all(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("exists(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("all(x::true,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("exists(x::true,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("all(x::1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("exists(x::1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("all(x::x+1,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("exists(x::x+1,insert(true,bag()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("all(x::missing,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("exists(x::missing,insert(1,bag()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("all(x::true,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("exists(x::true,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
    ]

    slice_060_boundary_success_cases = [
        ("select(x::x>1,(1,2,3))\n", "2:3:nil\n"),
        ("size(filter(x::true,set()))\n", "0\n"),
        ("size(filter(x::true,bag()))\n", "0\n"),
        ("size(filter(x::x>1,insert(1,insert(2,set()))))\n", "1\n"),
        ("member(2,filter(x::x>1,insert(1,insert(2,set()))))\n", "true\n"),
        ("member(1,filter(x::x>1,insert(1,insert(2,set()))))\n", "false\n"),
        ("size(filter(x::x==1,insert(1,insert(1,bag()))))\n", "2\n"),
        ("size(filter(x::false,insert(1,bag())))\n", "0\n"),
        ("size(select(x::true,set()))\n", "0\n"),
        ("size(select(x::x==2,insert(1,insert(2,set()))))\n", "1\n"),
        ("member(2,select(x::x==2,insert(1,insert(2,set()))))\n", "true\n"),
        ("size(select(x::x==1,insert(1,insert(1,bag()))))\n", "2\n"),
        ("p:=filter(x::x>0)\nsize(p(insert(1,set())))\n", "<function>\n1\n"),
        ("p:=select(x::x==1)\nmember(1,p(insert(1,bag())))\n", "<function>\ntrue\n"),
        ("map(size,(filter(x::true,insert(1,set())),select(x::true,insert(1,bag()))))\n", "1:1:nil\n"),
        ("class KeepSet < Set\nclassof(filter(x::true,insert(1,new KeepSet)))==KeepSet\n", "<class KeepSet>\ntrue\n"),
        ("class KeepBag < Bag\nsize(select(x::true,insert(1,insert(1,new KeepBag))))\n", "<class KeepBag>\n2\n"),
        ("attrs(filter(x::true,insert(1,set() with tag:=true)))\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,filter(x::x==o,insert(o,set())))\n", "<object Object>\ntrue\n"),
    ]

    slice_060_robustness_failure_cases = [
        ("filter()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("select()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("filter(x::true,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("select(x::true,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("filter(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("select(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("filter(x::true,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("select(x::true,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("filter(x::1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("select(x::1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("filter(x::x+1,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("select(x::x+1,insert(true,bag()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("filter(x::missing,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("select(x::missing,insert(1,bag()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("filter(x::true,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("select(x::true,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
    ]

    slice_061_boundary_success_cases = [
        ("reduce((acc,x)::acc+1,0,set())\n", "0\n"),
        ("reduce((acc,x)::acc+1,0,bag())\n", "0\n"),
        ("reduce((acc,x)::acc+x,0,insert(1,insert(2,set())))\n", "3\n"),
        ("reduce((acc,x)::acc+1,0,insert(1,insert(2,set())))\n", "2\n"),
        ("reduce((acc,x)::acc+x,0,insert(1,insert(1,bag())))\n", "2\n"),
        ("reduce((acc,x)::acc+1,0,insert(1,insert(1,bag())))\n", "2\n"),
        ("reduce((acc,x)::acc and x>0,true,insert(1,insert(2,set())))\n", "true\n"),
        ("reduce((acc,x)::acc or x==2,false,insert(1,insert(2,set())))\n", "true\n"),
        ("p:=reduce((acc,x)::acc+x,0)\np(insert(1,set()))\n", "<function>\n1\n"),
        ("map(reduce((acc,x)::acc+1,0),(insert(1,set()),insert(1,insert(1,bag())),set()))\n", "1:2:0:nil\n"),
        ("class CountSet < Set\nreduce((acc,x)::acc+1,0,insert(1,new CountSet))\n", "<class CountSet>\n1\n"),
        ("class CountBag < Bag\nreduce((acc,x)::acc+1,0,insert(1,insert(1,new CountBag)))\n", "<class CountBag>\n2\n"),
        ("o:=new Object\nreduce((acc,x)::acc+1,0,insert(o,set()))\n", "<object Object>\n1\n"),
        ("reduce((acc,x)::acc+1,0,filter(x::x>1,insert(1,insert(2,set()))))\n", "1\n"),
        ("size(reduce((acc,x)::insert(x,acc),set(),insert(1,insert(1,bag()))))\n", "1\n"),
        ("size(reduce((acc,x)::insert(x,acc),bag(),insert(1,insert(1,bag()))))\n", "2\n"),
        ("reduce((acc,x)::acc+x,10,remove(1,insert(1,set())))\n", "10\n"),
        ("reduce((acc,x)::acc+1,0,select(x::x==1,insert(1,insert(2,set()))))\n", "1\n"),
    ]

    slice_061_robustness_failure_cases = [
        ("reduce()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce((acc,x)::acc+x,0,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(1,0,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("reduce((acc,x)::acc+x,0,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("reduce((acc,x)::acc+x,0,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("reduce((acc,x)::acc+x,0,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("reduce((acc,x)::missing,0,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("reduce(x::x,0,insert(1,set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(hd,nil,insert((1),set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce((acc,x)::acc+x,0,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("reduce((acc,x)::1/0,0,insert(1,set()))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("reduce((acc,x)::acc+x,true,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("reduce((acc,x)::x:acc,nil,insert(1,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not reduce((acc,x)::acc+x,0,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("reduce((acc,x)::acc+x,0,insert(1,set()))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("reduce(append,nil,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_062_boundary_success_cases = [
        ("size(collect(x::x+1,set()))\n", "0\n"),
        ("size(collect(x::x+1,bag()))\n", "0\n"),
        ("member(2,collect(x::x+1,insert(1,set())))\n", "true\n"),
        ("member(3,collect(x::x+1,insert(1,insert(2,set()))))\n", "true\n"),
        ("size(collect(x::1,insert(1,insert(2,set()))))\n", "1\n"),
        ("size(collect(x::1,insert(1,insert(2,bag()))))\n", "2\n"),
        ("size(collect(x::x,insert(1,insert(1,bag()))))\n", "2\n"),
        ("p:=collect(x::x+1)\nmember(2,p(insert(1,set())))\n", "<function>\ntrue\n"),
        ("map(size,(collect(x::x+1,insert(1,set())),collect(x::x+1,insert(1,insert(1,bag()))),collect(x::x+1,set())))\n", "1:2:0:nil\n"),
        ("class ShiftSet < Set\nclassof(collect(x::x+1,insert(1,new ShiftSet)))==ShiftSet\n", "<class ShiftSet>\ntrue\n"),
        ("class ShiftBag < Bag\nsize(collect(x::x+1,insert(1,insert(1,new ShiftBag))))\n", "<class ShiftBag>\n2\n"),
        ("attrs(collect(x::x+1,insert(1,set() with tag:=true)))\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,collect(x::x,insert(o,set())))\n", "<object Object>\ntrue\n"),
        ("size(collect(x::x+1,filter(x::x>1,insert(1,insert(2,set())))))\n", "1\n"),
        ("member(2,collect(x::x+1,select(x::x==1,insert(1,insert(2,set())))))\n", "true\n"),
        ("size(collect(x::x+1,remove(1,insert(1,set()))))\n", "0\n"),
        ("reduce((acc,x)::acc+x,0,collect(x::x+1,insert(1,insert(2,set()))))\n", "5\n"),
        ("all(atom,collect(x::(y::y+x),insert(1,set())))\n", "true\n"),
    ]

    slice_062_robustness_failure_cases = [
        ("collect()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("collect(x::x,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("collect(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("collect(x::x,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("collect(x::x,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("collect(x::x,(1,2))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("collect(x::x+1,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("collect(x::missing,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("collect(x::1/0,insert(1,set()))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("collect(x::x+1,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("collect(version,insert(1,set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("collect(x::x+1,insert(\"a\",set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("collect(x::x+1,insert(1,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not collect(x::x,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("collect(x::x,insert(1,set()))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("map(size,collect(x::x,insert(1,set())))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_063_boundary_success_cases = [
        ("size(union(set(),set()))\n", "0\n"),
        ("size(difference(set(),set()))\n", "0\n"),
        ("size(intersection(set(),set()))\n", "0\n"),
        ("member(1,union(insert(1,set()),set()))\n", "true\n"),
        ("member(2,union(insert(1,set()),insert(2,set())))\n", "true\n"),
        ("size(union(insert(1,set()),insert(1,set())))\n", "1\n"),
        ("size(difference(insert(1,insert(2,set())),insert(2,set())))\n", "1\n"),
        ("member(1,difference(insert(1,insert(2,set())),insert(2,set())))\n", "true\n"),
        ("size(difference(insert(1,set()),insert(1,set())))\n", "0\n"),
        ("size(intersection(insert(1,set()),insert(2,set())))\n", "0\n"),
        ("member(2,intersection(insert(1,insert(2,set())),insert(2,set())))\n", "true\n"),
        ("u:=union(insert(1,set()))\nmember(2,u(insert(2,set())))\n", "<function>\ntrue\n"),
        ("map(size,(union(insert(1,set()),insert(2,set())),difference(insert(1,insert(2,set())),insert(2,set())),intersection(insert(1,insert(2,set())),insert(2,set()))))\n", "2:1:1:nil\n"),
        ("class LeftSet < Set\nclass RightSet < Set\nclassof(union(insert(1,new LeftSet),insert(2,new RightSet)))==LeftSet\n", "<class LeftSet>\n<class RightSet>\ntrue\n"),
        ("attrs(difference(insert(2,insert(1,set() with tag:=true)),insert(2,set())))\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,union(insert(o,set()),set()))\n", "<object Object>\ntrue\n"),
        ("reduce((acc,x)::acc+1,0,union(insert(1,set()),insert(2,set())))\n", "2\n"),
        ("member(3,union(collect(x::x+1,insert(1,set())),collect(x::x+1,insert(2,set()))))\n", "true\n"),
    ]

    slice_063_robustness_failure_cases = [
        ("union()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("difference()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("intersection()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("union(set(),set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("difference(set(),set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("intersection(set(),set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("union(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(set(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(nil,set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(set(),new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(Set,set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("union(set(),set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_064_boundary_success_cases = [
        ("subset(set(),set())\n", "true\n"),
        ("equal(set(),set())\n", "true\n"),
        ("subset(set(),insert(1,set()))\n", "true\n"),
        ("subset(insert(1,set()),set())\n", "false\n"),
        ("subset(insert(1,set()),insert(1,insert(2,set())))\n", "true\n"),
        ("subset(insert(1,insert(2,set())),insert(1,set()))\n", "false\n"),
        ("equal(insert(1,set()),insert(1,set()))\n", "true\n"),
        ("equal(insert(1,set()),insert(2,set()))\n", "false\n"),
        ("equal(insert(1,insert(2,set())),union(insert(1,set()),insert(2,set())))\n", "true\n"),
        ("subset(intersection(insert(1,set()),insert(1,insert(2,set()))),insert(1,set()))\n", "true\n"),
        ("subset(difference(insert(1,insert(2,set())),insert(2,set())),insert(1,set()))\n", "true\n"),
        ("all(x::subset(x,insert(1,insert(2,set()))),(set(),insert(1,set()),insert(2,set())))\n", "true\n"),
        ("map(x::equal(x,set()),(set(),insert(1,set())))\n", "true:false:nil\n"),
        ("s:=subset(insert(1,set()))\ns(insert(1,insert(2,set())))\n", "<function>\ntrue\n"),
        ("class SmallSet < Set\nsubset(insert(1,new SmallSet),insert(1,set()))\n", "<class SmallSet>\ntrue\n"),
        ("equal(insert(1,set() with tag:=true),insert(1,set() with other:=true))\n", "true\n"),
        ("o:=new Object\nsubset(insert(o,set()),insert(o,set()))\n", "<object Object>\ntrue\n"),
        ("equal(collect(x::x+1,insert(1,set())),insert(2,set()))\n", "true\n"),
    ]

    slice_064_robustness_failure_cases = [
        ("subset()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("equal()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("subset(set(),set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("equal(set(),set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("subset(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(set(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(nil,set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(set(),new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(Set,set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("equal(set(),1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("subset(set(),set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("equal(set(),set())==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("map(size,subset(set(),set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_065_boundary_success_cases = [
        ("size(add(1,set()))\n", "1\n"),
        ("member(1,add(1,set()))\n", "true\n"),
        ("size(add(1,add(1,set())))\n", "1\n"),
        ("equal(add(1,set()),insert(1,set()))\n", "true\n"),
        ("subset(insert(1,set()),add(2,insert(1,set())))\n", "true\n"),
        ("equal(add(2,add(1,set())),union(insert(1,set()),insert(2,set())))\n", "true\n"),
        ("member(\"x\",add(\"x\",set()))\n", "true\n"),
        ("member('x,add('x,set()))\n", "true\n"),
        ("a:=add(1)\nmember(1,a(set()))\n", "<function>\ntrue\n"),
        ("class SmallSet < Set\nclassof(add(1,new SmallSet))==SmallSet\n", "<class SmallSet>\ntrue\n"),
        ("attrs(add(1,set() with tag:=true))\n", "'tag:nil\n"),
        ("s:=set(); t:=add(1,s); equal(s,set()) and member(1,t)\n", "true\n"),
        ("o:=new Object\nmember(o,add(o,set()))\n", "<object Object>\ntrue\n"),
        ("o:=new Object\nsize(add(o,add(o,set())))\n", "<object Object>\n1\n"),
        ("size(add(new Object,add(new Object,set())))\n", "2\n"),
        ("all(x::member(x,add(2,add(1,set()))),(1,2))\n", "true\n"),
        ("equal(add(2,collect(x::x+1,insert(0,set()))),insert(1,insert(2,set())))\n", "true\n"),
        ("reduce((acc,x)::acc+1,0,add(2,add(1,set())))\n", "2\n"),
    ]

    slice_065_robustness_failure_cases = [
        ("add()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("add(1,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("add(1,bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1,nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1,(1,2))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1/0,set())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("add(1,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("add(1,set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not add(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(size,add(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd(add(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1,set())==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("add(1)(bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("add(1)(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_066_boundary_success_cases = [
        ("size(UNION(()))\n", "0\n"),
        ("equal(UNION(()),set())\n", "true\n"),
        ("size(UNION(list(set())))\n", "0\n"),
        ("member(1,UNION(list(insert(1,set()))))\n", "true\n"),
        ("all(x::member(x,UNION((insert(1,set()),insert(2,set())))),(1,2))\n", "true\n"),
        ("size(UNION((insert(1,set()),insert(1,set()))))\n", "1\n"),
        ("equal(UNION((insert(1,set()),insert(2,set()))),union(insert(1,set()),insert(2,set())))\n", "true\n"),
        ("subset(insert(1,set()),UNION((insert(1,set()),insert(2,set()))))\n", "true\n"),
        ("member(2,UNION((set(),insert(2,set()))))\n", "true\n"),
        ("u:=UNION\nmember(1,u((insert(1,set()),set())))\n", "<function>\ntrue\n"),
        ("class SmallSet < Set\nclassof(UNION((insert(1,new SmallSet),insert(2,set()))))==SmallSet\n", "<class SmallSet>\ntrue\n"),
        ("attrs(UNION((insert(1,set() with tag:=true),insert(2,set()))))\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,UNION((insert(o,set()),set())))\n", "<object Object>\ntrue\n"),
        ("size(UNION((add(new Object,set()),add(new Object,set()))))\n", "2\n"),
        ("equal(UNION((collect(x::x+1,insert(0,set())),add(2,set()))),insert(1,insert(2,set())))\n", "true\n"),
        ("reduce((acc,x)::acc+1,0,UNION((insert(1,set()),insert(2,set()))))\n", "2\n"),
        ("equal(UNION((UNION((insert(1,set()),insert(2,set()))),insert(3,set()))),insert(1,insert(2,insert(3,set()))))\n", "true\n"),
        ("size(UNION((add(\"x\",set()),add(\"x\",set()))))\n", "1\n"),
    ]

    slice_066_robustness_failure_cases = [
        ("UNION()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("UNION((),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("UNION(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((set(),bag()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((set(),nil))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(list(new Object))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(list(Set))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((1/0,set()))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("UNION(list(1/0))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("UNION(())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not UNION(())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(size,UNION(()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd(UNION(()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((set(),set()))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
    ]

    slice_067_boundary_success_cases = [
        ("locate(x::x==2,(1,2,3))\n", "2\n"),
        ("locate(x::x==9,(1,2,3))\n", "nil\n"),
        ("locate(x::true,())\n", "nil\n"),
        ("locate(x::x==1,set())\n", "nil\n"),
        ("locate(x::x==1,bag())\n", "nil\n"),
        ("locate(x::x==2,insert(2,insert(1,set())))\n", "2\n"),
        ("locate(x::x==1,insert(1,insert(1,bag())))\n", "1\n"),
        ("locate(atom,insert('x,set()))\n", "'x\n"),
        ("locate(x::x==\"b\",(\"a\",\"b\",\"c\"))\n", "\"b\"\n"),
        ("p:=locate(x::x>1)\np((1,2,3))\n", "<function>\n2\n"),
        ("map(locate(x::x==1),(insert(1,set()),insert(2,set())))\n", "1:(nil):nil\n"),
        ("class FindSet < Set\nlocate(x::x==3,insert(3,new FindSet))\n", "<class FindSet>\n3\n"),
        ("class FindBag < Bag\nlocate(x::x==4,insert(4,new FindBag))\n", "<class FindBag>\n4\n"),
        ("o:=new Object\nlocate(x::x==o,insert(o,set()))==o\n", "<object Object>\ntrue\n"),
        ("locate(x::x==2,filter(x::x>1,insert(1,insert(2,set()))))\n", "2\n"),
        ("locate(x::x==2,collect(x::x+1,insert(1,set())))\n", "2\n"),
        ("locate(x::x==3,UNION((insert(1,set()),insert(3,set()))))\n", "3\n"),
        ("locate(x::x>1,remove(1,insert(1,insert(2,set()))))\n", "2\n"),
    ]

    slice_067_robustness_failure_cases = [
        ("locate()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("locate(x::true,set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("locate(1,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("locate(x::true,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("locate(x::true,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("locate(x::1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("locate(x::x+1,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("locate(x::missing,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("locate(x::true,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("locate(x::1/0,insert(1,set()))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("locate(version,insert(1,set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("locate(x::x==9,insert(1,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not locate(x::x==1,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(size,locate(x::x==1,insert(1,set())))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("locate(x::x==1,insert(1,set()))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("locate(x::true,insert(new Object,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_068_boundary_success_cases = [
        ("forEachDo(x::x+1,(1,2,3))\n", "nil\n"),
        ("forEachDo(x::1/0,())\n", "nil\n"),
        ("forEachDo(x::1/0,set())\n", "nil\n"),
        ("forEachDo(x::1/0,bag())\n", "nil\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),(1,2,3))\no.total\n", "<object Object>\nnil\n6\n"),
        ("o:=new Object with count:=0\nforEachDo(x::(o.count:=o.count+1),insert(1,insert(2,set())))\no.count\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with count:=0\nforEachDo(x::(o.count:=o.count+1),insert(1,insert(1,bag())))\no.count\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with last:=0\nforEachDo(x::(o.last:=x),insert(2,set()))\no.last\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with total:=0\np:=forEachDo(x::(o.total:=o.total+x))\np((1,2))\no.total\n", "<object Object>\n<function>\nnil\n3\n"),
        ("map(atom,(forEachDo(x::x,()),forEachDo(x::x,set())))\n", "true:true:nil\n"),
        ("class EachSet < Set\no:=new Object with count:=0\nforEachDo(x::(o.count:=o.count+1),insert(3,new EachSet))\no.count\n", "<class EachSet>\n<object Object>\nnil\n1\n"),
        ("class EachBag < Bag\no:=new Object with count:=0\nforEachDo(x::(o.count:=o.count+1),insert(4,new EachBag))\no.count\n", "<class EachBag>\n<object Object>\nnil\n1\n"),
        ("o:=new Object\nbox:=new Object with seen:=false\nforEachDo(x::(box.seen:=x==o),insert(o,set()))\nbox.seen\n", "<object Object>\n<object Object>\nnil\ntrue\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),filter(x::x>1,insert(1,insert(2,set()))))\no.total\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),collect(x::x+1,insert(1,set())))\no.total\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),remove(1,insert(1,insert(2,set()))))\no.total\n", "<object Object>\nnil\n2\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),UNION((insert(1,set()),insert(3,set()))))\no.total\n", "<object Object>\nnil\n4\n"),
        ("o:=new Object with count:=0\nforEachDo(x::(o.count:=o.count+1),('a,\"b\"))\no.count\n", "<object Object>\nnil\n2\n"),
    ]

    slice_068_robustness_failure_cases = [
        ("forEachDo()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("forEachDo(x::x,(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("forEachDo(1,())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("forEachDo(x::x,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("forEachDo(x::x,Set)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("forEachDo(x::x+1,insert(true,set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("forEachDo(x::missing,insert(1,set()))\n", "ENACT_ERR_NAME_UNBOUND"),
        ("forEachDo(x::1/0,insert(1,set()))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("forEachDo(x::x,1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("forEachDo(version,insert(1,set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("forEachDo(x::x,insert(1,set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not forEachDo(x::x,insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(forEachDo(x::x,insert(1,set())))\n", "ENACT_ERR_LIST_EMPTY"),
        ("forEachDo(x::x,insert(1,set()))==1\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("forEachDo(x::x.missing,insert(new Object,set()))\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("forEachDo(x::x(1),insert(1,set()))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_069_boundary_success_cases = [
        ("size(set(()))\n", "0\n"),
        ("size(bag(()))\n", "0\n"),
        ("size(set((1,2,1)))\n", "2\n"),
        ("size(bag((1,2,1)))\n", "3\n"),
        ("member(2,set((1,2,1)))\n", "true\n"),
        ("member(3,set((1,2,1)))\n", "false\n"),
        ("map(member(1),(set(list(1)),bag((1,1))))\n", "true:true:nil\n"),
        ("reduce((acc,x)::acc+x,0,set((1,2,1)))\n", "3\n"),
        ("reduce((acc,x)::acc+1,0,bag((1,2,1)))\n", "3\n"),
        ("equal(set((1,2,1)),insert(1,insert(2,set())))\n", "true\n"),
        ("size(union(set((1,2)),set((2,3))))\n", "3\n"),
        ("size(collect(x::x+1,set((1,2))))\n", "2\n"),
        ("size(filter(x::x==1,bag((1,1,2))))\n", "2\n"),
        ("locate(x::x==2,set((1,2)))\n", "2\n"),
        ("o:=new Object with total:=0\nforEachDo(x::(o.total:=o.total+x),set((1,2)))\no.total\n", "<object Object>\nnil\n3\n"),
        ("s:=set((1,1))\nb:=bag((1,1))\nsize(s)+size(b)\n", "set(1:nil)\nbag(1:1:nil)\n3\n"),
        ("class SeedSet < Set\nSet:=SeedSet\nclassof(set(list(1)))==SeedSet\n", "<class SeedSet>\n<class SeedSet>\ntrue\n"),
        ("o:=new Object\nmember(o,set(list(o)))\n", "<object Object>\ntrue\n"),
    ]

    slice_069_robustness_failure_cases = [
        ("set(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("bag(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set((),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("bag((),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("bag(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("Set:=1\nset(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("Bag:=true\nbag(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("set(list(1))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not bag(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set(list(1)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(size,set((1,2)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(set((1,2)),bag((1,2)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set:=1\nset(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("size(set(new Object))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("class NotSet < Object\nSet:=NotSet\nset(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
    ]

    slice_070_boundary_success_cases = [
        ("subset(bag(),bag())\n", "true\n"),
        ("equal(bag(),bag())\n", "true\n"),
        ("subset(bag(),bag(list(1)))\n", "true\n"),
        ("subset(bag(list(1)),bag())\n", "false\n"),
        ("subset(bag(list(1)),bag((1,1)))\n", "true\n"),
        ("subset(bag((1,1)),bag(list(1)))\n", "false\n"),
        ("equal(bag((1,1)),bag((1,1)))\n", "true\n"),
        ("equal(bag((1,1)),bag(list(1)))\n", "false\n"),
        ("equal(bag((1,2,1)),bag((2,1,1)))\n", "true\n"),
        ("equal(bag((1,2)),bag((2,1,1)))\n", "false\n"),
        ("subset(filter(x::x==1,bag((1,1,2))),bag((1,1,1)))\n", "true\n"),
        ("subset(remove(1,bag((1,1,2))),bag((1,2)))\n", "true\n"),
        ("all(x::subset(x,bag((1,1,2))),(bag(),bag(list(1)),bag((1,1))))\n", "true\n"),
        ("map(x::equal(x,bag((1,1))),(bag((1,1)),bag(list(1))))\n", "true:false:nil\n"),
        ("p:=subset(bag(list(1)))\np(bag((1,1)))\n", "<function>\ntrue\n"),
        ("class SmallBag < Bag\nsubset(insert(1,insert(1,new SmallBag)),bag((1,1,1)))\n", "<class SmallBag>\ntrue\n"),
        ("equal(bag(list(1)) with tag:=true,bag(list(1)) with other:=true)\n", "true\n"),
        ("o:=new Object\nsubset(bag(list(o)),bag((o,o)))\n", "<object Object>\ntrue\n"),
    ]

    slice_070_robustness_failure_cases = [
        ("subset(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(bag(),bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("equal(bag(),bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("subset(list(1),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(bag(),list(1))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(bag(),new Object)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("equal(Bag,bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset(1/0,bag())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("equal(bag(),1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("subset(bag(),bag())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("equal(bag(),bag())==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("map(size,subset(bag(),bag()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("subset:=1\nsubset(bag(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_071_boundary_success_cases = [
        ("size(union(bag(),bag()))\n", "0\n"),
        ("equal(union(bag(list(1)),bag((1,1))),bag((1,1)))\n", "true\n"),
        ("size(union(bag((1,1)),bag((1,2,2))))\n", "4\n"),
        ("subset(bag((1,1)),union(bag((1,1)),bag(list(2))))\n", "true\n"),
        ("equal(difference(bag((1,1,2)),bag(list(1))),bag((1,2)))\n", "true\n"),
        ("size(difference(bag(list(1)),bag((1,1))))\n", "0\n"),
        ("equal(intersection(bag((1,1,2)),bag((1,2,2))),bag((1,2)))\n", "true\n"),
        ("size(intersection(bag((1,1)),bag(list(2))))\n", "0\n"),
        ("class LeftBag < Bag\nclass RightBag < Bag\nclassof(union(insert(1,new LeftBag),insert(2,new RightBag)))==LeftBag\n", "<class LeftBag>\n<class RightBag>\ntrue\n"),
        ("attrs(difference(bag((1,2)) with tag:=true,bag(list(2))))\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,intersection(bag((o,o)),bag(list(o))))\n", "<object Object>\ntrue\n"),
        ("reduce((acc,x)::acc+1,0,union(bag((1,1)),bag((1,2,2))))\n", "4\n"),
        ("u:=union(bag(list(1)))\nequal(u(bag((1,1,2))),bag((1,1,2)))\n", "<function>\ntrue\n"),
        ("map(size,(union(bag(list(1)),bag(list(2))),difference(bag((1,2)),bag(list(1))),intersection(bag((1,2)),bag(list(2)))))\n", "2:1:1:nil\n"),
        ("equal(union(filter(x::x==1,bag((1,1,2))),bag(list(2))),bag((1,1,2)))\n", "true\n"),
        ("equal(union(set((1,1)),set((1,2))),set((1,2)))\n", "true\n"),
        ("equal(difference(bag((1,2,2)),bag((2,2,2))),bag(list(1)))\n", "true\n"),
        ("size(intersection(bag((1,1,1)),bag((1,1))))\n", "2\n"),
    ]

    slice_071_robustness_failure_cases = [
        ("union(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(bag(),set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(bag(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("difference(nil,bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("intersection(Bag,bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(bag(),bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("difference(bag(),bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("intersection(bag(),bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("union(1/0,bag())\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("difference(bag(),1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("union(bag(),bag())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not difference(bag(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(size,intersection(bag(),bag()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd(union(bag(),bag()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union:=1\nunion(bag(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_072_boundary_success_cases = [
        ("classof(UNION(()))==Set\n", "true\n"),
        ("classof(UNION(list(bag())))==Bag\n", "true\n"),
        ("size(UNION(list(bag())))\n", "0\n"),
        ("equal(UNION((bag(list(1)),bag((1,1)))),bag((1,1)))\n", "true\n"),
        ("size(UNION((bag((1,1)),bag((1,2,2)),bag((2,2,3)))))\n", "5\n"),
        ("subset(bag((1,1,2)),UNION((bag((1,1)),bag((1,2)))))\n", "true\n"),
        ("equal(UNION((bag((1,2)),bag((2,2,3)))),bag((1,2,2,3)))\n", "true\n"),
        ("equal(UNION((bag((1,1)),bag(list(2)))),union(bag((1,1)),bag(list(2))))\n", "true\n"),
        ("u:=UNION\nequal(u((bag(list(1)),bag((1,1,2)))),bag((1,1,2)))\n", "<function>\ntrue\n"),
        ("class LeftBag < Bag\nclass RightBag < Bag\nclassof(UNION((insert(1,new LeftBag),insert(2,new RightBag))))==LeftBag\n", "<class LeftBag>\n<class RightBag>\ntrue\n"),
        ("attrs(UNION((bag(list(1)) with tag:=true,bag(list(2)))))\n", "'tag:nil\n"),
        ("o:=new Object\nreduce((acc,x)::acc+1,0,UNION((bag((o,o)),bag(list(o)))))\n", "<object Object>\n2\n"),
        ("equal(UNION((UNION((bag(list(1)),bag((1,1)))),bag(list(2)))),bag((1,1,2)))\n", "true\n"),
        ("map(size,(UNION((bag(list(1)),bag((1,1)))),UNION((bag(list(2)),bag((2,3))))))\n", "2:2:nil\n"),
        ("equal(UNION((filter(x::x==1,bag((1,1,2))),bag(list(2)))),bag((1,1,2)))\n", "true\n"),
        ("equal(UNION((set((1,1)),set((1,2)))),set((1,2)))\n", "true\n"),
        ("equal(UNION((bag(),bag((1,1)))),bag((1,1)))\n", "true\n"),
        ("equal(UNION((collect(x::x+1,bag((0,0))),bag(list(2)))),bag((1,1,2)))\n", "true\n"),
    ]

    slice_072_robustness_failure_cases = [
        ("UNION(list(bag()),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("UNION(bag(list(1)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(),set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(list(1)),set(list(1))))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(),nil))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(),new Object))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(list(Bag))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(),Bag))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION((bag(),1/0))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("UNION(list(1/0))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("UNION(list(bag()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not UNION(list(bag()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(size,UNION(list(bag())))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("hd(UNION(list(bag())))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(list(bag()))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("UNION:=1\nUNION(list(bag()))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_073_boundary_success_cases = [
        ("set()\n", "set()\n"),
        ("bag()\n", "bag()\n"),
        ("insert(1,set())\n", "set(1:nil)\n"),
        ("insert(1,insert(2,set()))\n", "set(1:2:nil)\n"),
        ("insert(1,insert(1,bag()))\n", "bag(1:1:nil)\n"),
        ("set((1,2,1))\n", "set(2:1:nil)\n"),
        ("bag((1,2,1))\n", "bag(1:2:1:nil)\n"),
        ("union(set((1,2)),set((2,3)))\n", "set(1:2:3:nil)\n"),
        ("union(bag((1,1)),bag((1,2)))\n", "bag(1:1:2:nil)\n"),
        ("difference(bag((1,1,2)),bag(list(1)))\n", "bag(1:2:nil)\n"),
        ("intersection(bag((1,1,2)),bag((1,2,2)))\n", "bag(1:2:nil)\n"),
        ("UNION((bag(list(1)),bag((1,1,2))))\n", "bag(1:1:2:nil)\n"),
        ("set(list((1,2)))\n", "set((1:2:nil):nil)\n"),
        ("insert(set(list(1)),set())\n", "set(set(1:nil):nil)\n"),
        ("set((\"a\",'x))\n", "set(\"a\":'x:nil)\n"),
        ("class DisplaySet < Set\nnew DisplaySet\n", "<class DisplaySet>\nset()\n"),
        ("set(list(new Object))\n", "set(<object Object>:nil)\n"),
        ("(set(list(1)),bag((2,2)))\n", "set(1:nil):bag(2:2:nil):nil\n"),
    ]

    slice_073_robustness_failure_cases = [
        ("set(list(1))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not bag(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set(list(1)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(size,bag(list(1)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set(list(1))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("UNION((set(),bag()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union(set(),bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("append(set(),nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("1:set()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("bag(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("Set:=1\nset()\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("Bag:=true\nbag()\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
        ("set:=1\nset()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("size(set(new Object))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("class NotSet < Object\nSet:=NotSet\nset(list(1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS"),
    ]

    slice_074_boundary_success_cases = [
        ("set().size()\n", "0\n"),
        ("bag().size()\n", "0\n"),
        ("set((1,2)).size()\n", "2\n"),
        ("bag((1,1,2)).size()\n", "3\n"),
        ("set((1,2)).member(1)\n", "true\n"),
        ("bag((1,1)).member(2)\n", "false\n"),
        ("set().insert(1)\n", "set(1:nil)\n"),
        ("set().insert(1).insert(1)\n", "set(1:nil)\n"),
        ("bag().insert(1).insert(1)\n", "bag(1:1:nil)\n"),
        ("set((1,2)).remove(1)\n", "set(2:nil)\n"),
        ("bag((1,1)).remove(1)\n", "bag(1:nil)\n"),
        ("set().insert(1).insert(2).size()\n", "2\n"),
        ("map(size,(set().insert(1),bag().insert(1).insert(1)))\n", "1:2:nil\n"),
        ("class DotSet < Set\n(new DotSet).insert(1).size()\n", "<class DotSet>\n1\n"),
        ("o:=new Object\nset(list(o)).member(o)\n", "<object Object>\ntrue\n"),
        ("size:=1\nset(list(1)).size()\n", "1\n1\n"),
        ("Set.size():=99\nset().size()\n", "<function>\n99\n"),
        ("f():=42\ns:=set() with size:=f\ns.size()\n", "<function>\nset()\n42\n"),
    ]

    slice_074_robustness_failure_cases = [
        ("set().size(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().member()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().member(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().insert()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().insert(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().remove()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().remove(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("(new Object).size()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("set().unitset()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("set().unitset+1\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("(1).size()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("Set.size()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("s:=set() with insert:=1\ns.insert(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("Set.insert(x):=1/0\nset().insert(1)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("size:=1\nsize(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set().insert(1)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_075_boundary_success_cases = [
        ("set((1,2)).union(set((2,3)))\n", "set(1:2:3:nil)\n"),
        ("bag((1,1)).union(bag((1,2)))\n", "bag(1:1:2:nil)\n"),
        ("set((1,2)).difference(set(list(2)))\n", "set(1:nil)\n"),
        ("bag((1,1,2)).difference(bag(list(1)))\n", "bag(1:2:nil)\n"),
        ("set((1,2)).intersection(set((2,3)))\n", "set(2:nil)\n"),
        ("bag((1,1,2)).intersection(bag((1,2,2)))\n", "bag(1:2:nil)\n"),
        ("set((1,2)).subset(set((1,2,3)))\n", "true\n"),
        ("bag((1,1)).subset(bag(list(1)))\n", "false\n"),
        ("set((1,2)).equal(set((2,1)))\n", "true\n"),
        ("bag((1,2,1)).equal(bag((2,1,1)))\n", "true\n"),
        ("set().add(1).add(1)\n", "set(1:nil)\n"),
        ("set().add(1).union(set(list(2))).subset(set((1,2,3)))\n", "true\n"),
        ("class LeftSet < Set\nclass RightSet < Set\nclassof((new LeftSet).add(1).union(new RightSet))==LeftSet\n", "<class LeftSet>\n<class RightSet>\ntrue\n"),
        ("attrs((set(list(1)) with tag:=true).union(set(list(2))))\n", "'tag:nil\n"),
        ("o:=new Object\nset(list(o)).union(set()).member(o)\n", "<object Object>\ntrue\n"),
        ("union:=1\nset(list(1)).union(set(list(2)))\n", "1\nset(1:2:nil)\n"),
        ("Set.union(other):=99\nset().union(set())\n", "<function>\n99\n"),
        ("f(x):=42\ns:=set() with equal:=f\ns.equal(set())\n", "<function>\nset()\n42\n"),
    ]

    slice_075_robustness_failure_cases = [
        ("set().union()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().union(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().difference()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().intersection(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().subset()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().equal(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().add()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().add(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("bag().add(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().union(bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("bag().difference(set())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().subset(bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().equal(nil)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("union:=1\nunion(set(),set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set().union(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(set().intersection(set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_076_boundary_success_cases = [
        ("set((1,2)).collect(x::x+1)\n", "set(2:3:nil)\n"),
        ("bag((1,1,2)).collect(x::x+1)\n", "bag(2:2:3:nil)\n"),
        ("set((1,2,3)).filter(x::x>1)\n", "set(2:3:nil)\n"),
        ("bag((1,1,2)).filter(x::x==1)\n", "bag(1:1:nil)\n"),
        ("set((1,2,3)).select(x::x!=2)\n", "set(1:3:nil)\n"),
        ("set((1,2)).all(x::x>0)\n", "true\n"),
        ("bag((1,2)).exists(x::x==2)\n", "true\n"),
        ("set((1,2,3)).locate(x::x>1)\n", "2\n"),
        ("set((1,2)).locate(x::x==9)\n", "nil\n"),
        ("o:=new Object with total:=0\nset((1,2)).forEachDo(x::(o.total:=o.total+x))\no.total\n", "<object Object>\nnil\n3\n"),
        ("set((1,2,3)).reduce((acc,x)::acc+x,0)\n", "6\n"),
        ("set((1,2)).collect(x::x+1).filter(x::x>2).size()\n", "1\n"),
        ("class DotBag < Bag\nclassof((new DotBag).insert(1).collect(x::x))==DotBag\n", "<class DotBag>\ntrue\n"),
        ("attrs((set(list(1)) with tag:=true).filter(x::true))\n", "'tag:nil\n"),
        ("o:=new Object\nset(list(o)).locate(x::x==o)==o\n", "<object Object>\ntrue\n"),
        ("collect:=1\nset(list(1)).collect(x::x+1)\n", "1\nset(2:nil)\n"),
        ("Set.collect(f):=99\nset().collect(x::x)\n", "<function>\n99\n"),
        ("f(x):=42\ns:=set() with all:=f\ns.all(x::false)\n", "<function>\nset()\n42\n"),
    ]

    slice_076_robustness_failure_cases = [
        ("set().collect()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().collect(x::x,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().filter()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().filter(x::true,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().reduce((a,b)::a+b,0,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().all(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set(list(1)).exists(x::1)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("set(list(1)).locate(x::1)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("set().forEachDo(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set(list(1)).reduce(x::x,0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("collect:=1\ncollect(x::x,set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set().collect(x::x)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(set().filter(x::true))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().all(x::true)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("set().map(x::x)\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
    ]

    slice_077_boundary_success_cases = [
        ("equal(UNION(set()),set())\n", "true\n"),
        ("equal(UNION(bag()),set())\n", "true\n"),
        ("equal(UNION(set((set(list(1)),set(list(2))))),set((1,2)))\n", "true\n"),
        ("equal(set((set(list(1)),set(list(2)))).UNION(),set((1,2)))\n", "true\n"),
        ("equal(bag((bag((1,1)),bag((1,2)))).UNION(),bag((1,1,2)))\n", "true\n"),
        ("classof(set(list(set(list(1)))).UNION())==Set\n", "true\n"),
        ("class InnerSet < Set\nclassof(set(list(new InnerSet)).UNION())==InnerSet\n", "<class InnerSet>\ntrue\n"),
        ("attrs(set(list(insert(1,set() with tag:=true))).UNION())\n", "'tag:nil\n"),
        ("o:=new Object\nmember(o,set(list(set(list(o)))).UNION())\n", "<object Object>\ntrue\n"),
        ("equal(UNION(set(list(UNION(set((set(list(1)),set(list(2)))))))),set((1,2)))\n", "true\n"),
        ("equal(set(list(bag((1,1)))).UNION(),bag((1,1)))\n", "true\n"),
        ("equal(bag(list(set(list(1)))).UNION(),set(list(1)))\n", "true\n"),
        ("equal(set((set(list(1)),set(list(2)))).UNION().add(3),set((1,2,3)))\n", "true\n"),
        ("set((set(list(1)),set(list(2)))).UNION().all(x::x>0)\n", "true\n"),
        ("UNION:=1\nset(list(set(list(1)))).UNION()\n", "1\nset(1:nil)\n"),
        ("Set.UNION():=99\nset(list(set())).UNION()\n", "<function>\n99\n"),
        ("f():=42\ns:=set() with UNION:=f\ns.UNION()\n", "<function>\nset()\n42\n"),
        ("equal(UNION(set((bag(list(1)),bag((1,1,2))))),bag((1,1,2)))\n", "true\n"),
    ]

    slice_077_robustness_failure_cases = [
        ("set().UNION(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set(list(1)).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("bag(list(1)).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set((set(),bag())).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set(list(new Object)).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set(list(Set)).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(set(list(1)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(set(list(new Object)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(set(list(Set)))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(set(list(1/0)))\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("set(list(set())).UNION()+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not set(list(set())).UNION()\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set(list(set())).UNION())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("UNION(set(list(set())))==nil\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("UNION:=1\nUNION(set(list(set())))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("s:=set() with UNION:=1\ns.UNION()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_078_boundary_success_cases = [
        ("set((1,2)).size\n", "<function>\n"),
        ("size:=1\nf:=set(list(1)).size\nf()\n", "1\n<function>\n1\n"),
        ("g():=42\ns:=set() with size:=g\ns.size\ns.size()\n", "<function>\nset()\n<function>\n42\n"),
        ("map(set(list(1)).member,(1,2))\n", "true:false:nil\n"),
        ("f:=set().insert\nf(1)\n", "<function>\nset(1:nil)\n"),
        ("f:=bag((1,1)).remove\nf(1)\n", "<function>\nbag(1:nil)\n"),
        ("f:=set(list(1)).union\nf(set(list(2)))\n", "<function>\nset(1:2:nil)\n"),
        ("f:=bag((1,1,2)).difference\nf(bag(list(1)))\n", "<function>\nbag(1:2:nil)\n"),
        ("f:=set((1,2)).intersection\nf(set((2,3)))\n", "<function>\nset(2:nil)\n"),
        ("f:=bag((1,1)).subset\nf(bag((1,1,2)))\n", "<function>\ntrue\n"),
        ("f:=bag((1,2,1)).equal\nf(bag((2,1,1)))\n", "<function>\ntrue\n"),
        ("f:=set().add\nf(1).member(1)\n", "<function>\ntrue\n"),
        ("f:=set((1,2)).collect\nf(x::x+1)\n", "<function>\nset(2:3:nil)\n"),
        ("f:=set((1,2,3)).filter\nf(x::x>1)\n", "<function>\nset(2:3:nil)\n"),
        ("f:=set((1,2,3)).select\nf(x::x!=2)\n", "<function>\nset(1:3:nil)\n"),
        ("f:=set((1,2)).all\nf(x::x>0)\n", "<function>\ntrue\n"),
        ("f:=bag((1,2)).exists\nf(x::x==2)\n", "<function>\ntrue\n"),
        ("f:=set((1,2,3)).locate\nf(x::x>1)\n", "<function>\n2\n"),
        ("o:=new Object with total:=0\nf:=set((1,2)).forEachDo\nf(x::(o.total:=o.total+x))\no.total\n", "<object Object>\n<function>\nnil\n3\n"),
        ("f:=set((1,2,3)).reduce\nr:=f((acc,x)::acc+x)\nr(0)\n", "<function>\n<function>\n6\n"),
        ("f:=set((set(list(1)),set(list(2)))).UNION\nequal(f(),set((1,2)))\n", "<function>\ntrue\n"),
    ]

    slice_078_robustness_failure_cases = [
        ("f:=set().size\nf(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=set().member\nf()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=set().member\nf(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=set().member\nf(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("f:=set().collect\nf(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("f:=set(list(1)).exists\nf(x::1)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("f:=set(list(1)).reduce\nf(x::x,0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("f:=bag().add\nf(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("f:=set().union\nf(bag())\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("f:=set(list(1)).UNION\nf()\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().map\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("s:=set() with size:=1\ns.size()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("set().size+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not set().member\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set().insert)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
    ]

    slice_079_boundary_success_cases = [
        ("class Node < Object\nNode.value():=1\n(new Node).value\n", "<class Node>\n<function>\n<function>\n"),
        ("class Node < Object\nNode.value():=1\nf:=(new Node).value\nf()\n", "<class Node>\n<function>\n<function>\n1\n"),
        (
            "class Node < Object\nNode.add(x):=self.base+x\nn:=new Node with base:=10\nf:=n.add\nf(5)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n15\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=10\nf:=n.add\np:=f(1)\np(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<function>\n13\n",
        ),
        ("class Node < Object\nNode.value():=1\nclass Leaf < Node\nf:=(new Leaf).value\nf()\n", "<class Node>\n<function>\n<class Leaf>\n<function>\n1\n"),
        (
            "class Node < Object\nNode.value():=1\nclass Leaf < Node\nLeaf.value():=2\nf:=(new Leaf).value\nf()\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n<function>\n2\n",
        ),
        (
            "class Node < Object\nNode.value():=1\nn:=new Node\nn.value:=()::2\nn.value\nn.value()\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<function>\n2\n",
        ),
        (
            "class Node < Object\nNode.add(x):=self.base+x\nn:=new Node with base:=10\nmap(n.add,(1,2))\n",
            "<class Node>\n<function>\n<object Node>\n11:12:nil\n",
        ),
        (
            "class Node < Object\nNode.gt(x):=x>self.min\nn:=new Node with min:=2\nfilter(n.gt,(1,2,3))\n",
            "<class Node>\n<function>\n<object Node>\n3:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=self.x\nn:=new Node with x:=1\nf:=n.get\nn.x:=2\nf()\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n2\n2\n",
        ),
        (
            "class Node < Object\nNode.value():=1\nn:=new Node\nf:=n.value\nNode.value():=2\nf()\nn.value()\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<function>\n1\n2\n",
        ),
        (
            "class Node < Object\nNode.get():=self.x\nn:=new Node with x:=1\nf:=n.get\nn:=new Node with x:=2\nf()\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<object Node>\n1\n",
        ),
        ("Set.size():=99\nf:=set().size\nf()\n", "<function>\n<function>\n99\n"),
        ("class Node < Object\nNode.self():=self\nn:=new Node\nf:=n.self\nf()==n\n", "<class Node>\n<function>\n<object Node>\n<function>\ntrue\n"),
        ("class Node < Object\nNode.value():=1\nlist((new Node).value)\n", "<class Node>\n<function>\n<function>:nil\n"),
        ("class Node < Object\nNode.value():=1\nn:=new Node\nf:=n.value\nf==f\n", "<class Node>\n<function>\n<object Node>\n<function>\ntrue\n"),
        (
            "class Node < Object\nNode.set(a,b):=self.x:=a+b\nn:=new Node with x:=0\nf:=n.set\np:=f(3)\np(4)\nn.x\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<function>\n7\n7\n",
        ),
        ("Object.root():=1\nclass Node < Object\nf:=(new Node).root\nf()\n", "<function>\n<class Node>\n<function>\n1\n"),
    ]

    slice_079_robustness_failure_cases = [
        ("(new Object).missing\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("1.value\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("class Node < Object\nNode.value():=1\nf:=(new Node).value\nf(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(x):=x\nf:=(new Node).add\nf()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(x):=x\nf:=(new Node).add\nf(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(x):=x\nf:=(new Node).add\nf(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("class Node < Object\nNode.add(a,b):=a+b\nf:=(new Node).add\np:=f(1)\np()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\nf:=(new Node).add\np:=f(1)\np(2,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.bad(x):=x+true\nf:=(new Node).bad\nf(1)\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.value():=1\n(new Node).value+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.value():=1\nnot (new Node).value\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class Node < Object\nNode.value():=1\nhd((new Node).value)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("class Node < Object\nNode.one(x):=x\nreduce((new Node).one,0,list(1))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.id(x):=x\nfilter((new Node).id,list(1))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class Node < Object\nNode.value():=1\nn:=new Node with value:=1\nn.value()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        (inconsistent_mro_prefix + "A.value():=1\n(new C).value\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_080_boundary_success_cases = [
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1)\n", "<class Node>\n<function>\n<function>\n"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1)(2)\n", "<class Node>\n<function>\n3\n"),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=10\np:=n.add(1)\np(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n13\n",
        ),
        ("class Node < Object\nNode.sum(a,b,c):=a+b+c\n(new Node).sum(1,2)(3)\n", "<class Node>\n<function>\n6\n"),
        ("class Node < Object\nNode.add(a,b):=a+b\nclass Leaf < Node\n(new Leaf).add(1)(2)\n", "<class Node>\n<function>\n<class Leaf>\n3\n"),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nclass Leaf < Node\nLeaf.add(a,b):=10+a+b\n(new Leaf).add(1)(2)\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n13\n",
        ),
        ("Object.root(a,b):=a+b\nclass Node < Object\n(new Node).root(1)(2)\n", "<function>\n<class Node>\n3\n"),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nn:=new Node\nn.add:=(a,b)::a*b\nn.add(2)(3)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n6\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=1\np:=n.add(1)\nn.base:=20\np(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n20\n23\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=1\np:=n.add(1)\nn:=new Node with base:=20\np(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<object Node>\n4\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nn:=new Node\np:=n.add(1)\nNode.add(a,b):=99\np(2)\nn.add(1)(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n<function>\n3\n99\n",
        ),
        ("class Node < Object\nNode.keep(a,b):=self\nn:=new Node\nn.keep(1)(2)==n\n", "<class Node>\n<function>\n<object Node>\ntrue\n"),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=0\nmap(n.add(10),(1,2))\n",
            "<class Node>\n<function>\n<object Node>\n11:12:nil\n",
        ),
        (
            "class Node < Object\nNode.gt(limit,x):=x>limit\nn:=new Node\nfilter(n.gt(2),(1,2,3))\n",
            "<class Node>\n<function>\n<object Node>\n3:nil\n",
        ),
        ("Set.mix(a,b):=a+b\nset().mix(1)(2)\n", "<function>\n3\n"),
        (
            "class Node < Object\nNode.set(a,b):=self.x:=a+b\nn:=new Node with x:=0\nn.set(3)(4)\nn.x\n",
            "<class Node>\n<function>\n<object Node>\n7\n7\n",
        ),
        ("class Node < Object\nNode.value():=1\n(new Node).value()\n", "<class Node>\n<function>\n1\n"),
        ("class Node < Object\nNode.add(a,b):=a+b\nlist((new Node).add(1))\n", "<class Node>\n<function>\n<function>:nil\n"),
    ]

    slice_080_robustness_failure_cases = [
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1,2,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("class Node < Object\nNode.add(a,b):=a+b\np:=(new Node).add(1)\np()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\np:=(new Node).add(1)\np(2,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\np:=(new Node).add(1)\np(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("class Node < Object\nNode.bad(a,b):=a+true\n(new Node).bad(1)(2)\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.add(a,b):=a+b\nn:=new Node with add:=1\nn.add(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("(new Object).missing(1)\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("1.add(1)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        (inconsistent_mro_prefix + "A.add(a,b):=a+b\n(new C).add(1)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("Set.tag(a,b):=a+b\nset().tag()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class Node < Object\nNode.add(a,b):=a+b\n(new Node).add(1)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("class Node < Object\nNode.id(a,b):=a+b\nfilter((new Node).id(0),list(1))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("class Node < Object\nNode.one(a,b):=a+b\nreduce((new Node).one(0),0,list(1))\n", "ENACT_ERR_ARITY_MISMATCH"),
    ]

    slice_081_boundary_success_cases = [
        ("set((1,2,3)).reduce((acc,x)::acc+x)\n", "<function>\n"),
        ("set((1,2,3)).reduce((acc,x)::acc+x)(0)\n", "6\n"),
        ("p:=set((1,2,3)).reduce((acc,x)::acc+x)\np(10)\n", "<function>\n16\n"),
        ("bag((1,1,2)).reduce((acc,x)::acc+x)(0)\n", "4\n"),
        ("set().reduce((acc,x)::acc+1)(0)\n", "0\n"),
        ("p:=set((1,2)).reduce((acc,x)::acc+x)\nmap(p,(0,10))\n", "<function>\n3:13:nil\n"),
        ("apply(f,x):=f(x)\napply(set((1,2)).reduce((acc,x)::acc+x),0)\n", "<function>\n3\n"),
        ("list(set((1,2)).reduce((acc,x)::acc+x))\n", "<function>:nil\n"),
        ("atom(set((1,2)).reduce((acc,x)::acc+x))\n", "true\n"),
        ("s:=set((1,2))\np:=s.reduce((acc,x)::acc+x)\ns:=set(list(10))\np(0)\n", "set(1:2:nil)\n<function>\nset(10:nil)\n3\n"),
        ("union(set(list(1)),set(list(2))).reduce((acc,x)::acc+x)(0)\n", "3\n"),
        ("class CountSet < Set\n(new CountSet).add(1).reduce((acc,x)::acc+x)(0)\n", "<class CountSet>\n1\n"),
        ("reduce:=1\nset((1,2)).reduce((acc,x)::acc+x)(0)\n", "1\n3\n"),
        ("s:=set() with reduce:=(f,z)::42\ns.reduce(x::x)(0)\n", "set()\n42\n"),
        ("Set.reduce(f,z):=99\nset().reduce(x::x)(0)\n", "<function>\n99\n"),
        ("set((1,2)).size()\n", "2\n"),
        ("set((1,2)).member(2)\n", "true\n"),
        ("set((set(list(1)),set(list(2)))).UNION()\n", "set(1:2:nil)\n"),
    ]

    slice_081_robustness_failure_cases = [
        ("set().reduce()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().reduce((acc,x)::acc+x,0,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().reduce(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("p:=set().reduce((acc,x)::acc+x)\np()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("p:=set().reduce((acc,x)::acc+x)\np(0,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("p:=set().reduce((acc,x)::acc+x)\np(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("set(list(1)).reduce((acc,x)::acc+x)(true)\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("set(list(1)).reduce(x::x)(0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set(list(1)).reduce(version)(0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set(list(1)).reduce((acc,x)::missing)(0)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("set(list(1)).reduce((acc,x)::1/0)(0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("set(list(1)).reduce((acc,x)::x:acc)(nil)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not set().reduce((acc,x)::acc+x)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("hd(set().reduce((acc,x)::acc+x))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("set().size(1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().member()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().map(x::x)\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("s:=set() with reduce:=1\ns.reduce(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_082_boundary_success_cases = [
        ("set().size()\n", "0\n"),
        ("bag().size()\n", "0\n"),
        ("set((1,2)).size\n", "<function>\n"),
        ("set((1,2)).member(2)\n", "true\n"),
        ("bag((1,1,2)).member(1)\n", "true\n"),
        ("set(list(1)).insert(2).size()\n", "2\n"),
        ("bag(list(1)).insert(1).size()\n", "2\n"),
        ("set((1,2)).reduce((acc,x)::acc+x)\n", "<function>\n"),
        ("set((1,2)).reduce((acc,x)::acc+x)(10)\n", "13\n"),
        ("set((set(list(1)),set(list(2)))).UNION()\n", "set(1:2:nil)\n"),
        ("set(list(1)).union(set(list(2)))\n", "set(1:2:nil)\n"),
        ("bag((1,1)).union(bag((1,2)))\n", "bag(1:1:2:nil)\n"),
        ("set((1,2)).subset(set((1,2,3)))\n", "true\n"),
        ("set((1,2,3)).filter(x::x>1)\n", "set(2:3:nil)\n"),
        ("set((1,2,3)).locate(x::x>1)\n", "2\n"),
        ("class ChildSet < Set\n(new ChildSet).insert(1).size()\n", "<class ChildSet>\n1\n"),
        ("size:=99\nset().size()\n", "99\n0\n"),
        ("Set.size():=99\nset().size()\n", "<function>\n99\n"),
        ("methods(Set)\n", "nil\n"),
    ]

    slice_082_robustness_failure_cases = [
        ("set().map(x::x)\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("set().unitset()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("(new Object).size()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("set().member()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().member(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("set().member(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("p:=set().member\np()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("p:=set().member\np(1,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("p:=set().member\np(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("bag().add(1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("s:=set() with size:=1\ns.size()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("Set.size():=1/0\nset().size()\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
    ]

    slice_083_boundary_success_cases = [
        ("badAttrs(Object)\n", "nil\n"),
        ("class A < Object\nbadAttrs(A)\n", "<class A>\nnil\n"),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.g():=2\nclass C < (A,B)\nbadAttrs(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\nnil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nbadAttrs(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nC.f():=3\nbadAttrs(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\nnil\n",
        ),
        (
            "class Top < Object\nTop.f():=0\nclass A < Top\nclass B < Top\nclass C < (A,B)\nbadAttrs(C)\n",
            "<class Top>\n<function>\n<class A>\n<class B>\n<class C>\nnil\n",
        ),
        (
            "class Top < Object\nTop.f():=0\nclass A < Top\nA.f():=1\nclass B < Top\nclass C < (A,B)\nbadAttrs(C)\n",
            "<class Top>\n<function>\n<class A>\n<function>\n<class B>\n<class C>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass D < (A,B)\nclass C < D\nbadAttrs(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class D>\n<class C>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nbadAttrs(classof(new C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmember('f,badAttrs(C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsize(badAttrs(C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmap(size,map(badAttrs,(A,B,C)))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n0:0:1:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nfilter(x::size(badAttrs(x))>0,(A,B,C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class C>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsize(badAttrs(C))==0 then 1 else 2\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n2\n",
        ),
        (
            "apply(f,x):=f(x)\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\napply(badAttrs,C)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n",
        ),
        (
            "badAttrs:=x::nil\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nbadAttrs(C)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\nnil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nbadAttrs(C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n'f:nil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nC.f():=3\nbadAttrs(C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n<function>\nnil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nA.g():=3\nB.f():=2\nB.g():=4\nclass C < (A,B)\nsize(badAttrs(C))\nall(x::member(x,badAttrs(C)),('f,'g))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<function>\n<function>\n<class C>\n2\ntrue\n",
        ),
    ]

    slice_083_robustness_failure_cases = [
        ("badAttrs()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("badAttrs(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("badAttrs(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('badAttrs("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs(badAttrs)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("badAttrs(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not badAttrs(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("badAttrs(Object)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("badAttrs:=1\nbadAttrs(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_084_boundary_success_cases = [
        ("suppliers(Object,'f)\n", "nil\n"),
        ("class A < Object\nsuppliers(A,'f)\n", "<class A>\nnil\n"),
        (
            "class A < Object\nA.f():=1\nsuppliers(A,'f)\n",
            "<class A>\n<function>\n<class A>:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass C < A\nsuppliers(C,'f)\n",
            "<class A>\n<function>\n<class C>\n<class A>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.g():=2\nclass C < (A,B)\nsuppliers(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nC.f():=3\nsuppliers(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n<class C>:nil\n",
        ),
        (
            "class Top < Object\nTop.f():=0\nclass A < Top\nclass B < Top\nclass C < (A,B)\nsuppliers(C,'f)\n",
            "<class Top>\n<function>\n<class A>\n<class B>\n<class C>\n<class Top>:nil\n",
        ),
        (
            "class Top < Object\nTop.f():=0\nclass A < Top\nA.f():=1\nclass B < Top\nclass C < (A,B)\nsuppliers(C,'f)\n",
            "<class Top>\n<function>\n<class A>\n<function>\n<class B>\n<class C>\n<class A>:<class Top>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass D < (A,B)\nclass C < D\nsuppliers(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class D>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(classof(new C),'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmember(A,suppliers(C,'f))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsize(suppliers(C,'f))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmap(size,map(x::suppliers(x,'f),(A,B,C)))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1:1:2:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nfilter(x::size(suppliers(x,'f))>1,(A,B,C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class C>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsize(suppliers(C,'f))==2 then 1 else 2\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "apply(f,c,a):=f(c,a)\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\napply(suppliers,C,'f)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        ("p:=suppliers(Object)\np('f)\n", "<function>\nnil\n"),
        (
            "suppliers:=(c,a)::nil\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(C,'f)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\nnil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nsuppliers(C,'f)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n<class A>:<class B>:nil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nC.f():=3\nsuppliers(C,'f)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n<function>\n<class C>:nil\n",
        ),
    ]

    slice_084_robustness_failure_cases = [
        ("suppliers()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("suppliers(Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("suppliers(1,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(true,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(\"x\",'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(nil,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers((1,2),'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(x::x,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(badAttrs,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("suppliers(Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('suppliers(Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,(1,2))\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,x::x)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,badAttrs)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(Object,'f)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not suppliers(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("suppliers(Object,'f)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("suppliers:=1\nsuppliers(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_085_boundary_success_cases = [
        ("badAttrs(new Object)\n", "nil\n"),
        ("class A < Object\nbadAttrs(new A)\n", "<class A>\nnil\n"),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nbadAttrs(new C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nC.f():=3\nbadAttrs(new C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\nnil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmap(size,map(badAttrs,(new A,new B,new C)))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n0:0:1:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nfilter(x::size(badAttrs(x))>0,(new A,new B,new C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<object C>:nil\n",
        ),
        (
            "apply(f,x):=f(x)\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\napply(badAttrs,new C)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nbadAttrs(new C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n'f:nil\n",
        ),
        ("suppliers(new Object,'f)\n", "nil\n"),
        (
            "class A < Object\nA.f():=1\nsuppliers(new A,'f)\n",
            "<class A>\n<function>\n<class A>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(new C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nC.f():=3\nsuppliers(new C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n<class C>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(new C,'g)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\nnil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmap(size,map(x::suppliers(x,'f),(new A,new B,new C)))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1:1:2:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nfilter(x::size(suppliers(x,'f))>1,(new A,new B,new C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<object C>:nil\n",
        ),
        (
            "apply(f,c,a):=f(c,a)\nclass A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\napply(suppliers,new C,'f)\n",
            "<function>\n<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\np:=suppliers(new C)\np('f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n<class A>:<class B>:nil\n",
        ),
        (
            inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nsuppliers(new C,'f)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<function>\n<function>\n<class A>:<class B>:nil\n",
        ),
    ]

    slice_085_robustness_failure_cases = [
        ("badAttrs(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("badAttrs(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not badAttrs(set())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("badAttrs(set())(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("suppliers(new Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("suppliers(new Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('suppliers(new Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,(1,2))\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("suppliers(new Object,'f)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not suppliers(new Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("suppliers(new Object,'f)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=suppliers(new Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
    ]

    slice_086_boundary_success_cases = [
        ("OK(new Object)\n", "true\n"),
        ("class A < Object\nOK(new A)\n", "<class A>\ntrue\n"),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nOK(new C)\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class Top < Object\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nOK(new Leaf)\n",
            "<class Top>\n<class Left>\n<class Right>\n<class Leaf>\ntrue\n",
        ),
        (
            inconsistent_mro_prefix + "OK(new C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nfalse\n",
        ),
        (
            inconsistent_mro_prefix + "OK(new C)==OK(classof(new C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            inconsistent_mro_prefix + "map(OK,(new A,new B,new C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\ntrue:true:false:nil\n",
        ),
        (
            inconsistent_mro_prefix + "filter(OK,(new A,new B,new C))\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<object A>:<object B>:nil\n",
        ),
        (
            "class A < Object\nall(OK,(new Object,new A))\n",
            "<class A>\ntrue\n",
        ),
        (
            inconsistent_mro_prefix + "OK(new C) then 1 else 2\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n2\n",
        ),
        (
            "f:=OK\nclass A < Object\nf(new A)\n",
            "<function>\n<class A>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nmap(OK,(A,new A,C,new C))\n",
            "<class A>\n<class B>\n<class C>\ntrue:true:true:true:nil\n",
        ),
    ]

    slice_086_robustness_failure_cases = [
        ("OK(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("OK(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(OK(set()))\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("OK(set())(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(OK,(Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("map(OK,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("filter(OK,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("all(OK,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
    ]

    slice_087_boundary_success_cases = [
        ("supers(new Object)\n", "nil\n"),
        ("superiors(new Object)\n", "nil\n"),
        ("class Node < Object\nsupers(new Node)\n", "<class Node>\n<class Object>:nil\n"),
        ("class Node < Object\nsuperiors(new Node)\n", "<class Node>\n<class Object>:nil\n"),
        (
            "class A < Object\nclass B < A\nclass C < B\nsupers(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < B\nsuperiors(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class B>:<class A>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nsupers(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nsuperiors(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class A>:<class B>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nsupers(new C)==supers(classof(new C))\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nsuperiors(new C)==superiors(classof(new C))\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nmap(size,map(supers,(new Object,new A,new C)))\n",
            "<class A>\n<class B>\n<class C>\n0:1:2:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nfilter(x::member(B,superiors(x)),(new Object,new A,new B,new C))\n",
            "<class A>\n<class B>\n<class C>\n<object C>:nil\n",
        ),
        ("f:=supers\nclass Node < Object\nf(new Node)\n", "<function>\n<class Node>\n<class Object>:nil\n"),
        ("superiors(set())\n", "<class Object>:nil\n"),
        ("supers(set())\n", "<class Object>:nil\n"),
        (
            inconsistent_mro_prefix + "supers(new C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\n<class A>:<class B>:nil\n",
        ),
    ]

    slice_087_robustness_failure_cases = [
        ("supers(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("superiors(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("supers(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not superiors(set())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(supers,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("map(superiors,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("filter(x::size(supers(x))>0,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("all(x::size(superiors(x))==0,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        (inconsistent_mro_prefix + "superiors(new C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "hd(superiors(new C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_088_boundary_success_cases = [
        ("methods(new Object)\n", "nil\n"),
        ("classes(new Object)\n", "<class Object>:nil\n"),
        ("class Node < Object\nmethods(new Node)\n", "<class Node>\nnil\n"),
        ("class Node < Object\nclasses(new Node)\n", "<class Node>\n<class Node>:<class Object>:nil\n"),
        (
            "class Node < Object\nNode.get():=1\nmethods(new Node)\n",
            "<class Node>\n<function>\n'get:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nmethods(new Leaf)\n",
            "<class Node>\n<function>\n<class Leaf>\nnil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nLeaf.set(v):=v\nmethods(new Leaf)\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n'set:nil\n",
        ),
        (
            "class A < Object\nclass B < A\nclass C < B\nclasses(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class C>:<class B>:<class A>:<class Object>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(new C)\n",
            "<class A>\n<class B>\n<class C>\n<class C>:<class A>:<class B>:<class Object>:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nmethods(new Node)==methods(classof(new Node))\n",
            "<class Node>\n<function>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nclasses(new C)==classes(classof(new C))\n",
            "<class A>\n<class B>\n<class C>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nclass C < (A,B)\nmap(size,map(classes,(new Object,new A,new C)))\n",
            "<class A>\n<class B>\n<class C>\n1:2:4:nil\n",
        ),
        (
            "class Node < Object\nNode.get():=1\nclass Leaf < Node\nLeaf.set(v):=v\nfilter(x::member('get,methods(x)),(new Object,new Node,new Leaf))\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n<object Node>:nil\n",
        ),
        ("f:=classes\nclass Node < Object\nf(new Node)\n", "<function>\n<class Node>\n<class Node>:<class Object>:nil\n"),
        ("classes(bag())\n", "<class Bag>:<class Object>:nil\n"),
        ("methods(set())\n", "nil\n"),
        (
            inconsistent_mro_prefix + "methods(new C)\n",
            "<class X>\n<class Y>\n<class A>\n<class B>\n<class C>\nnil\n",
        ),
    ]

    slice_088_robustness_failure_cases = [
        ("methods(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("classes(new Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methods(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not classes(set())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("map(methods,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("map(classes,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("filter(x::member(Object,classes(x)),(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("all(x::size(methods(x))==0,(new Object,1))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        (inconsistent_mro_prefix + "classes(new C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "hd(classes(new C))\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_089_boundary_success_cases = [
        ("class Node < Object\nNode.id():=1\n(new Node).id\n", "<class Node>\n<function>\n<function>\n"),
        ("class Node < Object\nNode.id():=1\nf:=(new Node).id\nf()\n", "<class Node>\n<function>\n<function>\n1\n"),
        ("class Node < Object\nNode.id():=1\n(new Node).id()\n", "<class Node>\n<function>\n1\n"),
        (
            "class Node < Object\nNode.id():=1\nclass Leaf < Node\n(new Leaf).id\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n",
        ),
        (
            "class Node < Object\nNode.id():=1\nclass Leaf < Node\n(new Leaf).id()\n",
            "<class Node>\n<function>\n<class Leaf>\n1\n",
        ),
        (
            "class Node < Object\nNode.id():=1\nclass Leaf < Node\nLeaf.id():=2\n(new Leaf).id()\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.v():=1\nB.v():=2\nclass C < (A,B)\n(new C).v()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nclass Leaf < Node\nf:=(new Leaf).add(2)\nf(3)\n",
            "<class Node>\n<function>\n<class Leaf>\n<function>\n5\n",
        ),
        (
            "class Node < Object\nNode.value():=1\nn:=new Node\nn.value:=x::x+10\nn.value(5)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n15\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=self.base+a+b\nn:=new Node with base:=1\np:=n.add(1)\nn.base:=20\np(2)\n",
            "<class Node>\n<function>\n<object Node>\n<function>\n20\n23\n",
        ),
    ]

    slice_089_robustness_failure_cases = [
        ("class Node < Object\n(new Node).missing\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class Node < Object\n(new Node).missing()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        (inconsistent_mro_prefix + "A.value():=1\n(new C).value\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.value():=1\n(new C).value()\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nclass Leaf < Node\n(new Leaf).add(1,2,1/0)\n",
            "ENACT_ERR_ARITY_MISMATCH",
        ),
        ("class Node < Object\nNode.value():=1\nn:=new Node with value:=1\nn.value()\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("1.value\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("1.value()\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
    ]

    slice_090_boundary_success_cases = [
        ("methodSupplier(Object,'missing)\n", "nil\n"),
        ("class Node < Object\nNode.f():=1\nmethodSupplier(Node,'f)\n", "<class Node>\n<function>\n<class Node>\n"),
        ("class Node < Object\nNode.f():=1\nmethodSupplier(new Node,'f)\n", "<class Node>\n<function>\n<class Node>\n"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nmethodSupplier(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<class A>\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=2\nmethodSupplier(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class B>\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmethodSupplier(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>\n",
        ),
        (
            "class Top < Object\nTop.f():=1\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nmethodSupplier(Leaf,'f)\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<class Leaf>\n<class Top>\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nC.f():=3\nmethodSupplier(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n<class C>\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nmethodSupplier(new B,'f)==methodSupplier(B,'f)\n",
            "<class A>\n<function>\n<class B>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nmap(x::methodSupplier(x,'f),(A,B,C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:<class A>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nfilter(x::methodSupplier(x,'f)==A,(A,B,C))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class C>:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\np:=methodSupplier(C)\np('f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n<class A>\n",
        ),
        (
            "apply(f,c,a):=f(c,a)\nclass A < Object\nA.f():=1\napply(methodSupplier,A,'f)\n",
            "<function>\n<class A>\n<function>\n<class A>\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\nsuppliers(C,'f)\nmethodSupplier(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<class A>:<class B>:nil\n<class A>\n",
        ),
        ("methodSupplier(set(),'size)\n", "nil\n"),
        ("Set.size():=99\nmethodSupplier(set(),'size)\n", "<function>\n<class Set>\n"),
        ("methodSupplier(set(),'add)\n", "nil\n"),
        ("methodSupplier:=x::nil\nclass A < Object\nA.f():=1\nmethodSupplier(A)\n", "<function>\n<class A>\n<function>\nnil\n"),
    ]

    slice_090_robustness_failure_cases = [
        ("methodSupplier()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodSupplier(Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodSupplier(1,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier(true,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier(\"x\",'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier(nil,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier((1,2),'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier(x::x,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodSupplier(Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodSupplier(Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('methodSupplier(Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodSupplier(Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodSupplier(Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodSupplier(Object,'f)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not methodSupplier(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("methodSupplier(Object,'f)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=methodSupplier(Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        (inconsistent_mro_prefix + "A.f():=1\nmethodSupplier(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f():=1\nmethodSupplier(new C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "C.f():=3\nmethodSupplier(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("methodSupplier:=1\nmethodSupplier(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    native_collection_effective_methods = (
        "'size:'union:'difference:'intersection:'subset:'equal:'UNION:'member:'insert:'remove:"
        "'add:'collect:'filter:'select:'all:'exists:'locate:'forEachDo:'reduce:nil\n"
    )
    native_collection_effective_methods_without_member = (
        "'size:'union:'difference:'intersection:'subset:'equal:'UNION:'insert:'remove:"
        "'add:'collect:'filter:'select:'all:'exists:'locate:'forEachDo:'reduce:nil\n"
    )

    slice_091_boundary_success_cases = [
        ("effectiveMethods(Object)\n", "nil\n"),
        ("class Node < Object\nNode.f():=1\neffectiveMethods(Node)\n", "<class Node>\n<function>\n'f:nil\n"),
        ("class Node < Object\nNode.f():=1\neffectiveMethods(new Node)\n", "<class Node>\n<function>\n'f:nil\n"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nmethods(B)\neffectiveMethods(B)\n",
            "<class A>\n<function>\n<class B>\nnil\n'f:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=2\neffectiveMethods(B)\nmethodSupplier(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<function>\n'f:nil\n<class B>\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.g():=2\nclass C < (A,B)\neffectiveMethods(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:'g:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\neffectiveMethods(C)\nmethodSupplier(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'f:nil\n<class A>\n",
        ),
        (
            "class Top < Object\nTop.f():=1\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\neffectiveMethods(Leaf)\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<class Leaf>\n'f:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.h():=2\nclass C < (A,B)\nC.g():=3\neffectiveMethods(C)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n<function>\n'g:'f:'h:nil\n",
        ),
        (
            "class A < Object\nA.a():=1\nclass B < A\nB.b():=2\nmap(size,map(effectiveMethods,(Object,A,B)))\n",
            "<class A>\n<function>\n<class B>\n<function>\n0:1:2:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nfilter(x::member('f,effectiveMethods(x)),(Object,A,B))\n",
            "<class A>\n<function>\n<class B>\n<class A>:<class B>:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\np:=effectiveMethods\np(A)\n",
            "<class A>\n<function>\n<function>\n'f:nil\n",
        ),
        (
            "apply(f,c):=f(c)\nclass A < Object\nA.f():=1\napply(effectiveMethods,A)\n",
            "<function>\n<class A>\n<function>\n'f:nil\n",
        ),
        ("effectiveMethods(set())\n", native_collection_effective_methods),
        ("Set.size():=99\neffectiveMethods(set())\n", "<function>\n" + native_collection_effective_methods),
        ("effectiveMethods(bag())\n", native_collection_effective_methods),
        ("effectiveMethods:=x::nil\nclass A < Object\nA.f():=1\neffectiveMethods(A)\n", "<function>\n<class A>\n<function>\nnil\n"),
    ]

    slice_091_robustness_failure_cases = [
        ("effectiveMethods()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("effectiveMethods(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("effectiveMethods(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("effectiveMethods(true)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ('effectiveMethods("x")\n', "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("effectiveMethods(nil)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("effectiveMethods((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("effectiveMethods(x::x)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("effectiveMethods(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not effectiveMethods(Object)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("effectiveMethods(Object)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=effectiveMethods\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        (inconsistent_mro_prefix + "A.f():=1\neffectiveMethods(C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f():=1\neffectiveMethods(new C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "C.f():=3\neffectiveMethods(C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("effectiveMethods:=1\neffectiveMethods(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_092_boundary_success_cases = [
        ("super:=7\nsuper\n", "7\n7\n"),
        ("super:=x::x+1\nsuper(2)\n", "<function>\n3\n"),
        (
            "class A < Object\nA.f():=1\nclass B < A\n(new B).f()\n",
            "<class A>\n<function>\n<class B>\n1\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=2\n(new B).f()\n",
            "<class A>\n<function>\n<class B>\n<function>\n2\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.f():=2\nclass C < (A,B)\n(new C).f()\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nmethodSupplier(B,'f)\neffectiveMethods(B)\n",
            "<class A>\n<function>\n<class B>\n<class A>\n'f:nil\n",
        ),
    ]

    slice_092_robustness_failure_cases = [
        ("super\n", "ENACT_ERR_NAME_UNBOUND"),
        ("super:=1\nsuper(true)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("class A < Object\nclass B < A\n(new B).missing()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.f(x):=x\nclass B < A\n(new B).f()\n", "ENACT_ERR_ARITY_MISMATCH"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nn:=new B with f:=1\nn.f()\n",
            "ENACT_ERR_TYPE_EXPECTED_FUNCTION",
        ),
        (inconsistent_mro_prefix + "A.f():=1\nB.f():=2\n(new C).f()\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_093_boundary_success_cases = [
        (
            "class A < Object\nA.f():=1\nclass B < A\nm:=(new B).f\nm()\n",
            "<class A>\n<function>\n<class B>\n<function>\n1\n",
        ),
        (
            "class A < Object\nA.add(x,y):=x+y\nclass B < A\nm:=(new B).add(2)\nm(3)\n",
            "<class A>\n<function>\n<class B>\n<function>\n5\n",
        ),
        (
            "class A < Object\nA.add(x,y):=x+y\nclass B < A\n(new B).add(4)(5)\n",
            "<class A>\n<function>\n<class B>\n9\n",
        ),
        (
            "class A < Object\nA.inc(x):=x+1\nA.twice(x):=self.inc(self.inc(x))\n(new A).twice(3)\n",
            "<class A>\n<function>\n<function>\n5\n",
        ),
        (
            "class A < Object\nA.inc(x):=x+1\nA.map(xs):=map(self.inc,xs)\n(new A).map((1,2))\n",
            "<class A>\n<function>\n<function>\n2:3:nil\n",
        ),
        (
            "class Left < Object\nLeft.f():=1\nclass Right < Object\nRight.f():=2\nclass Leaf < (Left,Right)\n(new Leaf).f()\n",
            "<class Left>\n<function>\n<class Right>\n<function>\n<class Leaf>\n1\n",
        ),
    ]

    slice_093_robustness_failure_cases = [
        ("class A < Object\nA.f():=super\n(new A).f()\n", "ENACT_ERR_NAME_UNBOUND"),
        ("class A < Object\nA.f(x):=x\nclass B < A\nm:=(new B).f\nm()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nA.f(x,y):=x+y\nclass B < A\nm:=(new B).f(1)\nm(2,3)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nclass B < A\nm:=(new B).missing\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nn:=new B with f:=1\nm:=n.f\nm()\n",
            "ENACT_ERR_TYPE_EXPECTED_FUNCTION",
        ),
        (inconsistent_mro_prefix + "A.f():=1\nB.f():=2\nm:=(new C).f\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
    ]

    slice_094_boundary_success_cases = [
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=super.f()+1\n(new B).f()\n",
            "<class A>\n<function>\n<class B>\n<function>\n2\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=super.f()+1\nclass C < B\nC.f():=super.f()+1\n(new C).f()\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class C>\n<function>\n3\n",
        ),
        (
            "class Left < Object\nLeft.f():=1\nclass Right < Object\nRight.f():=2\nclass Leaf < (Left,Right)\nLeaf.f():=super.f()\n(new Leaf).f()\n",
            "<class Left>\n<function>\n<class Right>\n<function>\n<class Leaf>\n<function>\n1\n",
        ),
        (
            "class Top < Object\nTop.f():=1\nclass A < Top\nA.f():=super.f()+1\nclass B < A\n(new B).f()\n",
            "<class Top>\n<function>\n<class A>\n<function>\n<class B>\n2\n",
        ),
        (
            "class A < Object\nA.add(x,y):=x+y\nclass B < A\nB.add(x,y):=super.add(x)(y)+1\n(new B).add(2,3)\n",
            "<class A>\n<function>\n<class B>\n<function>\n6\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.g():=(self.f:=99; super.f())\n(new B).g()\n",
            "<class A>\n<function>\n<class B>\n<function>\n1\n",
        ),
    ]

    slice_094_robustness_failure_cases = [
        ("super.f()\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("class A < Object\nA.f():=super.f()\n(new A).f()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.f():=1\nclass B < A\nB.f():=super.g()\n(new B).f()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.f(x):=x\nclass B < A\nB.f():=super.f()\n(new B).f()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nA.f():=1\nclass B < A\nB.f():=super.f(1)\n(new B).f()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("super:=new Object with f:=x::x\nsuper.f()\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
    ]

    slice_095_boundary_success_cases = [
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.get():=super.f\nm:=(new B).get()\nm()\n",
            "<class A>\n<function>\n<class B>\n<function>\n<function>\n1\n",
        ),
        (
            "class A < Object\nA.inc(x):=x+1\nclass B < A\nB.map(xs):=map(super.inc,xs)\n(new B).map((1,2))\n",
            "<class A>\n<function>\n<class B>\n<function>\n2:3:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.get():=super.f\nclass C < B\nm:=(new C).get()\nm()\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class C>\n<function>\n1\n",
        ),
        (
            "class A < Object\nA.add(x,y):=x+y\nclass B < A\nB.p(x):=super.add(x)\nm:=(new B).p(2)\nm(3)\n",
            "<class A>\n<function>\n<class B>\n<function>\n<function>\n5\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=super.f()+1\nclass C < B\nC.get():=super.f\nm:=(new C).get()\nm()\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class C>\n<function>\n<function>\n2\n",
        ),
        (
            "class Left < Object\nLeft.f():=1\nclass Right < Object\nRight.f():=2\nclass Leaf < (Left,Right)\nLeaf.get():=super.f\nm:=(new Leaf).get()\nm()\n",
            "<class Left>\n<function>\n<class Right>\n<function>\n<class Leaf>\n<function>\n<function>\n1\n",
        ),
    ]

    slice_095_robustness_failure_cases = [
        ("super.f\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("class A < Object\nA.f():=super.f\n(new A).f()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.f():=1\nclass B < A\nB.f():=super.g\n(new B).f()\n", "ENACT_ERR_ATTRIBUTE_UNBOUND"),
        ("class A < Object\nA.f(x):=x\nclass B < A\nB.g():=super.f\n(new B).g()()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nA.f():=1\nclass B < A\nB.g():=super.f\n(new B).g()(1)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("class A < Object\nA.f():=1\nclass B < A\nB.g():=super.f+1\n(new B).g()\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
    ]

    slice_096_boundary_success_cases = [
        ("super:=7\nsuper\n", "7\n7\n"),
        ("super:=x::x+1\nsuper(2)\n", "<function>\n3\n"),
        ("o:=new Object with super:=1\no.super\n", "<object Object>\n1\n"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=super.f()+1\n(new B).f()\n",
            "<class A>\n<function>\n<class B>\n<function>\n2\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.get():=super.f\nm:=(new B).get()\nm()\n",
            "<class A>\n<function>\n<class B>\n<function>\n<function>\n1\n",
        ),
        (
            "class A < Object\nA.read():=self.super\n(new A with super:=3).read()\n",
            "<class A>\n<function>\n3\n",
        ),
    ]

    slice_096_robustness_failure_cases = [
        ("super.f()\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("super.f\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("super:=new Object with f:=x::x\nsuper.f()\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("super:=new Object with f:=x::x\nsuper.f\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        ("apply0(f):=f()\napply0(super.f)\n", "ENACT_ERR_INVALID_SUPER_CONTEXT"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.make():=()::super.f\nm:=(new B).make()\nm()\n",
            "ENACT_ERR_INVALID_SUPER_CONTEXT",
        ),
    ]

    slice_097_boundary_success_cases = [
        ("methodArity(Object,'missing)\n", "nil\n"),
        ("class Node < Object\nNode.f():=1\nmethodArity(Node,'f)\n", "<class Node>\n<function>\n0\n"),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nmethodArity(Node,'add)\n",
            "<class Node>\n<function>\n2\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nmethodArity(new Node,'add)\n",
            "<class Node>\n<function>\n2\n",
        ),
        (
            "class A < Object\nA.f(x):=x\nclass B < A\nmethodArity(B,'f)\n",
            "<class A>\n<function>\n<class B>\n1\n",
        ),
        (
            "class A < Object\nA.f(x):=x\nclass B < A\nB.f(x,y,z):=x+y+z\nmethodArity(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<function>\n3\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f(x):=x\nB.f(x,y):=x+y\nclass C < (A,B)\nmethodArity(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n1\n",
        ),
        (
            "class Top < Object\nTop.f(x,y):=x+y\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nmethodArity(Leaf,'f)\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<class Leaf>\n2\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < Object\nB.f(x):=x\nclass C < (A,B)\nmap(x::methodArity(x,'f),(A,B,C))\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class C>\n0:1:0:nil\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\np:=methodArity(A)\np('f)\n",
            "<class A>\n<function>\n<function>\n2\n",
        ),
        (
            "apply(f,c,a):=f(c,a)\nclass A < Object\nA.f(x):=x\napply(methodArity,A,'f)\n",
            "<function>\n<class A>\n<function>\n1\n",
        ),
        ("methodArity(set(),'size)\n", "0\n"),
        ("Set.size(x):=x\nmethodArity(set(),'size)\n", "<function>\n1\n"),
        (
            "methodArity:=(c,a)::42\nclass A < Object\nA.f():=1\nmethodArity(A,'f)\n",
            "<function>\n<class A>\n<function>\n42\n",
        ),
    ]

    slice_097_robustness_failure_cases = [
        ("methodArity()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodArity(Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodArity(1,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity(true,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity(\"x\",'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity(nil,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity((1,2),'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity(x::x,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodArity(Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity(Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('methodArity(Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity(Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity(Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("not methodArity(Object,'missing)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("methodArity(Object,'missing)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=methodArity(Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        (inconsistent_mro_prefix + "A.f():=1\nmethodArity(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f():=1\nmethodArity(new C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "C.f():=3\nmethodArity(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("methodArity:=1\nmethodArity(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_098_boundary_success_cases = [
        ("methodParams(Object,'missing)\n", "nil\n"),
        ("class Node < Object\nNode.f():=1\nmethodParams(Node,'f)\n", "<class Node>\n<function>\nnil\n"),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nmethodParams(Node,'add)\n",
            "<class Node>\n<function>\n'a:'b:nil\n",
        ),
        (
            "class Node < Object\nNode.add(a,b):=a+b\nmethodParams(new Node,'add)\n",
            "<class Node>\n<function>\n'a:'b:nil\n",
        ),
        (
            "class A < Object\nA.f(x):=x\nclass B < A\nmethodParams(B,'f)\n",
            "<class A>\n<function>\n<class B>\n'x:nil\n",
        ),
        (
            "class A < Object\nA.f(x):=x\nclass B < A\nB.f(x,y,z):=x+y+z\nmethodParams(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<function>\n'x:'y:'z:nil\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f(x):=x\nB.f(x,y):=x+y\nclass C < (A,B)\nmethodParams(C,'f)\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\n'x:nil\n",
        ),
        (
            "class Top < Object\nTop.f(left,right):=left+right\nclass Left < Top\nclass Right < Top\nclass Leaf < (Left,Right)\nmethodParams(Leaf,'f)\n",
            "<class Top>\n<function>\n<class Left>\n<class Right>\n<class Leaf>\n'left:'right:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < Object\nB.f(x):=x\nclass C < (A,B)\nmap(size,map(x::methodParams(x,'f),(A,B,C)))\n",
            "<class A>\n<function>\n<class B>\n<function>\n<class C>\n0:1:0:nil\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\np:=methodParams(A)\np('f)\n",
            "<class A>\n<function>\n<function>\n'x:'y:nil\n",
        ),
        (
            "apply(f,c,a):=f(c,a)\nclass A < Object\nA.f(x):=x\napply(methodParams,A,'f)\n",
            "<function>\n<class A>\n<function>\n'x:nil\n",
        ),
        ("methodParams(set(),'size)\n", "nil\n"),
        ("Set.size(x):=x\nmethodParams(set(),'size)\n", "<function>\n'x:nil\n"),
        (
            "methodParams:=(c,a)::42\nclass A < Object\nA.f():=1\nmethodParams(A,'f)\n",
            "<function>\n<class A>\n<function>\n42\n",
        ),
    ]

    slice_098_robustness_failure_cases = [
        ("methodParams()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodParams(Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("methodParams(1,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams(true,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams(\"x\",'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams(nil,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams((1,2),'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams(x::x,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("methodParams(Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('methodParams(Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("not methodParams(Object,'missing)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("methodParams(Object,'missing)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=methodParams(Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        (inconsistent_mro_prefix + "A.f(x):=x\nmethodParams(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f(x):=x\nmethodParams(new C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "C.f(x):=x\nmethodParams(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("methodParams:=1\nmethodParams(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_099_boundary_success_cases = [
        ("callableArity(x::x)\n", "1\n"),
        ("callableArity((x,y)::x+y)\n", "2\n"),
        ("callableArity(()::1)\n", "0\n"),
        ("f(x,y,z):=x+y+z\ncallableArity(f)\n", "<function>\n3\n"),
        (
            "add:=(x,y,z)::x+y+z\np:=add(1)\ncallableArity(p)\n",
            "<function>\n<function>\n2\n",
        ),
        ("callableArity(hd)\n", "1\n"),
        ("callableArity(append)\n", "2\n"),
        ("callableArity(set)\n", "1\n"),
        ("p:=append(1:nil)\ncallableArity(p)\n", "<function>\n1\n"),
        (
            "class A < Object\nA.f(x,y):=x+y\ncallableArity((new A).f)\n",
            "<class A>\n<function>\n2\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\nm:=(new A).f(1)\ncallableArity(m)\n",
            "<class A>\n<function>\n<function>\n1\n",
        ),
        ("callableArity(set().size)\n", "0\n"),
        ("callableArity(set().member)\n", "1\n"),
        (
            "m:=set((1,2)).reduce((acc,x)::acc+x)\ncallableArity(m)\n",
            "<function>\n1\n",
        ),
        ("map(callableArity,(hd,append,x::x,()::1))\n", "1:2:1:0:nil\n"),
        ("callableArity:=x::42\ncallableArity(hd)\n", "<function>\n42\n"),
    ]

    slice_099_robustness_failure_cases = [
        ("callableArity()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableArity(hd,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableArity(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(true)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(\"x\")\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(nil)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("not callableArity(hd)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("callableArity(hd)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=callableArity\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArity:=1\ncallableArity(hd)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_100_boundary_success_cases = [
        ("callableParams(x::x)\n", "'x:nil\n"),
        ("callableParams((x,y)::x+y)\n", "'x:'y:nil\n"),
        ("callableParams(()::1)\n", "nil\n"),
        ("f(x,y,z):=x+y+z\ncallableParams(f)\n", "<function>\n'x:'y:'z:nil\n"),
        (
            "add:=(x,y,z)::x+y+z\np:=add(1)\ncallableParams(p)\n",
            "<function>\n<function>\n'y:'z:nil\n",
        ),
        (
            "make:=a::(b,c)::a+b+c\np:=make(1)\ncallableParams(p)\n",
            "<function>\n<function>\n'b:'c:nil\n",
        ),
        ("callableParams(hd)\n", "'list:nil\n"),
        ("callableParams(append)\n", "'left:'right:nil\n"),
        ("callableParams(set)\n", "'items:nil\n"),
        ("p:=append(1:nil)\ncallableParams(p)\n", "<function>\n'right:nil\n"),
        (
            "class A < Object\nA.f(x,y):=x+y\ncallableParams((new A).f)\n",
            "<class A>\n<function>\n'x:'y:nil\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\nm:=(new A).f(1)\ncallableParams(m)\n",
            "<class A>\n<function>\n<function>\n'y:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\ncallableParams((new A).f)\n",
            "<class A>\n<function>\nnil\n",
        ),
        (
            "class A < Object\nA.f(x):=x\nclass B < A\ncallableParams((new B).f)\n",
            "<class A>\n<function>\n<class B>\n'x:nil\n",
        ),
        ("callableParams(set().member)\n", "'value:nil\n"),
        (
            "m:=set((1,2)).reduce((acc,x)::acc+x)\ncallableParams(m)\n",
            "<function>\n'initial:nil\n",
        ),
        ("map(size,map(callableParams,(x::x,(x,y)::x+y,hd)))\n", "1:2:1:nil\n"),
        ("callableParams:=x::42\ncallableParams(hd)\n", "<function>\n42\n"),
    ]

    slice_100_robustness_failure_cases = [
        ("callableParams()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableParams(hd,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableParams(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(true)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(\"x\")\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(nil)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("not callableParams(hd)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("callableParams(hd)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("callableParams(hd)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=callableParams\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams:=1\ncallableParams(hd)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_101_boundary_success_cases = [
        ("callableArityRange(x::x)\n", "1:1:nil\n"),
        ("callableArityRange((x,y)::x+y)\n", "2:2:nil\n"),
        ("callableArityRange(()::1)\n", "0:0:nil\n"),
        ("f(x,y,z):=x+y+z\ncallableArityRange(f)\n", "<function>\n3:3:nil\n"),
        (
            "add:=(x,y,z)::x+y+z\np:=add(1)\ncallableArityRange(p)\n",
            "<function>\n<function>\n2:2:nil\n",
        ),
        ("callableArityRange(hd)\n", "1:1:nil\n"),
        ("callableArityRange(append)\n", "2:2:nil\n"),
        ("callableArityRange(set)\n", "0:1:nil\n"),
        ("callableArityRange(bag)\n", "0:1:nil\n"),
        ("p:=append(nil)\ncallableArityRange(p)\n", "<function>\n1:1:nil\n"),
        ("callableArity(set)==hd(tl(callableArityRange(set)))\n", "true\n"),
        (
            "class A < Object\nA.f(x,y):=x+y\ncallableArityRange((new A).f)\n",
            "<class A>\n<function>\n2:2:nil\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\nm:=(new A).f(1)\ncallableArityRange(m)\n",
            "<class A>\n<function>\n<function>\n1:1:nil\n",
        ),
        (
            "class A < Object\nA.f():=1\ncallableArityRange((new A).f)\n",
            "<class A>\n<function>\n0:0:nil\n",
        ),
        ("callableArityRange(set().size)\n", "0:0:nil\n"),
        ("callableArityRange(set().member)\n", "1:1:nil\n"),
        (
            "m:=set((1,2)).reduce((acc,x)::acc+x)\ncallableArityRange(m)\n",
            "<function>\n1:1:nil\n",
        ),
        ("map(callableArityRange,(hd,set,x::x))\n", "(1:1:nil):(0:1:nil):(1:1:nil):nil\n"),
        ("callableArityRange:=x::42\ncallableArityRange(hd)\n", "<function>\n42\n"),
    ]

    slice_101_robustness_failure_cases = [
        ("callableArityRange()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableArityRange(hd,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableArityRange(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(true)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(\"x\")\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(nil)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("not callableArityRange(hd)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("callableArityRange(hd)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("callableArityRange(hd)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=callableArityRange\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableArityRange:=1\ncallableArityRange(hd)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_102_boundary_success_cases = [
        ("callableMinArity(x::x)\n", "1\n"),
        ("callableMinArity((x,y)::x+y)\n", "2\n"),
        ("callableMinArity(()::1)\n", "0\n"),
        ("f(x,y,z):=x+y+z\ncallableMinArity(f)\n", "<function>\n3\n"),
        (
            "add:=(x,y,z)::x+y+z\np:=add(1)\ncallableMinArity(p)\n",
            "<function>\n<function>\n2\n",
        ),
        ("callableMinArity(hd)\n", "1\n"),
        ("callableMinArity(append)\n", "2\n"),
        ("callableMinArity(set)\n", "0\n"),
        ("callableMinArity(bag)\n", "0\n"),
        ("p:=append(nil)\ncallableMinArity(p)\n", "<function>\n1\n"),
        ("callableMinArity(set)==hd(callableArityRange(set))\n", "true\n"),
        (
            "class A < Object\nA.f(x,y):=x+y\ncallableMinArity((new A).f)\n",
            "<class A>\n<function>\n2\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\nm:=(new A).f(1)\ncallableMinArity(m)\n",
            "<class A>\n<function>\n<function>\n1\n",
        ),
        (
            "class A < Object\nA.f():=1\ncallableMinArity((new A).f)\n",
            "<class A>\n<function>\n0\n",
        ),
        ("callableMinArity(set().size)\n", "0\n"),
        ("callableMinArity(set().member)\n", "1\n"),
        (
            "m:=set((1,2)).reduce((acc,x)::acc+x)\ncallableMinArity(m)\n",
            "<function>\n1\n",
        ),
        ("map(callableMinArity,(hd,set,x::x,()::1))\n", "1:0:1:0:nil\n"),
        ("callableMinArity:=x::42\ncallableMinArity(hd)\n", "<function>\n42\n"),
    ]

    slice_102_robustness_failure_cases = [
        ("callableMinArity()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableMinArity(hd,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("callableMinArity(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(true)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(\"x\")\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(nil)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity((1,2))\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(new Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("not callableMinArity(hd)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("callableMinArity(hd)+true\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("callableMinArity(hd)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=callableMinArity\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableMinArity:=1\ncallableMinArity(hd)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_103_boundary_success_cases = [
        ("callableParams(tl)\n", "'list:nil\n"),
        ("callableParams(atom)\n", "'value:nil\n"),
        ("callableParams(isObject)\n", "'value:nil\n"),
        ("callableParams(classof)\n", "'object:nil\n"),
        ("callableParams(callableParams)\n", "'callable:nil\n"),
        ("callableParams(callableArityRange)\n", "'callable:nil\n"),
        ("callableParams(bag)\n", "'items:nil\n"),
        ("callableParams(map)\n", "'function:'collection:nil\n"),
        ("callableParams(filter)\n", "'predicate:'collection:nil\n"),
        ("callableParams(select)\n", "'predicate:'collection:nil\n"),
        ("callableParams(reduce)\n", "'function:'initial:'collection:nil\n"),
        ("callableParams(member)\n", "'value:'collection:nil\n"),
        ("callableParams(union)\n", "'left:'right:nil\n"),
        ("callableParams(UNION)\n", "'collections:nil\n"),
        ("callableParams(version)\n", "nil\n"),
        ("callableParams(set().size)\n", "nil\n"),
        ("callableParams(set().member)\n", "'value:nil\n"),
        ("callableParams(set().union)\n", "'right:nil\n"),
        ("callableParams(set().reduce)\n", "'function:'initial:nil\n"),
        (
            "m:=set((1,2)).reduce((acc,x)::acc+x)\ncallableParams(m)\n",
            "<function>\n'initial:nil\n",
        ),
        ("callableParams(bag().add)\n", "'value:nil\n"),
        (
            "map(size,map(callableParams,(hd,append,set().member,set().size,set().reduce)))\n",
            "1:2:1:0:2:nil\n",
        ),
        ("callableParams:=x::'local:nil\ncallableParams(hd)\n", "<function>\n'local:nil\n"),
    ]

    slice_103_robustness_failure_cases = [
        ("hd(callableParams(version))\n", "ENACT_ERR_LIST_EMPTY"),
        ("hd(callableParams(set().size))\n", "ENACT_ERR_LIST_EMPTY"),
        ("not callableParams(append)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("callableParams(append)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("callableParams(set().member)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("callableParams(set().reduce)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("hd(callableParams(hd))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(callableParams(set().member))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("tl(callableParams(hd))(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("callableParams:=1\ncallableParams(append)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_104_boundary_success_cases = [
        ("methodArity(set(),'size)\n", "0\n"),
        ("methodParams(set(),'size)\n", "nil\n"),
        ("methodArity(set(),'member)\n", "1\n"),
        ("methodParams(set(),'member)\n", "'value:nil\n"),
        ("methodArity(set(),'reduce)\n", "2\n"),
        ("methodParams(set(),'reduce)\n", "'function:'initial:nil\n"),
        ("methodArity(set(),'union)\n", "1\n"),
        ("methodParams(set(),'union)\n", "'right:nil\n"),
        ("methodArity(set(),'UNION)\n", "0\n"),
        ("methodParams(set(),'UNION)\n", "nil\n"),
        ("methodArity(bag(),'add)\n", "1\n"),
        ("methodParams(bag(),'add)\n", "'value:nil\n"),
        ("methodArity(Set,'member)\n", "1\n"),
        ("methodParams(Set,'member)\n", "'value:nil\n"),
        ("methodArity(Bag,'reduce)\n", "2\n"),
        ("methodParams(Bag,'reduce)\n", "'function:'initial:nil\n"),
        ("class MySet < Set\nmethodArity(MySet,'member)\n", "<class MySet>\n1\n"),
        ("class MyBag < Bag\nmethodParams(new MyBag,'add)\n", "<class MyBag>\n'value:nil\n"),
        ("Set.size(x):=x\nmethodArity(set(),'size)\n", "<function>\n1\n"),
        ("Set.member(x,y):=x\nmethodParams(set(),'member)\n", "<function>\n'x:'y:nil\n"),
        ("methodArity(set(),'missing)\n", "nil\n"),
        ("methodParams(set(),'missing)\n", "nil\n"),
        ("map(x::methodArity(set(),x),('size,'member,'reduce,'missing))\n", "0:1:2:(nil):nil\n"),
    ]

    slice_104_robustness_failure_cases = [
        ("not methodArity(set(),'member)\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("methodArity(set(),'member)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("methodParams(set(),'member)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("methodParams(set(),'member)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("hd(methodParams(set(),'size))\n", "ENACT_ERR_LIST_EMPTY"),
        ("methodArity(set(),1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(set(),1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity(set(),\"size\")\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(set(),\"size\")\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity(set(),new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodParams(set(),new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("methodArity:=1\nmethodArity(set(),'member)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("methodParams:=1\nmethodParams(set(),'member)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_105_boundary_success_cases = [
        ("effectiveMethods(set())\n", native_collection_effective_methods),
        ("effectiveMethods(Set)\n", native_collection_effective_methods),
        ("effectiveMethods(bag())\n", native_collection_effective_methods),
        ("effectiveMethods(Bag)\n", native_collection_effective_methods),
        ("size(effectiveMethods(set()))\n", "19\n"),
        ("hd(effectiveMethods(set()))\n", "'size\n"),
        ("member('reduce,effectiveMethods(set()))\n", "true\n"),
        ("member('missing,effectiveMethods(set()))\n", "false\n"),
        ("methods(Set)\n", "nil\n"),
        ("methodSupplier(set(),'member)\n", "nil\n"),
        ("methodArity(set(),'member)\n", "1\n"),
        ("Set.size():=99\neffectiveMethods(set())\n", "<function>\n" + native_collection_effective_methods),
        (
            "Set.member(x):=x\neffectiveMethods(set())\n",
            "<function>\n'member:" + native_collection_effective_methods_without_member,
        ),
        ("class MySet < Set\neffectiveMethods(MySet)\n", "<class MySet>\n" + native_collection_effective_methods),
        (
            "class MyBag < Bag\neffectiveMethods(new MyBag)\n",
            "<class MyBag>\n" + native_collection_effective_methods,
        ),
        (
            "class MySet < Set\nMySet.local():=1\neffectiveMethods(MySet)\n",
            "<class MySet>\n<function>\n'local:" + native_collection_effective_methods,
        ),
        ("map(size,map(effectiveMethods,(Object,Set,Bag)))\n", "0:19:19:nil\n"),
        (
            "filter(x::member('member,effectiveMethods(x)),(Object,Set,Bag))\n",
            "<class Set>:<class Bag>:nil\n",
        ),
        ("effectiveMethods:=x::nil\neffectiveMethods(set())\n", "<function>\nnil\n"),
    ]

    slice_105_robustness_failure_cases = [
        ("effectiveMethods(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("effectiveMethods(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("not effectiveMethods(set())\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("effectiveMethods(set())(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("hd(effectiveMethods(set()))+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("tl(effectiveMethods(set()))(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("filter(x::x,effectiveMethods(set()))\n", "ENACT_ERR_TYPE_EXPECTED_BOOL"),
        ("reduce((a,x)::a+x,0,effectiveMethods(set()))\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hd(filter(x::x=='missing,effectiveMethods(set())))\n", "ENACT_ERR_LIST_EMPTY"),
        (inconsistent_mro_prefix + "A.f():=1\neffectiveMethods(C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f():=1\neffectiveMethods(new C)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("effectiveMethods:=1\neffectiveMethods(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_106_boundary_success_cases = [
        ("hasMethod(Object,'missing)\n", "false\n"),
        ("class Node < Object\nNode.f():=1\nhasMethod(Node,'f)\n", "<class Node>\n<function>\ntrue\n"),
        ("class Node < Object\nNode.f():=1\nhasMethod(new Node,'f)\n", "<class Node>\n<function>\ntrue\n"),
        (
            "class A < Object\nA.f():=1\nclass B < A\nhasMethod(B,'f)\n",
            "<class A>\n<function>\n<class B>\ntrue\n",
        ),
        (
            "class A < Object\nA.f():=1\nclass B < A\nB.f():=2\nhasMethod(B,'f)\n",
            "<class A>\n<function>\n<class B>\n<function>\ntrue\n",
        ),
        (
            "class A < Object\nclass B < Object\nA.f():=1\nB.g():=2\nclass C < (A,B)\nmap(x::hasMethod(C,x),('f,'g,'missing))\n",
            "<class A>\n<class B>\n<function>\n<function>\n<class C>\ntrue:true:false:nil\n",
        ),
        ("hasMethod(set(),'member)\n", "true\n"),
        ("hasMethod(set(),'missing)\n", "false\n"),
        ("hasMethod(Set,'size)\n", "true\n"),
        ("hasMethod(Bag,'reduce)\n", "true\n"),
        ("class MySet < Set\nhasMethod(MySet,'union)\n", "<class MySet>\ntrue\n"),
        ("class MyBag < Bag\nhasMethod(new MyBag,'add)\n", "<class MyBag>\ntrue\n"),
        ("Set.member(x):=x\nhasMethod(set(),'member)\n", "<function>\ntrue\n"),
        ("methodSupplier(set(),'member)\nhasMethod(set(),'member)\n", "nil\ntrue\n"),
        ("methodArity(set(),'member)\nhasMethod(set(),'member)\n", "1\ntrue\n"),
        ("hasMethod(Object,'size)\n", "false\n"),
        ("map(x::hasMethod(set(),x),('size,'member,'reduce,'missing))\n", "true:true:true:false:nil\n"),
        (
            "filter(x::hasMethod(x,'member),(Object,Set,Bag))\n",
            "<class Set>:<class Bag>:nil\n",
        ),
        ("p:=hasMethod(set())\np('member)\n", "<function>\ntrue\n"),
        ("callableParams(hasMethod)\n", "'target:'method:nil\n"),
        ("not hasMethod(set(),'missing)\n", "true\n"),
        ("hasMethod:=(target,method)::false\nhasMethod(set(),'member)\n", "<function>\nfalse\n"),
    ]

    slice_106_robustness_failure_cases = [
        ("hasMethod()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("hasMethod(Object,'f,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("hasMethod(1,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod(true,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod(\"x\",'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod(nil,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod((1,2),'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod(x::x,'f)\n", "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT"),
        ("hasMethod(Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasMethod(Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('hasMethod(Object,"f")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasMethod(Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasMethod(Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasMethod(Object,'missing)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hasMethod(Object,'missing)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=hasMethod(Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("filter(x::hasMethod(set(),x),('member,1))\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        (inconsistent_mro_prefix + "A.f():=1\nhasMethod(C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        (inconsistent_mro_prefix + "A.f():=1\nhasMethod(new C,'f)\n", "ENACT_ERR_INCONSISTENT_LINEARIZATION"),
        ("hasMethod:=1\nhasMethod(Object,'f)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_107_boundary_success_cases = [
        ("hasAttr(new Object,'missing)\n", "false\n"),
        ("hasAttr(new Object with x:=1,'x)\n", "true\n"),
        ("hasAttr(new Object with x:=1,'y)\n", "false\n"),
        ("hasAttr(new Object with x:=1 with y:=2,'y)\n", "true\n"),
        ("hasAttr(new Object with x:=1 with x:=2,'x)\n", "true\n"),
        ("hasAttr(new Object with flag:=false,'flag)\n", "true\n"),
        ("hasAttr(new Object with empty:=nil,'empty)\n", "true\n"),
        ("hasAttr(new Object with f:=x::x,'f)\n", "true\n"),
        ("o:=new Object\nhasAttr(o,'x)\n", "<object Object>\nfalse\n"),
        ("o:=new Object\no.x:=1\nhasAttr(o,'x)\n", "<object Object>\n1\ntrue\n"),
        (
            "o:=new Object with child:=(new Object with value:=7)\nhasAttr(o.child,'value)\n",
            "<object Object>\ntrue\n",
        ),
        ("class Node < Object\nhasAttr(new Node with x:=1,'x)\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nNode.x():=1\nhasAttr(new Node,'x)\n", "<class Node>\n<function>\nfalse\n"),
        (
            "class Node < Object\nNode.x():=1\nhasMethod(new Node,'x)\nhasAttr(new Node,'x)\n",
            "<class Node>\n<function>\ntrue\nfalse\n",
        ),
        ("s:=set() with tag:=true\nhasAttr(s,'tag)\n", "set()\ntrue\n"),
        ("hasAttr(set(),'size)\n", "false\n"),
        ("hasAttr(set() with member:=1,'member)\n", "true\n"),
        ("map(x::hasAttr(new Object with x:=1,x),('x,'y))\n", "true:false:nil\n"),
        (
            "filter(x::hasAttr(x,'x),(new Object with x:=1,new Object))\n",
            "<object Object>:nil\n",
        ),
        ("p:=hasAttr(new Object with x:=1)\np('x)\n", "<function>\ntrue\n"),
        ("callableParams(hasAttr)\n", "'object:'attr:nil\n"),
        ("not hasAttr(new Object,'x)\n", "true\n"),
        ("hasAttr:=(object,attr)::false\nhasAttr(new Object with x:=1,'x)\n", "<function>\nfalse\n"),
    ]

    slice_107_robustness_failure_cases = [
        ("hasAttr()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("hasAttr(new Object,'x,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("hasAttr(1,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(true,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ('hasAttr("x",\'x)\n', "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(nil,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr((1,2),'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(Object,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(x::x,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(hd,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr(new Object,1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr(new Object,true)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ('hasAttr(new Object,"x")\n', "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr(new Object,nil)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr(new Object,new Object)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr(new Object,(1,2))\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr(new Object,'missing)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("hasAttr(new Object,'missing)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("p:=hasAttr(new Object)\np(1)\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("filter(x::hasAttr(new Object,x),('x,1))\n", "ENACT_ERR_TYPE_EXPECTED_ATOM"),
        ("hasAttr((new Object with x:=1).x,'x)\n", "ENACT_ERR_TYPE_EXPECTED_OBJECT"),
        ("hasAttr:=1\nhasAttr(new Object,'x)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_108_boundary_success_cases = [
        ("isClass(Object)\n", "true\n"),
        ("isClass(Set)\n", "true\n"),
        ("isClass(Bag)\n", "true\n"),
        ("isClass(new Object)\n", "false\n"),
        ("isClass(1)\n", "false\n"),
        ("isClass(true)\n", "false\n"),
        ('isClass("x")\n', "false\n"),
        ("isClass(nil)\n", "false\n"),
        ("isClass((1,2))\n", "false\n"),
        ("isClass(x::x)\n", "false\n"),
        ("isClass(hd)\n", "false\n"),
        ("class Node < Object\nisClass(Node)\n", "<class Node>\ntrue\n"),
        ("class Node < Object\nisClass(new Node)\n", "<class Node>\nfalse\n"),
        (
            "map(isClass,(Object,new Object,1,true,\"x\",nil,(1,2),x::x,hd))\n",
            "true:false:false:false:false:false:false:false:false:nil\n",
        ),
        (
            "filter(isClass,(Object,Set,Bag,new Object,1))\n",
            "<class Object>:<class Set>:<class Bag>:nil\n",
        ),
        ("isCallable(x::x)\n", "true\n"),
        ("isCallable(()::1)\n", "true\n"),
        ("isCallable(hd)\n", "true\n"),
        ("isCallable(version)\n", "true\n"),
        ("isCallable(set)\n", "true\n"),
        ("isCallable(append(nil))\n", "true\n"),
        ("isCallable(hasMethod(Object))\n", "true\n"),
        ("isCallable(new Object)\n", "false\n"),
        ("isCallable(Object)\n", "false\n"),
        ("isCallable(set())\n", "false\n"),
        ("isCallable(set().size)\n", "true\n"),
        ("isCallable(set().member)\n", "true\n"),
        (
            "class A < Object\nA.f(x):=x\nisCallable((new A).f)\n",
            "<class A>\n<function>\ntrue\n",
        ),
        (
            "class A < Object\nA.f(x,y):=x+y\nm:=(new A).f(1)\nisCallable(m)\n",
            "<class A>\n<function>\n<function>\ntrue\n",
        ),
        (
            "m:=set((1,2)).reduce((a,x)::a+x)\nisCallable(m)\n",
            "<function>\ntrue\n",
        ),
        (
            "map(isCallable,(hd,set,append(nil),x::x,1,Object,new Object,set().size))\n",
            "true:true:true:true:false:false:false:true:nil\n",
        ),
        ("all(isCallable,(hd,set,x::x,append(nil),set().size))\n", "true\n"),
        ("callableParams(isClass)\n", "'value:nil\n"),
        ("callableParams(isCallable)\n", "'value:nil\n"),
        ("not isClass(new Object)\n", "true\n"),
        ("not isCallable(new Object)\n", "true\n"),
        ("isClass:=x::false\nisClass(Object)\n", "<function>\nfalse\n"),
        ("isCallable:=x::false\nisCallable(hd)\n", "<function>\nfalse\n"),
    ]

    slice_108_robustness_failure_cases = [
        ("isClass()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isClass(Object,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isCallable()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isCallable(hd,1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isClass(missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("isCallable(missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("isClass(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("isCallable(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("isClass(Object)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("isClass(Object)==1\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("isClass(Object)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("isCallable(hd)+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("isCallable(hd)==1\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("isCallable(hd)(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(isClass,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(isCallable,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("reduce(isClass,0,list(Object))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(isCallable,0,list(hd))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isClass:=1\nisClass(Object)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("isCallable:=1\nisCallable(hd)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
    ]

    slice_109_boundary_success_cases = [
        ("isCollection(set())\n", "true\n"),
        ("isCollection(bag())\n", "true\n"),
        ("isSet(set())\n", "true\n"),
        ("isSet(bag())\n", "false\n"),
        ("isBag(bag())\n", "true\n"),
        ("isBag(set())\n", "false\n"),
        ("isCollection(new Object)\n", "false\n"),
        ("isSet(new Object)\n", "false\n"),
        ("isBag(new Object)\n", "false\n"),
        ("isCollection(Object)\n", "false\n"),
        ("isSet(Set)\n", "false\n"),
        ("isBag(Bag)\n", "false\n"),
        ("isCollection(1)\n", "false\n"),
        ("isCollection(true)\n", "false\n"),
        ('isCollection("x")\n', "false\n"),
        ("isCollection(nil)\n", "false\n"),
        ("isCollection((1,2))\n", "false\n"),
        ("isCollection(x::x)\n", "false\n"),
        ("isCollection(hd)\n", "false\n"),
        ("isCollection(append(nil))\n", "false\n"),
        ("class MySet < Set\nisCollection(new MySet)\n", "<class MySet>\ntrue\n"),
        ("class MySet < Set\nisSet(new MySet)\n", "<class MySet>\ntrue\n"),
        ("class MySet < Set\nisBag(new MySet)\n", "<class MySet>\nfalse\n"),
        ("class MyBag < Bag\nisCollection(new MyBag)\n", "<class MyBag>\ntrue\n"),
        ("class MyBag < Bag\nisBag(new MyBag)\n", "<class MyBag>\ntrue\n"),
        ("class MyBag < Bag\nisSet(new MyBag)\n", "<class MyBag>\nfalse\n"),
        ("class Plain < Object\nisCollection(new Plain)\n", "<class Plain>\nfalse\n"),
        ("isCollection(set((1,2))) and isSet(set((1,2)))\n", "true\n"),
        ("isCollection(bag((1,1))) and isBag(bag((1,1)))\n", "true\n"),
        ("isCollection(set() with tag:=true)\n", "true\n"),
        ("isSet(insert(1,set()))\n", "true\n"),
        ("isBag(insert(1,bag()))\n", "true\n"),
        ("map(isCollection,(set(),bag(),new Object,Object,1))\n", "true:true:false:false:false:nil\n"),
        ("map(isSet,(set(),bag(),new Object))\n", "true:false:false:nil\n"),
        ("map(isBag,(set(),bag(),new Object))\n", "false:true:false:nil\n"),
        ("filter(isCollection,(set(),bag(),new Object,1))\n", "set():bag():nil\n"),
        ("all(isCollection,(set(),bag()))\n", "true\n"),
        ("not isCollection(new Object)\n", "true\n"),
        ("not isSet(bag())\n", "true\n"),
        ("not isBag(set())\n", "true\n"),
        ("callableParams(isCollection)\n", "'value:nil\n"),
        ("callableParams(isSet)\n", "'value:nil\n"),
        ("callableParams(isBag)\n", "'value:nil\n"),
        ("isCollection:=x::false\nisCollection(set())\n", "<function>\nfalse\n"),
        ("isSet:=x::false\nisSet(set())\n", "<function>\nfalse\n"),
        ("isBag:=x::false\nisBag(bag())\n", "<function>\nfalse\n"),
    ]

    slice_109_robustness_failure_cases = [
        ("isCollection()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isCollection(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isSet()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isSet(set(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isBag()\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isBag(bag(),1/0)\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isCollection(missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("isSet(missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("isBag(missing)\n", "ENACT_ERR_NAME_UNBOUND"),
        ("isCollection(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("isSet(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("isBag(1/0)\n", "ENACT_ERR_DIVIDE_BY_ZERO"),
        ("isCollection(set())+1\n", "ENACT_ERR_TYPE_EXPECTED_INT"),
        ("isSet(set())==1\n", "ENACT_ERR_TYPE_EQUALITY_MISMATCH"),
        ("isBag(bag())(1)\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("map(isCollection,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(isSet,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("map(isBag,1)\n", "ENACT_ERR_TYPE_EXPECTED_LIST"),
        ("reduce(isCollection,0,list(set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(isSet,0,list(set()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("reduce(isBag,0,list(bag()))\n", "ENACT_ERR_ARITY_MISMATCH"),
        ("isCollection:=1\nisCollection(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("isSet:=1\nisSet(set())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
        ("isBag:=1\nisBag(bag())\n", "ENACT_ERR_TYPE_EXPECTED_FUNCTION"),
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
    ] + slice_008_token_cases + slice_009_token_cases + slice_010_token_cases + slice_013_token_cases + slice_017_token_cases + slice_023_token_cases + slice_024_token_cases + slice_026_token_cases + slice_027_token_cases + slice_033_token_cases + slice_034_token_cases + slice_035_token_cases + slice_039_token_cases + slice_041_token_cases + slice_042_token_cases + slice_050_token_cases

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
    ] + slice_008_boundary_success_cases + slice_009_boundary_success_cases + slice_010_boundary_success_cases + slice_011_boundary_success_cases + slice_012_boundary_success_cases + slice_013_boundary_success_cases + slice_014_boundary_success_cases + slice_015_boundary_success_cases + slice_016_boundary_success_cases + slice_017_boundary_success_cases + slice_018_boundary_success_cases + slice_019_boundary_success_cases + slice_020_boundary_success_cases + slice_021_boundary_success_cases + slice_022_boundary_success_cases + slice_023_boundary_success_cases + slice_024_boundary_success_cases + slice_025_boundary_success_cases + slice_026_boundary_success_cases + slice_027_boundary_success_cases + slice_028_boundary_success_cases + slice_029_boundary_success_cases + slice_031_boundary_success_cases + slice_032_boundary_success_cases + slice_033_boundary_success_cases + slice_034_boundary_success_cases + slice_035_boundary_success_cases + slice_036_boundary_success_cases + slice_037_boundary_success_cases + slice_038_boundary_success_cases + slice_039_boundary_success_cases + slice_040_boundary_success_cases + slice_041_boundary_success_cases + slice_042_boundary_success_cases + slice_043_boundary_success_cases + slice_044_boundary_success_cases + slice_045_boundary_success_cases + slice_046_boundary_success_cases + slice_047_boundary_success_cases + slice_048_boundary_success_cases + slice_049_boundary_success_cases + slice_050_boundary_success_cases + slice_051_boundary_success_cases + slice_052_boundary_success_cases + slice_053_boundary_success_cases + slice_054_boundary_success_cases + slice_055_boundary_success_cases + slice_056_boundary_success_cases + slice_057_boundary_success_cases + slice_058_boundary_success_cases + slice_059_boundary_success_cases + slice_060_boundary_success_cases + slice_061_boundary_success_cases + slice_062_boundary_success_cases + slice_063_boundary_success_cases + slice_064_boundary_success_cases + slice_065_boundary_success_cases + slice_066_boundary_success_cases + slice_067_boundary_success_cases + slice_068_boundary_success_cases + slice_069_boundary_success_cases + slice_070_boundary_success_cases + slice_071_boundary_success_cases + slice_072_boundary_success_cases + slice_073_boundary_success_cases + slice_074_boundary_success_cases + slice_075_boundary_success_cases + slice_076_boundary_success_cases + slice_077_boundary_success_cases + slice_078_boundary_success_cases + slice_079_boundary_success_cases + slice_080_boundary_success_cases + slice_081_boundary_success_cases + slice_082_boundary_success_cases + slice_083_boundary_success_cases + slice_084_boundary_success_cases + slice_085_boundary_success_cases + slice_086_boundary_success_cases + slice_087_boundary_success_cases + slice_088_boundary_success_cases + slice_089_boundary_success_cases + slice_090_boundary_success_cases + slice_091_boundary_success_cases + slice_092_boundary_success_cases + slice_093_boundary_success_cases + slice_094_boundary_success_cases + slice_095_boundary_success_cases + slice_096_boundary_success_cases + slice_097_boundary_success_cases + slice_098_boundary_success_cases + slice_099_boundary_success_cases + slice_100_boundary_success_cases + slice_101_boundary_success_cases + slice_102_boundary_success_cases + slice_103_boundary_success_cases + slice_104_boundary_success_cases + slice_105_boundary_success_cases + slice_106_boundary_success_cases + slice_107_boundary_success_cases + slice_108_boundary_success_cases + slice_109_boundary_success_cases

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
    ] + slice_008_robustness_failure_cases + slice_009_robustness_failure_cases + slice_010_robustness_failure_cases + slice_011_robustness_failure_cases + slice_012_robustness_failure_cases + slice_013_robustness_failure_cases + slice_014_robustness_failure_cases + slice_015_robustness_failure_cases + slice_016_robustness_failure_cases + slice_017_robustness_failure_cases + slice_018_robustness_failure_cases + slice_019_robustness_failure_cases + slice_020_robustness_failure_cases + slice_021_robustness_failure_cases + slice_022_robustness_failure_cases + slice_023_robustness_failure_cases + slice_024_robustness_failure_cases + slice_025_robustness_failure_cases + slice_026_robustness_failure_cases + slice_027_robustness_failure_cases + slice_028_robustness_failure_cases + slice_029_robustness_failure_cases + slice_031_robustness_failure_cases + slice_032_robustness_failure_cases + slice_033_robustness_failure_cases + slice_034_robustness_failure_cases + slice_035_robustness_failure_cases + slice_036_robustness_failure_cases + slice_037_robustness_failure_cases + slice_038_robustness_failure_cases + slice_039_robustness_failure_cases + slice_040_robustness_failure_cases + slice_041_robustness_failure_cases + slice_042_robustness_failure_cases + slice_043_robustness_failure_cases + slice_044_robustness_failure_cases + slice_045_robustness_failure_cases + slice_046_robustness_failure_cases + slice_047_robustness_failure_cases + slice_048_robustness_failure_cases + slice_049_robustness_failure_cases + slice_050_robustness_failure_cases + slice_051_robustness_failure_cases + slice_052_robustness_failure_cases + slice_053_robustness_failure_cases + slice_054_robustness_failure_cases + slice_055_robustness_failure_cases + slice_056_robustness_failure_cases + slice_057_robustness_failure_cases + slice_058_robustness_failure_cases + slice_059_robustness_failure_cases + slice_060_robustness_failure_cases + slice_061_robustness_failure_cases + slice_062_robustness_failure_cases + slice_063_robustness_failure_cases + slice_064_robustness_failure_cases + slice_065_robustness_failure_cases + slice_066_robustness_failure_cases + slice_067_robustness_failure_cases + slice_068_robustness_failure_cases + slice_069_robustness_failure_cases + slice_070_robustness_failure_cases + slice_071_robustness_failure_cases + slice_072_robustness_failure_cases + slice_073_robustness_failure_cases + slice_074_robustness_failure_cases + slice_075_robustness_failure_cases + slice_076_robustness_failure_cases + slice_077_robustness_failure_cases + slice_078_robustness_failure_cases + slice_079_robustness_failure_cases + slice_080_robustness_failure_cases + slice_081_robustness_failure_cases + slice_082_robustness_failure_cases + slice_083_robustness_failure_cases + slice_084_robustness_failure_cases + slice_085_robustness_failure_cases + slice_086_robustness_failure_cases + slice_087_robustness_failure_cases + slice_088_robustness_failure_cases + slice_089_robustness_failure_cases + slice_090_robustness_failure_cases + slice_091_robustness_failure_cases + slice_092_robustness_failure_cases + slice_093_robustness_failure_cases + slice_094_robustness_failure_cases + slice_095_robustness_failure_cases + slice_096_robustness_failure_cases + slice_097_robustness_failure_cases + slice_098_robustness_failure_cases + slice_099_robustness_failure_cases + slice_100_robustness_failure_cases + slice_101_robustness_failure_cases + slice_102_robustness_failure_cases + slice_103_robustness_failure_cases + slice_104_robustness_failure_cases + slice_105_robustness_failure_cases + slice_106_robustness_failure_cases + slice_107_robustness_failure_cases + slice_108_robustness_failure_cases + slice_109_robustness_failure_cases

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
    print(f"slice 045 boundary regression checks: {len(slice_045_boundary_success_cases)}")
    print(f"slice 045 robustness regression checks: {len(slice_045_robustness_failure_cases)}")
    print(f"slice 046 boundary regression checks: {len(slice_046_boundary_success_cases)}")
    print(f"slice 046 robustness regression checks: {len(slice_046_robustness_failure_cases)}")
    print(f"slice 047 boundary regression checks: {len(slice_047_boundary_success_cases)}")
    print(f"slice 047 robustness regression checks: {len(slice_047_robustness_failure_cases)}")
    print(f"slice 048 boundary regression checks: {len(slice_048_boundary_success_cases)}")
    print(f"slice 048 robustness regression checks: {len(slice_048_robustness_failure_cases)}")
    print(f"slice 049 boundary regression checks: {len(slice_049_boundary_success_cases)}")
    print(f"slice 049 robustness regression checks: {len(slice_049_robustness_failure_cases)}")
    print(f"slice 050 boundary regression checks: {len(slice_050_token_cases) + len(slice_050_boundary_success_cases)}")
    print(f"slice 050 robustness regression checks: {len(slice_050_robustness_failure_cases)}")
    print(f"slice 051 boundary regression checks: {len(slice_051_boundary_success_cases)}")
    print(f"slice 051 robustness regression checks: {len(slice_051_robustness_failure_cases)}")
    print(f"slice 052 boundary regression checks: {len(slice_052_boundary_success_cases)}")
    print(f"slice 052 robustness regression checks: {len(slice_052_robustness_failure_cases)}")
    print(f"slice 053 boundary regression checks: {len(slice_053_boundary_success_cases)}")
    print(f"slice 053 robustness regression checks: {len(slice_053_robustness_failure_cases)}")
    print(f"slice 054 boundary regression checks: {len(slice_054_boundary_success_cases)}")
    print(f"slice 054 robustness regression checks: {len(slice_054_robustness_failure_cases)}")
    print(f"slice 055 boundary regression checks: {len(slice_055_boundary_success_cases)}")
    print(f"slice 055 robustness regression checks: {len(slice_055_robustness_failure_cases)}")
    print(f"slice 056 boundary regression checks: {len(slice_056_boundary_success_cases)}")
    print(f"slice 056 robustness regression checks: {len(slice_056_robustness_failure_cases)}")
    print(f"slice 057 boundary regression checks: {len(slice_057_boundary_success_cases)}")
    print(f"slice 057 robustness regression checks: {len(slice_057_robustness_failure_cases)}")
    print(f"slice 058 boundary regression checks: {len(slice_058_boundary_success_cases)}")
    print(f"slice 058 robustness regression checks: {len(slice_058_robustness_failure_cases)}")
    print(f"slice 059 boundary regression checks: {len(slice_059_boundary_success_cases)}")
    print(f"slice 059 robustness regression checks: {len(slice_059_robustness_failure_cases)}")
    print(f"slice 060 boundary regression checks: {len(slice_060_boundary_success_cases)}")
    print(f"slice 060 robustness regression checks: {len(slice_060_robustness_failure_cases)}")
    print(f"slice 061 boundary regression checks: {len(slice_061_boundary_success_cases)}")
    print(f"slice 061 robustness regression checks: {len(slice_061_robustness_failure_cases)}")
    print(f"slice 062 boundary regression checks: {len(slice_062_boundary_success_cases)}")
    print(f"slice 062 robustness regression checks: {len(slice_062_robustness_failure_cases)}")
    print(f"slice 063 boundary regression checks: {len(slice_063_boundary_success_cases)}")
    print(f"slice 063 robustness regression checks: {len(slice_063_robustness_failure_cases)}")
    print(f"slice 064 boundary regression checks: {len(slice_064_boundary_success_cases)}")
    print(f"slice 064 robustness regression checks: {len(slice_064_robustness_failure_cases)}")
    print(f"slice 065 boundary regression checks: {len(slice_065_boundary_success_cases)}")
    print(f"slice 065 robustness regression checks: {len(slice_065_robustness_failure_cases)}")
    print(f"slice 066 boundary regression checks: {len(slice_066_boundary_success_cases)}")
    print(f"slice 066 robustness regression checks: {len(slice_066_robustness_failure_cases)}")
    print(f"slice 067 boundary regression checks: {len(slice_067_boundary_success_cases)}")
    print(f"slice 067 robustness regression checks: {len(slice_067_robustness_failure_cases)}")
    print(f"slice 068 boundary regression checks: {len(slice_068_boundary_success_cases)}")
    print(f"slice 068 robustness regression checks: {len(slice_068_robustness_failure_cases)}")
    print(f"slice 069 boundary regression checks: {len(slice_069_boundary_success_cases)}")
    print(f"slice 069 robustness regression checks: {len(slice_069_robustness_failure_cases)}")
    print(f"slice 070 boundary regression checks: {len(slice_070_boundary_success_cases)}")
    print(f"slice 070 robustness regression checks: {len(slice_070_robustness_failure_cases)}")
    print(f"slice 071 boundary regression checks: {len(slice_071_boundary_success_cases)}")
    print(f"slice 071 robustness regression checks: {len(slice_071_robustness_failure_cases)}")
    print(f"slice 072 boundary regression checks: {len(slice_072_boundary_success_cases)}")
    print(f"slice 072 robustness regression checks: {len(slice_072_robustness_failure_cases)}")
    print(f"slice 073 boundary regression checks: {len(slice_073_boundary_success_cases)}")
    print(f"slice 073 robustness regression checks: {len(slice_073_robustness_failure_cases)}")
    print(f"slice 074 boundary regression checks: {len(slice_074_boundary_success_cases)}")
    print(f"slice 074 robustness regression checks: {len(slice_074_robustness_failure_cases)}")
    print(f"slice 075 boundary regression checks: {len(slice_075_boundary_success_cases)}")
    print(f"slice 075 robustness regression checks: {len(slice_075_robustness_failure_cases)}")
    print(f"slice 076 boundary regression checks: {len(slice_076_boundary_success_cases)}")
    print(f"slice 076 robustness regression checks: {len(slice_076_robustness_failure_cases)}")
    print(f"slice 077 boundary regression checks: {len(slice_077_boundary_success_cases)}")
    print(f"slice 077 robustness regression checks: {len(slice_077_robustness_failure_cases)}")
    print(f"slice 078 boundary regression checks: {len(slice_078_boundary_success_cases)}")
    print(f"slice 078 robustness regression checks: {len(slice_078_robustness_failure_cases)}")
    print(f"slice 079 boundary regression checks: {len(slice_079_boundary_success_cases)}")
    print(f"slice 079 robustness regression checks: {len(slice_079_robustness_failure_cases)}")
    print(f"slice 080 boundary regression checks: {len(slice_080_boundary_success_cases)}")
    print(f"slice 080 robustness regression checks: {len(slice_080_robustness_failure_cases)}")
    print(f"slice 081 boundary regression checks: {len(slice_081_boundary_success_cases)}")
    print(f"slice 081 robustness regression checks: {len(slice_081_robustness_failure_cases)}")
    print(f"slice 082 boundary regression checks: {len(slice_082_boundary_success_cases)}")
    print(f"slice 082 robustness regression checks: {len(slice_082_robustness_failure_cases)}")
    print(f"slice 083 boundary regression checks: {len(slice_083_boundary_success_cases)}")
    print(f"slice 083 robustness regression checks: {len(slice_083_robustness_failure_cases)}")
    print(f"slice 084 boundary regression checks: {len(slice_084_boundary_success_cases)}")
    print(f"slice 084 robustness regression checks: {len(slice_084_robustness_failure_cases)}")
    print(f"slice 085 boundary regression checks: {len(slice_085_boundary_success_cases)}")
    print(f"slice 085 robustness regression checks: {len(slice_085_robustness_failure_cases)}")
    print(f"slice 086 boundary regression checks: {len(slice_086_boundary_success_cases)}")
    print(f"slice 086 robustness regression checks: {len(slice_086_robustness_failure_cases)}")
    print(f"slice 087 boundary regression checks: {len(slice_087_boundary_success_cases)}")
    print(f"slice 087 robustness regression checks: {len(slice_087_robustness_failure_cases)}")
    print(f"slice 088 boundary regression checks: {len(slice_088_boundary_success_cases)}")
    print(f"slice 088 robustness regression checks: {len(slice_088_robustness_failure_cases)}")
    print(f"slice 089 boundary regression checks: {len(slice_089_boundary_success_cases)}")
    print(f"slice 089 robustness regression checks: {len(slice_089_robustness_failure_cases)}")
    print(f"slice 090 boundary regression checks: {len(slice_090_boundary_success_cases)}")
    print(f"slice 090 robustness regression checks: {len(slice_090_robustness_failure_cases)}")
    print(f"slice 091 boundary regression checks: {len(slice_091_boundary_success_cases)}")
    print(f"slice 091 robustness regression checks: {len(slice_091_robustness_failure_cases)}")
    print(f"slice 092 boundary regression checks: {len(slice_092_boundary_success_cases)}")
    print(f"slice 092 robustness regression checks: {len(slice_092_robustness_failure_cases)}")
    print(f"slice 093 boundary regression checks: {len(slice_093_boundary_success_cases)}")
    print(f"slice 093 robustness regression checks: {len(slice_093_robustness_failure_cases)}")
    print(f"slice 094 boundary regression checks: {len(slice_094_boundary_success_cases)}")
    print(f"slice 094 robustness regression checks: {len(slice_094_robustness_failure_cases)}")
    print(f"slice 095 boundary regression checks: {len(slice_095_boundary_success_cases)}")
    print(f"slice 095 robustness regression checks: {len(slice_095_robustness_failure_cases)}")
    print(f"slice 096 boundary regression checks: {len(slice_096_boundary_success_cases)}")
    print(f"slice 096 robustness regression checks: {len(slice_096_robustness_failure_cases)}")
    print(f"slice 097 boundary regression checks: {len(slice_097_boundary_success_cases)}")
    print(f"slice 097 robustness regression checks: {len(slice_097_robustness_failure_cases)}")
    print(f"slice 098 boundary regression checks: {len(slice_098_boundary_success_cases)}")
    print(f"slice 098 robustness regression checks: {len(slice_098_robustness_failure_cases)}")
    print(f"slice 099 boundary regression checks: {len(slice_099_boundary_success_cases)}")
    print(f"slice 099 robustness regression checks: {len(slice_099_robustness_failure_cases)}")
    print(f"slice 100 boundary regression checks: {len(slice_100_boundary_success_cases)}")
    print(f"slice 100 robustness regression checks: {len(slice_100_robustness_failure_cases)}")
    print(f"slice 101 boundary regression checks: {len(slice_101_boundary_success_cases)}")
    print(f"slice 101 robustness regression checks: {len(slice_101_robustness_failure_cases)}")
    print(f"slice 102 boundary regression checks: {len(slice_102_boundary_success_cases)}")
    print(f"slice 102 robustness regression checks: {len(slice_102_robustness_failure_cases)}")
    print(f"slice 103 boundary regression checks: {len(slice_103_boundary_success_cases)}")
    print(f"slice 103 robustness regression checks: {len(slice_103_robustness_failure_cases)}")
    print(f"slice 104 boundary regression checks: {len(slice_104_boundary_success_cases)}")
    print(f"slice 104 robustness regression checks: {len(slice_104_robustness_failure_cases)}")
    print(f"slice 105 boundary regression checks: {len(slice_105_boundary_success_cases)}")
    print(f"slice 105 robustness regression checks: {len(slice_105_robustness_failure_cases)}")
    print(f"slice 106 boundary regression checks: {len(slice_106_boundary_success_cases)}")
    print(f"slice 106 robustness regression checks: {len(slice_106_robustness_failure_cases)}")
    print(f"slice 107 boundary regression checks: {len(slice_107_boundary_success_cases)}")
    print(f"slice 107 robustness regression checks: {len(slice_107_robustness_failure_cases)}")
    print(f"slice 108 boundary regression checks: {len(slice_108_boundary_success_cases)}")
    print(f"slice 108 robustness regression checks: {len(slice_108_robustness_failure_cases)}")
    print(f"slice 109 boundary regression checks: {len(slice_109_boundary_success_cases)}")
    print(f"slice 109 robustness regression checks: {len(slice_109_robustness_failure_cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
