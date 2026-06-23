# Slice 129: Error Diagnostics Golden Tests Phase 1 Design

Related requirements: [docs/slices/129-error-diagnostics-golden-tests-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/129-error-diagnostics-golden-tests-phase-1-requirements.md)

## Overview

Slice 129 adds a golden test layer for diagnostic text. Earlier regression tests assert that failures return the expected `ENACT_ERR_*` codes. This slice verifies the complete CLI-facing stderr shape as well:

```text
ENACT_ERR_CODE: message
ENACT_ERR_CODE: message at offset N
```

No runtime or parser behavior changes are required for Phase 1.

## Runner

`tests/test_error_diagnostics.py` runs `build/enact` with stdin source strings. Each case stores:

- a short name.
- source text.
- exact stdout.
- exact stderr.
- a classification of `boundary` or `robustness`.

The runner uses the repository root as the process working directory so command-level tests such as `load "tests/smoke/missing_fixture.en"` are stable regardless of the caller's shell location.

## Boundary Cases

Boundary cases focus on lexer/parser edges where offsets are user-visible:

- invalid character at offset `0`.
- invalid string literal at offset `0`.
- bare `=` compatibility diagnostic at offset `0`.
- unexpected token after an incomplete infix expression.
- missing final terminator at EOF without a trailing newline.
- unmatched parenthesis.

## Robustness Cases

Robustness cases cover representative runtime, command, object, and inheritance failures:

- arithmetic/runtime failures.
- type and arity failures.
- unbound identifiers.
- failed `load`.
- missing attributes.
- invalid `super` use.
- inconsistent multiple-inheritance linearization.

The inconsistent-linearization case also pins stdout emitted by preceding successful class definitions, ensuring script failure behavior remains visible and stable.
