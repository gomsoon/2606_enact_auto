# Slice 030: Stateful REPL / Evaluation Session Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/029-utility-builtins-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/029-utility-builtins-phase-1-requirements.md)

## 1. Slice Goal

This slice introduces an explicit evaluation session so interactive REPL input can preserve bindings across lines:

```text
x:=1.
x+2.
```

The second line shall evaluate to `3` in an interactive REPL session.

## 2. Source Basis

The PRD identifies ENACT as a read-eval-print loop language and also calls out future file loading. Both features need an environment that lives longer than a single parsed expression.

Earlier slices intentionally kept `enact_eval_text` stateless. This slice keeps that compatibility behavior and adds a separate stateful session API for interactive and future loader use.

## 3. In Scope

This slice includes:

- a public `EnactSession` API
- session initialization with the default builtin environment
- evaluating one expression at a time against a persistent session environment
- freeing a session and its retained environment
- using the session API for TTY REPL evaluation
- preserving bindings across successful REPL lines
- preserving the previous session environment after parse or evaluation failures
- regression tests for direct API behavior and TTY REPL behavior

## 4. Out Of Scope

This slice explicitly excludes:

- `load "filename"` syntax or file execution
- multi-expression parsing from one non-TTY stdin stream
- preserving state across separate process invocations
- transaction or rollback semantics beyond leaving previous bindings intact when a later expression fails before assignment
- changing `enact_eval_text`; it remains a fresh-environment helper
- prompts, history, line editing, or REPL commands

## 5. User-Facing Behavior

Accepted TTY examples:

- `x:=1.` then `x+2.` => `3`
- `x:=1.` then `x:=x+4.` then `x.` => `5`
- `base:=10.` then `add_base(y):=base+y.` then `base:=20.` then `add_base(1).` => `11`
- `fact(n):=n==0 then 1 else n*fact(n-1).` then `fact(5).` => `120`
- `add(x,y):=x+y.` then `inc:=add(1).` then `inc(4).` => `5`
- `version().` still returns `"enact-auto 0.1.0"` in a session
- `version:=()::"local".` then `version().` => `"local"`
- `x:=1.` then `x where x:=2.` then `x.` => `1`

Compatibility examples:

- `enact_eval_text("solo:=9.")` succeeds
- a later independent `enact_eval_text("solo.")` still reports `ENACT_ERR_NAME_UNBOUND`

Error examples:

- after `x:=5.`, evaluating `missing.` reports `ENACT_ERR_NAME_UNBOUND`, and a later `x.` still returns `5`
- after `x:=7.`, evaluating `(.` reports `ENACT_ERR_PARSE_UNMATCHED_PAREN`, and a later `x.` still returns `7`
- after `x:=2.`, evaluating `x+true.` reports `ENACT_ERR_TYPE_EXPECTED_INT`, and a later `x+1.` still returns `3`
- after `hd:=1.`, evaluating `hd(1:nil).` reports `ENACT_ERR_TYPE_EXPECTED_FUNCTION`, and a later `hd.` still returns `1`

## 6. Session API Requirements

The public API shall expose:

```c
typedef struct {
    EnactEnv env;
    bool initialized;
} EnactSession;

int enact_session_init(EnactSession *session);
EnactResult enact_session_eval_text(EnactSession *session, const char *source);
void enact_session_free(EnactSession *session);
```

`enact_session_init` shall install the same builtins that `enact_eval_text` installs for one-shot evaluation.

`enact_session_eval_text` shall parse a single expression and evaluate it against the session environment.

`enact_session_free` shall release all bindings retained by the session and mark it uninitialized.

## 7. Compatibility Requirements

`enact_eval_text` shall continue to use a fresh default environment for each call. This preserves the behavior documented in earlier slices and keeps unit tests that expect one-shot evaluation stable.

Token dumping remains stateless and is not affected by session state.

Non-TTY stdin evaluation remains a single one-shot source evaluation in this slice.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- assignment persistence across REPL lines
- reassignment using a previous binding
- function definition persistence across lines
- definition-time capture across later session rebinding
- recursive function definition across lines
- partial application stored in the session
- default builtins available in a new session
- builtin shadowing persistence
- local `where` binding isolation inside a session
- list values and higher-order list operations using session bindings
- direct C API tests for session lifecycle and stateless compatibility

## 9. Robustness Requirements

The regression suite shall include:

- null session initialization and evaluation behavior
- evaluation after session free
- unbound-name failure that does not clear earlier bindings
- parse failure that does not clear earlier bindings
- type failure that does not clear earlier bindings
- shadowed-builtin call failure that leaves the shadowing binding intact
- failed assignment right-hand side that does not create the target binding
- failed function call that leaves the function binding callable
- arity failure that does not evaluate an impossible side-effecting extra argument

## 10. Acceptance Criteria

This slice is accepted when:

- a TTY REPL session preserves user bindings across input lines
- `enact_eval_text` remains stateless across independent calls
- session parse and evaluation failures report diagnostics without discarding previous successful bindings
- token mode remains unchanged
- previous Slice 001 through Slice 029 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
