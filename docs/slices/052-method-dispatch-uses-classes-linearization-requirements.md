# Slice 052: Method Dispatch Uses classes(Class) Linearization Requirements

## Goal

Slice 052 aligns object method dispatch with the multiple-inheritance class linearization introduced for `classes(Class)` in Slice 051.

## Requirements

- Method lookup shall use the same linearization order reported by `classes(classof(object))`.
- A direct method on the receiver's class shall still win over inherited methods.
- For `class C < (A,B)`, methods on `A` shall be considered before methods on `B`.
- For shared ancestors, methods shall be considered at their position in the C3-style class linearization.
- Object attributes shall continue to shadow class methods.
- Once method lookup selects a method, arity mismatch shall report `ENACT_ERR_ARITY_MISMATCH` and shall not fall back to a later class.
- Missing methods after the full linearization shall still report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- `methods(Class)` shall remain direct-only and shall not report inherited methods.
- `classes`, `superiors`, and `supers` introspection behavior from Slice 051 shall remain unchanged.

## Regression Focus

- Existing single-inheritance dispatch remains unchanged.
- Multiple-inheritance dispatch follows `classes(Class)` order.
- Cases that previously would have found `Object` through depth-first traversal now find a later direct superclass when linearization places it before `Object`.
- Attribute shadowing, wrong arity, non-object receivers, and selected method body failures keep their existing diagnostics.

## Deferred

- Dedicated ambiguity diagnostics are deferred.
- `suppliers`, `OK`, and `badAttrs` remain deferred.
- Explicit `super` dispatch remains deferred.
