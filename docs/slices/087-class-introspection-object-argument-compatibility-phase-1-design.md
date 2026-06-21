# Slice 087: Class Introspection Object-Argument Compatibility Phase 1 Design

Related requirements: [docs/slices/087-class-introspection-object-argument-compatibility-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/087-class-introspection-object-argument-compatibility-phase-1-requirements.md)

## Compatibility Mapping

`supers` and `superiors` now reuse the shared class-or-object argument resolver:

1. Class values are used directly.
2. Object values are mapped to `enact_object_class(object)`.
3. Other values report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

After this mapping, each helper delegates to its existing class-based implementation path:

```text
supers(new C) == supers(classof(new C))
superiors(new C) == superiors(classof(new C))
```

## Helper Semantics

`supers` remains the direct-superclass helper. It reads the stored direct superclass list and therefore remains available even when a class cannot be consistently linearized.

`superiors` remains the transitive superclass-chain helper. It uses the checked class linearization path and preserves the existing `ENACT_ERR_INCONSISTENT_LINEARIZATION` diagnostic for inconsistent classes.

## Testing Shape

The regression suite keeps existing class-input checks and adds Slice 087 object-input checks for root classes, single inheritance, multi-level inheritance, multiple inheritance, higher-order calls, first-class builtin calls, and native collection objects.

Older object-misuse failure cases for `supers` and `superiors` are superseded by these object-input success cases. Non-class, non-object values now use the same `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT` diagnostic as the other class-or-object introspection helpers.

## Deferred Work

This slice does not make `classes` or `methods` accept object arguments. That remains a good follow-up slice because those helpers form the next natural class-introspection compatibility pair.
