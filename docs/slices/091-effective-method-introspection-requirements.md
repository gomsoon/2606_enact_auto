# Slice 091: Effective Method Introspection Requirements

## Goal

Slice 091 adds a conservative dispatch-facing method introspection helper:

```text
effectiveMethods(class_or_object)
```

The helper returns the user-defined method names visible through normal method dispatch for a class or object.

## Requirements

- `effectiveMethods` shall be a normal first-class builtin with arity one.
- The argument shall accept either a class value or an object value.
- Object arguments shall behave like `effectiveMethods(classof(object))`.
- The result shall be a list of quoted atoms naming effective user-defined methods.
- The result shall follow the checked `classes(Class)` linearization used by method dispatch.
- Direct methods on earlier classes in the linearization shall mask same-named methods on later classes.
- Method names shall appear at most once in the result.
- Direct methods on the receiver class shall appear before inherited methods.
- Within one class, method names shall keep the existing `methods(Class)` first-definition order.
- Multiple-inheritance ordering shall follow dispatch linearization order.
- If class linearization is inconsistent, the helper shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- `methods(class_or_object)` shall remain direct-only and unchanged.
- `methodSupplier(class_or_object, attr)` shall remain the single-name supplier query and unchanged.
- Native collection method table entries shall not appear in `effectiveMethods(set())` or `effectiveMethods(bag())`.
- User-defined methods on native collection classes, such as `Set.size`, shall appear when dispatch would see them.
- User bindings shall continue to be able to shadow `effectiveMethods`.

## Evaluation Boundaries

- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value type behavior.

## Regression Requirements

Boundary coverage shall include:

- root class with no methods.
- direct class methods.
- object argument compatibility.
- inherited method visibility.
- `methods` direct-only contrast.
- subclass override masking.
- multiple-inheritance method ordering.
- duplicate method names through multiple inheritance.
- shared ancestor method visibility.
- direct receiver methods ordered before inherited methods.
- higher-order composition through `map` and `filter`.
- first-class builtin use.
- partial builtin-style use through ordinary assignment.
- native collection class behavior.
- user binding shadowing.

Robustness coverage shall include:

- arity errors.
- non-class, non-object arguments.
- result misuse.
- partial use with a bad argument.
- inconsistent linearization for class and object arguments.
- user binding shadowing with a non-callable value.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
