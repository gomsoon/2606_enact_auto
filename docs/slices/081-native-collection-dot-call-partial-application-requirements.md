# Slice 081: Native Collection Dot-Call Partial Application Requirements

## Goal

Slice 081 lets direct native collection dot-calls produce partial bound collection method values when too few, but at least one, method argument is supplied:

```text
set((1,2,3)).reduce((acc,x)::acc+x)
```

The returned value is callable and can later be completed with the remaining native method argument.

## Requirements

- Direct native collection dot-calls shall reuse the existing bound collection method callable path from Slice 078.
- A direct native collection dot-call with fewer than the native method arity and at least one supplied method argument shall return a bound collection method value.
- Calling that returned value shall complete the original native collection method call with the same captured receiver and already-supplied method arguments.
- Exact-arity native collection dot-calls shall keep their existing behavior.
- Zero-argument direct native collection dot-calls to non-zero-arity native methods shall keep reporting `ENACT_ERR_ARITY_MISMATCH`.
- Over-applied direct native collection dot-calls shall keep reporting `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- Valid-arity argument evaluation errors shall propagate normally.
- Native collection dot-call partial values shall print as `<function>`.
- Native collection dot-call partial values shall be accepted anywhere an existing callable is accepted, including `map`, direct calls, list values, and predicate helpers that accept functions.
- Receiver object attributes shall continue to shadow native collection methods.
- User-defined class methods on `Set`, `Bag`, or subclasses shall continue to shadow native collection methods.
- Top-level bindings with the same name as a native collection method shall not affect native collection dot-method lookup.
- Unsupported collection method names shall keep reporting `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Native collection method-table integration is added by Slice 082.

## Regression Requirements

Boundary coverage shall include:

- direct partial creation for a native collection dot-call.
- immediate completion through chained call syntax.
- assignment of a native collection dot-call partial and later completion.
- Set and Bag receivers.
- empty collection receivers.
- higher-order use through `map`.
- use through an ordinary user-defined `apply` helper.
- partial values stored in lists.
- `atom` over native collection dot-call partial values.
- receiver capture across later variable rebinding.
- receiver expressions produced by other collection operations.
- subclass collection receivers.
- top-level builtin shadowing not affecting native dot-method lookup.
- receiver attribute shadowing.
- user-defined class method shadowing.
- exact zero-argument native dot-calls after the evaluator path change.
- exact one-argument native dot-calls after the evaluator path change.
- exact aggregate native dot-calls after the evaluator path change.

Robustness coverage shall include:

- zero-argument direct native dot-calls to non-zero-arity native methods.
- over-applied direct native dot-calls without evaluating impossible extra arguments.
- valid-arity direct partial argument evaluation errors.
- zero-argument completion attempts on native dot-call partial values.
- over-applied partial completion without evaluating impossible extra arguments.
- valid-arity partial completion argument evaluation errors.
- delayed reducer type errors after partial completion.
- delayed reducer arity errors after partial completion.
- delayed reducer name errors after partial completion.
- delayed reducer runtime errors after partial completion.
- misuse of native dot-call partial values as booleans.
- misuse of native dot-call partial values as lists.
- exact zero-argument native method over-application.
- exact one-argument native method under-application.
- unsupported native collection method names.
- non-callable receiver attributes shadowing native collection methods.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
