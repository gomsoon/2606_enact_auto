# Slice 057: Collection Insert Core for Set/Bag Design

Related requirements: [docs/slices/057-collection-insert-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/057-collection-insert-core-requirements.md)

## Functional Insert

`insert(value, collection)` is a functional update. It returns a new collection object with updated hidden payload items and leaves the original collection object unchanged.

This keeps the initial collection operation aligned with the evaluator's value-oriented style and avoids introducing object mutation semantics before the object model has an explicit mutation story for collection payloads.

## Object Copy Helper

The object runtime exposes a copy helper for collection objects:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The helper creates a new object with the same class, installs the supplied hidden collection items, and clones user attributes. Hidden collection items stay separate from `attrs(object)`.

## Set and Bag Semantics

`Set` uses existing value equality to suppress duplicates:

```text
size(insert(1, insert(1, set()))) == 1
```

`Bag` stores every inserted occurrence:

```text
size(insert(1, insert(1, bag()))) == 2
```

Both kinds store payload values in the same internal list representation introduced by Slice 056. Since collection printing is still object printing in this slice, the payload is observed through `size` and `member`. Slice 073 later adds kind-aware collection payload display.

## Type Boundary

`insert` only accepts collection objects as its second argument. Lists remain list values, not collection objects, so `insert(value, nil)` is rejected with the same established collection/list diagnostic:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

Existing list-only builtins remain unchanged for this slice.
