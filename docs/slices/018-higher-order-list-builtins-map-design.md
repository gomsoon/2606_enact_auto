# Slice 018: Higher-Order List Builtins Phase 1 Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/018-higher-order-list-builtins-map-requirements.md](/home/tprover/2606_enact_auto/docs/slices/018-higher-order-list-builtins-map-requirements.md)

Prerequisite design: [docs/slices/017-tuple-like-list-construction-design.md](/home/tprover/2606_enact_auto/docs/slices/017-tuple-like-list-construction-design.md)

## 1. Design Summary

Add `map` to the builtin table and factor callable application out of the AST call evaluator.

The reusable helper applies an already-evaluated callable value to an already-evaluated argument array:

```c
int enact_eval_apply_callable(
    const EnactValue *callee,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

`map` uses this helper for each list element.

## 2. Callable Helper

The helper supports the same callable kinds as ordinary calls:

```text
ENACT_VALUE_FUNCTION
ENACT_VALUE_BUILTIN
ENACT_VALUE_BUILTIN_PARTIAL
```

It implements the existing arity split:

```text
supplied < arity   -> return a partial callable
supplied == arity  -> apply the callable
supplied > arity   -> ENACT_ERR_ARITY_MISMATCH
```

For builtin partials, the captured prefix count is included in the split:

```text
captured + supplied < arity   -> return an extended builtin partial
captured + supplied == arity  -> apply the builtin
captured + supplied > arity   -> ENACT_ERR_ARITY_MISMATCH
```

The helper borrows its input values. It does not free the callee or argument array. On success, it writes an owned `EnactValue` to `out`.

## 3. Preserving AST Call Timing

Ordinary AST calls keep their existing evaluation timing:

1. evaluate the callee
2. validate that the supplied argument count is possible
3. evaluate arguments left-to-right
4. call `enact_eval_apply_callable`

This preserves previous robustness behavior:

```text
one(x):=x; one(1,1/0)
```

still fails with `ENACT_ERR_ARITY_MISMATCH` before evaluating `1/0`.

## 4. `map` Builtin

Add to the builtin table:

```c
{"map", 2, enact_builtin_map}
```

`map` validates:

1. first argument is callable
2. second argument is a list

Then it maps the list from head to tail. For each element:

```text
mapped_head = apply(callable, element)
mapped_tail = map remaining tail
result = mapped_head : mapped_tail
```

The implementation constructs a fresh output list and does not mutate the input list.

## 5. Empty List Behavior

`map(f, nil)` returns `nil`.

The callable argument is still validated before returning. Therefore:

```text
map(1, nil)
```

fails with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## 6. Ownership

During recursive mapping:

- each mapped head is owned until copied into the output cons cell
- each mapped tail list is released after it is retained by the new cons cell
- failure releases any mapped head already produced for the current stack frame

The callable and input list are borrowed from builtin arguments.

## 7. Test Strategy

Regression tests cover:

- simple `map` over `nil` and tuple-like lists
- user functions and lambdas
- builtin callables such as `hd`, `tl`, and `size`
- builtin partial callables such as `append(0:nil)`
- nested `map` partials
- `map` returning partial functions
- assigned and higher-order map partials
- closure capture through the mapped function
- non-callable, non-list, mapped-call failure, and over-arity errors

Unit tests cover:

- `map` lookup and arity metadata
- direct `enact_builtin_apply` for `map`
- builtin installation of `map`
- direct `enact_eval_apply_callable` on a user function
- direct rejection of a non-callable value by the helper

## 8. Future Extension Notes

`filter`, `all`, and `reduce` should reuse `enact_eval_apply_callable`.

`filter` and `all` will additionally need boolean result validation. `reduce` will need repeated two-argument callable application with an accumulator.
