# Slice 066: Set UNION Aggregate Core Requirements

## Goal

Slice 066 adds `UNION(list_of_sets)` as an aggregate Set union helper.

## Requirements

- `UNION(list_of_sets)` shall accept an ordinary ENACT list whose elements are `Set` collection objects.
- Elements whose classes inherit from `Set` shall be accepted.
- `UNION(())` shall return a new empty root `Set` object.
- For non-empty input, `UNION` shall return a new collection object instead of mutating any input Set.
- For non-empty input, the returned collection object shall keep the same runtime class as the first Set in the input list.
- For non-empty input, the returned collection object shall preserve user-visible attributes from the first Set in the input list.
- The returned Set shall contain every value from every input Set.
- Duplicate values shall be suppressed using existing runtime value equality.
- Object elements shall use existing object identity semantics.
- Nested aggregate results shall be accepted as ordinary Set inputs.
- `UNION(list_of_sets)` shall support existing builtin partial-application behavior.
- Passing a Set directly as the argument shall remain unsupported in this slice; the input must be a list.
- `Bag` elements shall remain unsupported in this slice; Slice 072 later adds same-kind Bag aggregate support.
- Mixed list/Set aggregate input forms other than an ordinary list of Set objects shall remain unsupported.
- Unsupported operands shall continue to report `ENACT_ERR_TYPE_EXPECTED_LIST`.

## Regression Requirements

Boundary coverage shall include:

- empty aggregate input.
- single empty Set input.
- single populated Set input.
- multiple populated Set inputs.
- duplicate suppression across input Sets.
- equivalence with binary `union`.
- composition with `subset`, `equal`, `add`, `collect`, `all`, and `reduce`.
- partial application of `UNION`.
- first-Set subclass preservation.
- first-Set attribute preservation.
- object identity membership.
- distinct-object membership.
- nested `UNION` results.

Robustness coverage shall include:

- arity mismatch.
- direct Set/Bag/non-list argument rejection.
- Bag element rejection.
- non-Set list element rejection.
- operand evaluation errors.
- misuse of returned Set objects where primitive or list values are required.

## Deferred

- Bag-aware aggregate union semantics are deferred in this slice and later added by Slice 072.
- Collection-input aggregate forms remain deferred in this slice and are later added by Slice 077.
- Dot-method collection syntax remains deferred in this slice and is later extended to aggregate `UNION` by Slice 077.
- Custom collection printing is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
