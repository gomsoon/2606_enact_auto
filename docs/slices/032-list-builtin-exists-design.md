# Slice 032: List Builtin Phase 4: exists Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/032-list-builtin-exists-requirements.md](/home/tprover/2606_enact_auto/docs/slices/032-list-builtin-exists-requirements.md)

Prerequisite design: [docs/slices/019-predicate-list-builtins-filter-all-design.md](/home/tprover/2606_enact_auto/docs/slices/019-predicate-list-builtins-filter-all-design.md)

## 1. Design Summary

Add `exists` to the builtin table near the other predicate list builtins:

```c
{"exists", 2, enact_builtin_exists},
```

No lexer, parser, AST, or evaluator syntax changes are required. `exists` is a normal first-class builtin value installed in the default environment.

## 2. Predicate Reuse

`exists` reuses the existing predicate helper from Slice 019:

```c
static int enact_builtin_apply_predicate(
    const EnactValue *callable,
    const EnactValue *argument,
    bool *out,
    EnactDiag *diag);
```

This keeps result validation aligned with `filter` and `all`:

1. apply the callable to one list element
2. require the result to be `ENACT_VALUE_BOOL`
3. copy the boolean payload
4. free the temporary result

## 3. Exists Callback

`enact_builtin_exists` validates:

1. first argument is callable
2. second argument is a list

Then it iterates from head to tail:

```text
for each element:
    if predicate(element) == true:
        return true
return false
```

`exists` over nil returns `false`.

`exists` short-circuits on the first true predicate result.

## 4. Arity And Partial Application

No special partial-application code is needed.

The existing builtin call path means:

```text
exists(predicate) -> <function>
```

and that partial value can later be completed with a list.

Over-application still fails before evaluating impossible extra arguments.

## 5. Ownership

`exists` does not allocate list cells and does not retain list elements.

The callback borrows each element long enough to call the predicate helper. Temporary predicate results are owned and freed inside the helper.

The only returned value is a fresh boolean value.

## 6. Error Behavior

Errors are delegated to the same helpers used by existing builtins:

- `enact_builtin_require_callable` for non-callable predicates
- `enact_builtin_require_list` for non-list inputs
- `enact_builtin_apply_predicate` for predicate application and boolean-result validation
- generic builtin arity checks before the callback is reached

If predicate application fails for an element, `exists` fails immediately and does not visit later elements.

## 7. Test Strategy

Regression tests cover:

- nil false result
- true and false matches
- short-circuit behavior
- lambda and builtin predicates
- builtin partial predicates
- partial application of `exists`
- composition with `map`, `filter`, and `all`
- shadowing behavior
- non-callable, non-list, non-boolean, arity, evaluation-order, and consumer type failures

Unit tests cover:

- builtin lookup
- arity metadata
- direct builtin apply over a list containing true and false predicate results
- direct builtin apply over nil
- default environment installation
