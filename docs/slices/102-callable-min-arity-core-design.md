# Slice 102: Callable Min Arity Core Design

Related requirements: [docs/slices/102-callable-min-arity-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/102-callable-min-arity-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
callableMinArity(callable)
```

It returns the minimum number of additional arguments required before a callable can execute.

## Shared Range Helper

Slice 101 introduced:

```c
enact_builtin_callable_remaining_arity_range(value, &min, &max, diag)
```

Slice 102 reuses that helper directly. `callableMinArity` reads `min` and returns it as an integer. This keeps the min, max, and range helpers on a single implementation path:

```text
callableMinArity(value)  -> min
callableArity(value)     -> max
callableArityRange(value)-> min:max:nil
```

## Range-Arity Builtins

`set` and `bag` are the visible range-arity builtins:

```text
callableArity(set)       -> 1
callableMinArity(set)    -> 0
callableArityRange(set)  -> 0:1:nil
```

For builtin partials, the existing range helper subtracts captured arguments from both bounds and clamps the lower bound at zero.

## Exact-Arity Callables

For functions, lambdas, bound object methods, and bound native collection methods, the minimum and maximum are identical. `callableMinArity` therefore matches `callableArity` for those values.

## Deferred Work

This slice does not add method-level arity ranges, builtin parameter names, native collection method parameter names, callable source/body metadata, or richer callable metadata records.

