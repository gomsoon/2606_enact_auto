# Slice 011: Currying and Partial Application Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/010-lambda-expressions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/010-lambda-expressions-requirements.md)

## 1. Slice Goal

This slice adds core partial application behavior for multi-argument functions.

The goal is to let a call with fewer arguments than a function's arity produce a new function value that captures the supplied prefix arguments:

```text
add:=(x,y)::x+y; inc:=add(1); inc(4).
```

## 2. Source Basis

The PRD records:

- functions are first-class values
- higher-order functions are required
- currying and partial application are required function features
- eager evaluation semantics are acceptable
- static binding of free variables at function definition time remains required

Slices 008-010 already provide named functions, multi-argument calls, lambda expressions, closure capture, and function values.

## 3. In Scope

This slice includes:

- partial application for parenthesized calls with at least one supplied argument
- prefix binding only
- returned function values for under-applied calls
- immediate completion of a partial call using existing parenthesized call syntax
- static capture of both original free variables and supplied prefix arguments
- eager evaluation of supplied prefix arguments
- over-application remaining an arity error
- tests for named functions, lambdas, higher-order use, strings, booleans, and malformed calls

## 4. Out Of Scope

This slice explicitly excludes:

- whitespace application
- implicit tuple/list arguments
- placeholders or non-prefix partial application
- zero-argument calls or zero-argument partials
- variadic functions
- automatic currying syntax rewrites
- recursive self-binding through partial application

## 5. User-Facing Behavior

Accepted examples:

- `add(x,y):=x+y; add(1)(4).` => `5`
- `add(x,y):=x+y; inc:=add(1); inc(4).` => `5`
- `add:=(x,y)::x+y; add(1)(4).` => `5`
- `tri:=(a,b,c)::a+b+c; tri(1)(2)(3).` => `6`
- `tri:=(a,b,c)::a+b+c; add1:=tri(1); add1(2,3).` => `6`
- `choose:=(a,b)::a; left:=choose("left"); left("right").` => `"left"`
- `both:=(a,b)::a and b; t:=both(true); t(false).` => `false`
- `x:=10; addx:=(a,b)::x+a+b; p:=addx(1); x:=20; p(2).` => `13`
- `apply:=(f,x)::f(x); add:=(a,b)::a+b; apply(add(2),3).` => `5`
- `add:=(x,y)::x+y; add(1).` => `<function>`

Error examples:

- `inc(x):=x+1; inc(1,2).` => `ENACT_ERR_ARITY_MISMATCH`
- `one(x):=x; one(1,1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `add(x,y):=x+y; add(true)(1).` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `ignore(a,b):=a; ignore(1/0).` => `ENACT_ERR_DIVIDE_BY_ZERO`

## 6. Semantic Requirements

For a function call with `argument_count == arity`:

1. evaluate each argument eagerly in the caller environment
2. clone the function's captured environment
3. bind all parameter names to the evaluated argument values
4. evaluate the function body in that local environment

For a function call with `argument_count < arity`:

1. evaluate each supplied argument eagerly in the caller environment
2. clone the function's captured environment
3. bind the supplied prefix parameter names to those evaluated argument values
4. create and return a new function value with:
   - the remaining parameter names
   - the same original body
   - the partially-bound environment from step 3

For a function call with `argument_count > arity`:

1. fail with `ENACT_ERR_ARITY_MISMATCH`
2. do not evaluate any call arguments

## 7. Error Requirements

Existing diagnostic codes are sufficient:

- `ENACT_ERR_ARITY_MISMATCH`
- `ENACT_ERR_DIVIDE_BY_ZERO`
- `ENACT_ERR_NAME_UNBOUND`
- `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EXPECTED_BOOL`

Under-application is no longer an arity error.

Over-application remains an arity error.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- named two-argument partial applied one argument at a time
- assigned partial function
- lambda partial function
- three-argument chained partial
- three-argument one-plus-two completion
- two-plus-one completion
- string value captured by partial
- boolean value captured by partial
- static capture with outer rebinding after partial creation
- higher-order function receiving a partial function
- bare under-applied call printing `<function>`
- partial of a returned function
- exact arity call remains unchanged

## 9. Robustness Requirements

The regression suite shall include:

- over-applied named function
- over-applied lambda function
- over-application does not evaluate extra failing arguments
- supplied prefix argument is evaluated eagerly
- type error is deferred until the function body is eventually evaluated when appropriate
- non-function call remains a type error
- empty call syntax remains rejected
- recursive self-binding remains unsupported

## 10. Acceptance Criteria

This slice is accepted when:

- under-applied calls return function values
- partial functions can be called to completion
- supplied arguments are captured statically
- over-application still fails with `ENACT_ERR_ARITY_MISMATCH`
- previous function, lambda, and closure tests remain green after expectation updates
- handwritten source coverage remains reported separately from generated parser/lexer coverage
