# Slice 060: Collection Filter/Select Core Requirements

## Goal

Slice 060 extends predicate-based filtering to object-backed `Set` and `Bag` payloads and adds the PRD-named `select` builtin as the same operation.

Update note: Slice 061 supersedes this slice's deferred `reduce` item by adding collection-aware `reduce`. Slice 062 adds collection-specific `collect`; `map` remains list-only.

## Requirements

- `filter(predicate, list)` shall keep the existing list result behavior.
- `select(predicate, list)` shall behave the same as `filter(predicate, list)`.
- `filter(predicate, collection)` shall accept `Set` and `Bag` collection objects.
- `select(predicate, collection)` shall accept `Set` and `Bag` collection objects.
- Both builtins shall also accept objects whose class inherits from `Set` or `Bag`.
- Collection filtering shall return a new collection object instead of mutating the input object.
- The returned collection object shall keep the same runtime class as the input collection object.
- The returned collection object shall preserve user-visible attributes from the input collection object.
- Filtering a `Set` shall keep values whose predicate result is `true`.
- Filtering a `Bag` shall keep every occurrence whose predicate result is `true`.
- Filtering an empty `Set` or `Bag` shall return an empty collection object.
- Predicate results shall still be required to be boolean values.
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

- `select` over ordinary lists.
- `filter` over empty `Set` and `Bag` objects.
- filtering populated `Set` objects with kept and rejected values.
- filtering populated `Bag` objects while preserving duplicate occurrences.
- `select` over populated `Set` and `Bag` objects.
- partial application of `filter` and `select` with collection objects.
- higher-order use over lists that contain collection objects.
- subclass objects of `Set` and `Bag`.
- attribute preservation.
- object identity filtering.

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
