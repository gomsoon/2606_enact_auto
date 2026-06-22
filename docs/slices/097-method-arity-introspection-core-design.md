# Slice 097: Method Arity Introspection Core Design

Related requirements: [docs/slices/097-method-arity-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/097-method-arity-introspection-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
methodArity(class_or_object, 'methodName)
```

It complements:

```text
methodSupplier(class_or_object, 'methodName)
effectiveMethods(class_or_object)
```

`methodSupplier` answers which class supplies a selected method. `effectiveMethods` lists selected method names. `methodArity` exposes one small piece of selected method metadata without exposing parameter names, source, or method bodies.

## Runtime Path

The implementation reuses the same class-or-object resolver and checked method lookup used by `methodSupplier`:

```c
enact_class_lookup_method_with_supplier(...)
```

The returned function is used only to read:

```c
enact_function_arity(method)
```

Then it is released immediately.

## Return Shape

If a method is selected, the result is an integer:

```text
class A < Object
A.f(x,y):=x+y
methodArity(A, 'f) -> 2
```

If no user-defined method is selected, the result is `nil`:

```text
methodArity(Object, 'missing) -> nil
```

Returning `nil` mirrors existing value-or-nil introspection helpers such as `methodSupplier`.

## Dispatch Consistency

Because `methodArity` uses the checked lookup helper, it follows the same user-defined method dispatch policy as object dot calls:

- subclass overrides win.
- inherited methods keep their original arity.
- multiple inheritance follows class linearization.
- inconsistent linearization reports `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Native Collection Methods

Builtin-backed native collection dot methods remain invisible:

```text
methodArity(set(), 'size) -> nil
```

This matches `methodSupplier` and `effectiveMethods`. If a user-defined method is added to `Set` or `Bag`, it is visible through normal class-method lookup.

## Deferred Work

This slice does not add callable arity introspection, method parameter-name introspection, method source/body introspection, native collection method-table provenance, or class-qualified method metadata records.
