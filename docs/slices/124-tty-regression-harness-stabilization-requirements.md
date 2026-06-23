# Slice 124: TTY Regression Harness Stabilization / bye TTY Exit Hardening Requirements

## Goal

Stabilize the functional TTY regression harness around `bye` termination so PTY timing does not make otherwise valid REPL behavior flaky.

## Functional Requirements

- TTY exit tests shall drive input in the same line-oriented shape as the interactive REPL.
- TTY output comparison shall normalize ordinary terminal newline variants:
  - LF
  - CRLF
  - CR
- TTY exit tests shall verify both:
  - process termination
  - exit status
- TTY exit tests may also verify ordered output fragments produced before the terminating `bye`.
- A successful `bye` in TTY mode shall still exit with status `0` when no earlier line failed.
- If an earlier TTY line failed, a later valid `bye` shall still terminate the process while preserving the prior non-zero exit status.

## Regression Scope

Boundary checks cover:

- bare newline-terminated `bye`
- dot-terminated `bye.`
- expression before newline-terminated `bye`
- expression before dot-terminated source followed by newline-terminated `bye`
- carriage-return terminated TTY input

Robustness checks cover:

- unbound-name failure followed by valid `bye`
- malformed `bye` followed by valid `bye`

## Non-Goals

- Do not change `bye` into a builtin.
- Do not add lexer, parser, AST, or evaluator support for `bye`.
- Do not change non-TTY script semantics.
- Do not make EOF an implicit top-level terminator.
- Do not add prompt rendering or interactive line editing.
