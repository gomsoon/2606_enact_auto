# Slice 031: Script / Batch Session Execution Core Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/031-script-batch-session-execution-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/031-script-batch-session-execution-core-requirements.md)

Prerequisite design: [docs/slices/030-stateful-repl-session-core-design.md](/home/tprover/2606_enact_auto/docs/slices/030-stateful-repl-session-core-design.md)

## 1. Design Summary

The parser remains a single-expression parser:

```text
input ::= expr "."
```

Script execution is implemented above the parser by splitting source text into top-level dot-terminated chunks and feeding each chunk through `enact_session_eval_text`.

This keeps the grammar stable and makes the later `load` feature reuse the same session script runner.

## 2. API Design

The public API gains:

```c
typedef int (*EnactScriptResultCallback)(const EnactResult *result, void *user_data);

int enact_session_eval_script(
    EnactSession *session,
    const char *source,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag);
```

The callback receives each successful top-level result. The API releases the result after the callback returns, so callers that need to retain values must copy them.

A null callback is accepted and discards successful values.

## 3. Chunking Design

`api.c` uses private helpers to find the next script chunk:

- skip leading whitespace and `%` line comments
- scan until a top-level `.`
- ignore dots while inside a double-quoted string
- ignore dots while inside a `%` line comment
- ignore dots while inside balanced parentheses
- if EOF arrives with non-trivia pending, return the trailing text as one final chunk

Returning a final unterminated chunk lets the existing parser produce diagnostics such as:

- `ENACT_ERR_PARSE_MISSING_DOT`
- `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `ENACT_ERR_LEX_BAD_STRING`

The splitter is intentionally not a second parser. It only finds safe top-level boundaries for the current grammar.

## 4. Evaluation Flow

`enact_session_eval_script` runs:

1. validate the session
2. find the next chunk
3. copy the chunk into a NUL-terminated buffer
4. call `enact_session_eval_text`
5. on success, invoke the callback if present
6. free the result
7. repeat until no chunks remain

On the first failure, it copies the failing result diagnostic into the caller-provided `EnactDiag` and stops.

## 5. CLI Integration

Non-TTY normal execution now initializes one `EnactSession` and calls `enact_session_eval_script`.

The CLI callback prints each successful result using the existing value printer.

TTY REPL execution keeps the Slice 030 line-by-line session behavior.

`--tokens` mode keeps the previous whole-input token dump behavior.

## 6. Error Behavior

Script execution stops at the first failing chunk.

Successful earlier chunks are not rolled back. This matches the session model and avoids introducing transaction semantics before the language has a broader error recovery design.

If a callback rejects a successful result, the API reports `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`. This is an internal caller error path rather than a language diagnostic.

## 7. Test Strategy

Functional regression tests cover:

- assignment and reassignment across chunks
- functions, recursion, and partial application across chunks
- strings containing dots
- comments containing dots
- tuple-like lists and higher-order list builtins
- builtins in script mode
- trailing comments
- missing names, malformed chunks, type errors, missing final dots, arity errors, and shadowed builtin failures

Unit tests cover:

- direct script API callback capture
- script bindings remaining visible after a script run
- trivia-only script input
- callback rejection
- null session rejection
- script failure diagnostics
- session survival after script failure

Coverage remains reported with the existing handwritten-source flow.
