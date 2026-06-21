# Slice 087: Class Introspection Object-Argument Compatibility Phase 1 Requirements

## Goal

Slice 087 makes the superclass introspection helpers accept either a class value or an object value:

```text
supers(class_or_object)
superiors(class_or_object)
```

This extends the object-argument compatibility pattern from `badAttrs`, `suppliers`, and `OK` to the first pair of class-chain helpers.

## Requirements

- `supers(object)` shall behave the same as `supers(classof(object))`.
- `superiors(object)` shall behave the same as `superiors(classof(object))`.
- Existing `supers(class)` and `superiors(class)` behavior shall remain unchanged.
- `supers(new Object)` and `superiors(new Object)` shall both return `nil`.
- `supers(object)` shall continue to report only direct superclasses.
- `superiors(object)` shall continue to report the transitive superclass linearization, excluding the object's own class.
- Object-valued calls shall compose with equality, `member`, `size`, `map`, `filter`, first-class builtin use, and collection objects such as `set()`.
- `superiors(object)` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION` when the object's class has inconsistent linearization.
- `supers(object)` shall remain direct-only and shall not require linearization consistency.
- User bindings shall continue to be able to shadow `supers` and `superiors`.

## Evaluation Boundaries

- `supers` and `superiors` shall keep arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- First arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root object values for both helpers.
- single-inheritance object values for both helpers.
- multi-level inheritance object values.
- multiple-inheritance object values.
- equivalence with `classof(object)`.
- higher-order composition over object values.
- first-class builtin use with object values.
- native collection object values.
- direct-only `supers(object)` behavior on an inconsistent class.

Robustness coverage shall include:

- over-applied object calls.
- list result misuse for object-input calls.
- non-class, non-object values during higher-order traversal.
- inconsistent-linearization propagation through `superiors(object)`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
