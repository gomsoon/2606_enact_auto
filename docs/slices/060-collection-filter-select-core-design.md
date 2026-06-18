# Slice 060: Collection Filter/Select Core Design

Related requirements: [docs/slices/060-collection-filter-select-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/060-collection-filter-select-core-requirements.md)

Update note: Slice 061 adds collection-aware `reduce` over the same hidden payload traversal surface. `map` remains deferred.

## Filter And Select

`filter` remains the existing list-oriented builtin. `select` is added as a PRD-named alias for the same predicate filtering operation:

```text
filter(predicate, input)
select(predicate, input)
```

Both names share the same implementation so their list and collection behavior cannot drift.

## Dual Result Shape

The result shape follows the input shape:

- list input returns a list
- collection object input returns a collection object

This preserves all prior list tests while making object-backed `Set` and `Bag` values usable with predicate filtering.

## Functional Collection Update

Collection filtering reuses the existing recursive list filter over the hidden payload. It then wraps the filtered payload with:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The returned object keeps the same runtime class and clones user-visible attributes. The input collection object is not mutated.

## Set And Bag Semantics

`Set` payloads already suppress duplicates through `insert`, so filtering keeps or rejects each stored set value.

`Bag` payloads preserve occurrences:

```text
size(filter(x::x == 1, insert(1, insert(1, bag())))) == 2
```

This keeps `Bag` filtering aligned with Slice 058 one-occurrence removal and with the hidden payload representation.

## Deliberately Narrow Scope

`map` remains list-only for collection objects. It exposes broader result-shape questions, while `filter` and `select` can safely preserve the input collection shape.
