# Slice 106: hasMethod Predicate Requirements

## Goal

Slice 106 adds a small dispatch-facing predicate:

```text
hasMethod(class_or_object, 'methodName)
```

It answers whether normal dot-method dispatch would find a callable method name for a class or object, including builtin-backed native collection methods.

## Requirements

- Add a builtin named `hasMethod`.
- `hasMethod` shall have arity two.
- The first argument shall accept either a class value or an object value.
- Object arguments shall use the object's runtime class.
- The second argument shall be an atom naming the method.
- If checked user-defined method lookup finds a method, return `true`.
- If no user-defined method is found and the class is Set-like or Bag-like, return `true` when the native collection method table contains the name.
- If neither lookup path finds a method, return `false`.
- If class linearization is inconsistent, report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- If the first argument is neither a class nor an object, report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- If the second argument is not an atom, report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- `hasMethod` shall be a normal first-class builtin and support existing builtin partial-application behavior.
- User shadowing of `hasMethod` shall behave like other builtins.

## Semantics

User-defined method examples:

```text
hasMethod(Object, 'missing) -> false

class A < Object
A.f():=1
hasMethod(A, 'f) -> true
```

Native collection method examples:

```text
hasMethod(set(), 'member) -> true
hasMethod(Set, 'size)     -> true
hasMethod(bag(), 'reduce) -> true
hasMethod(set(), 'missing)-> false
```

Subclasses of Set and Bag shall see native collection method availability:

```text
class MySet < Set
hasMethod(MySet, 'union) -> true
```

## Relationship To Existing Helpers

- `effectiveMethods(target)` lists discoverable method names.
- `methodArity(target, method)` and `methodParams(target, method)` expose selected signature metadata.
- `methodSupplier(target, method)` remains user-defined-method-only and may return `nil` where `hasMethod` returns `true` for native collection methods.

## Non-Goals

- This slice shall not expose native collection method suppliers.
- This slice shall not change `methods`, `effectiveMethods`, `methodSupplier`, `methodArity`, or `methodParams` semantics.
- This slice shall not add method source/body introspection.
- This slice shall not change dot-call dispatch order.

## Regression Requirements

Boundary coverage shall include:

- missing methods returning `false`.
- direct user-defined methods.
- object arguments.
- inherited methods.
- overridden methods.
- multiple-inheritance lookup.
- native Set and Bag methods.
- Set and Bag class arguments.
- Set and Bag subclass arguments.
- contrast with `methodSupplier` native invisibility.
- compatibility with `methodArity` native visibility.
- higher-order use through `map` and `filter`.
- builtin partial application.
- callable parameter metadata.
- user shadowing.

Robustness coverage shall include:

- arity mismatch.
- invalid first-argument types.
- invalid method-name argument types.
- misuse of boolean results as integers or callables.
- partial builtin completion with a bad method-name argument.
- higher-order use with invalid method-name elements.
- inconsistent linearization for class and object arguments.
- user shadowing with a non-function.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
