# Slice 063: Collection Set Operations Phase 1 Requirements

## Goal

Slice 063 extends the existing `union`, `difference`, and `intersection` builtins so they operate on object-backed `Set` values while preserving all existing list behavior.

Update note: Slice 064 adds Set-aware `subset` and `equal`. Slice 065 adds Set-aware `add`. Slice 066 adds Set-aware aggregate `UNION`. Slice 071 later adds same-kind Bag support for binary `union`, `difference`, and `intersection`.

## Requirements

- `union(list, list)`, `difference(list, list)`, and `intersection(list, list)` shall keep their existing list result behavior.
- `union(set, set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- `difference(set, set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- `intersection(set, set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- Set operations shall return a new collection object instead of mutating either input object.
- The returned collection object shall keep the same runtime class as the left operand.
- The returned collection object shall preserve user-visible attributes from the left operand.
- `union(left_set, right_set)` shall contain every value from either payload, with duplicates suppressed by the existing Set payload invariants.
- `difference(left_set, right_set)` shall contain values from the left payload that are not members of the right payload.
- `intersection(left_set, right_set)` shall contain values from the left payload that are members of the right payload.
- Membership shall use existing runtime value equality, including object identity semantics.
- Tests shall not depend on any user-visible iteration ordering for `Set` payloads.
- `Bag` operands shall remain unsupported in this slice; Slice 071 later adds same-kind Bag support.
- Mixed list/Set operands shall remain unsupported in this slice.
- Unsupported operands shall continue to report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Existing partial-application behavior shall remain unchanged.

## Regression Requirements

Boundary coverage shall include:

- empty Set operations.
- `union` with left-only, right-only, and duplicate values.
- `difference` with kept, removed, and empty results.
- `intersection` with matching and disjoint values.
- partial application of `union` with Set objects.
- higher-order use over lists containing Set-operation results.
- left-operand subclass preservation.
- left-operand attribute preservation.
- object identity membership.
- composition with `collect` and `reduce`.

Robustness coverage shall include:

- arity mismatch.
- mixed Set/Bag operand rejection.
- mixed list/Set operand rejection.
- class and non-collection object operand rejection.
- operand evaluation errors.
- misuse of returned Set objects where primitive or list values are required.

## Deferred

- Bag-aware binary `union`, `difference`, and `intersection` are deferred in this slice and later added by Slice 071.
- Bag-aware aggregate `UNION` semantics are deferred in this slice and later added by Slice 072. Slice 066 adds ordinary list-of-Set aggregate `UNION`.
- Dot-method collection syntax remains deferred.
- Custom collection printing is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
