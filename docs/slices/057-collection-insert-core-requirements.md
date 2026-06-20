# Slice 057: Collection Insert Core for Set/Bag Requirements

## Goal

Slice 057 adds the first payload-producing collection operation for `Set` and `Bag`: `insert(value, collection)`.

## Requirements

- The builtin table shall include `insert` with arity 2.
- `insert(value, collection)` shall accept `Set` and `Bag` collection objects.
- `insert(value, collection)` shall also accept objects whose class inherits from `Set` or `Bag`.
- `insert` shall return a new collection object instead of mutating the input object.
- The returned collection object shall keep the same runtime class as the input collection object.
- The returned collection object shall preserve user-visible attributes from the input collection object.
- For `Set` objects, inserting a value already present in the payload shall not increase the payload size.
- For `Bag` objects, inserting a value already present in the payload shall add another occurrence.
- `size` and `member` shall observe values added by `insert`.
- `insert` shall support normal builtin partial application.
- Non-collection second arguments shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Existing list behavior shall remain unchanged.
- Builtins not in this slice shall remain list-only for collection objects:
  - `append`
  - `remove`
  - `union`
  - `difference`
  - `intersection`
  - higher-order list traversals that require a list as their collection input

## Regression Requirements

Boundary coverage shall include:

- inserting into an empty `Set` and checking `size`.
- inserting into an empty `Set` and checking `member`.
- inserting a duplicate into a `Set`.
- inserting duplicate values into a `Bag`.
- preserving the original collection object.
- preserving the collection object's runtime class.
- preserving subclasses of `Set` and `Bag`.
- preserving user attributes.
- using `insert` through partial application and higher-order list builtins.
- inserting strings and object values.

Robustness coverage shall include:

- arity mismatch.
- value and collection argument evaluation errors.
- rejecting integers, `nil`, classes, and non-collection objects as the second argument.
- using returned collection objects with operators that still expect primitive values or lists.
- shadowing `insert` with a non-function binding.

## Deferred

- Collection-aware `remove` remains deferred for this slice. Slice 063 later adds Set-aware `union`, `difference`, and `intersection`; Slice 071 later adds same-kind Bag support for those binary operations.
- Dot-method collection syntax remains deferred.
- Custom collection printing is deferred in this slice and later added by Slice 073.
- Canonical ordering guarantees for collection printing remain deferred; Slice 073 later displays the current payload order.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
