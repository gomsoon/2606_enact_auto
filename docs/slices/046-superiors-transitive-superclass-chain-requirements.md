# Slice 046: superiors(Class) Transitive Superclass Chain Requirements

Update note: Slice 087 later makes `superiors(object)` behave like `superiors(classof(object))` and changes non-class, non-object misuse to `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

## Scope

Slice 046 adds the transitive superclass introspection builtin named by the PRD:

```text
superiors(Class)
```

`supers(Class)` remains the direct-superclass helper from Slice 045. `superiors(Class)` returns the superclass chain from the direct superclass to the root.

## Functional Requirements

- `superiors(class)` shall return a list of class values.
- `superiors(Object)` shall return `nil`.
- `superiors(Node)` shall return `<class Object>:nil` when `Node` directly extends `Object`.
- `superiors(C)` shall return `<class B>:<class A>:<class Object>:nil` for `C < B < A < Object`.
- The receiver class itself shall not be included in the result.
- The direct superclass shall be the head of the returned list.
- The root `Object` class shall be the final element when the input has `Object` as an ancestor.
- `superiors` shall preserve class identity and compose with equality, `member`, `hd`, `size`, `map`, and `filter`.
- `superiors(classof(object))` shall work by composing existing `classof` introspection with `superiors`.
- `superiors` shall be a normal first-class builtin.
- User bindings shall be able to shadow `superiors`, matching existing builtin behavior.

## Evaluation Boundaries

- `superiors` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Object values shall not be accepted directly; users should call `superiors(classof(obj))` when starting from an object.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class with no superiors
- root superiors equality with `nil`
- one-level superclass chain
- multi-level superclass chain
- direct-superclass head ordering
- root at the end of a multi-level chain
- self exclusion
- visible distinction from `supers`
- list size across root, one-level, and multi-level chains
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
- shadowed non-function `superiors`

## Out of Scope

This slice does not implement:

- multiple inheritance traversal
- cycle diagnostics
- `suppliers`, `OK`, or `badAttrs`
- method introspection
- attribute inheritance or default attributes
- `super` method calls

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
