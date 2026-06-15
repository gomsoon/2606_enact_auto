# Slice 012: Whitespace Function Application Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/011-currying-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/011-currying-partial-application-requirements.md)

## 1. Slice Goal

This slice adds ENACT-style function application by juxtaposition:

```text
inc 4
add 1 2
apply inc 3
```

The goal is to make parenthesized calls and whitespace-applied calls equivalent at the expression level while reusing the existing call AST and currying behavior.

## 2. Source Basis

The PRD records:

- function application in both parenthesized and whitespace-applied forms
- function definitions such as `f x := x+1`
- application precedence above arithmetic operators
- currying and partial application
- static binding of free variables at function definition time

Slices 008-011 already provide function values, parenthesized calls, lambdas, and partial application.

## 3. In Scope

This slice includes:

- whitespace application with identifier, integer, boolean, and string arguments
- whitespace application chains, parsed left-associatively
- whitespace application combined with parenthesized call syntax
- single- and multi-argument whitespace-style function definitions
- whitespace application inside function and lambda bodies
- interaction with partial application
- regression tests for precedence, arity, type errors, strings, booleans, and closures

## 4. Out Of Scope

This slice explicitly excludes:

- tuple/list comma outside parenthesized function calls
- zero-argument whitespace calls
- whitespace-sensitive lexical distinctions
- automatic parsing of `f -1` as `f(-1)`
- method or attribute application
- list constructors and builtins
- `fix`

Negative arguments should use parenthesized call/group syntax in this slice:

```text
f(-1)
f (-1)
```

## 5. User-Facing Behavior

Accepted examples:

- `inc(x):=x+1; inc 4.` => `5`
- `add(x,y):=x+y; add 2 3.` => `5`
- `tri(a,b,c):=a+b+c; tri 1 2 3.` => `6`
- `inc:=x::x+1; inc 4.` => `5`
- `apply(f,x):=f x; inc(y):=y+1; apply inc 3.` => `4`
- `add x y:=x+y; add 2 3.` => `5`
- `x:=10; addx a b:=x+a+b; x:=20; addx 1 2.` => `13`
- `id(x):=x; id "hi".` => `"hi"`
- `both(a,b):=a and b; both true false.` => `false`
- `add(x,y):=x+y; add 1.` => `<function>`
- `add(x,y):=x+y; add (1+2) 3.` => `6`

Error examples:

- `1 2.` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `true 1.` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `inc(x):=x+1; inc true.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `one(x):=x; one 1 2.` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `f 1:=1.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `f x x:=x.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`

## 6. Syntax Requirements

Whitespace application shall be represented in the parser as a call continuation:

```text
call ::= call "(" argument_list ")"
       | call application_argument
       | primary

application_argument ::= integer
                       | boolean
                       | string
                       | identifier
```

The parser may implement `application_argument` with duplicated primary actions to avoid grammar ambiguity around `(`.

Parenthesized arguments remain supported through the existing parenthesized call syntax:

```text
f (x+1)
```

which parses as a one-argument call.

## 7. Semantic Requirements

Whitespace application shall emit the same `AST_CALL` node kind as parenthesized calls.

The evaluator behavior is therefore exactly the behavior from Slice 011:

- exact application evaluates the function body
- under-application returns a partial function
- applying a non-function value fails with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`

Whitespace application chains are left-associative:

```text
add 1 2
```

parses as:

```text
(add 1) 2
```

This relies on partial application for multi-argument functions.

## 8. Precedence Requirements

Application binds tighter than arithmetic, comparison, `where`, logical operators, conditionals, assignment, and sequencing.

Therefore:

```text
add 1 2 + 3
```

parses as:

```text
((add 1) 2) + 3
```

To pass a compound expression as a whitespace argument, use parentheses:

```text
f (x+1)
```

## 9. Function Definition Requirements

Whitespace-style function definitions shall be accepted when:

- the left-hand side call chain starts with a bare identifier
- every argument in the left-hand side is a bare identifier
- parameter names are unique

Examples:

```text
inc x:=x+1
add x y:=x+y
```

Malformed forms such as `f 1:=1` and `f x x:=x` shall be rejected.

## 10. Boundary Analysis Requirements

The regression suite shall include:

- single-argument named function whitespace call
- multi-argument named function whitespace call
- three-argument curried whitespace call
- lambda value whitespace call
- higher-order whitespace call
- parenthesized partial plus whitespace completion
- whitespace-style single-argument definition
- whitespace-style multi-argument definition
- static capture through whitespace-style definition
- string argument
- boolean arguments
- under-applied whitespace call returning `<function>`
- compound argument passed through parentheses

## 11. Robustness Requirements

The regression suite shall include:

- integer called as a function
- boolean called as a function
- function called with wrong argument type
- exact application followed by another whitespace argument
- eager partial argument failure
- non-identifier parameter in whitespace-style definition
- duplicate parameter in whitespace-style definition
- recursive self-binding remains unsupported

## 12. Acceptance Criteria

This slice is accepted when:

- whitespace calls evaluate through existing `AST_CALL`
- `add 1 2` works through partial application
- whitespace-style function definitions work for one and multiple parameters
- malformed whitespace-definition LHS forms are rejected
- previous parenthesized call tests remain green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
