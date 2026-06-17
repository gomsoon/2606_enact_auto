# Slice 037: Root Object Runtime Core Design

## Runtime Values

Add two ref-counted runtime payloads:

```c
EnactClass
EnactObject
```

`EnactClass` stores the class name. `EnactObject` stores a retained pointer to its class. These are exposed through opaque declarations in `object.h` so the rest of the interpreter can copy and release them through `EnactValue`.

Add two value kinds:

```c
ENACT_VALUE_CLASS
ENACT_VALUE_OBJECT
```

Copying retains the underlying class or object. Freeing releases it. Equality is pointer identity for both kinds.

## Default Environment

`enact_install_builtins` also installs the root class binding:

```c
Object -> ENACT_VALUE_CLASS("Object")
```

This keeps `Object` on the same environment path as future class declarations. It is not added to the builtin lookup table and is not callable.

## Parser

Add `AST_NEW` as a unary AST node. For this slice the grammar accepts only:

```text
new Identifier
```

The parser lowers `new Object` to:

```text
AST_NEW(AST_IDENTIFIER("Object"))
```

Parenthesized creation and zero-argument constructor-call spelling remain deferred.

## Evaluation

`AST_NEW` evaluation:

1. evaluates its child expression
2. requires `ENACT_VALUE_CLASS`
3. creates an `EnactObject` retaining that class
4. returns `ENACT_VALUE_OBJECT`

If the child evaluates to a non-class, evaluation reports `ENACT_ERR_TYPE_EXPECTED_CLASS`.

## Printing

The command-line printer adds:

```text
<class Object>
<object Object>
```

The object print path asks the object for its class and prints that class name.

## Builtins

`isObject` changes from a placeholder that always returns false to a value-kind check:

```text
argument.kind == ENACT_VALUE_OBJECT
```

Classes are not objects, so `isObject(Object)` is false.

`atom` needs no special code because its current semantics already return true for every non-list value.

## Deferred Work

This slice deliberately leaves the following for later OO slices:

- `class Node < Object`
- instance attributes
- `with` initialization
- method lookup and message dispatch
- dot access
- inheritance
- class reflection or `classof`
- constructor functions and parenthesized constructor calls
