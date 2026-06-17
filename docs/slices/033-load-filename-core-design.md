# Slice 033: load "filename" Core Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/033-load-filename-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/033-load-filename-core-requirements.md)

Prerequisite design: [docs/slices/031-script-batch-session-execution-core-design.md](/home/tprover/2606_enact_auto/docs/slices/031-script-batch-session-execution-core-design.md)

## 1. Design Summary

Implement `load` as a session/script top-level command.

The design deliberately keeps `load` out of:

- the builtin table
- runtime value kinds
- expression AST nodes
- ordinary evaluator dispatch

This lets file I/O stay at the boundary of script execution while the evaluator remains focused on expression semantics.

## 2. Lexer And Parser

Add `TOK_LOAD` and a lexer rule:

```text
"load" -> TOK_LOAD
```

The parser does not accept `TOK_LOAD` in expression positions. This reserves the word and makes expression-only attempts fail with a parser diagnostic.

Token mode prints `TOK_LOAD`, which gives regression coverage for the reserved-word decision.

## 3. Script Runner Dispatch

`enact_session_eval_script` already splits source text into top-level dot-terminated chunks.

For each chunk it now checks:

```text
if chunk starts with exact reserved word "load":
    execute load command
else:
    evaluate chunk as expression
```

The exact-word check prevents names such as `loader` from being mistaken for the command.

## 4. Load Command Parser

The command parser accepts only:

```text
load <trivia> "decoded filename" <trivia> .
```

Trivia means whitespace or `%` line comments, matching the script chunk splitter.

The filename decoder mirrors ordinary string literal escapes:

- `\\`
- `\"`
- `\n`
- `\r`
- `\t`

Malformed or unterminated filename strings fail with `ENACT_ERR_LEX_BAD_STRING`.

## 5. File Reading

`api.c` owns a private text-file reader for load commands.

The reader:

1. opens the path with `fopen(path, "rb")`
2. reads the full file into a NUL-terminated buffer
3. reports open/read failures as `ENACT_ERR_LOAD_FILE`
4. reports allocation failures as `ENACT_ERR_OUT_OF_MEMORY`

No search path or path rebasing is performed in this slice.

## 6. Nested Execution

After reading the file, the command calls:

```c
enact_session_eval_script(session, loaded_source, callback, user_data, diag)
```

This reuses:

- current session bindings
- existing script chunking
- existing result callback output
- existing stop-on-first-failure behavior

The load command itself does not call the result callback and produces no synthetic success value.

## 7. API Boundary

`enact_session_eval_text` remains expression-only.

That means:

```c
enact_session_eval_text(session, "load \"x\".")
```

fails during parsing instead of reading a file. This is intentional and preserves the builtin/top-level-command distinction.

## 8. Diagnostics

Add:

```c
ENACT_ERR_LOAD_FILE
```

with message:

```text
could not load file
```

Command syntax errors use existing parser/string diagnostics where possible. Errors from a loaded script propagate unchanged.

## 9. Test Strategy

Regression tests cover:

- token output for `load`
- `loader` remaining an ordinary identifier
- load of a trivia-only file
- load of definitions into the caller session
- script continuation after load
- nested load
- loaded string literals containing dots
- TTY load and recovery after failed load
- missing file and malformed command forms
- parse and evaluation errors propagated from loaded scripts

Unit tests cover:

- load-file diagnostic names/messages
- direct API script load
- loaded bindings persisting in the session
- expression-only eval rejecting `load`
