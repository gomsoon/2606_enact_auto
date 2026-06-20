# Slice 071: Bag Algebraic Operations Phase 1 Requirements

## Goal

Slice 071 extends the existing binary `union`, `difference`, and `intersection` builtins so they operate on object-backed `Bag` values using multiplicity-aware algebra while preserving existing list and `Set` behavior.

## Requirements

- `union(list, list)`, `difference(list, list)`, and `intersection(list, list)` shall keep their existing list result behavior.
- `union(set, set)`, `difference(set, set)`, and `intersection(set, set)` shall keep their existing `Set` behavior.
- `union(bag, bag)` shall accept `Bag` collection objects and objects whose class inherits from `Bag`.
- `difference(bag, bag)` shall accept `Bag` collection objects and objects whose class inherits from `Bag`.
- `intersection(bag, bag)` shall accept `Bag` collection objects and objects whose class inherits from `Bag`.
- Bag operations shall return a new collection object instead of mutating either input object.
- The returned collection object shall keep the same runtime class as the left operand.
- The returned collection object shall preserve user-visible attributes from the left operand.
- `union(left_bag, right_bag)` shall contain each value with occurrence count `max(count(left_bag, value), count(right_bag, value))`.
- `difference(left_bag, right_bag)` shall contain each value with occurrence count `max(count(left_bag, value) - count(right_bag, value), 0)`.
- `intersection(left_bag, right_bag)` shall contain each value with occurrence count `min(count(left_bag, value), count(right_bag, value))`.
- Multiplicity comparison shall use existing runtime value equality, including object identity semantics.
- Tests shall not depend on any user-visible iteration ordering for `Bag` payloads.
- Mixed `Set`/`Bag`, list/Bag, class, and non-collection object operands shall remain unsupported and report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Existing partial-application behavior shall apply to all three builtins.

## Regression Requirements

Boundary coverage shall include:

- empty Bag operations.
- `union` with left-only, right-only, and duplicate values.
- `difference` with kept, removed, clipped-to-empty, and duplicate results.
- `intersection` with matching, disjoint, and duplicate values.
- partial application of `union` with Bag objects.
- higher-order use over lists containing Bag-operation results.
- composition with `filter`, `reduce`, `map`, `size`, `member`, and `subset`.
- left-operand subclass preservation.
- left-operand attribute preservation.
- object identity membership.
- existing Set operation behavior after the Bag extension.

Robustness coverage shall include:

- mixed `Set`/`Bag` operand rejection.
- mixed ordinary list/Bag operand rejection.
- class and non-collection object operand rejection.
- arity mismatch before evaluating extra arguments.
- operand evaluation errors.
- shadowed builtin names.
- misuse of returned Bag objects where primitive or list values are required.

## Deferred

- Bag-aware aggregate `UNION` semantics are deferred in this slice and later added by Slice 072.
- Dot-method collection syntax remains deferred.
- Custom collection printing is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
