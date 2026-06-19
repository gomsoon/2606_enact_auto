# Slice 067: Collection locate Core Requirements

## Goal

Slice 067 adds `locate(predicate, input)` as a first-match traversal builtin for ordinary lists and object-backed `Set`/`Bag` collections.

## Requirements

- The builtin table shall include `locate` with arity 2.
- `locate(predicate, input)` shall accept ordinary lists, `Set` objects, and `Bag` objects.
- `locate` shall also accept objects whose class inherits from `Set` or `Bag`.
- The first argument shall be callable.
- The predicate shall be applied once to each traversed element until it returns `true`.
- The predicate result shall be a bool.
- `locate` shall return a copy of the first matching element.
- `locate` shall return `nil` when the input is empty.
- `locate` shall return `nil` when no element matches.
- `locate` shall not mutate collection payloads or user-visible object attributes.
- Partial application shall follow the existing builtin partial application rules.
- Non-list and non-collection traversal inputs shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Predicate evaluation failures shall propagate the original diagnostic.

## Regression Requirements

Boundary coverage shall include:

- finding a value in an ordinary list.
- no-match and empty-list results.
- empty `Set` and `Bag` traversal.
- populated `Set` and `Bag` traversal.
- atom, string, and object values returned as located elements.
- partial application of `locate`.
- higher-order use over ordinary lists of collections.
- subclass objects of `Set` and `Bag`.
- composition with `filter`, `collect`, `remove`, and `UNION`.

Robustness coverage shall include:

- arity mismatch.
- non-callable predicates.
- non-list and non-collection traversal inputs.
- predicates that return non-bool values.
- predicate arity mismatch.
- predicate evaluation type, name, and arithmetic errors.
- traversal argument evaluation errors.
- misuse of returned values where primitive, bool, list, or equality-compatible values are required.

## Deferred

- A distinct not-found sentinel is deferred; `nil` is both the empty-list value and the no-match result.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.
- Slice 068 adds list/collection-aware `forEachDo`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
