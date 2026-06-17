# Slice 038: Class Definition Runtime Core Design

## Runtime Model

`EnactClass` gains an optional retained superclass pointer:

```c
struct EnactClass {
    size_t ref_count;
    char *name;
    EnactClass *superclass;
};
```

The root `Object` class keeps a null superclass. User-defined classes retain exactly one superclass for this slice.

The runtime exposes:

```c
EnactClass *enact_class_new_with_superclass(const char *name, EnactClass *superclass);
EnactClass *enact_class_superclass(const EnactClass *class_value);
```

Existing class copy/free behavior remains pointer-retain based through `ENACT_VALUE_CLASS`.

## AST

Add:

```c
AST_CLASS_DEF
```

with payload:

```c
char *name;
EnactAst *superclass;
```

The superclass is stored as an AST node so evaluation follows the existing environment lookup and diagnostic path. For Slice 038, the parser only builds an identifier node there.

## Parser

Add a narrow class-definition rule:

```text
class_definition:
    TOK_CLASS TOK_IDENTIFIER TOK_LT TOK_IDENTIFIER
```

The rule lowers:

```text
class Node < Object
```

to:

```text
AST_CLASS_DEF(name="Node", superclass=AST_IDENTIFIER("Object"))
```

Class definitions are accepted at the assignment-expression level, which lets them appear as top-level expressions and inside existing sequencing.

## Evaluation

`AST_CLASS_DEF` evaluation:

1. evaluates the superclass expression
2. requires `ENACT_VALUE_CLASS`
3. creates a new class with the requested name and retained superclass
4. defines that class in the current environment
5. returns the new class value

This means:

```text
class Node < Object
new Node
```

works because both expressions share the same session/script environment.

## Deferred Work

This slice does not implement:

- class bodies
- attributes
- `with`
- dot attribute access
- method definitions such as `A.f(x):=...`
- `self`
- inherited method or attribute lookup
- multiple inheritance
- superclass introspection builtins

Those features should build on the class identity and superclass storage introduced here.
