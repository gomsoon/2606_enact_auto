# Slice 066: Set UNION Aggregate Core Design

Related requirements: [docs/slices/066-set-union-aggregate-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/066-set-union-aggregate-core-requirements.md)

## Aggregate Surface

This slice introduces:

```text
UNION(list_of_sets)
```

The argument must be an ordinary ENACT list. Each element of that list must be an object-backed `Set`, including subclass instances. This keeps the initial aggregate form narrow and avoids defining collection-of-sets or Bag multiplicity behavior. Slice 072 later adds same-kind Bag aggregate support.

## Empty Input

`UNION(())` returns a fresh root `Set` object. This requires the builtin to use the environment-aware builtin path so it can construct `Set` through the installed class binding.

## Non-Empty Input

For non-empty input, the first Set acts as the result prototype:

- runtime class is copied from the first Set.
- user-visible attributes are copied from the first Set.
- collection payload is replaced by the aggregate union payload.

The aggregate payload is built by folding the same list-union helper used by binary `union`.

## Shared Union Helper

Binary `union` and aggregate `UNION` share a common list helper:

```c
enact_builtin_union_lists(left, right, out)
```

The helper applies the existing list rule:

```text
append(difference(left, right), right)
```

For Set payloads, this preserves the observable union semantics while continuing to use existing runtime value equality and object identity behavior.

## Deliberately Narrow Scope

This slice does not accept a Set directly as the aggregate argument, does not define Bag aggregate behavior, and does not introduce dot-method collection syntax or custom collection printing. Slice 072 later adds list-of-Bag aggregate behavior.
