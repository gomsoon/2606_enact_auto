# Slice 015: List Builtins Phase 2 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/014-builtin-function-infrastructure-requirements.md](/home/tprover/2606_enact_auto/docs/slices/014-builtin-function-infrastructure-requirements.md)

## 1. Slice Goal

This slice extends the builtin library with the next two list operations:

- `append`
- `size`

The goal is to validate the Slice 014 builtin infrastructure with a multi-argument builtin and a list-folding observer while keeping the implementation small enough to test thoroughly.

## 2. Source Basis

The PRD records:

- predefined list operations include `hd`, `tl`, `append`, `size`, `map`, `filter`, `all`, and `reduce`
- functions are first-class values
- function application works in both parenthesized and whitespace-applied forms
- list values are immutable cons lists after Slice 013
- builtin function values are ordinary environment bindings after Slice 014

## 3. In Scope

This slice includes:

- `append` as a two-argument builtin
- `size` as a one-argument builtin
- builtin lookup, installation, arity metadata, direct apply, and call tests for the new builtins
- regression tests for nil, singleton, multi-element, nested, string, boolean, and higher-order uses
- robustness tests for arity and type errors

## 4. Out Of Scope

This slice explicitly excludes:

- builtin partial application
- `map`, `filter`, `all`, and `reduce`
- `atom`
- tuple-like list construction with `(x,y,z)`
- recursive definitions or `fix`
- collection/object `size` behavior
- integer overflow stress tests for physically enormous lists

## 5. User-Facing Behavior

Accepted examples:

- `size nil.` => `0`
- `size(1:nil).` => `1`
- `size(1:2:3:nil).` => `3`
- `size((1:nil):2:nil).` => `2`
- `append(nil, 1:nil).` => `1:nil`
- `append(1:nil, nil).` => `1:nil`
- `append(1:2:nil, 3:4:nil).` => `1:2:3:4:nil`
- `append("a":nil, "b":nil).` => `"a":"b":nil`
- `append((1:nil):nil, 2:nil).` => `(1:nil):2:nil`
- `f:=append; f(1:nil, 2:nil).` => `1:2:nil`
- `apply(f,x,y):=f(x,y); apply(append, 1:nil, 2:nil).` => `1:2:nil`
- `measure(f,x):=f x; measure(size, 1:2:nil).` => `2`

Error examples:

- `size 1.` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `append(1, nil).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `append(nil, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `append(1:nil).` => `ENACT_ERR_ARITY_MISMATCH`
- `append(1:nil, 2:nil, 3:nil).` => `ENACT_ERR_ARITY_MISMATCH`
- `size(1:nil, 2:nil).` => `ENACT_ERR_ARITY_MISMATCH`

## 6. Syntax Requirements

No new syntax is required.

`append` and `size` remain ordinary identifiers resolved from the default environment.

Because builtin partial application is out of scope, `append` must be called with exactly two arguments in this slice:

```text
append(1:nil, 2:nil)
```

This form is preferred for list arguments because whitespace application binds more tightly than cons construction.

## 7. Semantic Requirements

`size list` shall:

1. require exactly one argument
2. require that argument to be a list
3. return the number of top-level cons cells as an integer

`append left right` shall:

1. require exactly two arguments
2. require both arguments to be lists
3. return a list containing the elements of `left` followed by the elements of `right`
4. preserve element values by using the normal `EnactValue` copy semantics
5. preserve immutability by not modifying either input list

`append nil right` returns `right`.

`append left nil` returns a copy-equivalent list containing the elements of `left`.

The returned list may share immutable suffix cells with the right argument.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- size of nil
- size of singleton list
- size of multi-element list
- size of nested list by top-level cells
- append nil left side
- append nil right side
- append two non-empty integer lists
- append string lists
- append nested-list head
- append result used by `hd`
- append result used by `tl`
- append assigned to another name
- append passed to higher-order function
- size passed to higher-order function
- append equality with direct cons construction

## 9. Robustness Requirements

The regression suite shall include:

- size with non-list argument
- append with non-list left argument
- append with non-list right argument
- append with one argument
- append with three arguments
- size with two arguments
- append left argument evaluation failure
- append right argument evaluation failure
- size argument evaluation failure
- append result used as integer
- size builtin used with list-construction precedence that does not imply partial application

## 10. Acceptance Criteria

This slice is accepted when:

- `append` and `size` are installed in the default environment
- `append` is callable as a two-argument builtin
- `size` is callable as a one-argument builtin
- both builtins can be assigned, passed, and compared like other builtin function values
- list input validation uses `ENACT_ERR_TYPE_EXPECTED_LIST`
- arity validation uses `ENACT_ERR_ARITY_MISMATCH` before evaluating extra impossible arguments
- previous Slice 001 through Slice 014 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
