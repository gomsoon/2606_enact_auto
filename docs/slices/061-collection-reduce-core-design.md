# Slice 061: Collection Reduce Core Design

Related requirements: [docs/slices/061-collection-reduce-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/061-collection-reduce-core-requirements.md)

Update note: Slice 062 adds collection-specific `collect`; `map` remains list-only.

## Shared Traversal Input

`reduce` now accepts the same traversal input shape used by collection-aware `all`, `exists`, `filter`, and `select`:

```c
enact_builtin_require_list_or_collection(...)
```

This keeps ordinary list behavior intact while allowing object-backed `Set` and `Bag` values to expose their hidden payload list to reducer traversal.

## Accumulator Semantics

The fold loop is unchanged after input resolution:

- copy the initial accumulator
- visit each payload element
- apply the reducer as `reducer(accumulator, element)`
- release the previous accumulator after a successful reducer result
- return the final accumulator

Empty collection payloads therefore return the initial accumulator copy, matching the established empty-list behavior.

## Collection Ordering

The runtime intentionally does not expose a user-visible iteration order guarantee for collection objects. Regression tests use commutative sums, element counts, boolean folds, and size checks so they verify traversal without depending on `Set` or `Bag` printing order.

## Error Propagation

Reducer validation and application still use the existing callable machinery. Non-callable reducers, reducer arity errors, type errors, name errors, divide-by-zero errors, and result misuse all propagate through the same paths used by list `reduce`.

Non-list, non-collection traversal inputs continue to report:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

## Deliberately Narrow Scope

`reduce` returns the reducer's accumulator value and does not construct a new collection result by itself. Collection-aware `map`, set-operation builtins, dot-method syntax, and custom collection printing remain deferred. Use `collect` for collection-shape-preserving transforms.
