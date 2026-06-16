# Slice 015: List Builtins Phase 2 Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/015-list-builtins-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/015-list-builtins-phase-2-requirements.md)

Prerequisite design: [docs/slices/014-builtin-function-infrastructure-design.md](/home/tprover/2606_enact_auto/docs/slices/014-builtin-function-infrastructure-design.md)

## 1. Design Summary

Extend the Slice 014 builtin table with:

- `append`, arity 2
- `size`, arity 1

No parser changes are needed. Both names remain ordinary identifiers.

## 2. Builtin Table Extension

The table becomes:

```c
static const EnactBuiltin builtin_table[] = {
    {"hd", 1, enact_builtin_hd},
    {"tl", 1, enact_builtin_tl},
    {"append", 2, enact_builtin_append},
    {"size", 1, enact_builtin_size},
};
```

`enact_install_builtins` already installs all table entries into the default environment, so no evaluator changes are required.

## 3. `size` Design

`size` accepts one list argument:

```text
size nil           -> 0
size (1:nil)       -> 1
size (1:2:3:nil)   -> 3
```

The implementation walks the `EnactList` chain:

```c
count = 0;
while (list) {
    count += 1;
    list = enact_list_tail(list);
}
```

The result is returned as `ENACT_VALUE_INT`.

If the argument is not a list, return `ENACT_ERR_TYPE_EXPECTED_LIST`.

## 4. `append` Design

`append` accepts two list arguments:

```text
append(nil, ys)      -> ys
append(xs, nil)      -> copy(xs)
append(1:nil, 2:nil) -> 1:2:nil
```

The list representation is immutable and reference-counted. Therefore append does not mutate the left input. It copies the left prefix and shares the immutable right suffix.

Recursive helper:

```c
static EnactList *enact_builtin_append_lists(EnactList *left, EnactList *right)
{
    if (!left) {
        return enact_list_retain(right);
    }

    tail = enact_builtin_append_lists(enact_list_tail(left), right);
    result = enact_list_cons(enact_list_head(left), tail);
    enact_list_release(tail);
    return result;
}
```

The helper returns a retained list pointer or `NULL` for nil. Because `NULL` also represents a successful nil list, callers distinguish out-of-memory only when the left input was non-empty and construction fails.

## 5. Type And Arity Behavior

Arity validation remains centralized in `enact_builtin_apply` and `enact_eval_call`.

This means:

```text
append(1:nil)
append(1:nil, 2:nil, 3:nil)
size(1:nil, 2:nil)
```

all fail with `ENACT_ERR_ARITY_MISMATCH`.

Argument evaluation still happens after arity validation, matching Slice 014 behavior.

Type validation happens inside each builtin:

```text
size 1
append(1, nil)
append(nil, 1)
```

fail with `ENACT_ERR_TYPE_EXPECTED_LIST`.

## 6. Precedence Note

Whitespace application binds more tightly than cons construction. Therefore:

```text
append 1:nil
```

does not mean `append(1:nil)`. It is parsed as a cons expression whose head attempts to evaluate `append 1`.

Tests should prefer parenthesized comma calls for `append` list arguments in this slice:

```text
append(1:nil, 2:nil)
```

## 7. Test Strategy

Regression tests cover:

- `size` on nil, singleton, multi-element, and nested lists
- `append` with nil and non-empty inputs
- appended results consumed by `hd`, `tl`, equality, and higher-order calls
- exact arity failures
- type failures for both argument positions
- eager evaluation failures
- precedence behavior around whitespace call plus cons

Unit tests cover:

- lookup and arity metadata for `append` and `size`
- direct apply success for both builtins
- direct apply type and arity failures
- direct AST call through an environment containing builtins

## 8. Future Extension Notes

Slice 016 can add either:

- `atom`, to support list-recursive branch conditions
- builtin partial application, to make multi-argument builtins behave more like user functions
- tuple-like list syntax, to make list examples less noisy

`map`, `filter`, `all`, and `reduce` should wait until there is a reusable internal function-application helper for applying an arbitrary `EnactValue` callee from C.
