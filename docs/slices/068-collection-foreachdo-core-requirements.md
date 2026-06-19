# Slice 068: Collection forEachDo Core Requirements

## Goal

Slice 068 adds `forEachDo(action, input)` as a side-effect-oriented traversal builtin for ordinary lists and object-backed `Set`/`Bag` collections.

## Requirements

- The builtin table shall include `forEachDo` with arity 2.
- `forEachDo(action, input)` shall accept ordinary lists, `Set` objects, and `Bag` objects.
- `forEachDo` shall also accept objects whose class inherits from `Set` or `Bag`.
- The first argument shall be callable.
- The action shall be applied once to each traversed element with one argument.
- The action result shall be ignored and released.
- `forEachDo` shall return `nil` after successful traversal.
- Empty ordinary lists, empty `Set` objects, and empty `Bag` objects shall return `nil` without invoking the action.
- `forEachDo` shall not mutate collection payloads by itself.
- Side effects performed by the action, such as object attribute assignment, shall be preserved.
- Partial application shall follow the existing builtin partial application rules.
- Non-list and non-collection traversal inputs shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Action evaluation failures shall stop traversal and propagate the original diagnostic.

## Regression Requirements

Boundary coverage shall include:

- ordinary list traversal.
- empty ordinary list, `Set`, and `Bag` traversal.
- action results being ignored.
- object attribute side effects.
- populated `Set` traversal.
- populated `Bag` traversal with duplicate occurrences.
- partial application of `forEachDo`.
- higher-order use over ordinary lists of `forEachDo` results.
- subclass objects of `Set` and `Bag`.
- object identity-sensitive actions.
- composition with `filter`, `collect`, `remove`, and `UNION`.
- atom and string payload traversal.

Robustness coverage shall include:

- arity mismatch.
- non-callable actions.
- non-list and non-collection traversal inputs.
- action arity mismatch.
- action evaluation type, name, arithmetic, function-call, and attribute errors.
- traversal argument evaluation errors.
- misuse of the `nil` result where primitive, bool, non-empty-list, or equality-compatible values are required.

## Deferred

- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.
- A richer unit value remains deferred; `nil` is the successful traversal result in this slice.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
