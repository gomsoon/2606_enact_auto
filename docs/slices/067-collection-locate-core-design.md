# Slice 067: Collection locate Core Design

Related requirements: [docs/slices/067-collection-locate-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/067-collection-locate-core-requirements.md)

## Traversal Surface

`locate(predicate, input)` shares the same traversal input helper as `all`, `exists`, and collection-aware `reduce`:

```c
enact_builtin_require_list_or_collection(input, &list, diag)
```

That keeps ordinary lists, `Set`, `Bag`, and collection subclasses aligned without adding a separate collection-only path.

## Predicate Application

Each candidate element is passed to the existing predicate helper:

```c
enact_builtin_apply_predicate(predicate, element, &matched, diag)
```

This preserves callable validation, bool-result validation, and diagnostic propagation for predicate failures.

## Result Ownership

When a predicate returns `true`, `locate` copies the matching runtime value into the output slot and stops traversal. This keeps the located value independent of the collection payload storage.

When traversal reaches the end without a match, the result is `nil`:

```text
locate(x::x==9, (1,2,3)) == nil
```

## Deliberately Narrow Scope

`nil` remains the no-match result, so locating a literal `nil` element is intentionally indistinguishable from no match in this slice. A richer option/result wrapper can be introduced later if the language needs that distinction.

`locate` does not mutate collection objects, does not introduce dot-method syntax, and does not define custom collection printing in this slice. Slice 073 later adds kind-aware collection payload display.
