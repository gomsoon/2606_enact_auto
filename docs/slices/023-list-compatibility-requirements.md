# Slice 023: List Compatibility Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Update note: Slice 027 supersedes this slice's empty-call boundary. `f()`, `list()`, and `size()` now parse as zero-argument calls; current builtins still report `ENACT_ERR_ARITY_MISMATCH` when called with no arguments.

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/022-recursive-named-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/022-recursive-named-functions-requirements.md)

## 1. Slice Goal

This slice finishes the documented singleton-list compatibility forms:

```text
99:()
list 99
```

Both forms shall use the existing immutable cons-list runtime. No tuple runtime type is introduced.

## 2. Source Basis

The PRD records:

- the empty list `nil`
- cons construction using `:`
- tuple-like list construction
- documented singleton list conventions such as `99:nil`, `99:()`, and `list 99`

Slice 017 intentionally deferred `()` and `list`. This slice closes that deferred list-compatibility work.

## 3. In Scope

This slice includes:

- empty parenthesized list syntax `()`
- lowering `()` to the existing `nil` AST/value
- cons compatibility such as `99:()`
- a unary `list` builtin
- `list` through parenthesized calls and whitespace application
- `list` as a higher-order callable
- regression tests for boundary behavior and robustness failures

## 4. Out Of Scope

This slice explicitly excludes:

- a new tuple or list runtime representation
- singleton tuple syntax such as `(x,)`
- changing ordinary grouping `(x)`
- changing multi-element tuple-like list syntax `(x,y,...)`
- accepting empty function calls such as `f()`; this was deferred to Slice 027
- preserving whitespace differences between `f()` and `f ()`
- quoted atom/symbol syntax
- object collections such as sets and bags

## 5. User-Facing Behavior

Accepted examples:

- `().` => `nil`
- `99:().` => `99:nil`
- `1:2:().` => `1:2:nil`
- `list 99.` => `99:nil`
- `list(99).` => `99:nil`
- `list nil.` => `(nil):nil`
- `size(()).` => `0`
- `atom(()).` => `true`
- `hd(list 5).` => `5`
- `tl(list 5).` => `nil`
- `append((), list 1).` => `1:nil`
- `map(list, (1,2)).` => `(1:nil):(2:nil):nil`

Error examples:

- `list().` => `ENACT_ERR_ARITY_MISMATCH` after Slice 027
- `size().` => `ENACT_ERR_ARITY_MISMATCH` after Slice 027
- `list(1,2).` => `ENACT_ERR_ARITY_MISMATCH`
- `list(1/0).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `hd(()).` => `ENACT_ERR_LIST_EMPTY`
- `():1.` => `ENACT_ERR_TYPE_EXPECTED_LIST`

## 6. Syntax Requirements

The parser shall accept `()` as a primary expression:

```text
primary ::= "(" ")"
```

The resulting AST shall be the same `AST_NIL` node used by the `nil` token.

Slice 023 intentionally left empty function calls unsupported. Slice 027 later added empty-call syntax, so both `f()` and `f ()` are now parsed as zero-argument calls because the lexer does not preserve whitespace.

## 7. Builtin Requirements

Add `list` as a unary builtin:

```text
list x
```

shall return:

```text
x:nil
```

The builtin shall participate in the same environment, higher-order function, shadowing, equality, and arity behavior as the existing builtins.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- tokenization for `()`
- tokenization for `99:()`
- tokenization for `list 99`
- empty list literal
- singleton cons with `()` tail
- multi-element cons with `()` tail
- whitespace `list` application
- parenthesized `list` application
- boolean singleton list
- nil singleton list
- nested list singleton
- `size` over `()`
- `atom` over `()`
- `hd` over `list`
- `tl` over `list`
- `append` with `()`
- cons whose right side is `list`
- higher-order `map(list, ...)`
- `reduce` with `()` as the initial accumulator
- assignment/equality with `()`
- builtin shadowing by user assignment

## 9. Robustness Requirements

The regression suite shall include:

- empty `list()` call reports arity mismatch after Slice 027
- empty `size()` call reports arity mismatch after Slice 027
- over-applied `list`
- over-applied `list` does not evaluate impossible extra arguments
- argument evaluation failure propagates
- unbound `list` argument failure
- list value used as an integer
- list value used as a boolean
- list value compared with a non-list
- list value used in ordering
- `hd(())` fails as empty list
- `tl(())` fails as empty list
- `()` used as a cons head with a non-list tail
- shadowed non-function `list` call fails

## 10. Acceptance Criteria

This slice is accepted when:

- `()` evaluates exactly as `nil`
- `99:()` evaluates exactly as `99:nil`
- `list x` returns `x:nil`
- `list` behaves like other unary builtins in higher-order calls
- empty function calls are deferred to Slice 027
- previous Slice 001 through Slice 022 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
