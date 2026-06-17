# Slice 033: load "filename" Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/031-script-batch-session-execution-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/031-script-batch-session-execution-core-requirements.md)

## 1. Slice Goal

This slice adds the first file-loading command:

```text
load "filename".
```

The command reads an ENACT script file and executes it against the current evaluation session.

## 2. Source Basis

The PRD requires:

- a REPL plus file loader
- `load "filename"` for batch execution of ENACT scripts
- `load` as a reserved word in the operator/command layer

Slices 030 and 031 already provide the current-session environment and multi-expression script runner needed for file loading.

## 3. In Scope

This slice includes:

- reserving `load` as a lexer token
- recognizing `load "filename".` as a top-level script/session command
- reading the named file as text
- executing the file with `enact_session_eval_script`
- preserving the caller's session environment
- forwarding loaded script results through the current script callback or REPL printer
- nested loads using the same command mechanism
- regression and unit tests for CLI, TTY, and API paths

## 4. Top-Level Command Boundary

`load` is not a builtin function.

This slice intentionally does not install `load` in the builtin table and does not create an AST node for it. `load` is handled by the session/script execution layer before ordinary expression parsing.

Consequences:

- `load "x".` works through `enact_session_eval_script`
- `enact_session_eval_text(session, "load \"x\".")` fails as an expression parse
- `load` cannot be assigned as an ordinary identifier
- `load` is not first-class, cannot be partially applied, and cannot be passed to `map`, `filter`, or other higher-order functions

## 5. Out Of Scope

This slice explicitly excludes:

- load-cycle detection
- include search paths
- resolving relative paths against the loading file's directory
- module systems or import namespaces
- suppressing loaded script expression output
- loading binary files
- sandbox or permissions policy

## 6. Path Resolution

The filename is interpreted as an ordinary decoded string literal and passed to the host file API.

Relative paths are resolved by the host process current working directory.

## 7. User-Facing Behavior

Accepted examples:

- `load "defs.en".`
- `load "defs.en". loaded_x+1.`
- a loaded file may define values that later expressions in the current session can use
- a loaded file may itself contain `load "other.en".`
- a trivia-only loaded file succeeds and produces no value

Error examples:

- `load.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `load 1.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `load("x").` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `load "missing.en".` => `ENACT_ERR_LOAD_FILE`
- `load "bad\q".` => `ENACT_ERR_LEX_BAD_STRING`
- `load "unterminated.` => `ENACT_ERR_LEX_BAD_STRING`
- a missing dot inside the loaded file propagates as `ENACT_ERR_PARSE_MISSING_DOT`
- an evaluation failure inside the loaded file propagates the underlying evaluation diagnostic

## 8. Execution Semantics

When script execution sees a top-level chunk beginning with the exact reserved word `load`:

1. require command trivia after `load`
2. require a string literal filename
3. require the normal terminating dot
4. read the file into memory
5. execute the file source with the same `EnactSession`
6. forward every loaded expression result through the caller's callback
7. produce no separate value for the load command itself

If loading or script execution fails, the command fails immediately and later script chunks are not executed.

As with existing script execution, successful chunks before a later failure may leave bindings in the session.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- tokenization of `load`
- similarly named identifiers such as `loader`
- trivia-only loaded files
- loaded definitions visible after the command
- loaded functions and calls
- top-level script continuation after load
- nested load
- strings containing dots inside loaded scripts
- REPL/TTY load behavior
- proof that `load` produces no value of its own

## 10. Robustness Requirements

The regression suite shall include:

- missing filename
- non-string filename
- parenthesized call-like syntax
- missing file
- invalid filename string literal escape
- unterminated filename string literal
- parse failure inside the loaded file
- evaluation failure inside the loaded file
- assignment to `load`
- attempting to use `load` inside an ordinary expression sequence
- REPL recovery after a failed load

## 11. Acceptance Criteria

This slice is accepted when:

- `load` is reserved and tokenized as `TOK_LOAD`
- `load` is not present in the builtin table
- `load "filename".` executes files through the session script runner
- loaded bindings persist in the current session
- nested loads work for acyclic scripts
- expression-only evaluation does not execute `load`
- all regression and unit tests pass
