# Slice 018: Higher-Order List Builtins Phase 1 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/017-tuple-like-list-construction-requirements.md](/home/tprover/2606_enact_auto/docs/slices/017-tuple-like-list-construction-requirements.md)

## 1. Slice Goal

This slice introduces the first higher-order list builtin:

```text
map(f, (1,2,3))
```

and adds a reusable evaluator helper for applying an already-evaluated callable value from C.

After this slice:

```text
map(x::x+1, (1,2,3)).
```

evaluates to:

```text
2:3:4:nil
```

## 2. Source Basis

The PRD records:

- functions are first-class values
- predefined list operations include `map`, `filter`, `all`, and `reduce`
- function application works through parenthesized and whitespace-applied forms
- currying and partial application are supported

Slice 016 made builtins participate in partial application. Slice 017 added readable list input syntax. This slice uses both pieces to make `map` practical and testable.

## 3. In Scope

This slice includes:

- `map` as a two-argument builtin
- a reusable callable-apply helper for already-evaluated `EnactValue` callables
- support for user functions, builtin functions, and builtin partials as the mapping function
- mapping over `nil`
- mapping over integer, boolean, string, and nested-list values
- mapping functions that return ordinary values or function values
- regression tests for boundary and robustness behavior
- unit tests for direct `map` application and the callable helper

## 4. Out Of Scope

This slice explicitly excludes:

- `filter`, `all`, and `reduce`
- a generalized iterator abstraction
- lazy map evaluation
- list mutation
- zero-argument callable application
- non-prefix partial application
- recursive definitions or `fix`
- object or collection class integration

## 5. User-Facing Behavior

Accepted examples:

- `map(x::x+1, nil).` => `nil`
- `map(x::x+1, (1,2,3)).` => `2:3:4:nil`
- `inc(x):=x+1; map(inc, (1,2,3)).` => `2:3:4:nil`
- `map(x::x, ("a","b")).` => `"a":"b":nil`
- `map(x::not x, (true,false,true)).` => `false:true:false:nil`
- `map(hd, ((1,2),(3,4))).` => `1:3:nil`
- `map(tl, ((1,2),(3,4))).` => `(2:nil):(4:nil):nil`
- `map(size, ((1,2),(3,4,5))).` => `2:3:nil`
- `map(append(0:nil), ((1,2),(3,4))).` => `(0:1:2:nil):(0:3:4:nil):nil`
- `map(map(x::x+1), ((1,2),(3,4))).` => `(2:3:nil):(4:5:nil):nil`
- `map(append, ((1,2),(3,4))).` => `<function>:<function>:nil`
- `m:=map(x::x+1); m((1,2)).` => `2:3:nil`

Error examples:

- `map(1, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `map(1, nil).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `map(x::x+1, 1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `map(x::x+1, (true,2)).` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `map(hd, (nil,(1,2))).` => `ENACT_ERR_LIST_EMPTY`
- `map(size, (1,2)).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `map(x::x+1, (1,2), 1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `map(x::x, (1/0,2)).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `map(x::x+1, (1,2))+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 6. Semantic Requirements

`map callable list` shall:

1. require exactly two arguments
2. require the first argument to be a callable value
3. require the second argument to be a list
4. apply the callable to each list element in order
5. collect each returned value into a new list
6. preserve the input list

`map` over `nil` returns `nil`, but still validates that the first argument is callable.

If applying the callable to any element fails, `map` fails immediately and returns that diagnostic.

If the callable returns a function or builtin partial value, the returned list stores that function value normally.

## 7. Callable Apply Helper Requirements

The evaluator shall expose a C helper that applies an already-evaluated callable:

```c
int enact_eval_apply_callable(
    const EnactValue *callee,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

The helper shall support:

- `ENACT_VALUE_FUNCTION`
- `ENACT_VALUE_BUILTIN`
- `ENACT_VALUE_BUILTIN_PARTIAL`

The helper shall:

- treat `arguments` as borrowed input
- not free `callee` or `arguments`
- return an owned `out` value on success
- preserve existing exact, under-applied, and over-applied arity behavior
- reject non-callable values with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`

AST call evaluation shall still validate impossible arity before evaluating call arguments.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- map over nil
- lambda over integer list
- named function over integer list
- identity over string list
- boolean transformation
- builtin `hd` over nested lists
- builtin `tl` over nested lists
- builtin `size` over nested lists
- builtin partial `append(prefix)` over nested lists
- nested `map` partial over nested lists
- bare `append` producing partial functions
- assigned map partial
- higher-order passing of a map partial
- closure capture through mapped function
- under-applied `map` printing `<function>`

## 9. Robustness Requirements

The regression suite shall include:

- non-callable mapper on non-empty list
- non-callable mapper on nil
- non-list second argument
- mapped callable type error
- mapped callable list-empty error
- mapped builtin type error
- map over-application does not evaluate impossible extra arguments
- map over-application with nil list does not evaluate impossible extra arguments
- list argument evaluation failure
- mapped result used as an integer
- mapped result used as a boolean
- mapped result compared with a non-list

## 10. Acceptance Criteria

This slice is accepted when:

- `map` is installed in the default environment
- `map` works with user functions, builtins, and builtin partials
- `map` can itself be partially applied
- callable application logic is shared through a reusable evaluator helper
- existing AST call arity timing remains unchanged
- previous Slice 001 through Slice 017 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
