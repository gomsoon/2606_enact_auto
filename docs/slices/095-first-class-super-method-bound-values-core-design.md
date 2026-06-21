# Slice 095: First-Class super.method Bound Values Core Design

Related requirements: [docs/slices/095-first-class-super-method-bound-values-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/095-first-class-super-method-bound-values-core-requirements.md)

## Attribute Read Strategy

The parser already reads:

```text
super.f
```

as:

```text
AST_ATTRIBUTE(AST_IDENTIFIER("super"), "f")
```

Slice 095 keeps that syntax shape and routes the attribute-read form through the evaluator. No lexer keyword or new AST node is added.

## Shared Super Binding Helper

Slice 094 implemented `super.f(...)` by selecting the next method after the current supplier, wrapping it as a bound object method, and applying it.

Slice 095 factors that selection-and-wrap step into a shared evaluator helper:

```text
super method lookup -> bound object method value
```

Both `super.f` and `super.f(...)` now use that helper. The call form simply applies the returned bound value through the existing callable path.

## Captured Runtime State

The returned value is an ordinary `ENACT_VALUE_BOUND_OBJECT_METHOD`. It captures:

- the current receiver object.
- the selected super method function.
- the selected supplier class.

That supplier capture matters when the value escapes the method body:

```text
C.get():=super.f
m:=(new C).get()
m()
```

The final `m()` call still runs with the supplier selected by the original `super.f` lookup, so any nested `super` inside that method continues after the captured supplier.

## Higher-Order Use

Because the result is a normal bound object method value, existing higher-order paths such as `map`, `filter`, and user helper functions do not need new callable rules.

For example:

```text
B.map(xs):=map(super.inc,xs)
```

works through the same bound method callable path used by ordinary first-class object methods.

## Diagnostics

This slice keeps the Slice 094 diagnostic policy:

- no active method/supplier context: `ENACT_ERR_NAME_UNBOUND`.
- no later method found: `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- inconsistent receiver class linearization: `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- calling with the wrong arity: `ENACT_ERR_ARITY_MISMATCH`.

A dedicated invalid-super-context diagnostic remains deferred.

## Deferred Work

This slice does not add bare `super` values, `super` attribute assignment, native collection `super` lookup, a dedicated super-context diagnostic, or method source/signature metadata.
