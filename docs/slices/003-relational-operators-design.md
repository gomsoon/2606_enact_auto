# Slice 003: Relational Operators Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/003-relational-operators-requirements.md](/home/tprover/2606_enact_auto/docs/slices/003-relational-operators-requirements.md)

Prerequisite design: [docs/slices/002-comparison-boolean-conditional-design.md](/home/tprover/2606_enact_auto/docs/slices/002-comparison-boolean-conditional-design.md)

## 1. Design Objective

This document defines the implementation design for completing primitive relational operators:

- `!=`
- `<`
- `>`
- `<=`
- `>=`

The design extends the existing Slice 002 comparison layer without introducing identifiers, environments, assignment, or richer runtime values.

## 2. Design Decisions Summary

The following decisions are fixed for Slice 003:

- `!=` is inequality and is defined as the inverse of same-kind equality.
- `!=` supports integers and booleans.
- Cross-kind `!=`, such as `true!=1.`, is a runtime type error.
- `<`, `>`, `<=`, and `>=` are integer-only ordering operators.
- Boolean ordering is not defined.
- Relational operators share the same precedence as `==`.
- Comparison remains non-associative by grammar shape.
- Chained forms such as `1<2<3.` remain syntax errors.
- Historical bare `=` remains rejected.

## 3. Lexer Design

The lexer should add tokens:

- `TOK_NEQ`
- `TOK_LT`
- `TOK_GT`
- `TOK_LTE`
- `TOK_GTE`

Rules must match two-character operators before one-character operators:

```text
"!=" => TOK_NEQ
"<=" => TOK_LTE
">=" => TOK_GTE
"<"  => TOK_LT
">"  => TOK_GT
```

Each token should set `expect_operand = true`.

## 4. Parser Design

The current `equality` nonterminal should be renamed conceptually to `comparison`.

Recommended grammar:

```text
logical_not        ::= TOK_NOT logical_not
                     | comparison

comparison         ::= additive
                     | additive TOK_EQEQ additive
                     | additive TOK_NEQ additive
                     | additive TOK_LT additive
                     | additive TOK_GT additive
                     | additive TOK_LTE additive
                     | additive TOK_GTE additive
```

This preserves non-associativity because `comparison` is not recursive.

## 5. AST Design

Add AST node kinds:

- `AST_NEQ`
- `AST_LT`
- `AST_GT`
- `AST_LTE`
- `AST_GTE`

All are binary nodes using the existing binary AST shape.

No new AST constructor is required.

## 6. Evaluation Design

### 6.1 Inequality

`AST_NEQ` should use the same type discipline as `AST_EQ`:

1. evaluate left and right operands
2. fail with `ENACT_ERR_TYPE_EQUALITY_MISMATCH` if runtime kinds differ
3. compare integer payloads for integers
4. compare boolean payloads for booleans
5. return the negated equality result as `ENACT_VALUE_BOOL`

### 6.2 Integer Ordering

`AST_LT`, `AST_GT`, `AST_LTE`, and `AST_GTE` should:

1. evaluate left and right operands
2. require both operands to be `ENACT_VALUE_INT`
3. fail with `ENACT_ERR_TYPE_EXPECTED_INT` otherwise
4. compare the integer payloads
5. return `ENACT_VALUE_BOOL`

### 6.3 Precedence Interaction

The existing evaluator naturally evaluates AST shape after parsing, so no evaluator-level precedence changes are required.

Regression tests should confirm:

- arithmetic operands bind before relational operators
- unary `not` binds after relational operators
- conditional conditions can use relational operators

## 7. Diagnostics

No new diagnostic code is required for this slice.

Use existing codes:

- `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EQUALITY_MISMATCH`
- `ENACT_ERR_LEX_BARE_EQUALS`

This avoids splitting primitive type errors too early.

## 8. Test Design

Integration tests should cover:

- token output for all new relational operators
- integer ordering truth tables
- integer boundary comparisons
- boolean inequality
- cross-kind inequality type error
- bool ordering type error
- malformed operator placement
- chained comparison rejection
- precedence with arithmetic, `not`, and conditional expressions

Unit tests should add focused evaluator coverage for:

- same-kind inequality
- integer ordering
- bool ordering rejection

## 9. Review Checklist

This design is ready for implementation if:

- lexer ordering avoids splitting `<=`, `>=`, and `!=`
- parser comparison nonterminal remains non-recursive
- `!=` and `==` share type behavior except for result inversion
- ordering operators reject non-integer operands
- existing Slice 002 short-circuit behavior is untouched
