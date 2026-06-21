# Slice 091: Effective Method Introspection Design

Related requirements: [docs/slices/091-effective-method-introspection-requirements.md](/home/tprover/2606_enact_auto/docs/slices/091-effective-method-introspection-requirements.md)

## Helper Contract

Slice 091 adds:

```text
effectiveMethods(class_or_object)
```

It returns the method names that normal user-defined dispatch can see for the class or object's runtime class.

Examples:

```text
class A < Object
A.f():=1
class B < A
effectiveMethods(B)  -> 'f:nil
methods(B)           -> nil
```

```text
class A < Object
A.f():=1
class B < A
B.f():=2
effectiveMethods(B)  -> 'f:nil
methodSupplier(B,'f) -> <class B>
```

## Relationship To Existing Helpers

`methods(class_or_object)` remains direct-only. It is useful for seeing exactly what a class declares.

`methodSupplier(class_or_object, attr)` remains the single-name dispatch supplier query. It answers who supplies one selected method.

`effectiveMethods(class_or_object)` sits between those helpers: it lists the names that dispatch would consider effective, but it does not expose signatures, arity, bodies, source locations, or native collection method-table provenance.

## Runtime Path

`object.c` adds:

```c
int enact_class_effective_method_names(EnactClass *class_value, EnactList **out, int *consistent);
```

The helper:

1. builds the checked class linearization with the same C3-style helper used by dispatch.
2. scans each class in linearization order.
3. adds direct method names in the same first-definition order used by `methods`.
4. skips names that were already added by an earlier class, preserving override masking.
5. returns an atom list or marks the linearization inconsistent.

The builtin maps object arguments to their runtime class through the existing class-or-object resolver. Inconsistent linearization is surfaced as `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Native Collection Methods

The helper reports user-defined class methods only. Builtin-backed native collection dot-method entries remain invisible:

```text
effectiveMethods(set()) -> nil
```

If a user defines a method on a native collection class, normal user-defined dispatch can see it and `effectiveMethods` reports it:

```text
Set.size():=99
effectiveMethods(set()) -> 'size:nil
```

## Deferred Work

This slice does not add `super`, method signatures, method source introspection, method bodies, arity metadata, or native collection method-table provenance.
