# Slice 070: Bag Multiplicity Predicates Requirements

## Goal

Slice 070 extends `subset` and `equal` to object-backed `Bag` values using multiplicity-aware semantics.

## Requirements

- `subset(left_bag, right_bag)` shall accept `Bag` collection objects and objects whose class inherits from `Bag`.
- `equal(left_bag, right_bag)` shall accept `Bag` collection objects and objects whose class inherits from `Bag`.
- Existing `Set` behavior for `subset` and `equal` shall remain unchanged.
- Mixed `Set`/`Bag` operands shall remain unsupported and report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Ordinary list operands shall remain unsupported and report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- `subset(left_bag, right_bag)` shall return `true` when every value occurs in `right_bag` at least as many times as it occurs in `left_bag`.
- `subset(bag(), any_bag)` shall return `true`.
- `subset(non_empty_bag, bag())` shall return `false`.
- `equal(left_bag, right_bag)` shall return `true` when both bags contain the same values with the same occurrence counts, independent of payload order.
- `equal(left_bag, right_bag)` shall be implemented as mutual multiplicity subset comparison.
- Multiplicity membership shall use existing runtime value equality, including object identity semantics.
- Predicate results shall be ordinary boolean values.
- Predicate helpers shall not mutate either operand.
- Predicate helpers shall ignore collection object runtime class and user-visible attributes when comparing payload contents.
- Existing partial-application behavior shall apply to both builtins.

## Regression Requirements

Boundary coverage shall include:

- empty Bag subset and equality.
- empty-left and empty-right subset behavior.
- single-occurrence and duplicate-occurrence subset success/failure.
- same-payload and different-multiplicity equality.
- order-independent Bag equality.
- composition with `filter`, `remove`, `all`, and `map`.
- partial application of `subset`.
- Bag subclass operands.
- attributes ignored for payload equality.
- object identity multiplicity.

Robustness coverage shall include:

- mixed Set/Bag operand rejection.
- ordinary list operand rejection.
- class and non-collection object operand rejection.
- arity mismatch before evaluating extra arguments.
- operand evaluation errors.
- shadowed builtin names.
- misuse of returned booleans where primitive, list, or equality-compatible values are required.

## Deferred

- Bag-aware binary `union`, `difference`, and `intersection` are deferred in this slice and later added by Slice 071.
- Bag-aware aggregate `UNION` remains deferred.
- Dot-method collection syntax remains deferred.
- Custom collection printing remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
