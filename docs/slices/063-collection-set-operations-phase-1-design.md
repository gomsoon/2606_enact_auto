# Slice 063: Collection Set Operations Phase 1 Design

Related requirements: [docs/slices/063-collection-set-operations-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/063-collection-set-operations-phase-1-requirements.md)

## Dual Input Surface

`union`, `difference`, and `intersection` keep their original list behavior when the left operand is a list.

When the left operand is a collection object, this slice routes to a Set-only path:

```text
union(left_set, right_set)
difference(left_set, right_set)
intersection(left_set, right_set)
```

The right operand must also be a `Set` collection object. `Bag` and mixed list/Set operations remain outside this slice. Slice 071 later adds same-kind Bag support for the same binary builtin names.

## Reused List Algorithms

The Set payload is already stored as an internal list with duplicate suppression provided by `insert` and `collect`. The Set-operation path therefore reuses the existing list helpers over hidden payloads:

```c
enact_builtin_difference_lists(...)
enact_builtin_append_lists(...)
enact_builtin_intersection_lists(...)
```

`union` follows the existing list rule:

```text
append(difference(left, right), right)
```

For Set payloads, that produces an observed Set containing values from either operand without introducing duplicates.

## Result Construction

Set operations wrap their result payload with:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The left operand is the prototype object, so the result preserves the left operand's runtime class and user-visible attributes.

## Order-Agnostic Tests

The runtime still does not expose a user-visible collection printing order. Regression tests verify Set-operation results through `size`, `member`, `reduce`, `all`, and `map(size, ...)` over ordinary lists of collection results.

## Deliberately Narrow Scope

This slice does not define Bag multiplicity semantics for `union`, `difference`, or `intersection`; Slice 071 later adds those binary Bag operations. Slice 064 adds Set-aware `subset` and `equal`; Slice 065 adds Set-aware `add`; Slice 066 adds ordinary list-of-Set aggregate `UNION`; Slice 072 later adds list-of-Bag aggregate `UNION`. Dot-method collection syntax and custom collection printing remain deferred.
