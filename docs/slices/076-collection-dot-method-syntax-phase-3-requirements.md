# Slice 076: Collection Dot-Method Syntax Phase 3: Traversal + Higher-Order Requirements

## Goal

Slice 076 extends collection receiver dot-call syntax to traversal and higher-order collection operations.

This slice enables these manual-style forms:

```text
collection.collect(transform)
collection.filter(predicate)
collection.select(predicate)
collection.all(predicate)
collection.exists(predicate)
collection.locate(predicate)
collection.forEachDo(action)
collection.reduce(reducer, initial)
```

## Requirements

- `collection.collect(transform)` shall evaluate as `collect(transform, collection)`.
- `collection.filter(predicate)` shall evaluate as `filter(predicate, collection)`.
- `collection.select(predicate)` shall evaluate as `select(predicate, collection)`.
- `collection.all(predicate)` shall evaluate as `all(predicate, collection)`.
- `collection.exists(predicate)` shall evaluate as `exists(predicate, collection)`.
- `collection.locate(predicate)` shall evaluate as `locate(predicate, collection)`.
- `collection.forEachDo(action)` shall evaluate as `forEachDo(action, collection)`.
- `collection.reduce(reducer, initial)` shall evaluate as `reduce(reducer, initial, collection)`.
- The free builtin forms shall remain unchanged.
- Dot-method traversal shall apply to objects whose runtime collection kind is `Set` or `Bag`.
- Returned collection objects shall preserve existing builtin behavior for runtime class, attributes, Set duplicate suppression, and Bag occurrence preservation.
- Predicate dot methods shall keep existing predicate result validation and short-circuit behavior.
- `forEachDo` shall keep existing side-effect and `nil` return behavior.
- `reduce` shall keep existing accumulator order and initial-value behavior.
- Object attributes shall continue to shadow same-named collection dot methods.
- User-defined class methods shall continue to shadow same-named collection dot methods.
- Collection dot methods shall not depend on same-named top-level environment bindings.
- Wrong method arity shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.

## Regression Requirements

Boundary coverage shall include:

- Set and Bag `collect`.
- Set and Bag `filter`.
- `select` as filter alias.
- `all`, `exists`, and `locate`.
- `locate` no-match returning `nil`.
- `forEachDo` with side effects.
- `reduce` with an explicit initial accumulator.
- chained traversal and prior dot-method operations.
- subclass receiver preservation.
- user-visible attribute preservation.
- object identity through traversal.
- top-level builtin shadowing that does not affect collection dot methods.
- object attribute shadowing over collection dot methods.
- class method shadowing over collection dot methods.

Robustness coverage shall include:

- wrong arity for supported traversal dot methods.
- impossible extra arguments not being evaluated after arity rejection.
- non-callable traversal functions.
- predicate results that are not booleans.
- reducer arity mismatches.
- shadowed free builtin calls still following normal environment rules.
- misuse of collection, boolean, and `nil` results in incompatible contexts.
- still-deferred collection dot methods remaining unbound.

## Deferred

- Dot-method collection syntax for `unitset` remains deferred; Slice 077 later adds aggregate `UNION`.
- Bound collection method values such as `collection.collect` remain deferred.
- Native method table integration remains deferred; this slice continues the focused evaluator bridge.
- Collection-aware `map` remains deferred; `collect` remains the collection-shape-preserving transform surface.
- Class-qualified, attribute-inclusive, sorted, or canonical collection display remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
