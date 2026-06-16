# Slice 032: List Builtin Phase 4: exists Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/019-predicate-list-builtins-filter-all-requirements.md](/home/tprover/2606_enact_auto/docs/slices/019-predicate-list-builtins-filter-all-requirements.md)

## 1. Slice Goal

This slice adds the remaining predicate-style list observer:

```text
exists(predicate, list)
```

`exists` returns `true` when at least one element satisfies the predicate and `false` otherwise.

## 2. Source Basis

The PRD lists `exists` among collection and list-oriented operations. Slice 020 explicitly deferred `exists` while adding `reduce`.

The current runtime already has the foundations needed for this slice:

- first-class callable values
- builtin partial application
- list values and tuple-like list construction
- `filter` and `all` predicate application semantics
- short-circuiting boolean operators and conditionals

## 3. In Scope

This slice includes:

- `exists` as a two-argument builtin
- callable validation for the predicate argument
- list validation for the input list
- left-to-right predicate application
- short-circuit return on the first true predicate result
- `false` result for `nil`
- boolean-only predicate result validation
- builtin partial application support
- regression and unit tests

## 4. Out Of Scope

This slice explicitly excludes:

- object or collection class integration
- method dispatch syntax
- `locate` or other search-result builtins
- lazy list values
- stream or iterator abstractions
- script `load` command behavior

## 5. User-Facing Behavior

Accepted examples:

- `exists(x::x>0, nil).` => `false`
- `exists(x::x>0, (1,2,3)).` => `true`
- `exists(x::x>3, (1,2,3)).` => `false`
- `exists(x::not x, (true,false)).` => `true`
- `exists(hd, ((false:nil),(true:nil))).` => `true`
- `q:=exists(x::x>1); q((1,2)).` => `true`
- `exists(member(2), map(unitset,(1,2,3))).` => `true`
- `exists(x::x>1).` => `<function>`

Error examples:

- `exists(1, nil).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `exists(x::x>1, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `exists(x::x+1, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `exists(size, ((1:nil),(2:nil))).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `exists(x::x>1, nil, 1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `exists(x::x, (1/0,2)).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `exists(x::false, (1,2))+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 6. Exists Semantics

`exists predicate list` shall:

1. require exactly two arguments
2. require the first argument to be callable
3. require the second argument to be a list
4. visit the list from head to tail
5. call the predicate with exactly one element argument
6. require each predicate result to be boolean
7. return `true` immediately when a predicate result is true
8. return `false` when the list is nil or no predicate result is true

`exists` over `nil` shall not call the predicate.

## 7. Arity And Partial Application Requirements

`exists` has arity 2.

The existing builtin partial-application behavior shall support:

- `exists(predicate)` returning a function-like partial
- completing that partial with a list
- passing the partial to higher-order helpers such as `apply` or `map`

Over-application shall continue to fail before evaluating impossible extra arguments.

## 8. Evaluation Order Requirements

The input list expression is evaluated eagerly before `exists` executes. Expression failures inside tuple-like list construction are therefore reported before predicate traversal begins.

Predicate calls happen left to right. Once a predicate returns `true`, `exists` shall not apply the predicate to later list elements.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- nil list result
- first-element true result
- last-element true result
- no-match false result
- boolean predicate negation
- builtin predicate use
- partial application
- higher-order passing of an `exists` partial
- builtin partial predicate use
- string values
- nested list values
- short-circuit behavior that avoids a later predicate type error
- composition with `all` and `filter`
- builtin shadowing behavior

## 10. Robustness Requirements

The regression suite shall include:

- non-callable predicate
- non-list input
- non-boolean lambda predicate result
- non-boolean builtin predicate result
- over-application
- eager list evaluation failure
- predicate failure after earlier false results
- consumer type errors when a boolean result is used as an integer or equality operand
- shadowed non-function builtin call
- higher-order partial use with the wrong remaining argument type
- short-circuit negative case where a later bad element is still evaluated because no earlier true result occurred

## 11. Acceptance Criteria

This slice is accepted when:

- `exists` is installed in the default builtin environment
- `exists` reports arity 2 through builtin metadata
- direct builtin application works in unit tests
- partial application of `exists` works through the existing builtin partial path
- nil and short-circuit behavior match this document
- all regression tests pass
