# Slice 012: Whitespace Function Application Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/012-whitespace-function-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/012-whitespace-function-application-requirements.md)

Prerequisite design: [docs/slices/011-currying-partial-application-design.md](/home/tprover/2606_enact_auto/docs/slices/011-currying-partial-application-design.md)

## 1. Design Objective

This document defines whitespace function application as a parser-only extension over the existing `AST_CALL` node.

No new evaluator branch or runtime value kind is needed.

## 2. Design Decisions Summary

- `f x` builds an `AST_CALL` with one argument.
- `f x y` is parsed left-associatively as `(f x) y`.
- Multi-argument behavior comes from Slice 011 partial application.
- `f (x+1)` continues to use the existing parenthesized call path.
- `f -1` is not introduced as special lexical behavior in this slice.
- Whitespace-style function definition lowers through the same function-literal assignment path as `f(x):=...`.

## 3. Parser Design

Add an application continuation to the existing call grammar:

```text
call ::= call "(" argument_list ")"
       | call application_argument
       | primary
```

`application_argument` intentionally excludes a bare `(` start to avoid ambiguity with the existing parenthesized call rule.

The supported argument starts are:

- integer literals
- booleans
- string literals
- identifiers

Compound arguments use parenthesized call syntax:

```text
f (x+1)
```

## 4. AST Design

Whitespace application reuses:

```c
AST_CALL
```

Each whitespace argument creates a one-element `EnactAstList`.

Examples:

```text
inc 4
```

becomes:

```text
AST_CALL(callee=inc, args=[4])
```

```text
add 1 2
```

becomes:

```text
AST_CALL(
  callee=AST_CALL(callee=add, args=[1]),
  args=[2])
```

The evaluator applies the outer call by first evaluating the inner partial call.

## 5. Function Definition LHS Design

Existing parenthesized definitions use:

```text
f(x,y):=body
```

and lower an `AST_CALL` left-hand side to:

```text
f := function_literal(params=[x,y], body=body)
```

Whitespace definitions produce nested call ASTs:

```text
f x y:=body
```

The assignment lowering step must therefore flatten a left-associated call chain when:

- the root callee is a bare identifier
- every collected argument is a bare identifier
- parameter names are unique

The same flattening also accepts harmless mixed forms such as:

```text
f(x) y:=body
```

because the AST shape has the same identifier-rooted call-chain structure.

## 6. Precedence Design

The call layer remains below unary and above multiplicative:

```text
unary ::= "-" unary
        | call
```

This preserves application precedence above arithmetic:

```text
add 1 2 + 3
```

as:

```text
((add 1) 2) + 3
```

## 7. Error Timing

Whitespace application uses existing evaluator timing.

`one 1 2` parses as:

```text
(one 1) 2
```

If `one 1` returns a non-function value, the outer call fails with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

Parenthesized over-application still fails with `ENACT_ERR_ARITY_MISMATCH`:

```text
one(1,2)
```

## 8. Test Design

Integration tests should cover:

- whitespace calls on named functions
- whitespace calls on lambda values
- curried multi-argument application
- higher-order calls
- whitespace-style function definitions
- precedence against arithmetic
- compound arguments through parentheses
- malformed function-definition left-hand sides
- type errors from non-function application

Unit tests do not need new evaluator coverage because the runtime still sees `AST_CALL`.

## 9. Review Checklist

This design is ready for implementation if:

- Bison introduces no parser conflicts
- `f(x)` remains a parenthesized call
- `f x` lowers to the same evaluator path as `f(x)`
- assignment LHS flattening still rejects non-identifier parameters
- existing parenthesized function definitions keep working
