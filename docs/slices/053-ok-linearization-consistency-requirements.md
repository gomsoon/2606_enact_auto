# Slice 053: OK(Class) Linearization Consistency Predicate Requirements

## Goal

Slice 053 adds the PRD-named `OK` introspection helper as a boolean predicate over class linearization consistency.

```text
OK(Class)
```

`OK(Class)` answers whether a class can be linearized without violating the declared local precedence order of its multiple-superclass graph.

## Requirements

- `OK(class)` shall return a boolean value.
- `OK(Object)` shall return `true`.
- Single-inheritance classes shall return `true`.
- Ordinary multiple-inheritance diamonds shall return `true`.
- Repeated direct superclasses shall not make a class inconsistent.
- A class whose superclass graph contains contradictory local precedence requirements shall return `false`.
- If a direct or transitive superclass is inconsistent, subclasses depending on it shall also return `false`.
- `OK(classof(object))` shall work by composing existing `classof` introspection with `OK`.
- `OK` shall be a normal first-class builtin and shall compose with `map`, `filter`, `all`, and conditionals.
- User bindings shall be able to shadow `OK`, matching existing builtin behavior.

## Evaluation Boundaries

- `OK` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Object values shall not be accepted directly; users should call `OK(classof(obj))` when starting from an object.
- Misusing the boolean result as an integer, list, or callable shall follow existing boolean-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class
- single-inheritance class
- simple multiple-inheritance class
- ordinary diamond inheritance
- nontrivial shared ancestor linearization
- repeated direct superclasses
- alias-repeated direct superclasses
- inconsistent local precedence order
- inconsistent class through `classof`
- mapping `OK` over a class list
- filtering classes with `OK`
- `all(OK, classes)`
- conditional use
- first-class builtin use
- builtin shadowing

Robustness coverage shall include:

- zero-argument call
- over-application without evaluating an impossible extra argument
- non-class primitive values
- list, object, function, and builtin values
- object misuse when `classof` is not used
- boolean result misuse as an integer
- boolean result misuse as a list
- boolean result misuse as a callable
- shadowed non-function `OK`

## Deferred

- `classes(Class)` and method dispatch keep their existing fallback behavior for inconsistent graphs in this slice.
- Dedicated inconsistency diagnostics remain deferred.
- `suppliers` and `badAttrs` remain deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
