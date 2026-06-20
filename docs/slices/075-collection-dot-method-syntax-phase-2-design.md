# Slice 075: Collection Dot-Method Syntax Phase 2: Algebra + Predicates Design

Related requirements: [docs/slices/075-collection-dot-method-syntax-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/075-collection-dot-method-syntax-phase-2-requirements.md)

## Bridge Extension

Slice 074 added a focused evaluator bridge for a small set of collection dot methods. Slice 075 keeps that design and extends only the method-name to builtin-argument mapping.

Receiver-first algebra and predicates map with the receiver in builtin argument slot zero:

```text
collection.union(other)        -> union(collection, other)
collection.difference(other)   -> difference(collection, other)
collection.intersection(other) -> intersection(collection, other)
collection.subset(other)       -> subset(collection, other)
collection.equal(other)        -> equal(collection, other)
```

Set insertion maps with the receiver in builtin argument slot one, matching the existing `add(value, set)` helper:

```text
set.add(value) -> add(value, set)
```

## Semantics

No collection semantics are reimplemented in the evaluator. The bridge constructs the same evaluated argument array that a free builtin call would receive and then calls `enact_builtin_apply_in_env`.

That means this slice inherits:

- same-kind Set/Bag validation for binary algebra and predicates.
- Set-only validation for `add`.
- left-receiver prototype preservation for algebra results.
- Set duplicate suppression and Bag multiplicity behavior.
- existing diagnostics for mixed operands and non-collection values.

## Shadowing Order

The existing dot-call lookup order remains unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. collection dot-method bridge.

This keeps explicit object or class behavior stronger than the synthetic collection surface while still allowing manual-style collection calls when no user-defined member shadows them.

## Deferred Work

Higher-order traversal dot methods are left for a later phase because they bring callable evaluation, short-circuit behavior, side effects, and `reduce` accumulator order into the method surface. `unitset` and aggregate `UNION` are also left out because their receiver shape is less direct than ordinary binary algebra.
