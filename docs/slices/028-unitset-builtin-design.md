# Slice 028: unitset Builtin Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/028-unitset-builtin-requirements.md](/home/tprover/2606_enact_auto/docs/slices/028-unitset-builtin-requirements.md)

Prerequisite design: [docs/slices/027-zero-argument-functions-calls-design.md](/home/tprover/2606_enact_auto/docs/slices/027-zero-argument-functions-calls-design.md)

## 1. Design Summary

`unitset` is a plain unary builtin installed in the default environment:

```c
{"unitset", 1, enact_builtin_unitset}
```

No lexer, parser, AST, or evaluator grammar changes are required. `unitset` remains an ordinary identifier and can be shadowed by user code.

## 2. Runtime Semantics

The implementation delegates to the existing singleton-list behavior used by `list`:

```text
unitset(x) == list(x)
```

This keeps ownership and printing behavior identical to the existing list construction path:

- `enact_list_cons` copies the head value
- nil tails are represented by `NULL`
- the returned `EnactValue` owns the newly constructed list

## 3. Error Behavior

Arity validation remains centralized in the callable/builtin apply path:

- `unitset()` reports `ENACT_ERR_ARITY_MISMATCH`
- `unitset(1,1/0)` reports `ENACT_ERR_ARITY_MISMATCH` before evaluating the impossible extra argument

Argument expressions are still evaluated before builtin execution, so:

```text
unitset(1/0)
```

reports `ENACT_ERR_DIVIDE_BY_ZERO`.

## 4. Higher-Order Behavior

Because `unitset` is a normal builtin value, it can be used directly in higher-order calls:

```text
map(unitset,(1,2))
reduce(union,nil,map(unitset,(1,2)))
```

When a higher-order builtin expects a predicate or reducer of a different return type or arity, existing diagnostics apply. For example:

```text
filter(unitset,(1,2))
```

returns `ENACT_ERR_TYPE_EXPECTED_BOOL` because `unitset` returns a list instead of a boolean.

## 5. Test Strategy

Functional regression tests cover:

- singleton construction for core value kinds
- equality with `list`
- membership and list operations over the result
- set-helper composition with `union`, `difference`, and `intersection`
- higher-order use with `map`, `filter`, `all`, and `reduce`
- function and builtin values inside singleton lists
- builtin shadowing

Robustness tests cover:

- arity failures
- argument evaluation failures
- unbound argument failures
- misuse of the returned list as an integer, boolean, function, equality peer, or cons tail
- use as an invalid predicate or reducer

Unit tests cover:

- lookup
- arity metadata
- direct builtin application
- default environment installation
