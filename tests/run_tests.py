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


def main() -> int:
    if not BIN.exists():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 2

    long_comment = "%" + ("comment" * 240) + "\n(8+2)/5."
    huge_integer = ("9" * 512) + "."
    long_identifier = ("abc_" * 80) + "z."

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
        ("f().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f():=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(1):=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x):=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(f)(x):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f((x)):=x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x):=.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f(x):=x; f().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("f().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f():=1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("()::1.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x,)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(,x)::x.", "ENACT_ERR_PARSE_UNMATCHED_PAREN"),
        ("(x,x)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("(x,1)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("((x),y)::x.", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
        ("f:=x::x; f().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("f().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("hd().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
        ("().", "ENACT_ERR_PARSE_UNEXPECTED_TOKEN"),
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
    ] + slice_008_token_cases + slice_009_token_cases + slice_010_token_cases + slice_013_token_cases + slice_017_token_cases

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
    ] + slice_008_boundary_success_cases + slice_009_boundary_success_cases + slice_010_boundary_success_cases + slice_011_boundary_success_cases + slice_012_boundary_success_cases + slice_013_boundary_success_cases + slice_014_boundary_success_cases + slice_015_boundary_success_cases + slice_016_boundary_success_cases + slice_017_boundary_success_cases + slice_018_boundary_success_cases + slice_019_boundary_success_cases + slice_020_boundary_success_cases + slice_021_boundary_success_cases + slice_022_boundary_success_cases

    failure_cases = [
        ("", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("1", "ENACT_ERR_PARSE_MISSING_DOT"),
        ("% comment only\n", "ENACT_ERR_PARSE_MISSING_DOT"),
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
    ] + slice_008_robustness_failure_cases + slice_009_robustness_failure_cases + slice_010_robustness_failure_cases + slice_011_robustness_failure_cases + slice_012_robustness_failure_cases + slice_013_robustness_failure_cases + slice_014_robustness_failure_cases + slice_015_robustness_failure_cases + slice_016_robustness_failure_cases + slice_017_robustness_failure_cases + slice_018_robustness_failure_cases + slice_019_robustness_failure_cases + slice_020_robustness_failure_cases + slice_021_robustness_failure_cases + slice_022_robustness_failure_cases

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

    total = len(token_cases) + len(token_failure_cases) + len(success_cases) + len(failure_cases)
    total += 1
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
