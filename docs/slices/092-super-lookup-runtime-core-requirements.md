# Slice 092: Super Lookup Runtime Core Requirements

## Goal

Slice 092 adds the runtime lookup helper needed by a future `super.method(...)` syntax without exposing new source syntax yet.

The helper answers:

```text
Given a receiver class, the class that supplied the currently executing method, and a method name,
which later class in receiver classes(receiver_class) would supply that method?
```

## Requirements

- The object runtime shall expose a helper for super-style user-defined method lookup.
- The helper shall accept:
  - the receiver's runtime class.
  - the current method supplier class.
  - the target method name.
  - output pointers for the selected function, selected supplier class, and linearization consistency.
- Lookup shall use the same checked `classes(Class)` linearization used by ordinary method dispatch.
- Lookup shall begin strictly after the current method supplier in that linearization.
- The current supplier class itself shall never be selected by super lookup.
- If a later class defines the target method directly, the helper shall return that function and that supplier class.
- If no later class defines the target method, the helper shall succeed with null function and null supplier outputs.
- If the current supplier is not present in the receiver's linearization, the helper shall succeed with null function and null supplier outputs.
- If the receiver class has inconsistent linearization, the helper shall succeed with `consistent = 0` and no selected method.
- Invalid C API arguments shall fail without selecting a method.
- Ordinary method dispatch, `methodSupplier`, `effectiveMethods`, bound method supplier retention, and native collection method lookup shall remain unchanged.
- `super` shall remain ordinary identifier syntax in user programs for this slice.

## Evaluation Boundaries

- Single-inheritance override cases shall find the overridden superclass method.
- Starting from a superclass supplier shall continue after that supplier and shall not reselect it.
- Starting from a supplier outside the receiver linearization shall return no method.
- Multiple-inheritance cases shall follow linearization order.
- Missing method names shall return no method.
- Inconsistent receiver classes shall report inconsistency through the helper's consistency output.

## Regression Requirements

Boundary coverage shall include:

- ordinary top-level `super` identifier binding.
- existing inherited method dispatch.
- existing override dispatch.
- existing multiple-inheritance dispatch.
- existing `methodSupplier` and `effectiveMethods` behavior.
- C unit coverage for single-inheritance super lookup.
- C unit coverage for multiple-inheritance super lookup.

Robustness coverage shall include:

- unbound ordinary `super` identifier behavior.
- ordinary non-callable `super` binding misuse.
- existing missing-method diagnostics.
- existing arity diagnostics for inherited methods.
- existing attribute shadowing diagnostics.
- existing inconsistent-linearization dispatch diagnostics.
- C unit coverage for invalid helper arguments.
- C unit coverage for missing and unrelated supplier cases.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
