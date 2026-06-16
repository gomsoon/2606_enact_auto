# Slice 021: Atom Builtin Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/021-atom-builtin-requirements.md](/home/tprover/2606_enact_auto/docs/slices/021-atom-builtin-requirements.md)

Prerequisite design: [docs/slices/020-higher-order-list-builtins-reduce-design.md](/home/tprover/2606_enact_auto/docs/slices/020-higher-order-list-builtins-reduce-design.md)

## 1. Design Summary

Add `atom` to the builtin table:

```c
{"atom", 1, enact_builtin_atom},
```

No lexer, parser, AST, or evaluator syntax changes are needed. `atom` is a normal first-class builtin value installed in the default environment.

## 2. Runtime Signature

Add a local builtin callback in `builtin.c`:

```c
static int enact_builtin_atom(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

The generic `enact_builtin_apply` layer already enforces arity 1 before this callback runs.

## 3. Runtime Rule

The implementation returns true unless the argument is a non-empty list:

```c
*out = enact_value_make_bool(
    arguments[0].kind != ENACT_VALUE_LIST || arguments[0].as.as_list == NULL);
```

Current runtime behavior:

| Value kind | atom result |
| --- | --- |
| integer | `true` |
| boolean | `true` |
| string | `true` |
| function | `true` |
| builtin | `true` |
| builtin partial | `true` |
| nil list | `true` |
| non-empty list | `false` |

This keeps lambda expressions atomic because lambda evaluation produces an `ENACT_VALUE_FUNCTION`.

## 4. Nil Decision

`nil` is represented internally as `ENACT_VALUE_LIST` with a null list payload.

For `atom`, the compound case is a non-empty list cell, not the list value kind by itself. Therefore:

```text
atom(nil)   -> true
atom(1:nil) -> false
```

This is useful for future recursive list examples where `atom` can serve as a simple base-condition check.

## 5. Ownership

`atom` does not allocate heap-backed runtime payloads. It returns an immediate boolean value.

It does not retain or free the input argument.

## 6. Arity And Evaluation Timing

No special arity code is needed.

The existing call path means:

- bare `atom` evaluates to a first-class builtin value
- `atom(extra, impossible)` fails with `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments
- `atom(1/0)` reports the argument evaluation failure before the builtin callback runs

## 7. Test Strategy

Regression tests cover:

- scalar values
- nil and non-empty lists
- tuple-like lists
- lambda and assigned function values
- builtin and builtin partial values
- higher-order use through `map`, `filter`, `all`, and `reduce`
- arity, argument-evaluation, result-consumption, and call-result failures

Unit tests cover:

- lookup and arity metadata for `atom`
- direct builtin application over integer, builtin, nil, and non-empty list inputs
- default environment installation

## 8. Future Extension Notes

When quoted atom syntax lands, quoted atom values should naturally return `true`.

When object/class/set/bag values land, `atom` behavior for those runtime kinds should be decided with manual examples. Until then, this slice intentionally defines only the currently implemented runtime kinds.
