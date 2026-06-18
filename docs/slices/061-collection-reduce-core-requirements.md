# Slice 061: Collection Reduce Core Requirements

## Goal

Slice 061 extends `reduce` so it can fold object-backed `Set` and `Bag` payloads while preserving existing list and partial-application behavior.

## Requirements

- `reduce(reducer, initial, list)` shall keep the existing list fold behavior.
- `reduce(reducer, initial, collection)` shall accept `Set` and `Bag` collection objects.
- `reduce` shall also accept objects whose class inherits from `Set` or `Bag`.
- Empty `Set` and `Bag` collection payloads shall return a copy of the initial accumulator, matching empty-list behavior.
- The reducer shall be applied as a callable with two arguments: the current accumulator and the current collection element.
- The accumulator and final result may be any runtime value.
- Collection traversal shall use the collection object's hidden payload list.
- Tests shall not depend on any user-visible iteration ordering for `Set` or `Bag`.
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

- empty `Set` and `Bag` folds.
- integer sum and element-count folds over populated `Set` objects.
- integer sum and occurrence-count folds over populated `Bag` objects.
- boolean accumulator folds.
- partial application of `reduce` with collection objects.
- higher-order use over lists that contain collection objects.
- subclass objects of `Set` and `Bag`.
- object identity traversal.
- folds over collection results from `filter`, `select`, and `remove`.
- collection accumulators built with `insert`.

Robustness coverage shall include:

- arity mismatch.
- non-callable reducers.
- non-list, non-collection traversal inputs.
- reducer arity mismatch.
- reducer evaluation type errors.
- reducer evaluation name errors.
- traversal argument evaluation errors.
- accumulator type mismatches.
- misuse of non-integer and non-boolean reduce results.

## Deferred

- Collection-aware `map` remains deferred.
- Collection-aware `union`, `difference`, and `intersection` remain deferred.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
