# Slice 072: Bag Aggregate UNION Phase 2 Requirements

## Goal

Slice 072 extends the aggregate `UNION` builtin so an ordinary list of `Bag` collection objects produces a multiplicity-aware Bag union while preserving the existing list-of-Set aggregate behavior.

## Requirements

- `UNION(list_of_sets)` shall keep its existing `Set` aggregate behavior.
- `UNION(list_of_bags)` shall accept an ordinary ENACT list whose elements are `Bag` collection objects.
- Elements whose classes inherit from `Bag` shall be accepted.
- `UNION(())` shall continue to return a new empty root `Set` object because an empty input list has no collection kind to infer.
- For non-empty Bag input, `UNION` shall return a new collection object instead of mutating any input Bag.
- For non-empty Bag input, the returned collection object shall keep the same runtime class as the first Bag in the input list.
- For non-empty Bag input, the returned collection object shall preserve user-visible attributes from the first Bag in the input list.
- The returned Bag shall contain each value with occurrence count equal to the maximum occurrence count across all input Bags.
- Multiplicity comparison shall use existing runtime value equality, including object identity semantics.
- Nested Bag `UNION` results shall be accepted as ordinary Bag inputs.
- `UNION(list_of_bags)` shall support existing builtin partial-application behavior.
- Passing a Set or Bag directly as the argument shall remain unsupported; the input must be an ordinary list.
- Mixed `Set`/`Bag` aggregate input shall remain unsupported and report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Non-collection list elements, class values, and non-collection objects shall remain unsupported and report `ENACT_ERR_TYPE_EXPECTED_LIST`.
- Tests shall not depend on any user-visible iteration ordering for `Bag` payloads.

## Regression Requirements

Boundary coverage shall include:

- existing empty aggregate input returning a Set.
- single empty Bag input.
- single populated Bag input.
- multiple populated Bag inputs.
- duplicate multiplicity maxima across input Bags.
- equivalence with binary Bag `union`.
- composition with `subset`, `equal`, `collect`, `filter`, `reduce`, and `map`.
- partial application of `UNION`.
- first-Bag subclass preservation.
- first-Bag attribute preservation.
- object identity multiplicity.
- nested Bag `UNION` results.
- existing Set aggregate behavior after the Bag extension.

Robustness coverage shall include:

- arity mismatch before evaluating extra arguments.
- direct Set/Bag/non-list argument rejection.
- mixed `Set`/`Bag` element rejection.
- non-collection list element rejection.
- class and non-collection object element rejection.
- operand evaluation errors.
- shadowed builtin names.
- misuse of returned Bag objects where primitive or list values are required.

## Deferred

- Collection-input aggregate forms remain deferred in this slice and are later added by Slice 077.
- Dot-method collection syntax remains deferred in this slice and is later extended to aggregate `UNION` by Slice 077.
- Custom collection printing is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
