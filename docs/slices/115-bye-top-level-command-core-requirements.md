# Slice 115: bye Top-Level Command Core Requirements

## Goal

Add the PRD-listed `bye` utility as a top-level session command that terminates script or REPL evaluation cleanly.

## Functional Requirements

- `bye` shall be recognized only as an exact top-level command name.
- `bye` shall accept ordinary top-level terminators:
  - `bye.`
  - `bye` followed by a top-level newline terminator
- The command shall produce no result value and shall not invoke the script result callback.
- In batch/script evaluation, `bye` shall stop evaluating later chunks in the same script.
- If `bye` appears inside a loaded file, evaluation of the loaded file and the outer script shall both stop.
- In the TTY REPL, `bye` shall terminate the current session with exit status `0` when no prior line failed.
- Names that merely start with `bye`, such as `byebye` or `bye_value`, shall remain ordinary identifiers.

## Boundary Requirements

- `bye` shall not be installed as a builtin.
- `enact_session_eval_text` shall remain expression-only and shall not execute `bye` as a command.
- The session API shall expose whether a session has requested exit so REPL-style callers can stop reading input.

## Error Requirements

- `bye` without a dot or newline terminator at end-of-file shall fail with `ENACT_ERR_PARSE_MISSING_DOT`.
- `bye` followed by any non-terminator token shall fail with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.
- Malformed `bye` commands shall not set the session exit request.

## Non-Goals

- Do not add a lexer token, AST node, runtime value, or evaluator branch for `bye`.
- Do not add `ask`, `cells`, or `maxcells`.
- Do not add process-level exit calls inside `api.c`; callers remain responsible for process control.
