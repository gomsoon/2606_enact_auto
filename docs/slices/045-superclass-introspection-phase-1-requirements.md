# Slice 045: Superclass Introspection Phase 1 Requirements

Update note: Slice 087 later makes `supers(object)` behave like `supers(classof(object))` and changes non-class, non-object misuse to `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

## Scope

Slice 045 adds the first class-inheritance introspection builtin:

```text
supers(Class)
```

The builtin returns the direct superclass list for a class. The current runtime supports exactly one superclass per user class, so Phase 1 returns either `nil` for the root `Object` class or a one-element class list for user-defined classes.

## Functional Requirements

- `supers(class)` shall return a list of class values.
- `supers(Object)` shall return `nil`.
- `supers(Node)` shall return `<class Object>:nil` when `Node` directly extends `Object`.
- `supers(Leaf)` shall return `<class Node>:nil` when `Leaf` directly extends `Node`.
- `supers` shall report direct superclasses only; transitive ancestors shall not be included.
- The returned class values shall preserve identity and work with equality, `member`, `hd`, `size`, `map`, and `filter`.
- `supers(classof(object))` shall work by composing existing `classof` introspection with `supers`.
- `supers` shall be a normal first-class builtin.
- User bindings shall be able to shadow `supers`, matching existing builtin behavior.

## Evaluation Boundaries

- `supers` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Object values shall not be accepted directly; users should call `supers(classof(obj))` when starting from an object.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class with no direct superclass
- root superclass list equality with `nil`
- user class direct superclass
- subclass direct superclass
- superclass identity through `hd`
- list size for root and non-root classes
- `member` over returned superclass lists
- class aliases
- direct-only behavior for a multi-level inheritance chain
- `map` and `filter` composition
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
- shadowed non-function `supers`

## Out of Scope

This slice does not implement:

- multiple inheritance
- `superiors` or any transitive ancestor helper
- `suppliers`, `OK`, or `badAttrs`
- method introspection
- attribute inheritance or default attributes
- `super` method calls

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
