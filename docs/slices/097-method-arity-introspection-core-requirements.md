# Slice 097: Method Arity Introspection Core Requirements

## Goal

Slice 097 adds a small method metadata helper:

```text
methodArity(class_or_object, 'methodName)
```

It returns the arity of the user-defined method that normal dispatch would select for the class or object's runtime class.

## Requirements

- Add a builtin named `methodArity`.
- `methodArity` shall have arity two.
- The first argument shall accept a class or object.
- Object arguments shall use the object's runtime class.
- The second argument shall be an atom naming the method.
- If normal user-defined method dispatch finds a method, return its arity as an integer.
- If no user-defined method is found, return `nil`.
- If the class cannot be consistently linearized, report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- If the first argument is neither a class nor an object, report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- If the second argument is not an atom, report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- `methodArity` shall be a normal first-class builtin and support existing builtin partial application behavior.
- User shadowing of `methodArity` shall behave like other builtins.

## Semantics

`methodArity` shall use the same checked lookup path as:

```text
methodSupplier(class_or_object, 'methodName)
```

Therefore:

- direct methods return their own arity.
- inherited methods return the inherited method's arity.
- overrides return the overriding method's arity.
- multiple inheritance follows the checked class linearization order.
- object arguments and class arguments agree for the same runtime class.

## Native Collection Methods

This slice exposes only user-defined class methods. Builtin-backed native collection dot methods remain hidden:

```text
methodArity(set(), 'size) -> nil
```

If a user defines a class method on a native collection class, it shall be visible:

```text
Set.size(x):=x
methodArity(set(), 'size) -> 1
```

## Regression Requirements

Boundary coverage shall include:

- missing methods returning `nil`.
- zero-argument methods.
- multi-argument methods.
- object arguments.
- inherited methods.
- overrides.
- multiple-inheritance lookup order.
- shared-superclass lookup.
- higher-order use.
- builtin partial application.
- helper-call use.
- native collection methods remaining hidden.
- user-defined native collection class methods being visible.
- user shadowing.

Robustness coverage shall include:

- arity mismatch.
- invalid first-argument types.
- invalid atom argument types.
- misuse of `nil` results as bools or callables.
- partial builtin completion with a bad atom argument.
- inconsistent linearization.
- user shadowing with a non-function.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
