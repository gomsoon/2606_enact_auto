# Slice 108: Type Predicate Helpers Phase 1 Requirements

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slices:

- [docs/slices/029-utility-builtins-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/029-utility-builtins-phase-1-requirements.md)
- [docs/slices/099-callable-arity-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/099-callable-arity-introspection-core-requirements.md)
- [docs/slices/107-hasattr-predicate-requirements.md](/home/tprover/2606_enact_auto/docs/slices/107-hasattr-predicate-requirements.md)

## Goal

Add two small predicate helpers:

```text
isClass(value)
isCallable(value)
```

These extend the existing `isObject` predicate with a class predicate and a callable predicate suitable for functions, builtins, partial applications, and bound methods.

## Functional Requirements

- Add a builtin named `isClass`.
- Add a builtin named `isCallable`.
- Both builtins shall have arity one.
- Both builtins shall return boolean values.
- `isClass(value)` shall return `true` only for class values.
- `isCallable(value)` shall return `true` for every value kind accepted by callable introspection and application:
  - user-defined functions
  - builtins
  - builtin partial applications
  - bound object methods
  - bound native collection methods
- Both predicates shall return `false` for all other value kinds.
- Both predicates shall be normal first-class builtins and support existing builtin partial-application and shadowing behavior.

## Boundary Examples

```text
isClass(Object) -> true
isClass(new Object) -> false
isClass(hd) -> false

isCallable(x::x) -> true
isCallable(hd) -> true
isCallable(append(nil)) -> true
isCallable(set().size) -> true
isCallable(Object) -> false
isCallable(set()) -> false
```

`isCallable` intentionally uses the broader callable vocabulary rather than only checking `ENACT_VALUE_FUNCTION`:

```text
callableParams(isCallable) -> 'value:nil
isCallable(callableParams) -> true
```

## Error Requirements

- Arity errors shall use the existing builtin arity diagnostics.
- Argument evaluation errors shall propagate normally.
- Type mismatches are not errors for these predicates; non-matching values return `false`.

## Non-Goals

- Do not add `isFunction`, `isSet`, `isBag`, or `isCollection`.
- Do not introduce structured runtime type names.
- Do not change callable application, callable arity, or callable parameter semantics.

## Regression Requirements

- Add boundary tests for all current core value categories.
- Add positive callable tests for functions, builtins, builtin partials, bound object methods, and bound collection methods.
- Add robustness tests for arity mismatch, argument evaluation failure, boolean-result misuse, and user shadowing.
- Keep handwritten source coverage reporting unchanged.
