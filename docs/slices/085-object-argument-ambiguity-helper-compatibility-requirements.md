# Slice 085: Object-Argument Ambiguity Helper Compatibility Requirements

## Goal

Slice 085 makes the ambiguity helpers accept either a class value or an object value:

```text
badAttrs(class_or_object)
suppliers(class_or_object, attr)
```

The manual describes these helpers in object-oriented terms. Slices 083 and 084 introduced class-oriented forms first because the current runtime represents inherited class-level attributes as methods. This slice adds the thin compatibility layer that maps an object argument to its runtime class.

## Requirements

- `badAttrs(object)` shall behave the same as `badAttrs(classof(object))`.
- `suppliers(object, attr)` shall behave the same as `suppliers(classof(object), attr)`.
- Existing class-argument behavior for `badAttrs(class)` and `suppliers(class, attr)` shall remain unchanged.
- Object arguments shall preserve the same effective supplier rules used for class arguments:
  - direct methods on the object's class mask inherited suppliers.
  - inherited ambiguity remains visible through the object's class.
  - shared common ancestors are deduplicated by supplier class identity.
- Object arguments shall remain usable on classes with inconsistent linearization because these helpers do not choose a method dispatch order.
- One-argument calls such as `suppliers(object)` shall follow existing builtin partial application behavior and return a callable.
- User bindings shall continue to be able to shadow `badAttrs` and `suppliers`.

## Evaluation Boundaries

- `badAttrs` shall keep arity one.
- `suppliers` shall keep arity two.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- First arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- `suppliers` second arguments that are not atoms shall continue to report `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- Misusing returned lists as integers, booleans, or callables shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- `badAttrs(new Object)`.
- object argument with no ambiguity.
- object argument with inherited ambiguity.
- object argument with direct class method masking inherited ambiguity.
- object arguments inside `map` and `filter`.
- first-class `badAttrs` application to an object.
- inconsistent linearization still allowing `badAttrs(object)`.
- `suppliers(new Object, attr)`.
- object argument with direct method supplier.
- object argument with two inherited suppliers.
- object argument with direct class method supplier masking inherited suppliers.
- missing attribute lookup through an object argument.
- object arguments inside `map` and `filter` for `suppliers`.
- first-class and partially applied `suppliers` with object arguments.
- inconsistent linearization still allowing `suppliers(object, attr)`.

Robustness coverage shall include:

- over-applied `badAttrs(object)` and `suppliers(object, attr)`.
- list result misuse for object-input `badAttrs`.
- non-atom `suppliers(object, attr)` second arguments.
- list result misuse for object-input `suppliers`.
- partial `suppliers(object)` completed with a non-atom.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
