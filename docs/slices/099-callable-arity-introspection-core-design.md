# Slice 099: Callable Arity Introspection Core Design

Related requirements: [docs/slices/099-callable-arity-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/099-callable-arity-introspection-core-requirements.md)

## Builtin Contract

The new builtin is:

```text
callableArity(callable)
```

It complements method-specific metadata helpers:

```text
methodArity(class_or_object, 'methodName)
methodParams(class_or_object, 'methodName)
methodSupplier(class_or_object, 'methodName)
```

`callableArity` answers a different question: given the callable value already in hand, how many more arguments can it accept at most?

## Supported Callable Kinds

The implementation accepts the same callable value kinds used by `map`, `filter`, `reduce`, and normal call evaluation:

- user-defined functions and lambdas.
- builtins.
- builtin partial values.
- bound object method values.
- bound native collection method values.

All other value kinds report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## Remaining-Arity Rules

For plain functions and lambdas, the answer is:

```text
enact_function_arity(function)
```

For builtins, the answer is:

```text
enact_builtin_arity(builtin)
```

For partial builtins, the answer subtracts captured arguments:

```text
enact_builtin_arity(builtin) - captured_count
```

For bound object methods, the answer subtracts captured dot-call arguments from the selected method function arity:

```text
enact_function_arity(method) - captured_count
```

For bound native collection methods, the receiver has already been bound by dot lookup and is not counted as a remaining argument:

```text
enact_builtin_arity(native_builtin) - 1 - captured_count
```

## Optional-Arity Builtins

`set` and `bag` are installed as range builtins with minimum arity zero and maximum arity one. `callableArity(set)` and `callableArity(bag)` return `1`, matching the existing public `enact_builtin_arity` meaning.

This slice deliberately does not add a second helper for minimum arity or arity ranges.

## Deferred Work

This slice does not add callable parameter names, callable source/body metadata, native method-table provenance, or any changes to call evaluation.
