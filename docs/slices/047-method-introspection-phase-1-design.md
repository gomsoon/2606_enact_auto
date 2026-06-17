# Slice 047: Method Introspection Phase 1 Design

Related requirements: [docs/slices/047-method-introspection-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/047-method-introspection-phase-1-requirements.md)

## Design Objective

Add a small method-introspection surface that reports only methods defined directly on a class:

```text
methods(Class)
```

This complements the existing dispatch behavior from Slice 043. Dispatch may walk the superclass chain, while `methods` intentionally reports direct class-local definitions only.

## Runtime Helper

`object.c` adds:

```c
int enact_class_method_names(const EnactClass *class_value, EnactList **out);
```

The helper keeps the private `EnactMethod` storage hidden from builtin code. It walks the class's direct method list and builds a list of atom values.

Method definitions are stored newest-first internally, so the helper prepends each discovered method name into the output list. That reverses storage order and returns first-definition order to users. Existing method replacement updates the stored function in place, so replacement naturally avoids duplicates and preserves order.

## Builtin

`builtin.c` adds:

```c
static int enact_builtin_methods(...)
```

The builtin:

1. requires a class argument
2. calls `enact_class_method_names`
3. returns `nil` for classes with no direct methods
4. returns an atom list for direct method names

The returned list uses the existing value/list ownership rules, so atom names are independently owned by the list result.

## Parser And Evaluator

No lexer, parser, AST, or evaluator changes are required. `methods` is installed through the existing builtin table and participates in first-class builtin behavior, partial application, higher-order list builtins, and shadowing exactly like other builtins.

## Direct-Only Boundary

Given:

```text
class Node < Object
Node.get():=1
class Leaf < Node
Leaf.set(v):=v
```

the expected phase-one behavior is:

```text
methods(Node) -> 'get:nil
methods(Leaf) -> 'set:nil
```

`(new Leaf).get()` still succeeds through inherited dispatch, but `methods(Leaf)` does not include `'get`.

## Deferred Work

Later slices may add:

- inherited method introspection
- method arity and signature metadata
- method resolution order reporting
- bound methods
- `super` calls
- class membership and ambiguity validation helpers
