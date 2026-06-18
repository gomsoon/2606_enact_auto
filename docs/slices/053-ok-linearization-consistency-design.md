# Slice 053: OK(Class) Linearization Consistency Predicate Design

Related requirements: [docs/slices/053-ok-linearization-consistency-requirements.md](/home/tprover/2606_enact_auto/docs/slices/053-ok-linearization-consistency-requirements.md)

## Runtime Helper

Slice 052 promoted class linearization into the object runtime. Slice 053 keeps that centralization and adds a strict consistency helper:

```c
int enact_class_linearization_is_consistent(EnactClass *class_value, int *out);
```

The helper reuses the same class-vector merge machinery as `classes(Class)` and method dispatch, but it disables the existing fallback candidate path.

When no C3-style candidate can satisfy all active sequence heads, the helper reports `*out = 0` and still returns success. Allocation or invalid internal arguments return failure.

## Fallback Preservation

`classes(Class)`, `superiors(Class)`, and method dispatch continue to allow the fallback path used before this slice.

This keeps existing behavior stable while `OK(Class)` exposes whether that fallback was necessary. A later slice can use this predicate as a gate for richer diagnostics.

## Duplicate Direct Superclasses

The private linearization input normalizes repeated direct superclass identities before merging. This preserves the existing deduplicated `classes` behavior and treats forms such as:

```text
class C < (A,A)
```

as redundant rather than inconsistent.

The public `supers(Class)` helper still reports the stored direct superclass list.

## Builtin

`OK` is installed as a one-argument builtin:

```text
OK(Class) -> true | false
```

It reports `ENACT_ERR_TYPE_EXPECTED_CLASS` for non-class arguments and otherwise returns a normal boolean value. It participates in first-class builtin behavior, higher-order list builtins, and shadowing exactly like the other introspection helpers.
