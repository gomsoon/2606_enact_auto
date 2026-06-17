# Slice 048: classes(Class) Inclusive Class Chain Design

Related requirements: [docs/slices/048-classes-inclusive-class-chain-requirements.md](/home/tprover/2606_enact_auto/docs/slices/048-classes-inclusive-class-chain-requirements.md)

## Design Objective

Add the PRD-named inclusive class-chain helper:

```text
classes(Class)
```

This complements the existing direct and transitive superclass helpers:

```text
supers(Class)    -> direct superclass list
superiors(Class) -> superclass chain, excluding Class
classes(Class)   -> class chain, including Class
```

## Semantics

Given:

```text
class A < Object
class B < A
class C < B
```

the three helpers intentionally differ:

```text
supers(C)    -> <class B>:nil
superiors(C) -> <class B>:<class A>:<class Object>:nil
classes(C)   -> <class C>:<class B>:<class A>:<class Object>:nil
```

For the root class:

```text
classes(Object) -> <class Object>:nil
```

## Builtin

`builtin.c` adds:

```c
static int enact_builtin_classes(...)
```

The builtin:

1. requires a class argument
2. recursively walks `enact_class_superclass`
3. conses the current class in front of the recursively produced superclass tail
4. returns the resulting class list

The implementation uses the same list/value copy path as `supers` and `superiors`, so returned class values preserve identity through retained class pointers.

## Parser And Evaluator

No lexer, parser, AST, or evaluator changes are required. `classes` is installed through the existing builtin table and participates in first-class builtin behavior, partial application, higher-order list builtins, and shadowing exactly like other builtins.

## Single-Inheritance Phase

The current runtime stores one retained superclass pointer per class. Therefore `classes(Class)` is linear and satisfies:

```text
classes(Class) == append(list(Class), superiors(Class))
```

When multiple inheritance lands, this helper can evolve to follow the chosen class-chain or method-resolution ordering while preserving the inclusive-head contract.

## Deferred Work

Later slices may add:

- multiple inheritance class-chain traversal
- ambiguity and validation helpers
- method resolution order reporting
- class-chain deduplication rules
- `super` dispatch
