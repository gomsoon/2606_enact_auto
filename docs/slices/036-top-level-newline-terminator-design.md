# Slice 036: Top-Level Newline Expression Terminator Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/036-top-level-newline-terminator-requirements.md](/home/tprover/2606_enact_auto/docs/slices/036-top-level-newline-terminator-requirements.md)

Prerequisite design: [docs/slices/031-script-batch-session-execution-core-design.md](/home/tprover/2606_enact_auto/docs/slices/031-script-batch-session-execution-core-design.md)

## 1. Design Summary

Keep the parser as a single-expression parser:

```text
input ::= expr "."
```

Add newline termination in the script/session chunking layer. When a top-level newline terminates a chunk, the script runner copies the chunk and appends a synthetic `.` before calling `enact_session_eval_text`.

This makes CLI, REPL, script, and `load` execution more ergonomic without destabilizing the grammar.

## 2. Chunking Rule

`enact_next_script_chunk` now recognizes two top-level terminators:

- `.`
- `\n`

Newline is a terminator only when:

- not inside a double-quoted string
- not inside parentheses
- at top-level after any trailing line comment

The splitter still skips leading whitespace and comment-only lines before starting a chunk.

## 3. Normalization

For dot-terminated chunks, the copied text is unchanged:

```text
1+2.
```

For newline-terminated chunks, the copied text includes the newline and appends a dot:

```text
1+2
.
```

Including the original newline matters for line comments:

```text
1 % comment
.
```

Without the newline, the synthetic dot would be consumed by the comment.

## 4. Load Commands

`load` remains a top-level script command.

Because newline-terminated chunks are normalized before load-command parsing, both forms work:

```text
load "defs.en".
load "defs.en"
```

Loaded files are evaluated through the same `enact_session_eval_script` path, so they may also use newline terminators.

## 5. Redundant Dot Compatibility

Some existing scripts write a dot on the line after an expression with a trailing comment:

```text
x:=1 % comment
.
```

After newline termination, the first line is already complete. To preserve that style, script execution skips one standalone dot chunk immediately after a newline-terminated chunk.

A standalone dot at the beginning of input still reports the existing parser error.

## 6. Parser And Lexer

No lexer token is added for newline.

No parser productions change in this slice.

Token dump mode continues to treat newline as whitespace. This keeps token-mode output focused on lexical tokens rather than script execution boundaries.

## 7. EOF Behavior

EOF without a final dot or newline remains unterminated.

For example:

```text
x:=1
x
```

evaluates the first line and then reports `ENACT_ERR_PARSE_MISSING_DOT` for the trailing `x`.

This conservative rule keeps accidental truncated input visible and can be revisited later if EOF-as-terminator becomes desirable.

## 8. TTY Behavior

TTY execution already reads one line at a time and calls `enact_session_eval_script`.

After this slice, pressing Enter sends a newline-terminated chunk, so ordinary REPL input no longer requires a trailing dot:

```text
1+2
```

prints:

```text
3
```

## 9. Limitations

This slice does not implement implicit continuation for top-level infix operators.

Therefore:

```text
1+
2
```

fails on the first line. Users can write multi-line expressions inside parentheses:

```text
(1+
2)
```

## 10. Test Strategy

Regression tests cover:

- one-line newline-terminated expression
- multiple newline chunks
- mixed dot/newline chunks
- comments with dots before newline
- redundant standalone dot compatibility after newline-terminated chunks
- tuple/list syntax across newlines inside parentheses
- function definition and call
- `load` without dot and loaded newline-only source
- TTY Enter-key evaluation and recovery
- incomplete expression, missing EOF terminator, unmatched parenthesis, bad string, and type failures

Unit tests cover:

- direct `enact_session_eval_script` with newline-only chunks
