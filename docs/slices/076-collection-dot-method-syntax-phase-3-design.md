# Slice 076: Collection Dot-Method Syntax Phase 3: Traversal + Higher-Order Design

Related requirements: [docs/slices/076-collection-dot-method-syntax-phase-3-requirements.md](/home/tprover/2606_enact_auto/docs/slices/076-collection-dot-method-syntax-phase-3-requirements.md)

## Bridge Extension

Slice 076 continues the evaluator bridge introduced in Slice 074 and extended in Slice 075. It only adds method-name to builtin-argument mappings; traversal semantics stay inside the existing builtin implementations.

Most traversal methods put the receiver in builtin argument slot one:

```text
collection.collect(f)      -> collect(f, collection)
collection.filter(p)      -> filter(p, collection)
collection.select(p)      -> select(p, collection)
collection.all(p)         -> all(p, collection)
collection.exists(p)      -> exists(p, collection)
collection.locate(p)      -> locate(p, collection)
collection.forEachDo(a)   -> forEachDo(a, collection)
```

`reduce` keeps the free builtin's reducer, initial, input order, so the receiver goes in builtin argument slot two:

```text
collection.reduce(f, z) -> reduce(f, z, collection)
```

## Semantics

No higher-order behavior is reimplemented in the evaluator. The bridge builds the same evaluated argument array as the corresponding free builtin call and delegates through `enact_builtin_apply_in_env`.

This preserves:

- callable validation.
- predicate boolean validation.
- `all` and `exists` short-circuit behavior.
- `locate` returning a copied matching value or `nil`.
- `forEachDo` side effects and `nil` return.
- `reduce` accumulator order.
- subclass and user-visible attribute preservation for collection-returning operations.

## Shadowing Order

The existing dot-call lookup order remains unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. collection dot-method bridge.

Top-level bindings named `collect`, `filter`, `reduce`, or similar do not affect collection dot methods because the bridge resolves through the builtin table directly.

## Deferred Work

`unitset` and aggregate `UNION` remain outside this slice because their natural receiver model is less direct than ordinary traversal. Slice 077 later adds aggregate `UNION`; bound collection method values and native method-table integration remain deferred.
