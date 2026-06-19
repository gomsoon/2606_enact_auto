# Slice 062: Collection Transform Core: collect Requirements

## Goal

Slice 062 adds `collect(transform, collection)` as the collection-shape-preserving transform operation for object-backed `Set` and `Bag` values.

Update note: Slice 063 adds Set-aware `union`, `difference`, and `intersection`. Slice 064 adds Set-aware `subset` and `equal`. Bag-aware set operations remain deferred.

## Requirements

- The builtin table shall include `collect` with arity 2.
- `collect(transform, collection)` shall accept `Set` and `Bag` collection objects.
- `collect` shall also accept objects whose class inherits from `Set` or `Bag`.
- The first argument shall be callable.
- The transform shall be applied once to each payload element with one argument.
- `collect` shall return a new collection object instead of mutating the input object.
- The returned collection object shall keep the same runtime class as the input collection object.
- The returned collection object shall preserve user-visible attributes from the input collection object.
- Collecting an empty `Set` or `Bag` shall return an empty collection object.
- For `Set` objects, duplicate transformed values shall be suppressed using existing runtime value equality.
- For `Bag` objects, every transformed occurrence shall be preserved.
- Existing list `map` behavior shall remain unchanged and list-only.
- `collect` shall reject ordinary lists; list transforms continue to use `map`.
- Non-collection second arguments shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Builtins not in this slice shall remain list-only for collection objects:
  - `map`
  - `append`
  - `union`
  - `difference`
  - `intersection`

## Regression Requirements

Boundary coverage shall include:

- empty `Set` and `Bag` transforms.
- transforms over populated `Set` objects.
- transforms over populated `Bag` objects.
- duplicate transformed values being suppressed for `Set`.
- duplicate transformed values being preserved for `Bag`.
- partial application of `collect`.
- higher-order use over lists that contain collected collection objects.
- subclass objects of `Set` and `Bag`.
- user-visible attribute preservation.
- object identity transforms.
- composition with `filter`, `select`, `remove`, `reduce`, and `all`.
- transforms that return function values.

Robustness coverage shall include:

- arity mismatch.
- non-callable transforms.
- non-collection traversal inputs, including ordinary lists.
- transform arity mismatch.
- transform evaluation type errors.
- transform evaluation name errors.
- collection argument evaluation errors.
- misuse of returned collection objects where primitive or list values are required.

## Deferred

- Collection-aware `map` remains deferred; `collect` is the collection-transform surface.
- Bag-aware `union`, `difference`, and `intersection` remain deferred.
- `forEachDo`, `locate`, `add`, and `UNION` remain deferred.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
