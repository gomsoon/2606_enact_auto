# Slice 062: Collection Transform Core: collect Design

Related requirements: [docs/slices/062-collection-transform-collect-requirements.md](/home/tprover/2606_enact_auto/docs/slices/062-collection-transform-collect-requirements.md)

Update note: Slice 063 adds Set-aware `union`, `difference`, and `intersection`. Slice 064 adds Set-aware `subset` and `equal`. Slice 065 adds Set-aware `add`. Slice 066 adds Set-aware aggregate `UNION`. Slice 067 adds list/collection-aware `locate`. Slice 071 later adds same-kind Bag support for binary `union`, `difference`, and `intersection`.

## Collection-Only Transform

`collect` is intentionally separate from list `map`:

```text
map(transform, list)        -> list
collect(transform, object)  -> collection object
```

This keeps existing list behavior stable and gives collection transforms a result shape that is not ambiguous.

## Shared Callable Application

The transform uses the same callable application helper as `map`:

```c
enact_eval_apply_callable(transform, element, 1, &mapped_value, diag)
```

Each payload element is transformed exactly once. Transform errors propagate normally.

## Result Construction

The mapped payload is wrapped with:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

That helper preserves the input object's runtime class and user-visible attributes while installing the transformed hidden payload.

## Set And Bag Semantics

`Set` results suppress duplicate transformed values using the same runtime equality helper used by `insert` and `member`.

`Bag` results preserve every transformed occurrence:

```text
size(collect(x::1, insert(1, insert(2, bag())))) == 2
```

This keeps `collect` aligned with the existing collection payload model.

## Deliberately Narrow Scope

`collect` does not accept ordinary lists; `map` remains the list transform builtin. Bag-aware binary set operations, dot-method syntax, and custom collection printing are deferred in this slice. Slice 067 adds `locate` for ordinary lists and object-backed collections. Slice 068 adds `forEachDo` over the same traversal surface. Slice 071 later adds binary Bag operations. Slice 073 later adds kind-aware collection payload display.
