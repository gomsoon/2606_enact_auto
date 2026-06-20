# Slice 077: Collection Aggregate UNION Dot/Core Requirements

## Goal

Slice 077 extends aggregate `UNION` from ordinary list inputs to collection inputs and adds a receiver dot-method form for collection-of-collections values.

This slice enables:

```text
UNION(collection_of_sets_or_bags)
collection_of_sets_or_bags.UNION()
```

## Requirements

- `UNION(list_of_sets_or_bags)` shall keep its existing behavior.
- `UNION(collection_of_sets_or_bags)` shall accept a `Set` or `Bag` collection object whose payload elements are all collection objects of the same inner kind.
- `collection.UNION()` shall evaluate as `UNION(collection)`.
- `UNION(set())` shall return a new empty root `Set` object.
- `UNION(bag())` shall return a new empty root `Set` object.
- Empty collection input shall mirror existing `UNION(())` behavior because there is no inner collection from which to infer a result kind or prototype.
- Non-empty collection input shall infer the aggregate result kind from the first contained collection object.
- Non-empty collection input shall preserve the first contained collection object's runtime class and user-visible attributes.
- Contained `Set` values shall use existing aggregate Set union semantics.
- Contained `Bag` values shall use existing aggregate Bag union semantics.
- Mixed contained `Set` and `Bag` values shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Non-collection contained values shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- The outer collection object's runtime kind, class, and attributes shall not affect the result prototype.
- The free builtin form shall remain first-class and shadowable through the ordinary environment.
- Dot-method `UNION` shall not depend on same-named top-level environment bindings.
- Object attributes shall continue to shadow collection dot methods.
- User-defined class methods shall continue to shadow collection dot methods.
- Wrong dot-method arity shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.

## Regression Requirements

Boundary coverage shall include:

- empty `Set` and `Bag` collection inputs.
- free builtin collection input.
- dot-method collection input.
- Set-of-Set aggregation.
- Bag-of-Bag aggregation.
- Set outer collection containing Bag inputs.
- Bag outer collection containing Set inputs.
- empty input returning root `Set`.
- first contained collection class preservation.
- first contained collection attribute preservation.
- object identity membership after aggregation.
- nested aggregate results.
- chaining aggregate results through existing collection dot methods.
- top-level builtin shadowing that does not affect dot `UNION`.
- object attribute shadowing over dot `UNION`.
- class method shadowing over dot `UNION`.

Robustness coverage shall include:

- wrong dot-method arity.
- non-collection elements inside collection inputs.
- mixed contained Set/Bag values.
- class and non-collection object elements.
- direct non-list, non-collection arguments to free `UNION`.
- operand evaluation errors while building collection input.
- misuse of returned collection objects in primitive or list-only contexts.
- shadowed free builtin calls still following normal environment rules.
- non-callable object attributes shadowing dot `UNION`.

## Deferred

- Dot-method collection syntax for `unitset` remains deferred because `unitset(value)` constructs a list-backed singleton rather than aggregating the receiver.
- Bound collection method values such as `collection.UNION` remain deferred in this slice and are later added by Slice 078.
- Native method table integration remains deferred; this slice continues the focused evaluator bridge.
- Class-qualified, attribute-inclusive, sorted, or canonical collection display remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
