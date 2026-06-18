# Slice 052: Method Dispatch Uses classes(Class) Linearization Design

Related requirements: [docs/slices/052-method-dispatch-uses-classes-linearization-requirements.md](/home/tprover/2606_enact_auto/docs/slices/052-method-dispatch-uses-classes-linearization-requirements.md)

## Shared Runtime Linearization

Slice 051 originally kept the C3-style linearization helper inside `builtin.c` because only `classes` and `superiors` needed it.

Slice 052 promotes that helper into the object runtime:

```c
int enact_class_linearization(EnactClass *class_value, EnactList **out);
```

This makes class introspection and method dispatch share one ordering rule.

## Dispatch Rule

`enact_class_lookup_method` now:

1. builds the linearization vector for the receiver class
2. checks each class's direct method table in linearization order
3. returns the first matching method

This replaces the older recursive direct-superclass traversal:

```text
old: C, first parent's whole chain, second parent's whole chain, ...
new: classes(C)
```

For example:

```text
class A < Object
class B < A
class C < Object
class D < (B,C)
```

`classes(D)` is:

```text
D:B:A:C:Object:nil
```

Method dispatch now uses that same order. A method on `C` is considered before a method inherited from `Object`.

## Builtins

`classes(Class)` now delegates to `enact_class_linearization`.

`superiors(Class)` delegates to the same helper and returns the tail of the resulting list.

`supers(Class)` remains direct-only and does not use linearization.

## Diagnostics

Method lookup itself still has no diagnostic channel. Allocation failure during lookup therefore behaves like a failed lookup, as before.

All user-facing method call diagnostics stay in the evaluator:

- missing method: `ENACT_ERR_ATTRIBUTE_UNBOUND`
- selected method wrong arity: `ENACT_ERR_ARITY_MISMATCH`
- selected method body failure: body diagnostic
- non-object receiver: `ENACT_ERR_TYPE_EXPECTED_OBJECT`
