# Slice 129: Error Diagnostics Golden Tests Phase 1 Requirements

## Goal

Pin the user-facing diagnostic output for representative CLI/script failures. The suite should complement the existing regression tests, which already check diagnostic codes, by also checking the full stderr text that users see.

## Functional Requirements

- Add a stdlib-only Python golden test for diagnostic output.
- Run the diagnostic golden test from `make test`.
- Execute the built `build/enact` binary through stdin with the repository root as the working directory.
- Compare exact:
  - non-zero process status.
  - stdout emitted before the failure, when applicable.
  - stderr including `ENACT_ERR_*` code, message, offset text, and trailing newline.
- Cover lexer/parser boundary diagnostics with offsets:
  - invalid character.
  - invalid string literal.
  - unsupported bare `=`.
  - unexpected token.
  - missing final terminator at EOF.
  - unmatched parenthesis.
- Cover representative runtime and command diagnostics:
  - divide by zero.
  - integer type error.
  - non-callable call.
  - arity mismatch.
  - unbound identifier.
  - load failure.
  - unbound attribute.
  - invalid `super` context.
  - inconsistent class linearization.

## Non-Requirements

- Do not redesign the diagnostic system.
- Do not add dynamic source snippets, line/column reporting, or stack traces in this phase.
- Do not replace feature-specific robustness tests; this slice only pins representative user-facing text.

## Regression Expectations

- The runner shall print boundary and robustness counts.
- The boundary count shall represent offset-sensitive lexer/parser edge diagnostics.
- The robustness count shall represent runtime, command, object, and inheritance diagnostics.
