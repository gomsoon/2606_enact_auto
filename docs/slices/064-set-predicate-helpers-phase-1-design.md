# Slice 064: Set Predicate Helpers Phase 1 Design

Related requirements: [docs/slices/064-set-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/064-set-predicate-helpers-phase-1-requirements.md)

Update note: Slice 070 extends these helpers to same-kind `Bag` operands with multiplicity-aware subset and equality.

## Set-Only Predicate Surface

This slice introduces two builtins:

```text
subset(left_set, right_set)
equal(left_set, right_set)
```

Both operands must be object-backed `Set` values in this slice. Objects whose classes inherit from `Set` are accepted through the existing collection-kind check. `Bag`, ordinary list, class, and non-collection object operands remain outside this slice.

## Payload Membership Helper

The Set payload is already represented as an internal duplicate-suppressed list. `subset` therefore walks the left payload and checks each value against the right payload using the existing membership helper:

```c
enact_builtin_list_contains_value(...)
```

That helper delegates to `enact_value_equal`, so primitive equality, class identity, function identity, and object identity follow the same rules as existing list and Set operations.

## Equality As Mutual Subset

Set `equal` is defined as:

```text
subset(left_set, right_set) and subset(right_set, left_set)
```

The implementation short-circuits when the left payload is not a subset of the right payload. This keeps the behavior simple and order-agnostic without adding a new collection equality model.

## Boolean Result Shape

Both helpers return ordinary boolean values. They do not return collection objects and do not mutate either operand.

## Deliberately Narrow Scope

The helpers compare payload membership only. Runtime class and user-visible attributes on collection objects are ignored for `equal`, which makes it a Set predicate rather than an object equality operation. Slice 065 adds Set-aware `add`; Slice 066 adds ordinary list-of-Set aggregate `UNION`. Bag multiplicity semantics are deferred in this slice and later added by Slice 070. Dot-method collection syntax remains deferred. Slice 073 later adds kind-aware collection payload display.
