# Slice 085: Object-Argument Ambiguity Helper Compatibility Design

Related requirements: [docs/slices/085-object-argument-ambiguity-helper-compatibility-requirements.md](/home/tprover/2606_enact_auto/docs/slices/085-object-argument-ambiguity-helper-compatibility-requirements.md)

## Compatibility Mapping

The ambiguity helper implementations remain class-based internally:

```text
badAttrs(C)
suppliers(C,'f)
```

Slice 085 adds a shared builtin helper that resolves the first argument:

1. Class values are used directly.
2. Object values are mapped to `enact_object_class(object)`.
3. Other values report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

This makes the manual-style object input a thin compatibility layer:

```text
badAttrs(new C)       == badAttrs(classof(new C))
suppliers(new C,'f)  == suppliers(classof(new C),'f)
```

The object itself is not inspected for instance attributes. `attrs(object)` remains the direct object-state helper, while `badAttrs` and `suppliers` remain inherited method supplier helpers.

## Supplier Semantics

No supplier algorithm changes are needed. After an object is mapped to its class, the existing Slice 083/084 rules apply:

- direct methods on the object's class mask inherited suppliers.
- inherited ambiguity remains visible through the object's class.
- shared common ancestors deduplicate by supplier class identity.
- inconsistent linearization does not block inspection.

## Diagnostics

Because the first argument now accepts two value kinds, this slice adds `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT` with message `class or object value required`.

The second argument of `suppliers` remains atom-only and keeps `ENACT_ERR_TYPE_EXPECTED_ATOM`.

## Deferred Work

This slice does not change return values from lists to native Sets, does not inspect direct object attributes as inherited attributes, and does not change `OK(Class)` into an attribute-ambiguity predicate. `OK(object)` compatibility is later added by Slice 086.
