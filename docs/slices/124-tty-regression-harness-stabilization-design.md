# Slice 124: TTY Regression Harness Stabilization / bye TTY Exit Hardening Design

Related requirements: [docs/slices/124-tty-regression-harness-stabilization-requirements.md](/home/tprover/2606_enact_auto/docs/slices/124-tty-regression-harness-stabilization-requirements.md)

## Overview

This slice hardens the Python functional test harness rather than the ENACT runtime. The existing runtime already reads TTY input one line at a time in `src/main.c`, evaluates each line through a persistent `EnactSession`, and exits the loop once `enact_session_exit_requested(...)` becomes true.

The previous `expect_tty_exit` helper wrote the whole input buffer to the PTY at once and then waited briefly for process exit. That shape could race with terminal echo, line discipline, and process shutdown timing for multi-line inputs such as:

```text
x:=1.
bye
```

## Harness Changes

TTY output decoding now goes through one shared normalization helper. It treats LF, CRLF, and CR as equivalent newline output so PTY echo details do not affect assertions.

`expect_tty_exit` now writes the source line by line. After each line it drains available PTY output briefly before writing the next line. This matches the REPL's line-oriented read loop more closely and avoids depending on bulk PTY buffering behavior.

The exit helper also accepts ordered expected fragments. This lets tests assert that pre-`bye` output happened before successful termination without trying to match full PTY echo output exactly.

## Runtime Impact

No runtime changes are required in this slice:

- `bye` remains a top-level session command implemented in `src/api.c`.
- `main.c` still owns the TTY read loop.
- non-TTY batch/script execution remains unchanged.

## Tests

Slice 124 adds TTY-only regression checks for:

- `bye`
- `bye.`
- expression output followed by `bye`
- the previously flaky `x:=1.\nbye\n` path
- carriage-return terminated input
- prior error followed by valid `bye`, preserving non-zero exit status
- malformed `bye` followed by valid `bye`, preserving non-zero exit status

The full functional runner prints explicit Slice 124 boundary and robustness counts.
