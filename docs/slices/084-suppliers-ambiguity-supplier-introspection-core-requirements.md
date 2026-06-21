# Slice 084: suppliers(Class, attr) Ambiguity Supplier Introspection Core Requirements

## Goal

Slice 084 adds the PRD/manual-named supplier helper:

```text
suppliers(Class, attr)
```

The manual describes `suppliers(obj, attr)` as the classes that supply an attribute to an object. The current runtime keeps inherited class-level behavior in methods, so this slice applies the rule to class method suppliers.

## Requirements

- `suppliers(class, attr)` shall return a list of class values that effectively supply method name `attr` to `class`.
- The second argument shall be a quoted atom, for example `suppliers(C, 'f)`.
- `suppliers(Object, attr)` shall return `nil` unless Object directly defines that method name.
- A class with no matching method supplier shall return `nil`.
- A direct method on the queried class shall return the queried class as the single supplier and shall mask same-named inherited suppliers.
- If two direct superclasses effectively supply the same method name from distinct classes, both supplier classes shall appear in superclass traversal order.
- If a shared ancestor is the only effective supplier reached through multiple paths, that ancestor shall appear once.
- If one branch overrides a shared ancestor method while another branch inherits it, both supplier classes shall appear.
- Ambiguity inherited through a superclass shall remain visible to subclasses until masked by a direct method definition.
- `suppliers(classof(object), attr)` shall work by composing existing `classof` introspection with `suppliers`.
- `suppliers` shall remain usable on classes with inconsistent linearization because it does not need to choose a method dispatch order.
- `suppliers` shall be a normal first-class builtin and shall compose with `map`, `filter`, `member`, `size`, conditionals, and user helper functions.
- One-argument calls such as `suppliers(Object)` shall follow existing builtin partial application behavior and return a callable.
- User bindings shall be able to shadow `suppliers`, matching existing builtin behavior.

## Evaluation Boundaries

- `suppliers` shall have arity two.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class first arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Non-atom second arguments shall report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- Object values shall not be accepted directly as the first argument; users should call `suppliers(classof(obj), attr)` when starting from an object.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class with missing method.
- class with no matching supplier.
- direct method supplier.
- inherited single supplier.
- unrelated superclass methods.
- two direct superclasses supplying the same method name.
- direct child method masking inherited suppliers.
- shared common ancestor supplying a method through multiple paths without duplication.
- one branch overriding a shared ancestor method.
- ambiguity inherited through an intermediate superclass.
- `classof` composition.
- `member` and `size` composition.
- `map` over class lists.
- `filter` over class lists.
- conditional use.
- first-class builtin use.
- partial application.
- builtin shadowing.
- inconsistent linearization still allowing `suppliers`.
- direct masking on an inconsistent class.

Robustness coverage shall include:

- zero-argument call.
- over-application without evaluating an impossible extra argument.
- non-class first-argument primitive values.
- list, object, function, and builtin first-argument values.
- subclass object misuse when `classof` is not used.
- non-atom second-argument primitive values.
- list, class, object, function, and builtin second-argument values.
- list result misuse as an integer.
- list result misuse as a boolean.
- list result misuse as a callable.
- shadowed non-function `suppliers`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
