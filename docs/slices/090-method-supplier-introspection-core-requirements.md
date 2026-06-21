# Slice 090: Method Supplier Introspection Core Requirements

## Goal

Slice 090 exposes the dispatch-selected method supplier recorded by Slice 089:

```text
methodSupplier(class_or_object, 'methodName)
```

The helper answers which class would supply the user-defined method selected by normal method dispatch.

## Requirements

- `methodSupplier` shall be a normal first-class builtin with arity two.
- The first argument shall accept either a class value or an object value.
- Object arguments shall behave like `methodSupplier(classof(object), attr)`.
- The second argument shall be a quoted atom naming the method.
- If dispatch would find a user-defined method, the helper shall return the class that directly defines the selected method.
- If dispatch would not find a user-defined method, the helper shall return `nil`.
- Direct methods shall return the receiver class.
- Inherited methods shall return the superclass that directly defines the selected method.
- Subclass overrides shall return the subclass.
- Multiple-inheritance lookup shall follow the same checked `classes(Class)` linearization used by method dispatch.
- If class linearization is inconsistent, the helper shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- Native collection method table entries shall not be exposed as method suppliers.
- User-defined methods on native collection classes, such as `Set.size`, shall be visible.
- Existing `suppliers(class_or_object, attr)` behavior shall remain unchanged. It remains an ambiguity inspection helper and may return multiple classes.
- User bindings shall continue to be able to shadow `methodSupplier`.

## Evaluation Boundaries

- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- First arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- Second arguments that are not atoms shall report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- Misusing the returned class or `nil` as an integer, boolean, callable, or list shall follow existing runtime type behavior.

## Regression Requirements

Boundary coverage shall include:

- missing methods returning `nil`.
- direct class suppliers.
- object argument compatibility.
- inherited supplier selection.
- subclass override selection.
- multiple-inheritance linearization selection.
- shared ancestor supplier selection.
- difference from `suppliers` when ambiguity inspection returns multiple classes.
- higher-order use through `map` and `filter`.
- first-class partial builtin application.
- native collection class behavior.
- user binding shadowing.

Robustness coverage shall include:

- arity errors.
- non-class, non-object first arguments.
- non-atom second arguments.
- result misuse.
- partial application with a bad second argument.
- inconsistent linearization for class and object arguments.
- user binding shadowing with a non-callable value.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
