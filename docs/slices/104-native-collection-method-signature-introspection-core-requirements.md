# Slice 104: Native Collection Method Signature Introspection Core Requirements

## Goal

Slice 104 extends method signature introspection to builtin-backed native collection dot methods:

```text
methodArity(class_or_object, 'methodName)
methodParams(class_or_object, 'methodName)
```

When normal user-defined method dispatch does not select a method, Set and Bag classes or objects may expose the signature of the native collection method that dot-call dispatch would use.

## Requirements

- `methodArity` shall continue to have arity two.
- `methodParams` shall continue to have arity two.
- The first argument shall continue to accept a class or object.
- Object arguments shall continue to use the object's runtime class.
- The second argument shall continue to be an atom naming the method.
- If normal user-defined method dispatch finds a method, return the user-defined method signature exactly as before.
- If no user-defined method is found and the class is Set-like or Bag-like, consult the native collection method table.
- Native collection method signatures shall omit the receiver argument.
- Native collection methods with no visible parameters shall return arity `0` from `methodArity` and `nil` from `methodParams`.
- If neither a user-defined method nor a native collection method is found, return `nil`.
- If the class cannot be consistently linearized, report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- Existing type errors and builtin partial-application behavior shall remain unchanged.

## Semantics

Native collection signature lookup shall mirror native dot-call availability:

```text
methodArity(set(), 'member)  -> 1
methodParams(set(), 'member) -> 'value:nil

methodArity(Set, 'size)      -> 0
methodParams(Set, 'size)     -> nil
```

The fallback shall apply to subclasses of Set and Bag:

```text
class MySet < Set
methodArity(MySet, 'member) -> 1
```

User-defined class methods shall keep priority over native collection methods:

```text
Set.member(x,y):=x
methodParams(set(), 'member) -> 'x:'y:nil
```

## Non-Goals

- This slice shall not add native collection methods to `methods`, `effectiveMethods`, `methodSupplier`, or `methodSuppliers`.
- This slice shall not add method body/source introspection.
- This slice shall not change dot-call dispatch order.

## Regression Requirements

Boundary coverage shall include:

- zero-visible-argument native methods.
- one-visible-argument native methods.
- multi-visible-argument native methods.
- Set and Bag receivers.
- class arguments and object arguments.
- subclass arguments.
- user-defined methods overriding native signatures.
- missing native method names returning `nil`.
- higher-order use.

Robustness coverage shall include:

- misuse of integer arity results as booleans or callables.
- misuse of parameter-list results as integers or callables.
- zero-parameter `nil` results used as non-empty lists.
- invalid method-name argument types.
- user shadowing with a non-function.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
