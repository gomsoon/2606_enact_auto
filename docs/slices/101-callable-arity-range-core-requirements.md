# Slice 101: Callable Arity Range Core Requirements

## Scope

Slice 101 adds callable-level arity range introspection:

```text
callableArityRange(callable)
```

This complements Slice 099 `callableArity(callable)`, which reports only the maximum remaining arity.

## Functional Requirements

- Add a builtin named `callableArityRange`.
- `callableArityRange` shall have arity one.
- `callableArityRange` shall return a two-element integer list:

```text
min:max:nil
```

- The first element shall be the minimum number of additional arguments the callable can accept for a successful call.
- The second element shall be the maximum number of additional arguments the callable can accept before over-application.
- For user-defined function values and lambda values, return an exact range where min equals max.
- For partially applied user-defined function values, return the exact remaining arity.
- For builtins, use the builtin's existing minimum and maximum arity metadata.
- For builtin partial values, subtract the already captured argument count from both builtin arity bounds, clamping the minimum at zero.
- For bound object method values, return the exact selected method arity minus already captured dot-call arguments.
- For bound native collection method values, return the exact native method-call arity minus already captured method arguments. The receiver itself is not counted as a remaining callable argument.
- Non-callable values shall fail with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.
- `callableArityRange` shall be a normal first-class builtin and support existing user shadowing behavior.

## Examples

```text
callableArityRange(x::x)             -> 1:1:nil
callableArityRange((x,y)::x+y)       -> 2:2:nil
callableArityRange(()::1)            -> 0:0:nil
```

```text
callableArityRange(append)           -> 2:2:nil
callableArityRange(append(nil))      -> 1:1:nil
```

```text
callableArityRange(set)              -> 0:1:nil
callableArityRange(bag)              -> 0:1:nil
```

```text
class A < Object
A.f(x,y):=x+y
callableArityRange((new A).f)        -> 2:2:nil
callableArityRange((new A).f(1))     -> 1:1:nil
```

## Out Of Scope

- a separate `callableMinArity` convenience helper.
- callable source/body introspection.
- builtin or native collection parameter-name metadata.
- changing application or partial-application semantics.
