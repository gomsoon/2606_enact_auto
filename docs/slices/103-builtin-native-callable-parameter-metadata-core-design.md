# Slice 103: Builtin / Native Callable Parameter Metadata Core Design

Related requirements: [docs/slices/103-builtin-native-callable-parameter-metadata-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/103-builtin-native-callable-parameter-metadata-core-requirements.md)

## Builtin Metadata

`EnactBuiltin` now stores an optional parameter-name array:

```c
const char *const *param_names;
```

The builtin table binds each non-zero-arity builtin to a small static name array. Zero-argument builtins can keep `NULL`, which `callableParams` reports as `nil`.

## Shared List Construction

Slice 103 adds a shared atom-list construction helper for parameter metadata. It is used by:

- user-defined function parameter lists.
- builtin parameter metadata.
- builtin partial remaining parameter lists.
- bound native collection method remaining parameter lists.

This keeps the output shape consistent: every parameter name is returned as an atom value, preserving call order.

## Builtin Partials

Builtin partial values store the original builtin and a captured argument count. `callableParams` reads the original metadata and starts at the captured count:

```text
callableParams(append)      -> 'left:'right:nil
callableParams(append(nil)) -> 'right:nil
```

Range-arity builtins such as `set` and `bag` expose their optional argument name on the original callable:

```text
callableParams(set) -> 'items:nil
```

They do not currently produce builtin partial values because their minimum arity is zero.

## Native Collection Dot Methods

Native collection method values are wrappers around an existing builtin plus a receiver index. `callableParams` reuses the builtin metadata but skips the bound receiver argument.

Examples:

```text
member(value, collection)
callableParams(set().member) -> 'value:nil

union(left, right)
callableParams(set().union)  -> 'right:nil

reduce(function, initial, collection)
callableParams(set().reduce) -> 'function:'initial:nil
```

If a native collection method has already captured method arguments, those names are skipped too:

```text
m := set((1,2)).reduce((acc,x)::acc+x)
callableParams(m) -> 'initial:nil
```

## Deferred Work

This slice does not expose method-level native collection introspection through `methodParams`, `methodArity`, or `effectiveMethods`. It also does not add callable source/body metadata or richer callable metadata records.

