# Slice 020: Higher-Order List Builtins Phase 3 Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/020-higher-order-list-builtins-reduce-requirements.md](/home/tprover/2606_enact_auto/docs/slices/020-higher-order-list-builtins-reduce-requirements.md)

Prerequisite design: [docs/slices/019-predicate-list-builtins-filter-all-design.md](/home/tprover/2606_enact_auto/docs/slices/019-predicate-list-builtins-filter-all-design.md)

## 1. Design Summary

Add `reduce` to the builtin table:

```c
{"reduce", 3, enact_builtin_reduce},
```

No lexer, parser, AST, or evaluator syntax changes are needed. `reduce` is a normal first-class builtin value installed in the default environment.

The implementation reuses:

- `enact_builtin_require_callable`
- `enact_builtin_require_list`
- `enact_eval_apply_callable`
- the existing builtin partial-application path

## 2. Runtime Signature

Add a local builtin callback in `builtin.c`:

```c
static int enact_builtin_reduce(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

The callback expects:

1. `arguments[0]`: reducer callable
2. `arguments[1]`: initial accumulator value
3. `arguments[2]`: input list

The generic `enact_builtin_apply` layer already enforces arity 3 before the callback is reached.

## 3. Fold Algorithm

The fold is left associative:

```text
acc = initial
for element in list:
    acc = reducer(acc, element)
return acc
```

Equivalent expansion:

```text
reduce(f, z, (a,b,c)) == f(f(f(z, a), b), c)
```

`nil` returns the initial value without calling the reducer:

```text
reduce(f, z, nil) == z
```

## 4. Accumulator Ownership

The initial accumulator is copied before iteration:

```c
enact_value_copy(&accumulator, &arguments[1])
```

Each loop iteration:

1. borrows the current accumulator and list head in a temporary two-value argument array
2. calls `enact_eval_apply_callable`
3. frees the previous accumulator
4. stores the reducer result as the next accumulator

At the end, ownership of the final accumulator is moved into `*out`.

If reducer application fails, the current accumulator is freed before returning failure.

## 5. Reducer Application

Reducer invocation uses:

```c
EnactValue reducer_arguments[2];

reducer_arguments[0] = accumulator;
reducer_arguments[1] = *head;
enact_eval_apply_callable(&arguments[0], reducer_arguments, 2, &next_accumulator, diag);
```

The temporary array borrows values only for the duration of the call. It does not own the accumulator or list head.

The existing callable helper handles:

- user functions
- builtin functions
- builtin partials
- arity mismatch
- non-callable values

## 6. Type Behavior

`reduce` itself does not impose a type on the accumulator.

Type errors come from:

- the reducer body
- the reducer builtin
- later expressions that consume the final reduced value

Examples:

```text
reduce((acc,x)::acc+x, true, (1,2)) -> ENACT_ERR_TYPE_EXPECTED_INT
reduce(append, nil, (1,2))          -> ENACT_ERR_TYPE_EXPECTED_LIST
```

## 7. Partial Application

No special partial code is needed.

The existing builtin call path means:

```text
reduce(reducer)          -> <function>
reduce(reducer, initial) -> <function>
```

The captured prefix arguments are evaluated eagerly when the partial is created, matching previous builtin partial behavior.

Over-application still fails before evaluating impossible extra arguments.

## 8. Test Strategy

Regression tests cover:

- nil, singleton, and multi-element lists
- sum, product, count, last-element, and reverse folds
- builtin reducer use with `append`
- boolean folds
- string and function-valued accumulators
- partial application after one and two arguments
- higher-order passing of a reduce partial
- composition with `map`, `filter`, and `all`
- non-callable, non-list, arity, evaluation, and result-consumption failures

Unit tests cover:

- lookup and arity metadata for `reduce`
- direct builtin application with `append` as reducer
- default environment installation

## 9. Future Extension Notes

After this slice, the initial functional list builtin group is complete:

```text
hd, tl, append, size, map, filter, all, reduce
```

Reasonable next slices include:

- `atom`, if recursive list examples need a base-condition helper
- `fix`, if recursive function examples become the next milestone focus
- object-core syntax such as `class`, `new`, and `with`
