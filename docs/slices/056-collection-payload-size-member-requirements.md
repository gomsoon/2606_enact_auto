# Slice 056: Collection Payload Core + size/member for Set/Bag Requirements

## Goal

Slice 056 gives `Set` and `Bag` objects a hidden collection payload and lets the existing `size` and `member` builtins read that payload.

## Requirements

- Objects whose class is `Set` or `Bag` shall carry a hidden collection payload.
- Objects whose class inherits from `Set` or `Bag` shall carry the same hidden collection payload kind.
- Empty collection payloads shall not appear in `attrs(object)`.
- `set()` and `bag()` shall continue to return `<object Set>` and `<object Bag>`.
- `new Set` and `new Bag` shall produce empty collection objects.
- `size(collection)` shall return `0` for an empty `Set` or `Bag` object.
- `member(value, collection)` shall return `false` for an empty `Set` or `Bag` object.
- `size` and `member` shall preserve all existing list behavior.
- Non-collection objects and classes shall still report `ENACT_ERR_TYPE_EXPECTED_LIST` when passed to `size` or as the second argument to `member`.
- Builtins not in this slice shall remain list-only:
  - `append`
  - `remove`
  - `union`
  - `difference`
  - `intersection`
  - higher-order list traversals such as `map`, `filter`, and `reduce`

## Regression Requirements

Boundary coverage shall include:

- `size(set())` and `size(bag())`.
- `member` on empty `Set` and `Bag` objects.
- `new Set` and `new Bag`.
- `attrs` staying empty for collection objects.
- higher-order use through lists that contain collection objects.
- partial application of `member` over a collection object.
- subclass objects of `Set` and `Bag`.

Robustness coverage shall include:

- `size` and `member` rejecting non-collection objects.
- `size` and `member` rejecting class values.
- arity mismatch before evaluating extra arguments.
- first-argument evaluation errors for `member`.
- still-list-only builtins rejecting `Set`/`Bag` objects.

## Deferred

- Populating collection payloads remains deferred.
- Mutating or functional collection operations such as `insert`, `remove`, `union`, `difference`, and `intersection` on collection objects remain deferred.
- Dot-method collection syntax such as `set().size()` remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
