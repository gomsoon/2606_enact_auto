# Slice 082: Native Collection Method Table Integration Requirements

## Goal

Slice 082 moves native collection dot-method metadata out of the evaluator and into a runtime lookup table owned by the builtin layer.

The user-visible collection method surface remains unchanged:

```text
set((1,2)).size()
set((1,2)).reduce((acc,x)::acc+x)(0)
bag((1,1,2)).member(1)
```

## Requirements

- Native collection method lookup shall be represented by a table of method name, supported collection receiver kind, underlying builtin, and receiver argument index.
- Bare native collection method reads and native collection dot-calls shall both use that table.
- The supported native collection method names shall remain the same as Slice 081.
- Receiver argument insertion shall remain the same as Slice 081.
- Exact calls, partial calls, and completed partial calls shall keep their Slice 081 behavior.
- Top-level bindings with the same name as a native collection method shall not affect native collection dot-method lookup.
- Receiver object attributes shall continue to shadow native collection methods.
- User-defined class methods on `Set`, `Bag`, or subclasses shall continue to shadow native collection methods.
- Unsupported collection method names shall keep reporting `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Native collection methods shall not be added to public `methods(Class)` introspection in this slice; `methods` continues to report user-defined direct class methods.

## Regression Requirements

Boundary coverage shall include:

- exact zero-argument Set method lookup through the native table.
- exact zero-argument Bag method lookup through the native table.
- bare native method read through the native table.
- partial native method creation through the native table.
- completion of a native method partial.
- Set receiver insertion at builtin argument index 0.
- Bag receiver insertion at builtin argument index 0.
- Set receiver insertion at builtin argument index 1.
- Bag receiver insertion at builtin argument index 1.
- receiver insertion at builtin argument index 2.
- aggregate collection method lookup.
- Set algebra lookup.
- Bag algebra lookup.
- predicate helper lookup.
- traversal helper lookup.
- subclass collection receiver lookup.
- top-level builtin shadowing that does not affect native dot-method lookup.
- user-defined class method shadowing over native collection methods.
- public `methods(Set)` introspection not exposing native table entries.

Robustness coverage shall include:

- unsupported native collection method names remaining unbound.
- native builtin names that are not collection methods remaining unbound.
- non-collection object dot-calls remaining unbound.
- zero-argument calls to non-zero-arity native collection methods.
- over-applied native collection method calls without evaluating impossible extra arguments.
- valid-arity argument evaluation errors still propagating.
- completed native method partial under-application.
- completed native method partial over-application without evaluating impossible extra arguments.
- completed native method partial evaluation errors still propagating.
- builtin semantic type errors after native table lookup.
- non-callable receiver attributes shadowing native collection methods.
- user-defined class method runtime errors shadowing native collection methods.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
