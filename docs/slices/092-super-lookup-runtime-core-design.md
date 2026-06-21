# Slice 092: Super Lookup Runtime Core Design

Related requirements: [docs/slices/092-super-lookup-runtime-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/092-super-lookup-runtime-core-requirements.md)

## Runtime Helper

Slice 092 adds:

```c
int enact_class_lookup_super_method_with_supplier(
    EnactClass *receiver_class,
    EnactClass *current_supplier,
    const char *name,
    EnactFunction **out,
    EnactClass **supplier_out,
    int *consistent);
```

The helper is deliberately runtime-only. No lexer, parser, AST, or evaluator `super` syntax is added in this slice.

## Lookup Rule

The helper first builds the checked linearization for the receiver class, using the same C3-style runtime path used by method dispatch, `methodSupplier`, and `effectiveMethods`.

Given:

```text
classes(Leaf) -> Leaf:Left:Right:Top:Object:nil
```

super lookup with `current_supplier = Left` starts at `Right`. It never reselects `Left`, even when `Left` directly defines the requested method.

This exactly models the future method-body rule:

```text
super.method(args)
```

from a method supplied by `current_supplier`.

## Missing And Invalid Context

If the current supplier is not present in the receiver linearization, the helper returns no selected method. That keeps this low-level API policy-neutral: the future evaluator can decide whether that should become an unbound-attribute diagnostic, an invalid-super-context diagnostic, or another error.

If no later class defines the method, the helper also returns no selected method.

If the receiver class cannot be consistently linearized, the helper returns successfully with `consistent = 0`. Callers can surface `ENACT_ERR_INCONSISTENT_LINEARIZATION` using the existing diagnostic policy.

## Relationship To Existing Dispatch

Ordinary method dispatch remains unchanged:

```text
class A < Object
A.f():=1
class B < A
B.f():=2
(new B).f() -> 2
```

Super lookup is an alternate lookup entrypoint. It does not affect attribute reads, dot-calls, bound method values, `methodSupplier`, `effectiveMethods`, or native collection method lookup.

## Testing Shape

The C unit tests cover invalid arguments, root/no-super cases, single-inheritance override lookup, lookup after a superclass supplier, unrelated supplier handling, missing names, and multiple-inheritance ordering.

The Python regression suite adds user-visible guardrails proving that existing dispatch behavior remains unchanged and that `super` remains an ordinary identifier in this slice.

## Deferred Work

This slice does not add `super.method(...)` syntax, bare `super`, first-class `super.method` values, `super` attribute read/write, native collection `super` lookup, method signatures, method source introspection, or method body metadata.
