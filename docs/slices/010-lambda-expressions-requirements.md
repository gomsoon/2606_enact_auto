# Slice 010: Lambda Expressions with `::` Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/009-multi-argument-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/009-multi-argument-functions-requirements.md)

## 1. Slice Goal

This slice introduces anonymous function expressions using `::`.

The goal is to make functions directly expressible as values without first binding a named function:

```text
inc:=x::x+1; inc(4).
```

## 2. Source Basis

The PRD records:

- functions are first-class values
- lambda expressions using `::`
- higher-order functions
- static binding of free variables at function definition time
- currying and recursive definitions remain future work

Slice 009 already provides multi-argument function values, closure capture, arity checking, and parenthesized calls.

## 3. In Scope

This slice includes:

- lexer support for `::`
- single-parameter lambda syntax:

```text
x::body
```

- parenthesized two-or-more parameter lambda syntax:

```text
(x,y)::body
```

- lambda expressions that evaluate to ordinary function values
- static environment capture when the lambda expression is evaluated
- duplicate parameter rejection
- tests for direct calls, assignment, closures, higher-order use, returned lambdas, strings, booleans, and malformed syntax

## 4. Out Of Scope

This slice explicitly excludes:

- zero-argument lambdas
- parenthesized single-parameter lambdas
- variadic lambdas
- destructuring parameters
- default arguments
- partial application
- whitespace application
- `fix`
- recursive self-binding
- tuple/list comma outside parameter lists

## 5. User-Facing Behavior

Accepted examples:

- `(x::x+1)(4).` => `5`
- `inc:=x::x+1; inc(4).` => `5`
- `add:=(x,y)::x+y; add(2,3).` => `5`
- `((x,y)::x*y)(3,4).` => `12`
- `id:=x::x; id("hi").` => `"hi"`
- `both:=(a,b)::a and b; both(true,false).` => `false`
- `x:=10; f:=y::x+y; x:=20; f(1).` => `11`
- `apply:=(f,x)::f(x); inc:=x::x+1; apply(inc,3).` => `4`
- `make:=a::(b,c)::a+b+c; s:=make(1); s(2,3).` => `6`
- `x::x+1.` => `<function>`

Lambda functions use the same call syntax and arity behavior as named functions.

## 6. Syntax Requirements

Add token:

```text
"::" => TOK_LAMBDA
```

Lambda syntax:

```text
lambda ::= lambda_head "::" assignment
         | conditional

lambda_head ::= identifier
              | "(" parameter_list ")"

parameter_list ::= identifier "," identifier
                 | parameter_list "," identifier
```

`assignment` shall use `lambda` as its non-assignment fallback:

```text
assignment ::= call ":=" assignment
             | lambda
```

The lambda body is an `assignment`, so a body sequence requires explicit parentheses:

```text
x::(y:=x+1; y)
```

## 7. Semantic Requirements

Lambda evaluation shall:

1. create a function value containing the parameter-name list, body AST, and a clone of the current environment
2. return the function value

The returned value is the same runtime function value category used by named functions.

## 8. Error Requirements

Existing diagnostic codes are sufficient:

- `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `ENACT_ERR_ARITY_MISMATCH`
- `ENACT_ERR_NAME_UNBOUND`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EXPECTED_BOOL`

Malformed lambda syntax shall fail with parser diagnostics.

Duplicate lambda parameter names shall fail with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

Recursive lambda use through assignment remains unsupported in this slice:

```text
f:=x::f(x); f(1).
```

fails with `ENACT_ERR_NAME_UNBOUND`.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- direct single-argument lambda call
- assigned single-argument lambda call
- assigned multi-argument lambda call
- immediate multi-argument lambda call
- string identity lambda
- boolean lambda
- static capture with outer rebinding
- higher-order lambda
- returned lambda closure
- body sequence through explicit parentheses
- bare lambda expression printing
- lambda as a call argument

## 10. Robustness Requirements

The regression suite shall include:

- missing lambda body
- leading `::`
- non-identifier lambda head
- empty parenthesized parameter list
- parenthesized single-parameter lambda head
- trailing comma in parameter list
- leading comma in parameter list
- duplicate parameter names
- non-identifier parameter
- parenthesized parameter identifier
- lambda arity mismatch
- eager argument evaluation failure
- recursive assignment-bound lambda failure

## 11. Acceptance Criteria

This slice is accepted when:

- `::` tokenizes as `TOK_LAMBDA`
- lambdas evaluate to function values
- lambdas capture definition-time environments
- single- and multi-argument lambdas can be called with existing call syntax
- duplicate lambda parameters are rejected
- previous slice tests remain green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
