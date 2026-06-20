# Slice 058: Collection Remove Core for Set/Bag Design

Related requirements: [docs/slices/058-collection-remove-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/058-collection-remove-core-requirements.md)

## Dual Path Remove

`remove(value, list)` keeps returning a list exactly as before. The builtin now has a second path for collection objects:

```text
remove(value, collection) -> collection
```

This preserves compatibility with the Slice 025 list helper while making `remove` the functional counterpart to Slice 057 `insert`.

## Functional Collection Update

Collection removal does not mutate the input object. It builds a new hidden payload list and then uses the existing collection-copy helper:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The returned object keeps the same runtime class and clones user-visible attributes.

## Set and Bag Semantics

Both collection kinds reuse the existing `remove` list helper, which removes the first equal occurrence.

For `Set`, this is enough because `insert` suppresses duplicates:

```text
size(remove(1, insert(1, set()))) == 0
```

For `Bag`, this gives one-occurrence removal:

```text
size(remove(1, insert(1, insert(1, bag())))) == 1
```

Membership and size remain the observable surface for collection payload contents because collection printing still uses object printing in this slice. Slice 073 later adds kind-aware collection payload display.

## Type Boundary

The second argument may be either:

- an ordinary list, preserving historical `remove` behavior
- a collection object, producing a collection object

Other values still report:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

`append`, `union`, `difference`, and `intersection` remain list-only in this slice.
