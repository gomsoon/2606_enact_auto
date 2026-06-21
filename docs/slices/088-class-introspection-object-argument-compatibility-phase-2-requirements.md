# Slice 088: Class Introspection Object-Argument Compatibility Phase 2 Requirements

## Goal

Slice 088 completes the class-introspection object-argument compatibility pair left after Slice 087:

```text
classes(class_or_object)
methods(class_or_object)
```

This makes `classes` and `methods` accept object values by mapping each object to its runtime class before performing the existing class-based introspection.

## Requirements

- `classes(object)` shall behave the same as `classes(classof(object))`.
- `methods(object)` shall behave the same as `methods(classof(object))`.
- Existing `classes(class)` and `methods(class)` behavior shall remain unchanged.
- `classes(new Object)` shall return `<class Object>:nil`.
- `methods(new Object)` shall return `nil` until methods are directly defined on `Object`.
- `classes(object)` shall return the inclusive class linearization for the object's class.
- `classes(object)` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION` when the object's class has inconsistent linearization.
- `methods(object)` shall continue to return only methods defined directly on the object's class.
- Inherited user-defined methods shall remain callable through dispatch but shall not appear in `methods(object)` for subclasses unless directly defined there.
- Native collection dot-method table entries shall not appear in `methods(set())` or `methods(bag())`.
- User-defined class methods on native collection classes shall still be visible through `methods(object)` when they are direct methods of the object's class.
- `classes` and `methods` shall remain normal first-class builtins and shall compose with `map`, `filter`, `all`, conditionals, and helper functions over object values.
- User bindings shall continue to be able to shadow `classes` and `methods`.

## Evaluation Boundaries

- `classes` and `methods` shall keep arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- First arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root object values for both helpers.
- single-inheritance object values for both helpers.
- multi-level and multiple-inheritance object values for `classes`.
- direct-method object introspection for `methods`.
- inherited-method exclusion for `methods(object)`.
- equivalence with `classof(object)`.
- higher-order composition over object values.
- first-class builtin use with object values.
- native collection object values.
- `methods(object)` staying available for inconsistent classes because it reads direct methods only.

Robustness coverage shall include:

- over-applied object calls.
- list result misuse for object-input calls.
- non-class, non-object values during higher-order traversal.
- inconsistent-linearization propagation through `classes(object)`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
