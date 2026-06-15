# Slice 009: Multi-Argument Named Functions and Calls Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/008-single-argument-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/008-single-argument-functions-requirements.md)

## 1. Slice Goal

This slice generalizes Slice 008 functions from exactly one argument to one or more arguments:

```text
add(x,y):=x+y; add(2,3).
```

The goal is to support comma-separated function parameter lists and comma-separated call argument lists without introducing tuples or list literals yet.

## 2. Source Basis

The PRD records:

- multi-argument function definitions such as `g(x,y):=x+y`
- higher-order functions
- static binding of free variables at function definition time
- tuple-like list construction using commas, deferred from this slice

Slice 008 already introduced function values, closure capture, and parenthesized calls. This slice preserves that execution model while widening arity.

## 3. In Scope

This slice includes:

- lexer support for comma tokenization
- parser support for one-or-more function parameters:

```text
name(parameter1,parameter2,...):=body
```

- parser support for one-or-more call arguments:

```text
callee(argument1,argument2,...)
```

- AST support for argument lists
- function values containing parameter-name lists
- eager left-to-right argument evaluation
- arity checking before argument evaluation
- parameter binding in order
- duplicate parameter rejection
- tests for multi-argument primitive values, closures, higher-order calls, returned closures, and side-effecting arguments

## 4. Out Of Scope

This slice explicitly excludes:

- zero-argument functions
- empty call argument lists
- tuple/list syntax using comma outside function call syntax
- destructuring parameters
- variadic functions
- default arguments
- named arguments
- currying and partial application
- recursive binding and `fix`
- whitespace function application

## 5. User-Facing Behavior

Accepted examples:

- `add(x,y):=x+y; add(2,3).` => `5`
- `mix(a,b,c):=a*b+c; mix(2,3,4).` => `10`
- `first(a,b):=a; first("left","right").` => `"left"`
- `both(a,b):=a and b; both(true,false).` => `false`
- `x:=10; addx(a,b):=x+a+b; x:=20; addx(1,2).` => `13`
- `apply2(f,x,y):=f(x,y); add(a,b):=a+b; apply2(add,2,3).` => `5`
- `make(a):=sum(b,c):=a+b+c; s:=make(1); s(2,3).` => `6`

Single-argument functions remain valid:

```text
inc(x):=x+1; inc(4).
```

returns `5`.

## 6. Syntax Requirements

Add comma:

```text
"," => TOK_COMMA
```

Calls shall parse one-or-more assignment expressions as arguments:

```text
argument_list ::= assignment
                | argument_list "," assignment

call ::= call "(" argument_list ")"
       | primary
```

Function definitions continue to be recognized by lowering a call-shaped assignment left-hand side:

```text
add(x,y):=x+y
```

into:

```text
AST_ASSIGN(name="add", value=AST_FUNCTION_LITERAL(params=["x","y"], body=x+y))
```

All parameter expressions in a function-definition left-hand side must be bare identifiers. Parenthesized identifiers are rejected.

## 7. Semantic Requirements

Function definition shall:

1. create a function value containing the parameter-name list, body AST, and a clone of the current environment
2. bind that function value to the function name
3. return the function value

Function call shall:

1. evaluate the callee expression
2. require the callee to be a function value
3. compare call argument count with function parameter count
4. fail with `ENACT_ERR_ARITY_MISMATCH` if the counts differ
5. evaluate each argument expression left-to-right in the caller environment
6. clone the function's captured environment
7. bind each parameter name to its corresponding evaluated argument in order
8. evaluate the function body in the cloned environment
9. free temporary values and the cloned local environment
10. return the body result

Arity checking happens before argument evaluation.

## 8. Error Requirements

Add one diagnostic code:

- `ENACT_ERR_ARITY_MISMATCH`

This diagnostic is used when a function receives the wrong number of arguments.

Malformed comma placement uses existing parser diagnostics:

- leading comma
- trailing comma
- empty argument list
- empty parameter list

Duplicate parameters shall fail with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- two-argument integer function
- three-argument integer function
- string argument selection
- boolean argument operation
- single-argument compatibility
- definition-time capture with multiple parameters
- higher-order multi-argument function
- returned multi-argument closure
- left-to-right side-effecting argument evaluation
- call-local parameter assignment isolation

## 10. Robustness Requirements

The regression suite shall include:

- too few arguments
- too many arguments
- multi-argument call to a single-argument function
- empty argument list
- empty parameter list
- leading comma
- trailing comma
- duplicate parameter names
- non-identifier parameter expression
- parenthesized parameter identifier
- non-function multi-argument call
- argument type error inside the body
- eager argument evaluation failure
- recursive function call without recursive binding support

## 11. Acceptance Criteria

This slice is accepted when:

- comma tokenizes inside function syntax
- one-or-more parameter function definitions parse and evaluate
- one-or-more argument calls parse and evaluate
- single-argument functions from Slice 008 still work
- arity mismatches report `ENACT_ERR_ARITY_MISMATCH`
- duplicate parameters are rejected
- previous slice tests remain green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
