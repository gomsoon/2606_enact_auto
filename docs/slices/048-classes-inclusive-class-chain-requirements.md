# Slice 048: classes(Class) Inclusive Class Chain Requirements

## Scope

Slice 048 adds the PRD-named class-chain introspection builtin:

```text
classes(Class)
```

`superiors(Class)` returns the superclass chain excluding the input class. `classes(Class)` returns the inclusive chain starting with the input class and ending at the root.

## Functional Requirements

- `classes(class)` shall return a list of class values.
- `classes(Object)` shall return `<class Object>:nil`.
- `classes(Node)` shall return `<class Node>:<class Object>:nil` when `Node` directly extends `Object`.
- `classes(C)` shall return `<class C>:<class B>:<class A>:<class Object>:nil` for `C < B < A < Object`.
- The input class shall be the head of the returned list.
- The root `Object` class shall be the final element when the input has `Object` as an ancestor.
- `classes(class)` shall equal `append(list(class), superiors(class))` for the current single-inheritance runtime.
- `classes` shall preserve class identity and compose with equality, `member`, `hd`, `tl`, `size`, `map`, and `filter`.
- `classes(classof(object))` shall work by composing existing `classof` introspection with `classes`.
- `classes` shall be a normal first-class builtin.
- User bindings shall be able to shadow `classes`, matching existing builtin behavior.

## Evaluation Boundaries

- `classes` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Object values shall not be accepted directly; users should call `classes(classof(obj))` when starting from an object.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class inclusive chain
- root class head and tail
- root class size
- one-level class chain
- multi-level class chain
- input-class head ordering
- root at the end of a multi-level chain
- self inclusion compared with `superiors`
- equality with `append(list(Class), superiors(Class))`
- `member`, `map`, and `filter` composition
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
- shadowed non-function `classes`

## Out of Scope

This slice does not implement:

- multiple inheritance traversal
- class-chain deduplication
- cycle diagnostics
- `suppliers`, `OK`, or `badAttrs`
- method resolution order reporting
- `super` method calls

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
