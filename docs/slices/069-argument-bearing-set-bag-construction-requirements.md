# Slice 069: Argument-Bearing set(...) / bag(...) Construction Requirements

## Goal

Slice 069 lets the existing `set` and `bag` constructors populate collection payloads from ordinary ENACT lists while keeping the zero-argument constructor forms from Slice 055.

## Requirements

- `set()` shall continue to return a new empty object whose class is the current `Set` binding.
- `bag()` shall continue to return a new empty object whose class is the current `Bag` binding.
- `set(list_value)` shall accept one ordinary ENACT list argument.
- `bag(list_value)` shall accept one ordinary ENACT list argument.
- `set(list_value)` shall return a `Set` collection object populated from the list with duplicate values suppressed by existing runtime equality.
- `bag(list_value)` shall return a `Bag` collection object populated from the list with duplicate occurrences preserved.
- Empty list arguments shall produce empty collection objects.
- Constructor results shall keep using the current environment binding for `Set` and `Bag`, matching the existing `set()` and `bag()` behavior.
- Constructor results shall work with the existing collection builtins such as `size`, `member`, `map`, `reduce`, `filter`, `locate`, `forEachDo`, `union`, and `equal`.
- `set` and `bag` shall support builtin arity range `0..1`.
- `enact_builtin_arity()` shall keep reporting the maximum builtin arity.
- A new `enact_builtin_min_arity()` helper shall expose the minimum builtin arity for evaluation and unit-test use.
- Over-application with two or more arguments shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating extra arguments.
- Non-list single arguments shall report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Evaluation errors in the accepted single argument shall propagate normally.

## Regression Requirements

Boundary coverage shall include:

- empty list conversion for `Set` and `Bag`.
- duplicate suppression for `Set`.
- duplicate preservation for `Bag`.
- membership checks over constructed collections.
- higher-order use through partially applied builtins.
- reduction, filtering, locating, and side-effect traversal over constructed collections.
- set operations over constructed sets.
- constructor results assigned to variables.
- subclass-aware construction through rebinding `Set`.
- object identity values inside constructor lists.

Robustness coverage shall include:

- non-list constructor arguments.
- over-application with unevaluated failing extra arguments.
- accepted argument evaluation errors.
- shadowed `Set`, `Bag`, `set`, and `bag` bindings.
- misuse of constructed collections as integers, booleans, and ordinary lists.
- collection-operation type mismatches.
- rebinding `Set` to a non-`Set` class.

## Deferred

- Literal collection syntax beyond ordinary list conversion remains deferred.
- Dot-method collection construction remains deferred.
- Custom collection printing remains deferred.
- Bag-aware binary algebraic operations are deferred in this slice and later added by Slice 071.
- Bag-aware aggregate `UNION` is deferred in this slice and later added by Slice 072.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
