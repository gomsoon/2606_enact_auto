# Slice 047: Method Introspection Phase 1 Requirements

Update note: Slice 088 later makes `methods(object)` behave like `methods(classof(object))` and changes non-class, non-object misuse to `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

## Scope

Slice 047 adds a direct-method introspection builtin:

```text
methods(Class)
```

`methods` returns the names of methods defined directly on the class argument. Inherited methods remain callable through dispatch, but are not included in this phase.

## Functional Requirements

- `methods(class)` shall return a list of atom values.
- `methods(Object)` shall return `nil` until methods are directly defined on `Object`.
- `methods(Node)` shall return method names defined directly on `Node`.
- Method names shall be returned in first-definition order.
- Redefining an existing method shall not duplicate or reorder its name.
- Inherited methods shall not appear in a subclass's direct `methods` result.
- Direct subclass methods shall appear even when the superclass defines other methods.
- `methods` shall preserve normal list behavior and compose with `member`, `size`, `map`, and `filter`.
- `methods(classof(object))` shall work by composing existing `classof` introspection with `methods`.
- `methods` shall be a normal first-class builtin.
- User bindings shall be able to shadow `methods`, matching existing builtin behavior.

## Evaluation Boundaries

- `methods` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Object values shall not be accepted directly; users should call `methods(classof(obj))` when starting from an object.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class with no methods
- root method list equality with `nil`
- class with no direct methods
- single direct method
- multiple direct methods and ordering
- method replacement without duplication
- inherited method exclusion
- direct subclass method inclusion
- inherited dispatch still working while direct introspection excludes inherited methods
- `member`, `size`, `map`, and `filter` composition
- `classof` composition
- first-class builtin use
- builtin shadowing

Robustness coverage shall include:

- zero-argument call
- over-application without evaluating an impossible extra argument
- non-class primitive values
- list, object, function, and builtin values
- subclass object misuse
- list result misuse as an integer
- list result misuse as a boolean
- shadowed non-function `methods`

## Out of Scope

This slice does not implement:

- inherited method introspection
- method signature or arity introspection
- bound method values, later added by Slice 079
- method source or body inspection
- `super` method calls
- multiple inheritance method resolution reporting

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
