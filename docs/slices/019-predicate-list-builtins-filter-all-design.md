# Slice 019: Predicate List Builtins Phase 2 Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/019-predicate-list-builtins-filter-all-requirements.md](/home/tprover/2606_enact_auto/docs/slices/019-predicate-list-builtins-filter-all-requirements.md)

Prerequisite design: [docs/slices/018-higher-order-list-builtins-map-design.md](/home/tprover/2606_enact_auto/docs/slices/018-higher-order-list-builtins-map-design.md)

## 1. Design Summary

Add `filter` and `all` to the builtin table:

```c
{"filter", 2, enact_builtin_filter},
{"all", 2, enact_builtin_all},
```

Both builtins reuse `enact_eval_apply_callable` from Slice 018.

The new shared predicate helper applies a callable to one list element and requires a boolean result.

## 2. Predicate Helper

Add a local helper in `builtin.c`:

```c
static int enact_builtin_apply_predicate(
    const EnactValue *callable,
    const EnactValue *argument,
    bool *out,
    EnactDiag *diag);
```

It:

1. calls `enact_eval_apply_callable(callable, argument, 1, &result, diag)`
2. requires `result.kind == ENACT_VALUE_BOOL`
3. copies the boolean payload to `out`
4. frees the temporary `result`

Non-boolean predicate results fail with `ENACT_ERR_TYPE_EXPECTED_BOOL`.

## 3. Filter Design

`filter` validates:

1. first argument is callable
2. second argument is a list

Then it recursively filters the input list from right to left during unwinding:

```text
keep = predicate(head)
filtered_tail = filter(tail)
if keep:
    return head : filtered_tail
return filtered_tail
```

The cons operation copies the kept element, so the input list remains immutable and unchanged.

The output preserves the original order.

## 4. All Design

`all` validates:

1. first argument is callable
2. second argument is a list

Then it iterates from head to tail:

```text
for each element:
    if predicate(element) == false:
        return false
return true
```

`all` over nil returns `true`.

`all` short-circuits on the first false predicate result.

## 5. Arity And Partial Application

No special partial-application code is needed.

The existing builtin call path from Slice 016 means:

```text
filter(predicate) -> <function>
all(predicate)    -> <function>
```

and those partial values can later be completed with a list.

Over-application still fails before evaluating impossible extra arguments.

## 6. Ownership

`filter` owns the filtered tail returned by recursive calls.

When a head is kept:

1. `enact_list_cons(head, filtered_tail)` copies the head and retains the tail
2. the local tail reference is released
3. the new list is returned as owned output

When a head is dropped, the filtered tail ownership is passed upward unchanged.

`all` does not allocate list cells.

## 7. Test Strategy

Regression tests cover:

- nil, all-kept, none-kept, and partially-kept filter results
- order preservation
- `size(filter(...))` count checks
- string and nested-list filtering
- `filter` partials
- `filter` composed with `map`
- nil, true, false, negated, and builtin predicate `all`
- `all` partials
- `all` short-circuiting
- non-callable, non-list, non-bool predicate, arity, and evaluation-failure paths

Unit tests cover:

- lookup and arity metadata for `filter` and `all`
- direct builtin application using `hd` as a predicate over lists of booleans
- default environment installation

## 8. Future Extension Notes

`reduce` is now the remaining core higher-order list builtin from the initial list-processing group.

It should reuse `enact_eval_apply_callable`, but it will need a two-argument callable invocation helper shape and accumulator ownership rules.
