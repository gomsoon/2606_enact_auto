# Slice 025: List Set-Operation Builtins Phase 1 Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/025-list-set-operation-builtins-requirements.md](/home/tprover/2606_enact_auto/docs/slices/025-list-set-operation-builtins-requirements.md)

## 1. Overview

This slice adds five ordinary C-backed builtins to the existing builtin table:

```c
{"member", 2, enact_builtin_member},
{"remove", 2, enact_builtin_remove},
{"union", 2, enact_builtin_union},
{"difference", 2, enact_builtin_difference},
{"intersection", 2, enact_builtin_intersection},
```

No lexer, parser, AST, or evaluator grammar changes are required. These names remain ordinary identifiers that resolve to builtin values installed in the default environment.

## 2. Shared Membership Helper

Add a helper:

```c
static int enact_builtin_list_contains_value(
    EnactList *list,
    const EnactValue *needle,
    bool *out)
```

The helper:

- scans list cells from head to tail
- compares each head with `needle` using `enact_value_equal`
- returns `true` through `out` on the first match
- returns `false` through `out` when the scan reaches nil

Different runtime kinds compare as non-equal because `enact_value_equal` already has that behavior.

## 3. `member`

`enact_builtin_member` requires the second argument to be a list via `enact_builtin_require_list`.

It delegates to `enact_builtin_list_contains_value` and returns an immediate boolean value.

Failure modes:

- non-list second argument: `ENACT_ERR_TYPE_EXPECTED_LIST`
- internal equality helper failure: `ENACT_ERR_OUT_OF_MEMORY`
- wrong arity: handled by `enact_builtin_apply`

## 4. `remove`

`enact_builtin_remove_one` recursively walks the input list.

State:

```c
bool removed;
```

Algorithm:

1. nil returns nil
2. if no value has been removed yet and the current head equals the needle, return a retained tail
3. otherwise recurse into the tail
4. cons the current head onto the rewritten tail

This removes only the first equal occurrence and preserves the order of the remaining list.

## 5. `difference`

`enact_builtin_difference_lists(left, right, out)` recursively walks `left`.

For each left-side head:

- if the head is a member of `right`, omit it
- otherwise cons it onto the filtered tail

The resulting list preserves left-side order.

## 6. `intersection`

`enact_builtin_intersection_lists(left, right, out)` mirrors `difference`.

For each left-side head:

- if the head is a member of `right`, keep it
- otherwise omit it

The resulting list preserves left-side order.

## 7. `union`

The manual's set example implies this ordering:

```text
union(left, right) = append(difference(left, right), right)
```

The implementation follows that rule directly:

1. validate both arguments as lists
2. compute `left_only = difference(left, right)`
3. append `left_only` to `right` with the existing `enact_builtin_append_lists` helper
4. release the temporary `left_only`

For example:

```text
union((3,2,1),(5,4,3)) => 2:1:5:4:3:nil
```

## 8. Memory Ownership

The implementation follows existing list helper ownership patterns:

- newly constructed result cells are owned by the returned `EnactValue`
- temporary filtered lists are released after being consumed
- retained tails are used only when `remove` can safely reuse the unchanged suffix
- `nil` is represented by a null `EnactList *`

All copied list cells use `enact_list_cons`, which deep-copies the head value and retains the tail.

## 9. Partial Application

No special partial-application implementation is needed. The existing builtin partial object handles all five new arity-2 builtins.

Examples:

```text
member(2)          % predicate over lists
remove(2)          % list transformer
union((1,2))       % function from right list to union result
difference((1,2))  % function from right list to difference result
intersection((1,2))
```

Captured values are evaluated eagerly by the existing call evaluator.

## 10. Tests

Functional regression tests cover:

- empty list behavior
- head, middle, tail, and missing membership
- strings, nested lists, functions, and builtins as elements
- remove at different positions
- union, difference, and intersection over nil and overlapping lists
- manual-style union ordering
- partial application
- higher-order use with `reduce`, `filter`, `map`, and `all`

Robustness tests cover:

- non-list arguments
- arity failures
- argument evaluation failures
- partial application with invalid captured types
- list and boolean result misuse

Unit tests cover:

- builtin lookup
- arity metadata
- direct builtin application
- default environment installation

## 11. Review Checklist

This design is ready when:

- no parser conflicts are introduced
- all new names are plain builtins, not reserved words
- list result ordering is deterministic and documented
- duplicate-input behavior is documented as outside the manual's set-list precondition
- all previous list, higher-order, partial, recursive, and fix tests remain green
