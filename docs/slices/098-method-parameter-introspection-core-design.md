# Slice 098: Method Parameter Introspection Core Design

Related requirements: [docs/slices/098-method-parameter-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/098-method-parameter-introspection-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
methodParams(class_or_object, 'methodName)
```

It complements:

```text
methodSupplier(class_or_object, 'methodName)
methodArity(class_or_object, 'methodName)
effectiveMethods(class_or_object)
```

`methodParams` exposes parameter names for the selected user-defined method without exposing method source, method body ASTs, or class-qualified metadata records.

## Runtime Path

The implementation reuses the same class-or-object resolver and checked method lookup used by `methodSupplier` and `methodArity`:

```c
enact_class_lookup_method_with_supplier(...)
```

After lookup succeeds, it reads:

```c
enact_function_arity(method)
enact_function_param_name(method, index)
```

The returned function is released immediately after the atom list is built.

## Return Shape

For a selected method with parameters, the result is an atom list in declaration order:

```text
class A < Object
A.f(x,y):=x+y
methodParams(A, 'f) -> 'x:'y:nil
```

For a selected zero-parameter method, the result is the empty list:

```text
class A < Object
A.f():=1
methodParams(A, 'f) -> nil
```

For a missing user-defined method, the result is also `nil`:

```text
methodParams(Object, 'missing) -> nil
```

This is intentionally list-shaped. Callers that need to distinguish zero-parameter methods from missing methods can combine this helper with `methodArity` or `methodSupplier`.

## Dispatch Consistency

Because `methodParams` uses the checked lookup helper, it follows the same user-defined method dispatch policy as object dot calls:

- subclass overrides win.
- inherited methods keep their original parameter names.
- multiple inheritance follows class linearization.
- inconsistent linearization reports `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Native Collection Methods

Builtin-backed native collection dot methods remain invisible:

```text
methodParams(set(), 'size) -> nil
```

This matches `methodSupplier`, `effectiveMethods`, and `methodArity`. If a user-defined method is added to `Set` or `Bag`, it is visible through normal class-method lookup.

## Deferred Work

This slice does not add callable parameter introspection, method source/body introspection, native collection method-table provenance, or class-qualified method metadata records.
