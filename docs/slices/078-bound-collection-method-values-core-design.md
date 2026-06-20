# Slice 078: Bound Collection Method Values Core Design

Related requirements: [docs/slices/078-bound-collection-method-values-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/078-bound-collection-method-values-core-requirements.md)

## Runtime Value

Slice 078 adds a small callable runtime value:

```c
ENACT_VALUE_BOUND_COLLECTION_METHOD
```

The payload stores:

- the native builtin to delegate to.
- the receiver argument index used by the collection dot bridge.
- a copied receiver value.
- zero or more already-supplied method arguments for partial application.

This shape is intentionally collection-specific. It avoids changing user-defined method dispatch in this slice; Slice 079 later adds general bound object method values.

## Lookup Policy

Bare attribute read now uses the same native collection method bridge as collection dot-calls, after preserving the established shadowing order:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. native collection method bridge.

When step 2 finds a user-defined class method, the evaluator does not fall through to the native bridge. Since general method values are deferred, the bare read reports `ENACT_ERR_ATTRIBUTE_UNBOUND`.

## Calling Policy

Applying a bound collection method builds the same builtin argument array that a direct collection dot-call would have built:

```text
collection.member(value) -> member(value, collection)
m := collection.member
m(value)                 -> member(value, collection)
```

Receiver slot placement is reused from the existing bridge:

- slot zero: `size`, algebra, predicates, and aggregate `UNION`.
- slot one: element operations and traversal callables.
- slot two: `reduce`.

The evaluator delegates through `enact_builtin_apply_in_env`, so direct dot-call and bound method call behavior share diagnostics, result construction, class preservation, attribute preservation, Set duplicate suppression, Bag multiplicity behavior, and aggregate semantics.

## Partial Application

Bound collection method values can capture method arguments in the same way ordinary functions and builtins can:

```text
r := set((1,2,3)).reduce
sum_from := r((acc,x)::acc+x)
sum_from(0)
```

Zero-argument calls on non-zero-arity bound methods remain arity errors. This avoids creating unobservable no-op partials and matches existing callable arity checks.

## Printing And Equality

Bound collection methods print as `<function>`.

Runtime equality is pointer identity for bound collection method payloads, matching builtin partial values. User-facing equality between bound collection methods and other callable kinds remains a kind mismatch.

## Deferred Work

General bound user-defined object methods remain deferred in this slice and are later added by Slice 079. Native collection method-table integration also remains deferred; this slice keeps using the focused evaluator bridge from Slices 074 through 077.
