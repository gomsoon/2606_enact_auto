# Slice 098: Method Parameter Introspection Core Requirements

## Goal

Slice 098 adds method parameter-name metadata:

```text
methodParams(class_or_object, 'methodName)
```

It returns the parameter names of the user-defined method that normal dispatch would select for the class or object's runtime class.

## Requirements

- Add a builtin named `methodParams`.
- `methodParams` shall have arity two.
- The first argument shall accept a class or object.
- Object arguments shall use the object's runtime class.
- The second argument shall be an atom naming the method.
- If normal user-defined method dispatch finds a method, return its parameter names as an atom list in declaration order.
- If the selected method has zero parameters, return `nil`.
- If no user-defined method is found, return `nil`.
- If callers need to distinguish a zero-parameter method from a missing method, they shall use `methodArity` or `methodSupplier`.
- If the class cannot be consistently linearized, report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- If the first argument is neither a class nor an object, report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- If the second argument is not an atom, report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- `methodParams` shall be a normal first-class builtin and support existing builtin partial application behavior.
- User shadowing of `methodParams` shall behave like other builtins.

## Semantics

`methodParams` shall use the same checked lookup path as:

```text
methodSupplier(class_or_object, 'methodName)
methodArity(class_or_object, 'methodName)
```

Therefore:

- direct methods return their own parameter names.
- inherited methods return the inherited method's parameter names.
- overrides return the overriding method's parameter names.
- multiple inheritance follows the checked class linearization order.
- object arguments and class arguments agree for the same runtime class.

## Native Collection Methods

This slice exposes only user-defined class methods. Builtin-backed native collection dot methods remain hidden:

```text
methodParams(set(), 'size) -> nil
```

If a user defines a class method on a native collection class, it shall be visible:

```text
Set.size(x):=x
methodParams(set(), 'size) -> 'x:nil
```

## Regression Requirements

Boundary coverage shall include:

- missing methods returning `nil`.
- zero-argument methods returning `nil`.
- multi-argument methods preserving declaration order.
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
