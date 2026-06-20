# Slice 077: Collection Aggregate UNION Dot/Core Design

Related requirements: [docs/slices/077-collection-aggregate-union-dot-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/077-collection-aggregate-union-dot-core-requirements.md)

## Input Widening

Existing aggregate `UNION` already delegates all inner aggregation work to a shared helper:

```text
enact_builtin_union_aggregate_lists(collections, &prototype, &result, diag)
```

Slice 077 widens only the top-level input extraction:

```text
UNION(list_of_collections)
UNION(collection_of_collections)
```

Both forms produce the same internal `EnactList *collections` sequence before calling the existing aggregate helper.

## Empty Input

`UNION(())` already returns a fresh root `Set` because no first collection exists to infer a result kind or prototype.

Collection input follows the same rule:

```text
UNION(set()) -> set()
UNION(bag()) -> set()
set().UNION() -> set()
bag().UNION() -> set()
```

The outer collection kind is intentionally not used as the aggregate result kind. The outer collection is only a container for the collection values being aggregated.

## Dot Bridge

The evaluator bridge maps:

```text
collection.UNION() -> UNION(collection)
```

`UNION` is a one-argument environment-aware builtin, so the receiver occupies builtin argument slot zero and the method arity is zero.

The existing dot-call resolution order stays unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. collection dot-method bridge.

This keeps user-defined methods and object attributes able to shadow the native bridge, while top-level bindings named `UNION` do not affect dot calls.

## Semantics

No aggregate behavior is reimplemented in the evaluator. Dot calls delegate through `enact_builtin_apply_in_env`, so collection-input and list-input forms share:

- Set duplicate suppression.
- Bag multiplicity maxima.
- mixed-kind rejection.
- non-collection element rejection.
- prototype class and attribute preservation from the first contained collection.
- empty-input construction through the current environment's `Set` class binding.

## Deferred Work

`unitset` dot syntax remains deferred because it is a singleton-list constructor, not a receiver aggregate. Bound collection method values and native method-table integration also remain deferred.
