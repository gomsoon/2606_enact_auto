# Slice 059: Collection Predicate Traversal Design

Related requirements: [docs/slices/059-collection-predicate-traversal-requirements.md](/home/tprover/2606_enact_auto/docs/slices/059-collection-predicate-traversal-requirements.md)

## Shared Traversal Input

Update note: Slice 060 builds on this read-only traversal step by adding collection-aware `filter` and `select`. Slice 061 adds collection-aware `reduce` over the same payload traversal surface. Slice 062 adds collection-specific `collect`; `map` remains list-only.

`all` and `exists` now use the existing list-or-collection helper for their traversal input:

```c
enact_builtin_require_list_or_collection(...)
```

This keeps ordinary list behavior intact while allowing object-backed `Set` and `Bag` values to expose their hidden payload list to read-only predicate traversal.

## Boolean-Only Surface

This slice intentionally chooses `all` and `exists` before `map`, `filter`, or `reduce` because both builtins return booleans. They do not need to decide whether transformed results should be lists, `Set` objects, `Bag` objects, or subclass-preserving collection objects.

The observed collection behavior is therefore small and predictable:

```text
all(x::x > 0, insert(1, set())) == true
exists(x::x == 1, insert(1, bag())) == true
```

## Empty Collections

Empty collection payloads follow the existing empty-list rules:

```text
all(predicate, set()) == true
exists(predicate, set()) == false
```

The same applies to `bag()` and empty subclasses of `Set` or `Bag`.

## Predicate Semantics

Predicate application is unchanged:

- the first argument must be callable
- each predicate result must be boolean
- `all` short-circuits on `false`
- `exists` short-circuits on `true`

Any predicate evaluation error is reported normally.

## Deliberately Narrow Scope

Collection-aware `map` remains deferred. Slice 062 answers the collection transform use case with a separate `collect` builtin that preserves collection shape.
