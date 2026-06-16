# Slice 020: Higher-Order List Builtins Phase 3 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/019-predicate-list-builtins-filter-all-requirements.md](/home/tprover/2606_enact_auto/docs/slices/019-predicate-list-builtins-filter-all-requirements.md)

## 1. Slice Goal

This slice adds the remaining core higher-order list builtin from the initial list-processing group:

```text
reduce(reducer, initial, list)
```

`reduce` folds a list from left to right, carrying an accumulator value through each element.

## 2. Source Basis

The PRD records:

- functions are first-class values
- predefined list operations include `map`, `filter`, `all`, and `reduce`
- currying and partial application are supported
- eager evaluation semantics are acceptable for this implementation

Slices 018 and 019 already added `map`, `filter`, `all`, and the shared callable-application helper used by C builtins.

## 3. In Scope

This slice includes:

- `reduce` as a three-argument builtin
- callable validation for the reducer argument
- list validation for the input list
- left-to-right accumulator evaluation
- reducer application with exactly two arguments: current accumulator and current element
- support for accumulator values of any runtime kind
- support for reducer results of any runtime kind
- partial application of `reduce`
- regression and unit tests

## 4. Out Of Scope

This slice explicitly excludes:

- `exists`
- `atom`
- recursive definitions or `fix`
- lazy list values
- object or collection class integration
- special syntax for folds
- a generalized iterator abstraction shared by all list builtins

## 5. User-Facing Behavior

Accepted examples:

- `reduce((acc,x)::acc+x, 0, nil).` => `0`
- `reduce((acc,x)::acc+x, 0, (1,2,3)).` => `6`
- `reduce((acc,x)::acc*x, 1, (2,3,4)).` => `24`
- `reduce((acc,x)::acc+1, 0, (10,20,30)).` => `3`
- `reduce((acc,x)::x, 0, (1,2,3)).` => `3`
- `reduce((acc,x)::x:acc, nil, (1,2,3)).` => `3:2:1:nil`
- `reduce(append, nil, ((1,2),(3,4),nil)).` => `1:2:3:4:nil`
- `reduce((acc,x)::acc and x, true, (true,true,false)).` => `false`
- `reduce((acc,x)::acc or x, false, (false,true,false)).` => `true`
- `reduce((acc,x)::x, "", ("a","b")).` => `"b"`
- `r:=reduce((acc,x)::acc+x); r(0,(1,2)).` => `3`
- `r:=reduce((acc,x)::acc+x,0); r((1,2)).` => `3`
- `reduce((acc,x)::acc+x).` => `<function>`

Error examples:

- `reduce(1, 0, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `reduce(1, 0, nil).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `reduce((acc,x)::acc+x, 0, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `reduce((acc,x)::acc+x, 0, (1,true)).` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `reduce(x::x, 0, (1,2)).` => `ENACT_ERR_ARITY_MISMATCH`
- `reduce(hd, nil, ((1:nil),(2:nil))).` => `ENACT_ERR_ARITY_MISMATCH`
- `reduce((acc,x)::acc+x, 0, (1,2), 1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `reduce((acc,x)::acc+x, 0, (1/0,2)).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `reduce((acc,x)::x:acc, nil, (1,2))+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 6. Reduce Semantics

`reduce reducer initial list` shall:

1. require exactly three arguments
2. require the first argument to be callable
3. require the third argument to be a list
4. copy the second argument into a local accumulator
5. visit the list from head to tail
6. call the reducer as `reducer(accumulator, element)` for each element
7. replace the accumulator with the reducer result
8. return the final accumulator

When the list is `nil`, `reduce` returns a copy of the initial value and never applies the reducer.

The reducer result may have any runtime kind. This allows folds that produce integers, booleans, strings, lists, functions, builtins, or builtin partials.

## 7. Arity And Partial Application Requirements

`reduce` has arity 3.

The existing builtin partial-application behavior shall support:

- `reduce(reducer)` returning a function-like partial
- `reduce(reducer, initial)` returning a function-like partial
- completing either partial with the remaining argument or arguments

Reducer application itself uses ordinary callable arity behavior. A one-argument reducer applied to `(accumulator, element)` shall fail with `ENACT_ERR_ARITY_MISMATCH`.

## 8. Evaluation Order Requirements

The ordinary call evaluator shall continue to reject over-application before evaluating impossible extra arguments.

The list argument is still evaluated eagerly before `reduce` executes. Therefore expression failures inside tuple-like list construction are reported before the reducer starts.

During reduction, reducer calls happen left to right. If any reducer application fails, `reduce` fails immediately and does not evaluate later reducer applications.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- reduce over nil
- integer sum
- integer product
- element counting
- last-element selection
- list reversal
- builtin reducer over nested lists
- boolean conjunction fold
- boolean disjunction fold
- boolean equality-style fold
- string accumulator replacement
- singleton list fold
- reduce partial with one captured argument
- reduce partial with two captured arguments
- higher-order passing of a reduce partial
- map over reduce result
- reduce over filter result
- all over reduce result
- reducer returning a function value
- under-applied reduce printing `<function>`

## 10. Robustness Requirements

The regression suite shall include:

- non-callable reducer over non-empty list
- non-callable reducer over nil
- non-list input
- reducer type error on a later element
- one-argument reducer arity mismatch
- builtin reducer arity mismatch
- reduce over-application does not evaluate impossible extra arguments
- reduce over-application with nil list does not evaluate impossible extra arguments
- list argument evaluation failure
- reducer body evaluation failure
- initial accumulator type error
- first element type error
- reduced list used as an integer
- reduced list used as a boolean
- reduced list compared with a non-list
- builtin reducer argument type failure

## 11. Acceptance Criteria

This slice is accepted when:

- `reduce` is installed in the default environment
- `reduce` has arity 3
- `reduce` works with user functions, lambdas, builtins, and builtin partials when their arity and types match the fold
- `reduce` folds left to right
- `reduce` can return any runtime value kind
- `reduce` can be partially applied
- previous Slice 001 through Slice 019 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
