# Slice 122: Manual Example Golden Tests Phase 2: Object Core Requirements

## Goal

Add a dedicated golden regression suite for the PRD Milestone 3 object-core manual examples.

This slice does not add language behavior. It collects object-oriented examples that were previously covered across feature-specific slices and pins them under one compatibility-oriented slice.

## Functional Requirements

- Add golden evaluator tests for object-core examples named by the PRD:
  - `Leaf`
  - `Tree`
  - parent recomputation
  - class conflict examples
- Prefer manual-style object syntax where the current implementation supports it:
  - `class Child < Parent`
  - `new Class`
  - `object with attr:=value`
  - `object.method(args)`
  - `object.attr`
  - newline top-level terminators
- Include examples that exercise:
  - class creation and object construction.
  - inheritance and inherited method dispatch.
  - `self` and dynamic object attribute reads.
  - object attribute mutation.
  - object attributes shadowing class methods.
  - multiple-superclass method lookup.
  - ambiguity helpers for conflicting inherited methods.
  - linearization consistency checks.
- Keep the tests deterministic and independent of object identity text beyond the existing stable `<object Class>` display.

## Boundary Coverage

Boundary coverage shall include:

- Leaf/Tree class hierarchy construction.
- inherited method dispatch from `Tree` to `Leaf`.
- list traversal over Leaf objects.
- stateful object method mutation.
- parent attribute recomputation after parent mutation.
- parent-aware method recomputation using a manual conditional.
- direct subclass method override.
- object attribute shadowing over a class method.
- class linearization display for a Leaf/Tree chain.
- multiple-superclass method dispatch.
- conflicting inherited method introspection with `badAttrs`.
- supplier introspection with `suppliers`.
- direct method resolution masking inherited conflicts.
- inconsistent linearization reporting with `OK`.
- manual conditional branching from an `OK` result.

## Robustness Coverage

This slice shall not add new robustness cases. Existing object feature slices already own malformed class syntax, missing attributes, non-object receivers, method arity errors, invalid `self`/`super` use, and inconsistent-linearization diagnostics.

The Slice 122 robustness regression count shall therefore be zero.

## Non-Goals

- Do not change parser, evaluator, builtin, or runtime behavior.
- Do not add collection-core manual golden examples.
- Do not add new object syntax.
- Do not remove or deduplicate existing feature-specific tests.
- Do not introduce OCR or external PDF parsing into the test runner.
