# Slice 069: Argument-Bearing set(...) / bag(...) Construction Design

Related requirements: [docs/slices/069-argument-bearing-set-bag-construction-requirements.md](/home/tprover/2606_enact_auto/docs/slices/069-argument-bearing-set-bag-construction-requirements.md)

## Constructor Surface

`set` and `bag` become range-arity builtins:

```text
set()        -> empty Set object
set(list)    -> Set object populated from list
bag()        -> empty Bag object
bag(list)    -> Bag object populated from list
```

The one-argument form intentionally accepts ordinary ENACT lists only. Existing list notation, including tuple-like construction and `list(x)`, remains the source syntax for payloads.

## Builtin Arity Range

Most builtins remain exact-arity builtins. Slice 069 adds a minimum arity field to the builtin descriptor so `set` and `bag` can be `0..1` without introducing general varargs:

```c
size_t enact_builtin_min_arity(const EnactBuiltin *builtin);
size_t enact_builtin_arity(const EnactBuiltin *builtin);
```

`enact_builtin_arity()` keeps its existing meaning for exact-arity builtins and reports the maximum accepted arity for range-arity builtins. The evaluator uses `min_arity` to decide whether a builtin call should produce a partial application or execute immediately.

## Payload Construction

The constructor still begins by creating a fresh object from the current `Set` or `Bag` binding. The one-argument path then validates that the argument is an ordinary list and copies its values into the object's collection payload.

For `Set`, construction reuses existing runtime equality to suppress duplicates. For `Bag`, each list occurrence is retained. The result is stored with:

```c
enact_object_copy_with_collection_items(collection, items)
```

This keeps the payload in the collection storage already used by `insert`, `remove`, `collect`, `filter`, `reduce`, and related builtins.

## Evaluation Order

The accepted single argument is evaluated before the builtin callback runs, so failures such as `set(1/0)` now propagate the underlying evaluation diagnostic. Calls with two or more arguments remain arity mismatches before evaluating extra arguments, preserving the project's over-application rule.

## Environment Binding

The constructor continues to look up `Set` and `Bag` in the current evaluation environment. Rebinding `Set` to a subclass of `Set` allows `set(list)` to produce that subclass, while rebinding it to a non-class or non-Set class reports `ENACT_ERR_TYPE_EXPECTED_CLASS`.

## Deliberately Narrow Scope

This slice does not add literal set or bag syntax, dot-method constructor syntax, custom collection printing, or new Bag-specific algebra. It only makes the existing constructor names useful with ordinary list payloads.
