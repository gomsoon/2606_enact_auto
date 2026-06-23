# Slice 123: Manual Example Golden Tests Phase 3: Collections Core Requirements

## Goal

Add a dedicated golden regression suite for the PRD Milestone 4 collection-core manual examples.

This slice does not add language behavior. It collects collection examples that were previously covered across feature-specific slices and pins them under one compatibility-oriented slice.

## Functional Requirements

- Add golden evaluator tests for collection-core examples named by the PRD:
  - `set()`
  - `bag()`
  - `collect`
  - `union`
  - `difference`
  - `intersection`
  - `UNION`
  - `badAttrs`
- Prefer manual-style collection syntax where the current implementation supports it:
  - argument-bearing `set(...)` and `bag(...)` construction.
  - collection printing as `set(payload)` and `bag(payload)`.
  - free builtin calls such as `collect(fn, set)`.
  - collection dot-method calls such as `set(...).union(...)`.
  - newline top-level terminators.
- Include examples that exercise:
  - Set duplicate suppression.
  - Bag duplicate preservation.
  - `size` and `member`.
  - `insert` and `remove`.
  - `collect`, `filter`, `select`, and `reduce`.
  - Set algebra through free builtins.
  - Set and Bag aggregate `UNION`.
  - collection dot-method chaining.
  - bound native collection method values in higher-order calls.
  - subclass collection runtime class preservation.
  - collection method availability with `hasMethod`.
  - ambiguity helper compatibility through `badAttrs`.
- Keep the tests deterministic. Set display shall pin the current runtime payload order for these examples; it shall not claim sorted or mathematical canonical ordering.

## Boundary Coverage

Boundary coverage shall include:

- empty Set and Bag display.
- constructor-based duplicate behavior for Set and Bag.
- membership true and false cases.
- insertion and removal through dot methods.
- Bag removal preserving remaining multiplicity.
- collection transform with `collect`.
- predicate traversal with `filter` and `select`.
- accumulation with `reduce`.
- binary `union`, `difference`, and `intersection`.
- Set equality and subset predicates.
- free aggregate `UNION` over a list of sets.
- dot aggregate `UNION` over a set of sets.
- aggregate `UNION` over a bag of bags.
- chained collection algebra dot methods.
- native collection method values passed to `map`.
- collection subclass result class preservation.
- `badAttrs` and `hasMethod` over collection-related targets.

## Robustness Coverage

This slice shall not add new robustness cases. Existing collection feature slices already own malformed collection inputs, mixed Set/Bag rejection, arity errors, predicate type errors, non-collection operands, display misuse, and shadowed builtin diagnostics.

The Slice 123 robustness regression count shall therefore be zero.

## Non-Goals

- Do not change parser, evaluator, builtin, or runtime behavior.
- Do not add new collection syntax.
- Do not make Set printing sorted or canonical.
- Do not change collection equality, membership, or object identity semantics.
- Do not remove or deduplicate existing feature-specific tests.
- Do not introduce OCR or external PDF parsing into the test runner.
