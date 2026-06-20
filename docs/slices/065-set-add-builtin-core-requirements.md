# Slice 065: Set add Builtin Core Requirements

## Goal

Slice 065 adds `add(value, set)` as a Set-specific insertion helper for object-backed `Set` values.

## Requirements

- `add(value, set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- `add(value, set)` shall return a new collection object instead of mutating the input Set.
- The returned collection object shall keep the same runtime class as the input Set.
- The returned collection object shall preserve user-visible attributes from the input Set.
- Adding a value that is not already a member shall produce a Set containing that value.
- Adding a value that is already a member shall suppress the duplicate and preserve Set cardinality.
- Membership shall use existing runtime value equality, including object identity semantics.
- `add` shall support arbitrary existing value kinds as the element value.
- `add(value)` shall continue to use existing builtin partial-application behavior.
- `Bag` operands shall remain unsupported in this slice.
- Ordinary list operands shall remain unsupported in this slice.
- Unsupported collection operands shall report `ENACT_ERR_TYPE_EXPECTED_LIST`, matching the existing collection helper diagnostics.
- Existing `insert(value, collection)` behavior shall remain unchanged.

## Regression Requirements

Boundary coverage shall include:

- adding to an empty Set.
- membership after add.
- duplicate suppression.
- equivalence with existing `insert` for Set payloads.
- composition with `subset`, `equal`, `union`, `collect`, `all`, and `reduce`.
- string and quoted atom element values.
- partial application of `add`.
- Set subclass preservation.
- attribute preservation.
- input Set immutability.
- same-object duplicate suppression.
- distinct-object identity membership.

Robustness coverage shall include:

- arity mismatch.
- Bag operand rejection.
- ordinary list operand rejection.
- class and non-collection object operand rejection.
- operand evaluation errors.
- misuse of returned Set objects where primitive or list values are required.
- partial-application misuse.

## Deferred

- Slice 066 adds ordinary list-of-Set aggregate `UNION`.
- Bag-aware predicate semantics are deferred in this slice and later added by Slice 070.
- Bag-aware binary `union`, `difference`, and `intersection` are deferred in this slice and later added by Slice 071.
- Bag-aware aggregate `UNION` is deferred in this slice and later added by Slice 072.
- Dot-method collection syntax remains deferred.
- Custom collection printing is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
