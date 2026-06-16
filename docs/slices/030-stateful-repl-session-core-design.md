# Slice 030: Stateful REPL / Evaluation Session Core Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/030-stateful-repl-session-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/030-stateful-repl-session-core-requirements.md)

Prerequisite design: [docs/slices/029-utility-builtins-phase-1-design.md](/home/tprover/2606_enact_auto/docs/slices/029-utility-builtins-phase-1-design.md)

## 1. Design Summary

This slice adds an explicit session object around the existing environment:

```c
typedef struct {
    EnactEnv env;
    bool initialized;
} EnactSession;
```

The parser remains single-expression based. The evaluator already accepts an explicit environment through `enact_eval_ast_with_env`, so the session design reuses that path instead of changing expression semantics.

## 2. API Design

The public API gains:

```c
int enact_session_init(EnactSession *session);
EnactResult enact_session_eval_text(EnactSession *session, const char *source);
void enact_session_free(EnactSession *session);
```

`enact_session_init` initializes the embedded environment and installs the default builtins.

`enact_session_eval_text` parses the provided source and evaluates the parsed AST with the embedded environment.

`enact_session_free` frees the embedded environment and marks the session as uninitialized so accidental reuse reports an ordinary API error instead of reading freed bindings.

## 3. Parser Factoring

`api.c` factors the existing parse setup into a private helper:

```c
static int enact_parse_text(const char *source, EnactAst **out, EnactDiag *diag);
```

Both one-shot evaluation and session evaluation share this helper. The helper owns scanner setup, parse context setup, error filling, and scanner cleanup. On success, the caller owns the returned AST. On failure, any partial AST is freed before returning.

## 4. Evaluation Behavior

`enact_eval_text` continues to create a fresh environment:

1. parse source
2. initialize an `EnactEnv`
3. install builtins
4. evaluate with `enact_eval_ast_with_env`
5. free the temporary environment

`enact_session_eval_text` instead uses the session environment:

1. parse source
2. evaluate with `enact_eval_ast_with_env`
3. keep the environment alive for the next call

Assignments and recursive definitions already mutate the provided environment, so they naturally become persistent when the same environment is reused.

## 5. REPL Integration

TTY evaluation now initializes one `EnactSession` before entering the read loop. Each line is evaluated through that session.

Token mode keeps the previous stateless behavior and still calls `enact_dump_tokens_text` per line.

Non-TTY stdin keeps the existing whole-input one-shot behavior. This avoids mixing file-loader semantics into the session slice.

## 6. Failure Behavior

Parse failures occur before evaluator entry and therefore cannot mutate the session environment.

Evaluation failures preserve all prior successful bindings. If an expression mutates the environment before failing later in the same expression, existing expression semantics still apply. This slice does not add transactional rollback.

Calls against a null or freed session return `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`, matching the project's existing internal API error convention for invalid evaluator inputs.

## 7. Test Strategy

Unit tests cover:

- null session handling
- session initialization and builtin availability
- assignment persistence across `enact_session_eval_text` calls
- failure preserving previous bindings
- function definition-time capture across later session rebinding
- `enact_eval_text` remaining stateless
- evaluation after `enact_session_free`

Functional TTY tests cover:

- assignment and reassignment across lines
- named functions, recursion, and partial application across lines
- default builtin availability and shadowing
- local `where` isolation
- list bindings with `map` and `reduce`
- unbound-name, parse, type, arity, shadowed-builtin, and failed-assignment robustness cases

Coverage remains reported with the existing handwritten-source flow.
