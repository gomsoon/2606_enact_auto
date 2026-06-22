# Slice 106: hasMethod Predicate Design

Related requirements: [docs/slices/106-hasmethod-predicate-requirements.md](/home/tprover/2606_enact_auto/docs/slices/106-hasmethod-predicate-requirements.md)

## Contract

The new builtin is:

```text
hasMethod(class_or_object, 'methodName)
```

It returns a boolean rather than method metadata. This keeps Slice 106 focused on availability and avoids making any new supplier/provenance promises for native collection table entries.

## Lookup Order

The lookup order mirrors dot dispatch and the recent method metadata helpers:

1. Resolve the first argument to a class, using the object's runtime class when needed.
2. Validate the second argument as an atom.
3. Run checked user-defined method lookup.
4. If a user-defined method is selected, return `true`.
5. Otherwise, if the class is Set-like or Bag-like, check the native collection method table.
6. If no path finds the method, return `false`.

Inconsistent class linearization is reported before native fallback, matching ordinary dot-call behavior.

## Native Collection Boundary

Native collection methods count as available methods for this predicate:

```text
hasMethod(set(), 'member) -> true
hasMethod(set(), 'size)   -> true
```

This intentionally differs from `methodSupplier`:

```text
methodSupplier(set(), 'member) -> nil
hasMethod(set(), 'member)      -> true
```

The distinction is useful: `hasMethod` answers whether a call can dispatch, while `methodSupplier` still answers which user-defined class supplies selected source-level method code.

## User-Defined Priority

If a user-defined class method shadows a native collection method, the answer remains `true`. The predicate does not expose which path won:

```text
Set.member(x):=x
hasMethod(set(), 'member) -> true
```

Callers that need signature metadata can combine `hasMethod` with `methodArity` and `methodParams`.

## Deferred Work

This slice does not add native supplier metadata, native method source/body metadata, method-kind records, or a richer structured method-info API.
