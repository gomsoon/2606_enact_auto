# Slice 044: attrs(obj) Basic Introspection Requirements

## Scope

Slice 044 adds a small object-introspection builtin:

```text
attrs(obj)
```

The builtin returns the names of attributes stored directly on an object as a list of quoted atoms.

## Functional Requirements

- `attrs(object)` shall return a list of atom values.
- An object with no direct attributes shall return `nil`.
- Attribute names shall be returned in first-definition order:

```text
attrs(new Node with x:=1 with y:=2)  ->  'x:'y:nil
```

- Redefining an existing attribute shall not duplicate or reorder that attribute name:

```text
attrs(new Node with x:=1 with y:=2 with x:=3)  ->  'x:'y:nil
```

- Attributes created by object attribute assignment shall be visible through `attrs`.
- Object-valued attributes shall keep their own independent attribute lists.
- The builtin shall only report directly stored object attributes.
- Class methods, inherited methods, classes, and superclass names shall not appear in `attrs` output.
- `attrs` shall be a normal first-class builtin and shall work with higher-order list builtins.
- User bindings shall be able to shadow `attrs`, matching existing builtin behavior.

## Evaluation Boundaries

- `attrs` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-object arguments shall report `ENACT_ERR_TYPE_EXPECTED_OBJECT`.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- empty object attributes
- single attribute
- multiple attributes in first-definition order
- attribute redefinition without duplicate names
- attribute assignment-created names
- object-valued nested attributes
- `member`, `size`, `map`, and `all` composition with `attrs`
- methods excluded from `attrs`
- subclass object attributes
- first-class builtin use
- builtin shadowing

Robustness coverage shall include:

- zero-argument call
- over-application without evaluating an impossible extra argument
- non-object values across primitive, list, class, function, and builtin categories
- list result misuse as an integer
- list result misuse as a boolean
- shadowed non-function `attrs`

## Out of Scope

This slice does not implement:

- class attribute introspection
- inherited/default attribute lookup
- method introspection
- superclass introspection
- attribute value introspection beyond the existing dot-read operation

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
