# Slice 075: Collection Dot-Method Syntax Phase 2: Algebra + Predicates Requirements

## Goal

Slice 075 extends collection receiver dot-call syntax from the basic operations in Slice 074 to collection algebra and predicate helpers.

This slice enables these manual-style forms:

```text
collection.union(other)
collection.difference(other)
collection.intersection(other)
collection.subset(other)
collection.equal(other)
set.add(value)
```

## Requirements

- `collection.union(other)` shall evaluate as `union(collection, other)`.
- `collection.difference(other)` shall evaluate as `difference(collection, other)`.
- `collection.intersection(other)` shall evaluate as `intersection(collection, other)`.
- `collection.subset(other)` shall evaluate as `subset(collection, other)`.
- `collection.equal(other)` shall evaluate as `equal(collection, other)`.
- `set.add(value)` shall evaluate as `add(value, set)`.
- The free builtin forms shall remain unchanged.
- Dot-method algebra shall apply to objects whose runtime collection kind is `Set` or `Bag` according to the existing builtin semantics.
- `add` shall remain Set-only and shall reject Bag receivers through the existing builtin diagnostic.
- Binary Set and Bag algebra shall keep the existing same-kind operand rules.
- Mixed Set/Bag operands, ordinary lists, classes, and non-collection objects shall keep the existing builtin diagnostics.
- Returned collection objects shall preserve the existing builtin behavior for runtime class, attributes, Set duplicate suppression, and Bag multiplicity.
- Predicate dot methods shall return ordinary booleans.
- Object attributes shall continue to shadow same-named collection dot methods.
- User-defined class methods shall continue to shadow same-named collection dot methods.
- Collection dot methods shall not depend on same-named top-level environment bindings.
- Wrong method arity shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.

## Regression Requirements

Boundary coverage shall include:

- Set and Bag `union`.
- Set and Bag `difference`.
- Set and Bag `intersection`.
- Set and Bag `subset`.
- Set and Bag `equal`.
- Set `add`.
- chained algebra and predicate calls.
- subclass receiver preservation.
- user-visible attribute preservation.
- object identity membership after algebra.
- top-level builtin shadowing that does not affect collection dot methods.
- object attribute shadowing over collection dot methods.
- class method shadowing over collection dot methods.

Robustness coverage shall include:

- wrong arity for supported algebra and predicate dot methods.
- impossible extra arguments not being evaluated after arity rejection.
- Bag receiver rejection for `add`.
- mixed Set/Bag operands.
- non-collection and list operands where collection operands are required.
- misuse of returned collections in primitive or list-only contexts.
- misuse of predicate boolean results in list-only or callable contexts.
- shadowed free builtin calls still following normal environment rules.

## Deferred

- Dot-method collection syntax for `collect`, `filter`, `select`, `all`, `exists`, `locate`, `forEachDo`, and `reduce` remains deferred.
- Dot-method collection syntax for `unitset` and `UNION` remains deferred.
- Bound collection method values such as `collection.union` remain deferred.
- Native method table integration remains deferred; this slice continues the focused evaluator bridge.
- Class-qualified, attribute-inclusive, sorted, or canonical collection display remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
