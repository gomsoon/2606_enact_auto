# Slice 090: Method Supplier Introspection Core Design

Related requirements: [docs/slices/090-method-supplier-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/090-method-supplier-introspection-core-requirements.md)

## Helper Contract

Slice 090 adds:

```text
methodSupplier(class_or_object, 'methodName)
```

It returns the single class that normal user-defined method dispatch would select as the direct owner of `methodName`.

Examples:

```text
class A < Object
A.f():=1
class B < A
methodSupplier(B,'f)  -> <class A>
```

```text
class A < Object
A.f():=1
class B < A
B.f():=2
methodSupplier(B,'f)  -> <class B>
```

Missing methods return `nil`, matching existing value-or-nil helpers such as `locate`.

## Relationship To suppliers

`suppliers(class_or_object, attr)` remains the ambiguity inspection helper introduced by Slice 084 and widened by Slice 085. It walks the inheritance graph without requiring a consistent method resolution order and may return multiple classes.

`methodSupplier` is different: it uses the checked method lookup path from Slice 089, so it returns the one supplier normal dispatch would use. When the class cannot be linearized consistently, it reports `ENACT_ERR_INCONSISTENT_LINEARIZATION` instead of returning ambiguity data.

For example:

```text
class A < Object
class B < Object
A.f():=1
B.f():=2
class C < (A,B)

suppliers(C,'f)      -> <class A>:<class B>:nil
methodSupplier(C,'f) -> <class A>
```

## Runtime Path

The builtin reuses the shared class-or-object resolver:

1. class values are used directly.
2. object values map to their runtime class.
3. other values report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

After validating the atom method name, the builtin calls:

```c
enact_class_lookup_method_with_supplier(...)
```

The returned method function is released immediately because the builtin only exposes the supplier metadata. If the supplier exists, the builtin retains the class before returning it as an `ENACT_VALUE_CLASS`.

## Native Collection Methods

`methodSupplier` reports user-defined class methods only. It does not expose builtin-backed native collection method table entries:

```text
methodSupplier(set(),'size) -> nil
```

If a user defines a method on a native collection class, normal user-defined dispatch sees it and `methodSupplier` reports it:

```text
Set.size():=99
methodSupplier(set(),'size) -> <class Set>
```

## Testing Shape

The regression suite covers direct methods, inherited methods, overrides, multiple inheritance, shared ancestors, object arguments, higher-order use, partial builtin application, user shadowing, native collection behavior, and inconsistency diagnostics.

The C unit tests cover builtin registration, arity, installation, missing-method nil behavior, and type diagnostics for both argument positions.

## Deferred Work

This slice does not add `super`, effective method listing, method signature introspection, method source introspection, or native collection method-table provenance.
