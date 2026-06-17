# Slice 040: `classof` + Basic Introspection Design

Related requirements: [docs/slices/040-classof-basic-introspection-requirements.md](/home/tprover/2606_enact_auto/docs/slices/040-classof-basic-introspection-requirements.md)

## Design Objective

Add object class introspection without changing the lexer, parser, AST, or evaluator. `classof` is a normal builtin value installed in the default environment.

## Builtin Callback

`classof` is implemented in `builtin.c` as a one-argument callback:

```c
static int enact_builtin_classof(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
```

The generic builtin apply layer already checks arity before the callback runs.

The callback:

1. requires `arguments[0].kind == ENACT_VALUE_OBJECT`
2. reads the object's class with `enact_object_class`
3. retains that class
4. returns it as `ENACT_VALUE_CLASS`

Retaining the class is required because returned values are owned by the caller and freed through the normal `EnactValue` path.

## Builtin Table

Add:

```c
{"classof", 1, enact_builtin_classof},
```

No reserved word or parser special case is introduced. The name remains shadowable by ordinary assignment, like the rest of the builtin table.

## Type Semantics

`classof` is object-only in this slice.

This avoids inventing primitive classes or a metaclass model before manual-backed object dispatch has landed. For now:

```text
classof(new Node)  -> <class Node>
classof(Node)      -> ENACT_ERR_TYPE_EXPECTED_OBJECT
classof(1)         -> ENACT_ERR_TYPE_EXPECTED_OBJECT
```

## Test Design

Regression tests cover:

- root object class introspection
- user-defined class identity
- subclass objects
- assigned object values
- attribute composition
- lambda and higher-order builtin use
- non-object type errors
- arity errors

Unit tests cover:

- builtin lookup
- arity metadata
- default environment installation
- direct `enact_builtin_apply`
- object class identity and diagnostic failure for an integer input

## Deferred Work

Later OO slices can build on `classof` by adding:

- primitive class values
- `attrs`
- superclass and ambiguity introspection helpers
- class-level methods
- method dispatch and `self`
