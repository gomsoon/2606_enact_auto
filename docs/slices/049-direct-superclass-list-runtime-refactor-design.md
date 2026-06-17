# Slice 049: Direct Superclass List Runtime Refactor Design

Related requirements: [docs/slices/049-direct-superclass-list-runtime-refactor-requirements.md](/home/tprover/2606_enact_auto/docs/slices/049-direct-superclass-list-runtime-refactor-requirements.md)

## Design Objective

Prepare the class runtime for multiple inheritance without changing public language behavior yet.

Before this slice, `EnactClass` stored one retained superclass pointer:

```c
EnactClass *superclass;
```

After this slice, it stores an ordered private linked list:

```c
EnactClassLink *superclasses;
```

The current parser and evaluator still create at most one direct superclass. That keeps the user-visible single-inheritance behavior stable while letting the runtime and introspection helpers speak in list-shaped terms.

## Runtime Storage

`object.c` adds a private class-link node:

```c
typedef struct EnactClassLink {
    EnactClass *class_value;
    struct EnactClassLink *next;
} EnactClassLink;
```

Each link retains its class value. Class release walks the link list and releases every retained direct superclass.

## Compatibility API

The existing API remains:

```c
EnactClass *enact_class_superclass(const EnactClass *class_value);
```

It now returns the first direct superclass, or null when the class has no direct superclasses. This keeps existing tests and single-inheritance call sites simple.

The slice also adds:

```c
int enact_class_superclasses(const EnactClass *class_value, EnactList **out);
```

This helper returns the direct superclass list as class values in stored order. For the current public syntax, the result is either `nil` or a one-element list.

## Builtin Refactor

`supers(Class)` now delegates to `enact_class_superclasses` instead of manually wrapping `enact_class_superclass` in a one-element list.

`superiors(Class)` and `classes(Class)` keep their existing single-inheritance traversal through `enact_class_superclass`. This preserves current behavior while giving future multiple-inheritance slices a clear place to replace traversal rules.

## Method Lookup

`enact_class_lookup_method` is split into:

1. direct method lookup on the current class
2. recursive lookup across the direct-superclass link list

For this slice, the link list has at most one superclass, so lookup order remains exactly the same: subclass first, then superclass chain.

When multiple direct superclasses are introduced, this shape naturally becomes left-to-right direct-superclass traversal unless a later slice replaces it with a manual-confirmed method-resolution rule.

## Parser And Evaluator

No lexer, parser, AST, or evaluator grammar changes are required. `AST_CLASS_DEF` still evaluates one superclass expression and calls `enact_class_new_with_superclass`.

## Behavioral Preservation

The following examples intentionally keep their Slice 048 results:

```text
supers(Object) -> nil
supers(Node)   -> <class Object>:nil
classes(C)     -> <class C>:<class B>:<class A>:<class Object>:nil
```

Inherited method dispatch and direct method introspection are also preserved.

## Deferred Work

Later slices may add:

- parser support for `class C < (A,B)`
- constructor support for multiple direct superclasses
- `supers(C)` returning multiple direct superclasses
- multiple-inheritance `superiors` and `classes` traversal
- ambiguity helpers such as `suppliers`, `OK`, and `badAttrs`
- explicit `super` dispatch
