# Slice 093: Method Execution Supplier Context Core Design

Related requirements: [docs/slices/093-method-execution-supplier-context-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/093-method-execution-supplier-context-core-requirements.md)

## Runtime Context

Slice 093 adds an evaluator-local method execution context:

```c
typedef struct EnactEvalMethodContext {
    const struct EnactEvalMethodContext *previous;
    EnactClass *receiver_class;
    EnactClass *supplier_class;
} EnactEvalMethodContext;
```

The active context is dynamically scoped while a user-defined method body is being evaluated. Nested method calls push a new context and restore the previous one afterward.

## Why It Is Not An Env Binding

The context is intentionally separate from `EnactEnv`.

`EnactEnv` stores normal lexical bindings such as `self`, function parameters, and user variables. The selected method supplier is runtime dispatch metadata, not a user-visible binding. Keeping it out of `EnactEnv` avoids accidental capture by closures and leaves `super` free to become syntax with explicit evaluator semantics later.

## Supplier Flow

The supplier selected by the Slice 089 lookup path already reaches bound object method values:

```text
dot lookup -> EnactBoundObjectMethod(function, receiver, supplier)
```

Slice 093 completes the next step:

```text
bound object method apply -> method execution context -> method body evaluation
```

Bound object method partial application already preserves supplier metadata, so completing a partial method call naturally uses the same supplier.

Bound methods created through the older no-supplier constructor still execute normally. They simply enter the method body with a null supplier in the execution context.

## Relationship To Super Lookup

Slice 092 added:

```c
enact_class_lookup_super_method_with_supplier(receiver_class, current_supplier, name, ...)
```

Slice 093 provides the missing evaluator-side data needed by a future syntax rule:

```text
super.method(args)
```

That future rule can read `receiver_class` and `supplier_class` from the active method context, then call the Slice 092 helper.

## User-Visible Behavior

This slice does not add new syntax or builtins. Existing method dispatch, method values, partial application, higher-order list and collection builtins, `methodSupplier`, and `effectiveMethods` should continue to behave the same.

`super` remains an ordinary identifier.

## Deferred Work

This slice does not add `super.method(...)`, bare `super`, first-class `super.method` values, `super` attribute read/write, native collection `super` lookup, or user-facing method context introspection.
