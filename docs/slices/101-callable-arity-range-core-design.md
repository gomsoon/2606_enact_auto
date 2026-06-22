# Slice 101: Callable Arity Range Core Design

Related requirements: [docs/slices/101-callable-arity-range-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/101-callable-arity-range-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
callableArityRange(callable)
```

It returns:

```text
min:max:nil
```

`callableArity(callable)` remains the maximum remaining arity helper. `callableArityRange` exposes both the minimum and maximum remaining arity while preserving the same callable-type surface.

## Shared Range Helper

Slice 101 extends the internal callable arity helper into a range helper:

```c
enact_builtin_callable_remaining_arity_range(value, &min, &max, diag)
```

`callableArity` now delegates to this helper and keeps returning `max`. `callableArityRange` delegates to the same helper and packages `min` and `max` into a two-integer list.

## Range Rules

For functions and lambdas:

```text
min == max == enact_function_arity(function)
```

Function partial application already creates a new function value with only the remaining parameters, so the same exact rule applies.

For builtins:

```text
min == enact_builtin_min_arity(builtin)
max == enact_builtin_arity(builtin)
```

For builtin partial values:

```text
min == max(0, enact_builtin_min_arity(builtin) - captured_count)
max == enact_builtin_arity(builtin) - captured_count
```

For bound object methods:

```text
min == max == enact_function_arity(method) - captured_count
```

For bound native collection methods, the receiver is already bound by dot lookup:

```text
min == max == enact_builtin_arity(native_builtin) - 1 - captured_count
```

## Optional-Arity Builtins

`set` and `bag` are the first visible callers that benefit from the range:

```text
callableArity(set)       -> 1
callableArityRange(set)  -> 0:1:nil
```

This keeps the existing maximum-arity meaning intact while exposing the lower bound when callers need it.

## Deferred Work

This slice does not add `callableMinArity`, callable source/body metadata, builtin parameter names, or native collection method parameter names.
