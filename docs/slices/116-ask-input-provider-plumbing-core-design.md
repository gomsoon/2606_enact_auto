# Slice 116: Ask Input Provider Plumbing + ask() Core Design

Related requirements: [docs/slices/116-ask-input-provider-plumbing-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/116-ask-input-provider-plumbing-core-requirements.md)

## Overview

`ask` is implemented as a normal first-class builtin, but unlike deterministic builtins such as `version`, it needs runtime input. This slice adds a small input-provider slot to `EnactEnv` so the existing builtin env-callback path can deliver session services to `ask()`.

The implementation keeps input out of:

- lexer state
- parser grammar
- AST nodes
- ordinary user bindings

That keeps `ask` as a library function while still making input source selection a host/session responsibility.

## Input Provider Shape

`EnactEnv` now carries:

```c
typedef int (*EnactInputProvider)(void *user_data, char **out_line, EnactDiag *diag);
```

The provider returns a newly allocated line owned by the caller. It may include a trailing line terminator; `ask()` strips that before returning the ENACT string.

The public helpers are:

```c
void enact_env_set_input_provider(EnactEnv *env, EnactInputProvider provider, void *user_data);
int enact_env_read_input(EnactEnv *env, char **out_line, EnactDiag *diag);
void enact_session_set_input_provider(EnactSession *session, EnactInputProvider provider, void *user_data);
```

## Runtime Semantics

`ask()`:

1. validates zero-argument arity through the generic builtin path.
2. calls `enact_env_read_input`.
3. fails with `ENACT_ERR_INPUT_UNAVAILABLE` when no provider or no line is available.
4. removes a final `\n` or `\r\n`.
5. returns the remaining text as `ENACT_VALUE_STRING`.

`ask` itself remains first-class:

```text
ask
```

prints as:

```text
<function>
```

## Provider Propagation

The input provider is runtime context attached to an environment. Environment cloning copies the provider pointer and user data so local evaluation environments, closures, and higher-order calls can keep using the active session input source.

The provider is not visible as an identifier and is not included in value equality or printing.

## CLI Behavior

TTY execution installs a provider backed by the same `stdin` stream used by the REPL read loop. When evaluating:

```text
ask()
hello
```

the `ask()` call consumes `hello` as input and returns `"hello"`. The consumed input line is not evaluated as a separate expression.

Non-TTY CLI execution continues to read all of `stdin` as program source before evaluation. This slice does not add a source/input delimiter for batch mode, so `ask()` in that path fails unless a host embedding installs an input provider through the session API.

## Tests

Regression tests cover:

- first-class `ask`
- callable metadata for `ask`
- user shadowing of `ask`
- missing-provider failure
- arity mismatch without input consumption
- TTY `ask()` consuming the next input line
- empty input line handling
- zero-argument wrapper calls such as `apply0(ask)`
- closure and higher-order `map(x::ask(), ...)` use

Unit tests cover:

- diagnostic name/message for input unavailability
- env provider set/read behavior
- provider cloning through environments
- direct builtin failure without env
- env-callback success with newline and CRLF stripping
- session-level provider installation
- closure calls through session script evaluation
