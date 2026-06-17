# Slice 035: OO Keyword / Parser Scaffolding Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/035-oo-keyword-parser-scaffolding-requirements.md](/home/tprover/2606_enact_auto/docs/slices/035-oo-keyword-parser-scaffolding-requirements.md)

Prerequisite design: [docs/slices/034-quoted-atoms-symbol-core-design.md](/home/tprover/2606_enact_auto/docs/slices/034-quoted-atoms-symbol-core-design.md)

## 1. Design Summary

Reserve the first object-oriented keywords in the lexer and token dumper:

```c
TOK_CLASS
TOK_NEW
TOK_WITH
```

Do not add grammar productions or evaluator behavior yet. Unsupported object-oriented forms should fail through the existing parser diagnostic path.

## 2. Lexer

Add exact keyword rules before the identifier rule:

```text
"class" -> TOK_CLASS
"new"   -> TOK_NEW
"with"  -> TOK_WITH
```

The existing identifier rule still recognizes names such as:

```text
classy
newer
within
self
```

Quoted atoms continue to use the quoted-atom rule, so:

```text
'class
'new
'with
```

remain `TOK_ATOM_LITERAL` tokens rather than OO keyword tokens.

## 3. Parser

Declare the new tokens in `enact.y`.

No parser productions consume the tokens in this slice. Therefore:

- `class Node < Object.` reports `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `new Object.` reports `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `obj with x:=1.` reports `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`

This is intentional scaffolding. Later slices can add grammar one feature at a time while preserving today's rejection behavior as the before-state.

## 4. `self`

Do not reserve `self` globally.

The current functional core already allows `self` as a normal identifier, and recursive/fixed function tests rely on that. Method support can later bind the ordinary identifier `self` in a method-call environment.

This avoids a needless compatibility break before object method semantics exist.

## 5. Newline Terminator

Do not change expression termination in this slice.

Newline-as-terminator is a good REPL ergonomics candidate, but it crosses several boundaries:

- parser input currently requires `expr TOK_DOT`
- non-TTY script execution splits chunks at top-level dots
- `load` delegates to the same script execution path
- future dot-member syntax needs careful interaction with dot termination

Recommended follow-up:

```text
Slice 036 candidate: Top-Level Newline Expression Terminator
```

That slice should treat newlines as terminators only at top level and only where a complete expression or command can end.

## 6. Token Dumping

Extend `scan.c` so token mode prints:

```text
TOK_CLASS
TOK_NEW
TOK_WITH
```

This gives stable regression coverage for the reservation decision.

## 7. Test Strategy

Regression tests cover:

- token output for `class`, `new`, and `with`
- similar identifiers staying ordinary identifiers
- quoted atom payloads matching the new keywords
- successful evaluation of similar identifiers and `self`
- parser rejection for class/new/with forms not yet implemented
- assignment attempts to reserved OO keywords

No unit tests are required because this slice does not add new runtime structures or public C APIs.
