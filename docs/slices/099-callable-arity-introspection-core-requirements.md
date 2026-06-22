# Slice 099: Callable Arity Introspection Core Requirements

## Scope

Slice 099 adds a small callable-level arity introspection helper:

```text
callableArity(callable)
```

This generalizes the Slice 097 `methodArity(class_or_object, 'methodName)` idea from selected class methods to first-class callable values.

## Functional Requirements

- Add a builtin named `callableArity`.
- `callableArity` shall have arity one.
- `callableArity` shall return an integer.
- For user-defined function values and lambda values, return the number of parameters still accepted by that function value.
- For builtin values, return the builtin's maximum accepted arity.
- For builtin partial values, return the builtin's maximum arity minus the already captured argument count.
- For bound object method values, return the selected method arity minus the already captured dot-call argument count.
- For bound native collection method values, return the native method-call arity minus the already captured method argument count. The receiver itself is not counted as a remaining callable argument.
- Non-callable values shall fail with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.
- `callableArity` shall be a normal first-class builtin and support existing user shadowing behavior.

## Partial Application Policy

The returned arity is the maximum number of additional arguments the callable can still accept before over-application.

Examples:

```text
callableArity(append)        -> 2
callableArity(append(nil))   -> 1
callableArity(set)           -> 1
callableArity(set().member)  -> 1
callableArity(set().size)    -> 0
```

`set` and `bag` keep their existing optional-argument constructor behavior. This slice reports their maximum accepted arity, not a minimum arity range.

## Out Of Scope

- callable parameter-name introspection.
- callable minimum-arity introspection.
- method source/body introspection.
- native collection method provenance metadata.
- changing application or partial-application semantics.
