# Slice 065: Set add Builtin Core Design

Related requirements: [docs/slices/065-set-add-builtin-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/065-set-add-builtin-core-requirements.md)

## Set-Specific Surface

This slice introduces:

```text
add(value, set)
```

`add` is intentionally Set-only. It accepts object-backed `Set` values, including subclass instances, and rejects `Bag`, ordinary list, class, and non-collection object operands.

## Reused Insert Semantics

The existing `insert(value, collection)` builtin already implements the runtime mechanics needed by `add`:

- duplicate suppression for Set payloads.
- value equality through `enact_value_equal`.
- object identity semantics for object elements.
- non-mutating collection-copy construction.
- runtime class and attribute preservation.

`add` first validates that its second argument is a Set collection object, then delegates to the existing `insert` implementation. This keeps Set insertion semantics in one place while narrowing the public surface for the manual-style Set helper.

## Result Shape

`add` returns a collection object, not a boolean and not a list. Tests observe the result through `size`, `member`, `subset`, `equal`, `attrs`, `classof`, `all`, and `reduce` rather than relying on collection printing order.

## Deliberately Narrow Scope

This slice does not change `insert`, does not add Bag-specific `add`, and does not introduce dot-method collection syntax. Slice 066 adds ordinary list-of-Set aggregate `UNION`; Bag multiplicity semantics and custom collection printing remain deferred.
