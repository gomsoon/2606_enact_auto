# Slice 040: `classof` + Basic Introspection Requirements

## Scope

Slice 040 adds the first class introspection builtin:

```text
classof(object)
```

The goal is to make OO tests able to observe an object's runtime class before method dispatch, `self`, class-level attributes, or multiple inheritance are implemented.

## Functional Requirements

### `classof`

- `classof(value)` shall be installed as a normal one-argument builtin.
- When `value` is an object, `classof` shall return the object's class value.
- The returned class shall preserve object class identity:

```text
class Node < Object
classof(new Node) == Node
```

- `classof(new Object)` shall return the root `Object` class.
- `classof` shall compose with existing assignment, list printing, object attributes, lambdas, and higher-order list builtins.

### Type Boundary

This slice intentionally defines `classof` only for object values.

Non-object values shall report `ENACT_ERR_TYPE_EXPECTED_OBJECT`, including:

- integers
- booleans
- strings
- lists and `nil`
- functions and builtins
- class values such as `Object` or `Node`

Primitive value classes and metaclasses remain deferred until the class model has a larger semantic basis.

## Regression Requirements

Boundary coverage shall include:

- `classof(new Object)`
- equality between `classof(new Object)` and `Object`
- user-defined class objects
- subclass objects
- assigned objects
- attributes that store objects or class values
- `map`, `all`, and lambda composition
- class values printed inside lists

Robustness coverage shall include:

- zero-argument and over-applied `classof`
- non-object inputs across implemented runtime kinds
- class values used as inputs
- returned class values misused as integers or other incompatible kinds

## Out of Scope

This slice does not implement:

- `attrs`
- `supers`, `classes`, `superiors`, `suppliers`, `OK`, or `badAttrs`
- primitive classes such as `Integer`, `Boolean`, or `String`
- a metaclass or `Class` object model
- method dispatch or `self`
- inherited attribute or method lookup

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
