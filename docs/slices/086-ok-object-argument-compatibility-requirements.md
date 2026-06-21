# Slice 086: OK Object-Argument Compatibility Requirements

## Goal

Slice 086 makes `OK` accept either a class value or an object value:

```text
OK(class_or_object)
```

`OK(Class)` remains the linearization-consistency predicate introduced by Slice 053. This slice adds the same object-to-class compatibility layer that Slice 085 added for `badAttrs` and `suppliers`.

## Requirements

- `OK(object)` shall behave the same as `OK(classof(object))`.
- Existing `OK(class)` behavior shall remain unchanged.
- `OK(new Object)` shall return `true`.
- `OK(object)` shall return `false` when the object's class has inconsistent linearization.
- `OK` shall remain a normal first-class builtin and shall compose with `map`, `filter`, `all`, conditionals, and user helper functions over object values.
- User bindings shall continue to be able to shadow `OK`.
- `OK` shall remain a linearization-consistency predicate only; this slice shall not integrate `badAttrs` or supplier ambiguity into the result.

## Evaluation Boundaries

- `OK` shall keep arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- First arguments that are neither class nor object values shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.
- Misusing the boolean result as an integer, list, or callable shall follow existing boolean-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- `OK(new Object)`.
- object argument for single inheritance.
- object argument for multiple inheritance.
- object argument for ordinary diamond inheritance.
- object argument for inconsistent local precedence order.
- equivalence with `OK(classof(object))`.
- `map`, `filter`, and `all` over object values.
- conditional use with an object argument.
- first-class builtin use with an object argument.
- mixed class and object lists.

Robustness coverage shall include:

- over-applied `OK(object)`.
- boolean result misuse for object-input `OK`.
- non-class, non-object values in higher-order calls.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
