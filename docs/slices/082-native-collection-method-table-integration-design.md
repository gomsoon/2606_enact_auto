# Slice 082: Native Collection Method Table Integration Design

Related requirements: [docs/slices/082-native-collection-method-table-integration-requirements.md](/home/tprover/2606_enact_auto/docs/slices/082-native-collection-method-table-integration-requirements.md)

## Native Table

Earlier slices kept the native collection method name mapping inside `eval.c`. That was useful while dot-call behavior was still changing, but by Slice 081 both bare reads and direct dot-calls already shared the bound collection method callable path.

Slice 082 moves the remaining method metadata into `builtin.c`:

- method name.
- supported collection receiver kind.
- receiver argument index for the underlying builtin call.

The public lookup helper is:

```c
int enact_builtin_collection_method(
    EnactCollectionKind kind,
    const char *name,
    const EnactBuiltin **builtin_out,
    size_t *receiver_index_out);
```

This keeps the evaluator focused on lookup order and callable dispatch, while the builtin layer owns which builtin-backed operations are native collection methods.

## Lookup Order

The evaluator lookup order is unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. native collection method table lookup.

This preserves the established shadowing behavior. Attributes and user-defined methods still win over native collection methods. Top-level bindings still do not affect native dot-method lookup because the table resolves directly to the builtin table.

## Receiver Argument Index

The native table records the same receiver insertion indexes used by the former evaluator bridge:

- receiver index `0` for methods like `size`, `union`, `difference`, `intersection`, `subset`, `equal`, and `UNION`.
- receiver index `1` for methods like `member`, `insert`, `remove`, `add`, `collect`, `filter`, `select`, `all`, `exists`, `locate`, and `forEachDo`.
- receiver index `2` for `reduce`.

The bound collection method value still performs the actual argument assembly and delegates to `enact_builtin_apply_in_env`, so partial application, arity diagnostics, collection preservation, and builtin semantic errors remain centralized.

## Introspection

Slice 082 deliberately does not change `methods(Class)`. That builtin continues to report user-defined direct class methods rather than native builtin-backed collection methods. Native collection method introspection can be added later with a dedicated contract if it becomes useful.

## Deferred Work

This slice does not add `super`, method signature introspection, method source introspection, or public native method introspection.
