# Slice 078: Bound Collection Method Values Core Requirements

## Goal

Slice 078 lets supported native collection dot methods be read as callable values.

This slice enables:

```text
collection.size
collection.member
collection.collect
collection.UNION
```

These values capture the receiver object and can be called later.

## Requirements

- Reading a supported native collection method from a collection object shall return a callable value.
- Calling that value shall behave like the corresponding collection dot-call with the original receiver captured.
- Bound collection method values shall print as `<function>`, matching existing user functions, builtins, and builtin partials.
- Bound collection method values shall be accepted anywhere an existing callable is accepted, including `map`, `filter`, `all`, `exists`, `collect`, `forEachDo`, and `reduce`.
- Bound collection method values shall support partial application when at least one new argument is supplied and fewer than the method arity has been reached.
- Zero-argument calls to non-zero-arity bound methods shall report `ENACT_ERR_ARITY_MISMATCH`.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- Argument evaluation errors for valid-arity calls shall propagate normally.
- Object attributes shall continue to shadow native collection method values.
- User-defined class methods shall continue to shadow native collection method values.
- Because general object method values remain deferred, a bare read of a user-defined class method shall still report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Top-level bindings with the same name as a collection method shall not affect bound collection method lookup.
- Unsupported collection method names shall keep reporting `ENACT_ERR_ATTRIBUTE_UNBOUND`.

## Regression Requirements

Boundary coverage shall include:

- bare native method reads.
- zero-argument bound methods such as `size`.
- receiver-index-zero methods such as `union`, `difference`, `intersection`, `subset`, `equal`, and `UNION`.
- receiver-index-one methods such as `member`, `insert`, `remove`, `add`, `collect`, `filter`, `select`, `all`, `exists`, `locate`, and `forEachDo`.
- receiver-index-two methods such as `reduce`.
- higher-order use with list traversal builtins.
- bound method partial application.
- object attribute shadowing.
- top-level builtin shadowing not affecting bound collection methods.

Robustness coverage shall include:

- wrong arity for zero-, one-, and two-argument bound collection methods.
- impossible extra arguments not being evaluated after arity rejection.
- valid-arity argument evaluation errors.
- callable type validation inside higher-order methods.
- predicate result validation.
- reducer arity validation.
- Set-only method rejection for Bag receivers.
- mixed collection-kind rejection.
- invalid aggregate payloads.
- unsupported method names remaining unbound.
- user-defined class method shadowing over native bound methods.
- non-callable object attributes shadowing native bound methods.
- misuse of bound method values as integers, booleans, and lists.

## Deferred

- General user-defined object method values such as `object.method` remain deferred.
- Bound values for unsupported collection helper surfaces such as `collection.unitset` remain deferred.
- Native method table integration remains deferred; this slice continues the focused evaluator bridge.
- Dedicated bound-method printing remains deferred; bound collection methods print as `<function>`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
