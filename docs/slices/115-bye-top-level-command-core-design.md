# Slice 115: bye Top-Level Command Core Design

Related requirements: [docs/slices/115-bye-top-level-command-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/115-bye-top-level-command-core-requirements.md)

## Overview

`bye` is implemented beside the existing `load` command in `src/api.c`, at the session/script boundary. It is deliberately not a builtin because it controls evaluation flow instead of producing a normal ENACT value.

The command path remains outside:

- the lexer keyword table
- the parser grammar
- expression AST nodes
- evaluator dispatch
- the builtin table

This keeps ordinary expression evaluation focused on values and leaves process/session control in the host-facing API layer.

## Command Recognition

The script evaluator checks each top-level chunk with an exact command-name helper. `bye` is recognized only when the command name is not followed by an identifier character.

That means:

- `bye` is a command candidate.
- `bye.` is a command candidate.
- `bye()` is a malformed command.
- `bye:=1` is a malformed command.
- `byebye` remains an identifier.
- `bye_value` remains an identifier.

## Command Syntax

The command parser accepts:

```text
bye <trivia> .
```

The newline terminator slice already appends a synthetic dot to newline-terminated chunks before command parsing, so `bye\n` follows the same internal syntax as `bye.`.

Trivia uses the existing script trivia skipper: spaces, tabs, carriage returns, newlines, and `%` comments.

## Session Exit State

`EnactSession` gains an `exit_requested` flag. A successful `bye` command sets that flag and returns success without invoking the result callback.

`enact_session_eval_script` stops before evaluating any later chunk once the flag is set. Because loaded files use the same session and call back into `enact_session_eval_script`, a `bye` inside a loaded file naturally propagates to the outer script.

The public helper:

```c
int enact_session_exit_requested(const EnactSession *session);
```

lets `main.c` stop the TTY read loop without teaching the REPL about command parsing details.

## CLI Behavior

Batch execution returns success when `bye` stops a script. Output from chunks evaluated before `bye` remains visible; chunks after `bye` produce no output.

TTY execution evaluates each input line through the session script path. After each line, `main.c` checks the session exit flag and exits the loop cleanly.

## Tests

Regression tests cover:

- `bye` and `bye.` producing no value
- script evaluation stopping after `bye`
- dot-separated and newline-separated command forms
- `bye` in a loaded file stopping the outer script
- `byebye` and `bye_value` remaining identifiers
- malformed `bye`, `bye 1`, `bye()`, `bye:=1`, and `bye.x`
- TTY process exit after `bye`

Unit tests cover:

- `bye` not being a builtin
- initial session exit state
- malformed `bye` not setting exit state
- expression-only evaluation not executing `bye`
- successful `bye` setting exit state
- later script calls on an exited session producing no results
