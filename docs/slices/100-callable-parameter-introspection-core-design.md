# Slice 100: Callable Parameter Introspection Core Design

Related requirements: [docs/slices/100-callable-parameter-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/100-callable-parameter-introspection-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
callableParams(callable)
```

It complements:

```text
methodParams(class_or_object, 'methodName)
callableArity(callable)
```

`methodParams` starts from a class or object plus a method name and reports the selected user-defined method's parameters. `callableParams` starts from a first-class callable value and reports the parameter names still visible on that value.

## Supported Callable Kinds

The helper accepts the same callable value kinds recognized by the higher-order builtins and call evaluator:

- user-defined functions and lambdas.
- builtins.
- builtin partial values.
- bound object method values.
- bound native collection method values.

All other value kinds report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## Parameter List Construction

The implementation uses a shared function-parameter-to-list helper that copies parameter names into quoted atom values and preserves declaration order.

For plain user-defined functions and lambdas, it emits:

```text
enact_function_param_name(function, 0)
...
enact_function_param_name(function, arity - 1)
```

Function partial application already creates a new `EnactFunction` whose parameter list contains only the remaining names, so no extra offset is needed for those values.

For bound object methods, the bound value stores the original selected method and the count of already captured method arguments. `callableParams` starts at that captured count:

```text
enact_function_param_name(method, captured_count)
...
enact_function_param_name(method, arity - 1)
```

## Builtins And Native Collection Methods

Builtins, builtin partials, and bound native collection methods do not currently carry public parameter-name metadata. This slice returns `nil` for those callable kinds.

This keeps Slice 100 small and avoids inventing names for native arguments before the project has a broader native-method metadata contract.

## Deferred Work

This slice does not add builtin parameter names, native collection method parameter names, callable source/body metadata, or arity-range metadata.
