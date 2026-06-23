# Slice 116: Ask Input Provider Plumbing + ask() Core Requirements

## Goal

Add the PRD-listed `ask` utility as a zero-argument builtin that reads one input line from the active evaluation session and returns it as an ENACT string.

## Functional Requirements

- `ask` shall be installed in the default environment as a first-class zero-argument builtin.
- `ask()` shall read one line from the current session input provider.
- The returned value shall be an owned ENACT string.
- A trailing line terminator shall be removed from the returned string.
  - `\n` shall be removed.
  - `\r\n` shall be removed.
- Empty input lines shall return the empty string.
- `ask` shall print as `<function>` when evaluated without being called.
- `ask` shall work through ordinary zero-argument callable paths such as user-defined wrappers and higher-order call sites that capture the active session environment.
- User bindings shall be able to shadow `ask` through existing environment rules.

## Input Provider Requirements

- Session evaluation shall support an input provider callback separate from ordinary lexical bindings.
- TTY execution shall install a provider that reads from `stdin`.
- Unit and API tests shall be able to install a deterministic provider.
- `enact_session_eval_text` and `enact_session_eval_script` shall use the provider stored on their session environment.
- `enact_eval_text` shall not install an implicit provider.

## Error Requirements

- `ask()` without an input provider shall fail with `ENACT_ERR_INPUT_UNAVAILABLE`.
- `ask()` at provider EOF shall fail with `ENACT_ERR_INPUT_UNAVAILABLE`.
- `ask` called with any argument shall fail with `ENACT_ERR_ARITY_MISMATCH` before consuming input.
- Misusing a shadowed non-callable `ask` shall keep existing callable diagnostics.

## Non-Goals

- Do not add prompt text, prompt printing, or `ask(prompt)` in this slice.
- Do not change non-TTY CLI batch parsing to split program source from later input.
- Do not add asynchronous input, multiline input, or raw character input.
- Do not add `cells` or `maxcells`.
