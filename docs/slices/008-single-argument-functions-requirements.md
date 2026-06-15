# Slice 008: Single-Argument Named Functions and Parenthesized Calls Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/007-local-definitions-where-requirements.md](/home/tprover/2606_enact_auto/docs/slices/007-local-definitions-where-requirements.md)

## 1. Slice Goal

This slice introduces the first function mechanism:

```text
f(x):=x+1; f(99).
```

The goal is intentionally small: named functions with exactly one argument, called with explicit parentheses.

## 2. Source Basis

The PRD records:

- function definitions using static binding
- function calls
- lexical scoping
- function work should arrive incrementally and with regression tests

Slice 007 added local environment cloning through `where`; this slice reuses that environment foundation for function argument binding.

## 3. In Scope

This slice includes:

- parser support for named single-argument function definitions:

```text
name(parameter):=body
```

- parser support for parenthesized single-argument calls:

```text
callee(argument)
```

- AST support for function literals and calls
- runtime function values
- static environment capture when the function is defined
- eager argument evaluation when the function is called
- local argument binding while evaluating the function body
- function values that can be assigned, passed, returned by evaluation, and printed as `<function>`
- tests for integer, boolean, string, closure, sequencing, higher-order, and error behavior

## 4. Out Of Scope

This slice explicitly excludes:

- multiple function arguments
- zero-argument functions
- comma-separated argument lists
- unparenthesized function application
- anonymous functions
- currying
- recursion and `fix`
- mutual recursion
- local function definition lists inside `where`
- overloaded or method-style calls

Recursion is intentionally deferred because the static capture point in this slice happens before the new function name is defined.

## 5. User-Facing Behavior

Accepted examples:

- `f(x):=x+1; f(99).` => `100`
- `double(x):=x*2; double(3)+1.` => `7`
- `id(x):=x; id("hi").` => `"hi"`
- `not_fn(x):=not x; not_fn(false).` => `true`
- `x:=10; f(y):=x+y; f(1).` => `11`
- `x:=10; f(y):=x+y; x:=20; f(1).` => `11`
- `f(x):=(y:=x+1; y); f(2).` => `3`
- `f(x):=x+1.` => `<function>`
- `f(x):=x; y:=f; y(4).` => `4`
- `apply(f):=f(3); inc(x):=x+1; apply(inc).` => `4`
- `make_adder(x):=add(y):=x+y; add2:=make_adder(2); add2(5).` => `7`

The function body observes the environment captured at definition time, plus the current call argument bound to the parameter name.

## 6. Syntax Requirements

Function definitions shall parse as a specialized assignment form:

```text
assignment ::= identifier "(" identifier ")" ":=" assignment
             | identifier ":=" assignment
             | conditional
```

This means a function definition creates or updates the binding for the function name.

Calls shall parse as a postfix operation above primary expressions and below unary minus:

```text
call  ::= call "(" assignment ")"
        | primary

unary ::= "-" unary
        | call
```

Only one argument expression is accepted. Empty argument lists and comma-separated lists are syntax errors.

## 7. Semantic Requirements

Function definition shall:

1. create a function value containing the parameter name, body AST, and a clone of the current environment
2. bind that function value to the function name
3. return the function value

Function call shall:

1. evaluate the callee expression
2. require the callee to be a function value
3. evaluate the argument expression eagerly in the caller environment
4. clone the function's captured environment
5. define the parameter name in that cloned environment
6. evaluate the function body in the cloned environment
7. free temporary values and the cloned local environment
8. return the body result

Assignments inside a function body mutate only the call-local environment.

## 8. Error Requirements

Add one diagnostic code:

- `ENACT_ERR_TYPE_EXPECTED_FUNCTION`

This diagnostic is used when a non-function value is called:

```text
1(2).
```

Malformed function definitions or calls continue to use existing parser diagnostics.

Recursive calls in this slice fail through `ENACT_ERR_NAME_UNBOUND` when the captured environment does not contain the function's own name.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- minimal integer function call
- function call inside arithmetic
- string identity function
- boolean function
- definition-time environment capture
- capture stability after outer rebinding
- sequence inside a function body
- local `where` inside a function body
- function definition result printing
- function assignment and indirect call
- higher-order single-argument function call
- returned closure call

## 10. Robustness Requirements

The regression suite shall include malformed or risky cases such as:

- unbound function call
- calling an integer
- calling a boolean
- argument type error inside the body
- empty call argument list
- empty function parameter list
- non-identifier function parameter
- parenthesized assignment or function-definition left-hand side
- missing function body
- missing closing parenthesis
- recursive function call without recursive binding support
- function body assignment does not leak to the caller

## 11. Acceptance Criteria

This slice is accepted when:

- named single-argument function definitions parse and evaluate
- parenthesized single-argument calls parse and evaluate
- functions capture their definition environment statically
- function argument bindings are local to the call
- non-function calls report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- previous slice tests remain green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
