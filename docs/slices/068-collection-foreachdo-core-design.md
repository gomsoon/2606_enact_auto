# Slice 068: Collection forEachDo Core Design

Related requirements: [docs/slices/068-collection-foreachdo-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/068-collection-foreachdo-core-requirements.md)

## Traversal Surface

`forEachDo(action, input)` uses the same input helper as `all`, `exists`, `locate`, and collection-aware `reduce`:

```c
enact_builtin_require_list_or_collection(input, &list, diag)
```

That makes ordinary lists, `Set`, `Bag`, and collection subclasses share one traversal path.

## Action Application

Each element is passed to the action through the normal callable helper:

```c
enact_eval_apply_callable(action, element, 1, &result, diag)
```

Unlike predicate builtins, `forEachDo` does not require a bool result. Any successful action result is immediately released, and traversal continues.

## Result Value

Successful traversal returns `nil`, including empty inputs:

```text
forEachDo(x::x+1, (1,2,3)) == nil
forEachDo(x::1/0, ()) == nil
```

This treats `nil` as the current unit-like value for side-effect-oriented traversal.

## Side Effects

The builtin itself does not alter collection payloads. Side effects come from the supplied callable, for example assigning to a captured object's attributes:

```text
o := new Object with total := 0
forEachDo(x::(o.total := o.total + x), (1,2,3))
```

Action failures stop traversal and preserve the original diagnostic.

## Deliberately Narrow Scope

This slice does not add dot-method collection syntax, custom collection printing, or a distinct unit value. Slice 073 later adds kind-aware collection payload display.
