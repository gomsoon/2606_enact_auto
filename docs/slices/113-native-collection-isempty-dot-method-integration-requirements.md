# Slice 113: Native Collection isEmpty Dot-Method Integration Requirements

## Goal

Expose the Slice 112 `isEmpty` predicate through the native collection dot-method surface so Set and Bag values can use `collection.isEmpty()` and `collection.isEmpty` consistently with other native collection methods.

## Functional Requirements

- Empty Set and Bag values shall support zero-argument dot-calls:
  - `set().isEmpty()` returns `true`.
  - `bag().isEmpty()` returns `true`.
- Non-empty Set and Bag values shall return `false` through the same dot-call surface.
- Bare dot reads such as `set().isEmpty` shall return a bound collection method value that prints as `<function>`.
- Applying the bound value with zero arguments shall produce the same result as the direct dot-call.
- Set-like and Bag-like subclasses shall inherit the native `isEmpty` method table entry.
- Existing shadowing order shall be preserved:
  - object attributes named `isEmpty` shadow the native method.
  - user-defined class methods named `isEmpty` shadow the native method.
  - top-level bindings named `isEmpty` do not affect native dot-method lookup.

## Introspection Requirements

- `hasMethod(collection, 'isEmpty)` shall return `true` for Set-like and Bag-like targets.
- `methodArity(collection, 'isEmpty)` shall return `0`.
- `methodParams(collection, 'isEmpty)` shall return `nil`.
- `callableArity(collection.isEmpty)`, `callableMinArity(collection.isEmpty)`, and `callableArityRange(collection.isEmpty)` shall expose zero-argument callable metadata.
- `callableParams(collection.isEmpty)` shall return `nil`.
- `effectiveMethods(Set)` and related Set/Bag effective method listings shall include `'isEmpty` in native collection method-table order.
- Direct `methods(Set)` shall remain user-defined-only and shall not list native `isEmpty`.

## Robustness Requirements

- Extra arguments to `collection.isEmpty(...)` or a bound `collection.isEmpty` value shall fail with arity diagnostics without evaluating impossible extra arguments.
- Non-collection receivers shall keep the existing dot-method diagnostics.
- Non-callable receiver attributes named `isEmpty` shall shadow native lookup and fail when called.
- Empty parameter metadata shall still behave like `nil`, including `hd(methodParams(set(), 'isEmpty))` failing with `ENACT_ERR_LIST_EMPTY`.

## Non-Goals

- Do not add a new collection method dispatch mechanism.
- Do not change top-level `isEmpty(value)` semantics.
- Do not add native collection methods to `methods(Class)`.
