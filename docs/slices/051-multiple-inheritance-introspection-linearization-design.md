# Slice 051: Multiple-Inheritance Introspection Linearization Design

Related requirements: [docs/slices/051-multiple-inheritance-introspection-linearization-requirements.md](/home/tprover/2606_enact_auto/docs/slices/051-multiple-inheritance-introspection-linearization-requirements.md)

## Linearization Rule

The class linearization follows a C3-style merge:

```text
linearize(C) = C + merge(linearize(S1), linearize(S2), ..., (S1,S2,...))
```

`S1`, `S2`, and later entries are the direct superclasses in declared order.

This keeps local precedence stable while making shared ancestors appear once near the end of the list. For example:

```text
class A < Object
class B < Object
class C < (A,B)
classes(C) -> C:A:B:Object:nil
```

## Runtime Shape

`builtin.c` owns the linearization helper because the current use is introspection-specific. The object runtime still exposes only direct-superclass helpers:

- `enact_class_superclass` for first-superclass compatibility
- `enact_class_superclasses` for the direct superclass list

The linearization helper collects class pointers in a temporary vector, then materializes the result as an `EnactList` of class values.

## Builtins

`classes(Class)` materializes the full vector from index `0`.

`superiors(Class)` materializes the same vector from index `1`, excluding the class itself.

`supers(Class)` is unchanged and remains direct-only.

## Conflict Handling

The merge chooses the first head that does not appear in any remaining tail. If no such candidate exists, it falls back to the first available head to keep introspection deterministic.

A dedicated ambiguity or inconsistent-linearization diagnostic is deferred until the object model has explicit validation helpers.
