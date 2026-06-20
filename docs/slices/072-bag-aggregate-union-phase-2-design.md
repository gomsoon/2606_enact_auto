# Slice 072: Bag Aggregate UNION Phase 2 Design

Related requirements: [docs/slices/072-bag-aggregate-union-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/072-bag-aggregate-union-phase-2-requirements.md)

## Same Aggregate Surface

`UNION` keeps the same one-argument aggregate shape:

```text
UNION(collection_list)
```

The argument is still an ordinary ENACT list. Direct collection inputs remain unsupported:

```text
UNION(bag()) -> ENACT_ERR_TYPE_EXPECTED_LIST
UNION(set()) -> ENACT_ERR_TYPE_EXPECTED_LIST
```

## Kind Selection

For non-empty aggregate input, the first collection object determines the aggregate kind and result prototype:

```text
first Set -> Set aggregate union
first Bag -> Bag aggregate union
```

Every later element must be the same collection kind. Mixed `Set`/`Bag` aggregate inputs report `ENACT_ERR_TYPE_EXPECTED_LIST` rather than converting between duplicate-suppressed and multiplicity-aware semantics.

`UNION(())` keeps the Slice 066 behavior and constructs a fresh root `Set`, because there is no first element from which to infer `Bag`.

## Shared Union Helpers

The aggregate helper folds over hidden collection payload lists. Set aggregate input continues to call:

```c
enact_builtin_union_lists(...)
```

Bag aggregate input calls the Slice 071 helper:

```c
enact_builtin_bag_union_lists(...)
```

This yields the same Bag multiplicity rule as binary `union`:

```text
count(result, value) == max(count(input_i, value) for every input_i)
```

## Result Construction

Non-empty aggregate results are wrapped with:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The first collection object is the prototype, so Bag aggregate results preserve the first Bag's runtime class and user-visible attributes. This mirrors the existing Set aggregate behavior.

## Order-Agnostic Tests

Regression tests observe Bag aggregate payloads through `equal`, `subset`, `size`, `member`, `reduce`, and `map(size, ...)`. They avoid relying on collection printing or payload traversal order.

## Deliberately Narrow Scope

This slice adds Bag support to list-based `UNION` only. Collection-input aggregate forms and dot-method collection syntax remain deferred here; Slice 077 later adds collection-input and dot-method aggregate `UNION`. Slice 073 later adds kind-aware collection payload display.
