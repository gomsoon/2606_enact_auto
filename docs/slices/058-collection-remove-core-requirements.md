# Slice 058: Collection Remove Core for Set/Bag Requirements

## Goal

Slice 058 extends `remove(value, collection)` to object-backed `Set` and `Bag` payloads while preserving the existing list `remove` behavior.

## Requirements

- `remove(value, list)` shall keep the existing list result semantics.
- `remove(value, collection)` shall accept `Set` and `Bag` collection objects.
- `remove(value, collection)` shall also accept objects whose class inherits from `Set` or `Bag`.
- `remove` shall return a new collection object when its second argument is a collection object.
- The returned collection object shall keep the same runtime class as the input collection object.
- The returned collection object shall preserve user-visible attributes from the input collection object.
- Removing a value from a `Set` shall remove the matching payload value when present.
- Removing a missing value from a `Set` shall return a collection with the same observed membership and size.
- Removing a value from a `Bag` shall remove one matching occurrence when present.
- Removing a value from a `Bag` with repeated occurrences shall leave the remaining occurrences observable through `size` and `member`.
- Removing from an empty `Set` or `Bag` shall return an empty collection object.
- Non-list, non-collection second arguments shall continue to report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- `insert`, `size`, and `member` shall observe collection payloads produced by `remove`.
- Builtins not in this slice shall remain list-only for collection objects:
  - `append`
  - `union`
  - `difference`
  - `intersection`
  - higher-order list traversals that require a list as their collection input

## Regression Requirements

Boundary coverage shall include:

- removing from an empty `Set`.
- removing an existing value from a `Set`.
- removing a missing value from a `Set`.
- removing the only occurrence from a `Bag`.
- removing one occurrence from a `Bag` with duplicates.
- preserving the original collection object.
- preserving the collection object's runtime class.
- preserving subclasses of `Set` and `Bag`.
- preserving user attributes.
- using `remove` through partial application and higher-order list builtins.
- removing strings and object-identity values.

Robustness coverage shall include:

- arity mismatch.
- value and collection argument evaluation errors.
- rejecting integers, classes, and non-collection objects when a collection/list is required.
- using returned collection objects with operators that still expect primitive values or lists.
- shadowing `remove` with a non-function binding.

## Deferred

- Slice 063 later adds Set-aware `union`, `difference`, and `intersection`; Bag-aware set operations remain deferred.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.
- Slice 068 adds list/collection-aware `forEachDo`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
