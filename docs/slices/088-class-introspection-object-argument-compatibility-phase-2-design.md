# Slice 088: Class Introspection Object-Argument Compatibility Phase 2 Design

Related requirements: [docs/slices/088-class-introspection-object-argument-compatibility-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/088-class-introspection-object-argument-compatibility-phase-2-requirements.md)

## Compatibility Mapping

`classes` and `methods` now reuse the shared class-or-object argument resolver used by `badAttrs`, `suppliers`, `OK`, `supers`, and `superiors`:

1. Class values are used directly.
2. Object values are mapped to `enact_object_class(object)`.
3. Other values report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

After this mapping, the helpers delegate to their existing class-based paths:

```text
classes(new C) == classes(classof(new C))
methods(new C) == methods(classof(new C))
```

## Helper Semantics

`classes` remains the inclusive class-chain helper. It uses the checked linearization path and therefore keeps reporting `ENACT_ERR_INCONSISTENT_LINEARIZATION` for object values whose class cannot be linearized.

`methods` remains direct-method introspection. It reads the direct method table of the object's class and does not expose inherited methods, native collection method table entries, method signatures, method bodies, or source.

## Testing Shape

The regression suite keeps existing class-input checks and adds Slice 088 object-input checks for root objects, single inheritance, direct methods, inherited-method exclusion, multiple inheritance, higher-order calls, native collection objects, and inconsistent classes.

Older object-misuse failure cases for `classes` and `methods` are superseded by these object-input success cases. Non-class, non-object values now use the same `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT` diagnostic as the other class-or-object introspection helpers.

## Deferred Work

This slice does not add inherited or effective method introspection, native collection method table introspection, `super` calls, method signature introspection, or method source introspection.
