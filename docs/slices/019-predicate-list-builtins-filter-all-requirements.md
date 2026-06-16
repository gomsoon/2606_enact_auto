# Slice 019: Predicate List Builtins Phase 2 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/018-higher-order-list-builtins-map-requirements.md](/home/tprover/2606_enact_auto/docs/slices/018-higher-order-list-builtins-map-requirements.md)

## 1. Slice Goal

This slice adds two predicate-based higher-order list builtins:

```text
filter(predicate, list)
all(predicate, list)
```

`filter` keeps the elements whose predicate result is `true`.

`all` returns whether every element satisfies the predicate.

## 2. Source Basis

The PRD records:

- functions are first-class values
- predefined list operations include `map`, `filter`, `all`, and `reduce`
- logical values and predicate-style expressions are part of the expression core

Slice 018 added `map` and the reusable `enact_eval_apply_callable` helper. This slice reuses that helper and adds boolean-result validation for predicate callables.

## 3. In Scope

This slice includes:

- `filter` as a two-argument builtin
- `all` as a two-argument builtin
- callable validation for predicate arguments
- list validation for input lists
- boolean validation for predicate results
- order-preserving filtered list construction
- `all` over nil
- `all` short-circuiting on the first false predicate result
- partial application of `filter` and `all`
- regression and unit tests

## 4. Out Of Scope

This slice explicitly excludes:

- `reduce`
- a generalized list iterator abstraction
- first-class `not` as a builtin identifier
- lazy list values
- object or collection class integration
- recursive definitions or `fix`

## 5. User-Facing Behavior

Accepted examples:

- `filter(x::x>1, nil).` => `nil`
- `filter(x::x>1, (1,2,3)).` => `2:3:nil`
- `filter(x::true, (1,2,3)).` => `1:2:3:nil`
- `filter(x::false, (1,2,3)).` => `nil`
- `filter(x::x=="a", ("a","b","a")).` => `"a":"a":nil`
- `filter(x::size(x)>2, ((1,2),(3,4,5),nil)).` => `(3:4:5:nil):nil`
- `size(filter(x::true, (1,2,3))).` => `3`
- `size(filter(x::false, (1,2,3))).` => `0`
- `p:=filter(x::x>1); p((1,2,3)).` => `2:3:nil`
- `map(x::x*2, filter(x::x>1, (1,2,3))).` => `4:6:nil`
- `all(x::x>0, nil).` => `true`
- `all(x::x>0, (1,2,3)).` => `true`
- `all(x::x>1, (1,2,3)).` => `false`
- `all(x::not x, (false,false)).` => `true`
- `q:=all(x::x>0); q((1,2)).` => `true`
- `filter(x::x>1).` => `<function>`
- `all(x::x>1).` => `<function>`

Error examples:

- `filter(1, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `all(1, nil).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `filter(x::x>1, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `all(x::x>1, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `filter(x::x+1, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `all(x::x+1, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `filter(hd, ((1:nil),(2:nil))).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `all(size, ((1:nil),(2:nil))).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `filter(x::x>1, (1,2), 1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `filter(x::x, (1/0,2)).` => `ENACT_ERR_DIVIDE_BY_ZERO`

## 6. Filter Semantics

`filter predicate list` shall:

1. require exactly two arguments
2. require the first argument to be callable
3. require the second argument to be a list
4. apply the predicate to each list element from head to tail
5. require each predicate result to be boolean
6. copy each element whose predicate result is `true` into a new list
7. preserve the original element order

The result list count is not generally equal to the input list count. It may be:

- equal, when every predicate result is `true`
- zero, when every predicate result is `false`
- any count between those bounds

## 7. All Semantics

`all predicate list` shall:

1. require exactly two arguments
2. require the first argument to be callable
3. require the second argument to be a list
4. apply the predicate to each list element from head to tail
5. require each predicate result to be boolean
6. return `false` as soon as a predicate result is false
7. return `true` for nil or when every predicate result is true

`all` short-circuits. If an earlier element returns false, later predicate applications are not evaluated.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- filter over nil
- filter keeping a proper suffix
- filter keeping all elements
- filter keeping no elements
- filter over strings
- filter over nested lists using `size`
- filtered length equal to input length
- filtered length zero
- assigned filter partial
- higher-order passing of a filter partial
- map over filter result
- all over nil
- all true over all elements
- all false over one element
- all with logical negation
- all with builtin predicate
- assigned all partial
- all short-circuit behavior
- under-applied filter printing `<function>`
- under-applied all printing `<function>`

## 9. Robustness Requirements

The regression suite shall include:

- non-callable filter predicate
- non-callable all predicate over nil
- non-list filter input
- non-list all input
- non-boolean filter predicate result
- non-boolean all predicate result
- builtin predicate returning non-bool for filter
- builtin predicate returning non-bool for all
- filter over-application does not evaluate impossible extra arguments
- all over-application does not evaluate impossible extra arguments
- filter list argument evaluation failure
- all list argument evaluation failure
- filter evaluates later predicates after false results
- filtered list used as an integer
- filtered list used as a boolean
- filtered list compared with a non-list

## 10. Acceptance Criteria

This slice is accepted when:

- `filter` and `all` are installed in the default environment
- both builtins work with user functions, builtins, and builtin partials when they return booleans
- predicate return type validation uses `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `filter` preserves input order
- `all` short-circuits on false
- both builtins can be partially applied
- previous Slice 001 through Slice 018 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
