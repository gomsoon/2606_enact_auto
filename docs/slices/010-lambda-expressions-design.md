# Slice 010: Lambda Expressions with `::` Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/010-lambda-expressions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/010-lambda-expressions-requirements.md)

Prerequisite design: [docs/slices/009-multi-argument-functions-design.md](/home/tprover/2606_enact_auto/docs/slices/009-multi-argument-functions-design.md)

## 1. Design Objective

This document defines anonymous function syntax as a thin parser layer over the existing function literal AST and runtime closure value.

No new runtime value kind is needed.

## 2. Design Decisions Summary

- `x::body` is a single-parameter lambda.
- `(x,y)::body` is a multi-parameter lambda.
- `(x)::body` is rejected to avoid ambiguity with grouped expressions.
- `()::body` is rejected.
- Duplicate lambda parameters are rejected.
- Lambda bodies parse as `assignment`.
- A lambda evaluates to the same function value used by named functions.
- Recursive self-binding is deferred.

## 3. Lexer Design

Add:

```c
TOK_LAMBDA
```

The lexer rule for `::` must appear before other colon-prefixed tokens. `TOK_LAMBDA` sets operand expectation to true because an expression body follows it.

## 4. Parser Design

Add a lambda layer between assignment and conditional:

```text
assignment ::= call ":=" assignment
             | lambda

lambda     ::= lambda_head "::" assignment
             | conditional

lambda_head ::= identifier
              | "(" parameter_list ")"

parameter_list ::= identifier "," identifier
                 | parameter_list "," identifier
```

The lambda action constructs:

```text
AST_FUNCTION_LITERAL(params=[...], body=...)
```

This reuses Slice 009 function values exactly.

## 5. Precedence and Body Shape

The body is an `assignment`, not a full `sequence`.

Therefore:

```text
x::x+1; 2
```

is parsed as:

```text
(x::x+1); 2
```

Sequence bodies require parentheses:

```text
x::(y:=x+1; y)
```

The body may still contain conditionals, `where`, assignments, calls, and nested lambdas.

## 6. Parameter Validation

Bare lambda:

```text
x::x
```

creates a one-name parameter list.

Parenthesized lambda heads accept only bare identifiers:

```text
(x,y)::x+y
```

Rejected forms include:

```text
()::1
(x)::x
(x,)::x
(,x)::x
(x,x)::x
(x,1)::x
((x))::x
```

## 7. Evaluation Design

No evaluator branch is added for lambdas because the parser emits `AST_FUNCTION_LITERAL`.

Existing `AST_FUNCTION_LITERAL` evaluation:

1. clones the current environment
2. clones the body AST
3. clones the parameter list
4. returns `ENACT_VALUE_FUNCTION`

This gives lambdas the same static binding behavior as named functions.

## 8. Closure Examples

Static capture:

```text
x:=10; f:=y::x+y; x:=20; f(1).
```

returns `11`.

Returned lambda:

```text
make:=a::(b,c)::a+b+c; s:=make(1); s(2,3).
```

returns `6`.

Higher-order use:

```text
apply:=(f,x)::f(x); apply(x::x+1,3).
```

returns `4`.

## 9. Test Design

Integration tests should cover:

- token output for `::`
- bare and parenthesized lambda heads
- one- and multi-argument lambda calls
- assigned lambdas
- immediate lambda calls
- nested returned lambdas
- lambdas passed as call arguments
- static capture
- malformed lambda heads
- duplicate parameters
- arity mismatch
- recursive assignment-bound lambda failure

Unit tests do not need a new evaluator branch, but existing direct `AST_FUNCTION_LITERAL` tests continue to cover runtime closure evaluation.

## 10. Review Checklist

This design is ready for implementation if:

- Bison introduces no parser conflicts
- lambda syntax does not loosen assignment left-hand-side validation
- `::` does not interfere with `:=`
- all parser-owned parameter lists are freed on parse failure
