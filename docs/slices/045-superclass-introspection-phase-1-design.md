# Slice 045: Superclass Introspection Phase 1 Design

Related requirements: [docs/slices/045-superclass-introspection-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/045-superclass-introspection-phase-1-requirements.md)

## Design Objective

Add a stable, low-risk class introspection builtin that exposes the direct superclass relation already stored on `EnactClass`.

The runtime surface is:

```text
supers(Class)
```

and the result is a list of class values.

## Naming

The PRD names `supers` alongside later OO inspection helpers such as `classes`, `superiors`, `suppliers`, `OK`, and `badAttrs`. This slice uses `supers` instead of introducing a new name such as `superof`.

## Builtin

`builtin.c` adds:

```c
static int enact_builtin_supers(...)
```

The builtin:

1. requires a class argument
2. reads `enact_class_superclass`
3. returns `nil` when no direct superclass exists
4. otherwise returns a one-element list containing the direct superclass value

The existing list/value copy path retains class values while building the result list.

## Direct-Only Semantics

`supers` intentionally returns direct superclasses only:

```text
class A < Object
class B < A
class C < B
supers(C)  ->  <class B>:nil
```

This matches the future multiple-inheritance shape where direct superclasses naturally form a list. Transitive ancestor inspection belongs to a later helper such as `superiors`.

## Parser And Evaluator

No lexer, parser, AST, or evaluator changes are required. `supers` is installed through the existing builtin table and participates in first-class builtin behavior, partial application, higher-order list builtins, and shadowing exactly like other builtins.

## Deferred Work

Later slices may add:

- transitive superclass introspection
- multiple inheritance direct superclass lists
- method introspection
- ambiguity and validation helpers
- `super` dispatch
