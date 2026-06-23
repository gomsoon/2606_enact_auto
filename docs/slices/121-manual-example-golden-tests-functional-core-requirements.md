# Slice 121: Manual Example Golden Tests Phase 1: Functional Core Requirements

## Goal

Add a dedicated golden regression suite for the PRD Milestone 2 functional-core manual examples.

This slice does not add language behavior. It collects manual-derived examples that were previously covered across feature-specific slices and pins them under one compatibility-oriented slice.

## Functional Requirements

- Add golden evaluator tests for functional-core examples named in the PRD:
  - factorial
  - nfib
  - reverse
  - twice
- Prefer manual-style surface syntax where the current implementation supports it:
  - `condition then true_expr else false_expr`
  - newline top-level terminators
  - whitespace function application
  - `()` nil compatibility where useful
- Include higher-order `twice` examples that exercise function arguments and returned functions.
- Include both single-expression and multi-line script-style golden cases.
- Keep the tests deterministic and independent of timing, cell counts, or environment-global state.

## Boundary Coverage

Boundary coverage shall include:

- factorial recursion over an integer boundary.
- a larger factorial value.
- nfib using the manual-style recurrence currently adopted by the project.
- recursive list reversal over tuple-like list syntax.
- `twice` as a two-argument higher-order helper.
- curried `twice`.
- whitespace-defined and whitespace-applied `twice`.
- `twice` composed with `map`.
- `twice` built through a small `compose` helper.
- newline-terminated manual examples.

## Robustness Coverage

This slice shall not add new robustness cases. Existing feature slices already own malformed input, type errors, arity errors, and recursion failures for these features.

The Slice 121 robustness regression count shall therefore be zero.

## Non-Goals

- Do not change parser, evaluator, builtin, or runtime behavior.
- Do not add object-core or collection-core manual golden examples.
- Do not add new manual syntax.
- Do not remove or deduplicate existing feature-specific tests.
- Do not introduce external PDF parsing into the test runner.
