# ENACT Compatibility Matrix

This matrix summarizes the current implementation status against the PRD, the ENACT manual-derived compatibility target, and the project-default extensions.

Status values:

- `Implemented`: supported by the current runtime and regression suite.
- `Baseline Gate`: supported as a guardrail but below the PRD final target.
- `Deferred`: intentionally left for a later milestone.
- `Project Default`: a documented modernization or extension, not a strict historical claim.

## Milestone Coverage

| Area | Status | Evidence | Test Anchor |
| --- | --- | --- | --- |
| Language skeleton: build, lexer/parser, expression evaluation | Implemented | Slices 001-007 | `make test`, token cases, parser/evaluator regressions |
| Functional core: arithmetic, comparison, conditionals, functions, lambdas, currying, `where`, `fix` | Implemented | Slices 001-026, 121 | Slice 121 manual functional golden tests |
| Stateful REPL and script execution | Implemented | Slices 030-031, 036, 124 | TTY regression tests and script-session unit tests |
| File loading with `load "filename"` | Implemented | Slices 033, 036 | load functional, TTY, and unit tests |
| Object core: `class`, `new`, `with`, attributes, methods, `self`, inheritance | Implemented | Slices 037-054, 122 | Slice 122 manual object golden tests |
| Multiple inheritance introspection and diagnostics | Implemented | Slices 049-054, 083-091 | ambiguity, `OK`, supplier, and effective-method tests |
| `super` runtime and first-class `super.method` values | Implemented | Slices 092-096 | super dispatch and diagnostic tests |
| Method and callable signature introspection | Implemented | Slices 097-105 | arity, parameter, native collection signature tests |
| Type predicate helpers | Implemented | Slices 106-113 | predicate and dot-method integration tests |
| Collection core: `Set`, `Bag`, traversal, algebra, display, dot methods | Implemented | Slices 055-082, 123 | Slice 123 manual collection golden tests |
| Utility functions and commands: `version`, `time`, `bye`, `ask`, `cells`, `maxcells` | Implemented | Slices 029, 114-119 | utility functional and unit tests |
| Runtime cell accounting and leak harness | Implemented | Slices 117-120 | runtime stats unit tests and leak regression harness |
| Coverage reporting for handwritten C sources | Implemented | Slice 125 | `make coverage` |
| Coverage baseline gate | Baseline Gate | Slice 125 | `make coverage-check` at 81.0% line / 73.0% branch |
| CI quality gate | Implemented | Slice 126 | GitHub Actions runs `make test` and `make coverage-check` |

## Project Defaults And Compatibility Choices

| Topic | Status | Current Behavior | Notes |
| --- | --- | --- | --- |
| Double-quoted literals | Project Default | immutable string values | Historical quoted literal semantics may differ; strict mode deferred |
| Equality | Project Default | `==` | Historical `=` compatibility is deferred |
| Inequality | Project Default | `!=` | Historical `<>` compatibility is deferred |
| Unary negation | Project Default | `-` | Historical `~` compatibility is deferred |
| Top-level newline terminator | Project Default | newline terminates top-level REPL/script chunks | Added for practical REPL/script ergonomics |
| `load` and `bye` | Implemented | top-level session commands | Not installed as builtins and not first-class values |
| Set display order | Implemented | deterministic current payload order in tests | Not a promise of sorted mathematical canonical order |
| Set membership over objects | Implemented | identity-sensitive object membership | Matches the project interpretation of ENACT object semantics |

## Deferred Items

| Item | Status | Rationale |
| --- | --- | --- |
| Full Appendix 2 collection class source compatibility | Deferred | PRD explicitly defers full source compatibility unless manual review makes it necessary |
| Strict historical compatibility mode | Deferred | Future mode may accept historical spelling and quoted literal behavior |
| Rich string operations, formatting, interpolation, mutable strings | Deferred | Initial delivery only requires immutable string values |
| Performance tuning beyond correctness | Deferred | Correctness and regression stability remain the current priority |
| Debugger, formatter, LSP, tracing UI | Deferred | Extended tooling is out of scope for the current compatibility target |
| Coverage final target 95% line / 90% branch | Deferred | Baseline gate is active; ratcheting to final PRD targets remains future hardening work |

## Quality Gates

Local and CI quality gates are:

```text
make test
make coverage-check
```

Current handwritten-source coverage baseline:

```text
lines >= 81.0%
branches >= 73.0%
```

Recent measured totals:

```text
TOTAL lines 4800/5897 (81.4%)  branches 2494/3373 (73.9%)
```
