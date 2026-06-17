# Slice 046: superiors(Class) Transitive Superclass Chain Design

Related requirements: [docs/slices/046-superiors-transitive-superclass-chain-requirements.md](/home/tprover/2606_enact_auto/docs/slices/046-superiors-transitive-superclass-chain-requirements.md)

## Design Objective

Add the PRD's transitive superclass introspection helper while preserving the Slice 045 meaning of `supers` as direct-superclass introspection.

The runtime surface is:

```text
superiors(Class)
```

and the result is a list of class values ordered from direct superclass to root.

## Semantics

Given:

```text
class A < Object
class B < A
class C < B
```

the two helpers intentionally differ:

```text
supers(C)     -> <class B>:nil
superiors(C) -> <class B>:<class A>:<class Object>:nil
```

The input class is excluded from `superiors`.

## Builtin

`builtin.c` adds:

```c
static int enact_builtin_superiors(...)
```

The builtin:

1. requires a class argument
2. recursively walks `enact_class_superclass`
3. returns `nil` for root classes
4. conses each direct superclass in front of the recursively produced tail

The existing list/value copy path retains class values while building the result list.

## Parser And Evaluator

No lexer, parser, AST, or evaluator changes are required. `superiors` is installed through the existing builtin table and participates in first-class builtin behavior, partial application, higher-order list builtins, and shadowing exactly like other builtins.

## Single-Inheritance Phase

The current class runtime stores one retained superclass pointer per class. This slice therefore produces a simple linear chain. Multiple inheritance can later extend the traversal rules without changing the PRD-level distinction between direct `supers` and transitive `superiors`.

## Deferred Work

Later slices may add:

- multiple inheritance traversal
- ambiguity and validation helpers
- method introspection
- class/object membership helpers
- `super` dispatch
