# Slice 100: Callable Parameter Introspection Core Requirements

## Scope

Slice 100 adds a callable-level parameter-name introspection helper:

```text
callableParams(callable)
```

This generalizes the Slice 098 `methodParams(class_or_object, 'methodName)` idea from selected user-defined class methods to first-class callable values.

## Functional Requirements

- Add a builtin named `callableParams`.
- `callableParams` shall have arity one.
- `callableParams` shall return a list of atom values.
- For user-defined function values and lambda values, return the callable's remaining parameter names in declaration order.
- For partially applied user-defined function values, return only the remaining parameter names.
- For bound object method values, return the selected method's parameter names after any already captured dot-call arguments.
- For zero-argument callables, return `nil`.
- For builtins, builtin partial values, and bound native collection method values, return `nil` because parameter-name metadata is not available.
- Non-callable values shall fail with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.
- `callableParams` shall be a normal first-class builtin and support existing user shadowing behavior.

## Examples

```text
callableParams(x::x)            -> 'x:nil
callableParams((x,y)::x+y)      -> 'x:'y:nil
callableParams(()::1)           -> nil
```

```text
f(x,y,z):=x+y+z
callableParams(f)               -> 'x:'y:'z:nil
callableParams(f(1))            -> 'y:'z:nil
```

```text
class A < Object
A.f(x,y):=x+y
callableParams((new A).f)       -> 'x:'y:nil
callableParams((new A).f(1))    -> 'y:nil
```

```text
callableParams(hd)              -> nil
callableParams(append(nil))     -> nil
callableParams(set().member)    -> nil
```

## Out Of Scope

- builtin parameter-name metadata.
- native collection method parameter-name metadata.
- callable source/body introspection.
- callable minimum-arity or arity-range introspection.
- changing application or partial-application semantics.
