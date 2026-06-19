# Slice 059: Collection Predicate Traversal Requirements

## Goal

Slice 059 extends the predicate traversal builtins `all` and `exists` so they can read object-backed `Set` and `Bag` payloads.

Update note: Slice 060 supersedes this slice's deferred `filter` item by adding collection-aware `filter` and `select`. Slice 061 supersedes this slice's deferred `reduce` item by adding collection-aware `reduce`. Slice 062 adds collection-specific `collect`; `map` remains list-only.

## Requirements

- `all(predicate, list)` shall keep the existing list traversal behavior.
- `exists(predicate, list)` shall keep the existing list traversal behavior.
- `all(predicate, collection)` shall accept `Set` and `Bag` collection objects.
- `exists(predicate, collection)` shall accept `Set` and `Bag` collection objects.
- Both builtins shall also accept objects whose class inherits from `Set` or `Bag`.
- Empty collection behavior shall match empty list behavior:
  - `all(predicate, empty_collection)` returns `true`.
  - `exists(predicate, empty_collection)` returns `false`.
- Non-empty collection payloads shall be traversed using the same callable predicate application used for lists.
- Predicate results shall still be required to be boolean values.
- `all` shall short-circuit on the first `false` predicate result.
- `exists` shall short-circuit on the first `true` predicate result.
- Non-list, non-collection traversal inputs shall continue to report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Existing list behavior and partial-application behavior shall remain unchanged.
- Builtins not in this slice shall remain list-only for collection objects:
  - `map`
  - `append`
  - `union`
  - `difference`
  - `intersection`

## Regression Requirements

Boundary coverage shall include:

- `all` and `exists` over empty `Set` and `Bag` objects.
- true and false results over populated `Set` objects.
- true and false results over populated `Bag` objects.
- traversal over payloads produced by `insert` and `remove`.
- partial application of `all` and `exists` with collection objects.
- higher-order use over lists that contain collection objects.
- subclass objects of `Set` and `Bag`.
- object identity membership through predicate traversal.

Robustness coverage shall include:

- arity mismatch.
- non-callable predicates.
- non-list, non-collection traversal inputs.
- non-boolean predicate results.
- predicate evaluation type errors.
- predicate evaluation name errors.
- traversal argument evaluation errors.

## Deferred

- Collection-aware `map` remains deferred.
- Collection-aware `union`, `difference`, and `intersection` remain deferred.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
