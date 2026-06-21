# Slice 089: Method Lookup Supplier Metadata Core Design

Related requirements: [docs/slices/089-method-lookup-supplier-metadata-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/089-method-lookup-supplier-metadata-core-requirements.md)

## Lookup Result

Slice 089 adds a richer method lookup entrypoint:

```c
int enact_class_lookup_method_with_supplier(
    EnactClass *class_value,
    const char *name,
    EnactFunction **out,
    EnactClass **supplier_out,
    int *consistent);
```

The function builds the same checked linearization vector as `enact_class_lookup_method`. It then scans direct method tables in linearization order. When it finds a method, it returns the retained function in `out` and the direct-owning class in `supplier_out`.

The supplier pointer is borrowed lookup metadata. Callers that need to store it past the lookup call must retain it.

## Backward Compatibility

The existing API stays as a wrapper:

```c
int enact_class_lookup_method(...);
```

It calls the supplier-aware API and discards the supplier pointer. Existing callers keep the same retained-function ownership contract, the same consistency reporting, and the same missing-method behavior.

## Bound Method Metadata

`EnactBoundObjectMethod` now stores an optional retained supplier class.

Attribute reads and dot-calls both use the supplier-aware lookup API. When they bind a user-defined object method, they create the bound method with the selected supplier class. Bound method extension for partial application copies this metadata so partially applied method values still know where the original dispatch selected the method.

The original `enact_bound_object_method_new` constructor remains available and creates a bound method without supplier metadata. This keeps direct construction sites and external tests source-compatible.

## User-Facing Behavior

This slice intentionally does not change visible semantics:

- bound object methods still print as `<function>`.
- method calls still evaluate the same selected function.
- object attributes still shadow class methods.
- user-defined class methods still shadow native collection methods.
- missing methods and inconsistent linearization keep the same diagnostics.
- `methods(Class)` and `methods(object)` remain direct-method introspection helpers.

## Testing Shape

C unit tests cover the new internal surface directly:

- null argument validation for the supplier-aware lookup API.
- direct supplier identity.
- inherited supplier identity.
- override supplier identity.
- null supplier on missing lookup.
- supplier storage on bound object method values.
- supplier preservation across bound object method partial application.
- compatibility of the older lookup and constructor wrappers.

The Python regression suite checks that existing user-visible method behavior remains unchanged across attribute reads, dot-calls, inherited dispatch, multiple-inheritance dispatch, partial application, attribute shadowing, and robustness diagnostics.

## Deferred Work

This slice does not add `super`, inherited/effective method introspection, method signature introspection, method source introspection, or native collection method-table provenance. Slice 090 later exposes the selected user-defined method supplier through `methodSupplier`.
