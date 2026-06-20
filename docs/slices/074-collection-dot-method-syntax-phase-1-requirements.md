# Slice 074: Collection Dot-Method Syntax Phase 1 Requirements

## Goal

Slice 074 introduces the first collection receiver method surface for object-backed `Set` and `Bag` values.

This slice lets the most basic collection operations be written in manual-style dot-call form while reusing the existing builtin semantics:

```text
collection.size()
collection.member(value)
collection.insert(value)
collection.remove(value)
```

## Requirements

- `collection.size()` shall evaluate as `size(collection)`.
- `collection.member(value)` shall evaluate as `member(value, collection)`.
- `collection.insert(value)` shall evaluate as `insert(value, collection)`.
- `collection.remove(value)` shall evaluate as `remove(value, collection)`.
- Dot-method collection syntax shall apply to objects whose runtime collection kind is `Set` or `Bag`.
- The receiver expression shall be evaluated before method lookup, matching existing dot-call behavior.
- Object attributes shall continue to shadow same-named collection dot methods.
- User-defined class methods shall continue to shadow same-named collection dot methods.
- Collection dot methods shall not depend on same-named top-level environment bindings.
- Collection dot methods shall use exact method arity and shall not create partial method values.
- Wrong method arity shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- Returned collection objects shall preserve the existing builtin behavior for runtime class, attributes, Set duplicate suppression, and Bag duplicate preservation.
- Non-collection objects shall not gain these dot methods and shall keep the existing missing-attribute behavior.
- Existing builtin function forms shall remain unchanged.

## Regression Requirements

Boundary coverage shall include:

- empty Set and Bag `size()` calls.
- populated Set and Bag `size()` calls.
- Set and Bag `member(value)` calls.
- Set `insert(value)` duplicate suppression.
- Bag `insert(value)` duplicate preservation.
- Set and Bag `remove(value)` calls.
- chained collection dot calls.
- collection dot-call results used by existing list and higher-order builtins.
- subclass collection receivers.
- object identity membership.
- top-level builtin shadowing that does not affect collection dot methods.
- object attribute shadowing over collection dot methods.
- class method shadowing over collection dot methods.

Robustness coverage shall include:

- wrong arity for each supported collection dot method.
- impossible extra arguments not being evaluated after arity rejection.
- non-collection object receivers.
- non-object receivers.
- class receivers.
- unsupported collection method names.
- bare collection method attribute reads without a call.
- non-callable object attributes shadowing collection dot methods.
- user-defined method shadowing that raises its own runtime diagnostic.
- misuse of collection and boolean dot-method results in primitive contexts.
- shadowed free builtin calls still following normal environment rules.

## Deferred

- Dot-method collection syntax for `collect`, `filter`, `select`, `all`, `exists`, `locate`, `forEachDo`, and `reduce` remains deferred.
- Dot-method collection syntax for `union`, `difference`, `intersection`, `subset`, `equal`, `add`, `unitset`, and `UNION` remains deferred.
- Bound collection method values such as `collection.size` remain deferred.
- Native method table integration remains deferred; this slice uses a focused evaluator bridge after normal attribute and class-method lookup.
- Class-qualified, attribute-inclusive, sorted, or canonical collection display remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
