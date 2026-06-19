# Slice 064: Set Predicate Helpers Phase 1 Requirements

## Goal

Slice 064 adds Set-specific predicate helpers `subset` and `equal` for object-backed `Set` values.

Update note: Slice 070 later extends `subset` and `equal` to same-kind `Bag` operands using multiplicity-aware semantics. Mixed `Set`/`Bag` operands remain unsupported.

## Requirements

- `subset(left_set, right_set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- `equal(left_set, right_set)` shall accept `Set` collection objects and objects whose class inherits from `Set`.
- `subset(left_set, right_set)` shall return `true` when every value in the left payload is a member of the right payload.
- `subset(set(), any_set)` shall return `true`.
- `subset(non_empty_set, set())` shall return `false`.
- `equal(left_set, right_set)` shall return `true` when both operands contain the same payload values, independent of payload order.
- `equal(left_set, right_set)` shall be implemented as mutual subset comparison.
- Membership shall use existing runtime value equality, including object identity semantics.
- Predicate results shall be ordinary boolean values.
- Predicate helpers shall not mutate either operand.
- Predicate helpers shall ignore collection object runtime class and user-visible attributes when comparing payload membership.
- `Bag` operands shall remain unsupported in this slice; Slice 070 later adds same-kind `Bag` support.
- Ordinary list operands shall remain unsupported in this slice.
- Mixed list/Set operands shall remain unsupported in this slice.
- Unsupported operands shall continue to report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Existing partial-application behavior shall apply to both builtins.

## Regression Requirements

Boundary coverage shall include:

- empty Set subset and equality.
- empty-left and empty-right subset behavior.
- single-element and multi-element subset success/failure.
- same-payload and different-payload equality.
- equality composed with `union`, `difference`, `intersection`, and `collect`.
- higher-order use through list `all` and `map`.
- partial application of `subset`.
- Set subclass operands.
- attributes ignored for payload equality.
- object identity membership.

Robustness coverage shall include:

- arity mismatch.
- mixed Set/Bag operand rejection.
- ordinary list operand rejection.
- class and non-collection object operand rejection.
- operand evaluation errors.
- misuse of returned booleans where primitive, list, or equality-compatible values are required.

## Deferred

- Bag-aware `subset` and `equal` are deferred in this slice and later added by Slice 070.
- Slice 065 adds Set-aware `add`. Slice 066 adds ordinary list-of-Set aggregate `UNION`.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
