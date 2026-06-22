# Slice 102: Callable Min Arity Core Requirements

## Goal

Slice 102 adds callable-level minimum arity introspection:

```text
callableMinArity(callable)
```

This complements Slice 099 `callableArity(callable)`, which reports the maximum remaining arity, and Slice 101 `callableArityRange(callable)`, which reports both bounds.

## Functional Requirements

- Add a builtin named `callableMinArity`.
- `callableMinArity` shall have arity one.
- `callableMinArity` shall return an integer.
- For exact-arity functions, lambdas, partial functions, bound object methods, and bound native collection methods, `callableMinArity` shall return the same value as `callableArity`.
- For range-arity builtins, `callableMinArity` shall return the minimum remaining arity.
- For builtin partials, `callableMinArity` shall subtract captured arguments from the builtin minimum arity and clamp the result at zero.
- Non-callable arguments shall report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.
- `callableMinArity` shall be a normal first-class builtin and support existing user shadowing behavior.

## Examples

```text
callableMinArity(x::x)          -> 1
callableMinArity((x,y)::x+y)    -> 2
callableMinArity(()::1)         -> 0

callableMinArity(append)        -> 2
callableMinArity(append(nil))   -> 1

callableMinArity(set)           -> 0
callableMinArity(bag)           -> 0

class A < Object
A.f(x,y):=x+y
callableMinArity((new A).f)     -> 2
callableMinArity((new A).f(1))  -> 1
```

## Consistency

For every callable value:

```text
callableMinArity(callable) == hd(callableArityRange(callable))
callableArity(callable) == hd(tl(callableArityRange(callable)))
```

