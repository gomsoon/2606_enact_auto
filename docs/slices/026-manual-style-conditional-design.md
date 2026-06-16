# Slice 026: Manual-Style Conditional Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/026-manual-style-conditional-requirements.md](/home/tprover/2606_enact_auto/docs/slices/026-manual-style-conditional-requirements.md)

## 1. Overview

This slice adds the manual conditional surface form while keeping the existing evaluator unchanged.

The project now accepts both:

```text
condition then true_expr else false_expr
true_expr if condition else false_expr
```

Both lower to the existing `AST_CONDITIONAL` representation.

## 2. Lexer

Add an exact reserved-word rule before the identifier fallback:

```c
"then" { return enact_emit_simple_token(TOK_THEN, 1); }
```

The emitted token sets `expect_operand` because a branch expression must follow.

Because flex chooses the longest match, identifiers such as `thenish` and `thenValue` still match the identifier rule rather than the shorter reserved word.

## 3. Token Dumping

Add `TOK_THEN` to `scan.c` token-name mapping:

```c
case TOK_THEN:
    return "TOK_THEN";
```

This keeps token regression tests precise and makes future parser debugging easier.

## 4. Parser

Add the token:

```bison
%token TOK_THEN
```

Extend `conditional`:

```bison
conditional:
    logical_or
  | logical_or TOK_THEN conditional TOK_ELSE conditional
  | logical_or TOK_IF logical_or TOK_ELSE conditional
```

The `then` arm builds:

```c
enact_make_conditional($1, $3, $5)
```

where:

- `$1` is the condition
- `$3` is the true branch
- `$5` is the false branch

The existing project-style `if` arm remains unchanged:

```c
enact_make_conditional($3, $1, $5)
```

where:

- `$1` is the true branch
- `$3` is the condition
- `$5` is the false branch

## 5. Conflict Check

The grammar is checked with:

```text
bison -Wcounterexamples -d -o /tmp/enact.tab.c src/enact.y
```

The expected result is no warnings and no counterexamples.

The use of `conditional` for both branches keeps nested manual conditionals right-associative in the false branch and also allows a nested conditional in the true branch:

```text
true then false then 1 else 2 else 3
```

evaluates as:

```text
true then (false then 1 else 2) else 3
```

## 6. Evaluator

No evaluator changes are required.

The existing conditional evaluator already:

- evaluates the condition first
- requires `ENACT_VALUE_BOOL`
- evaluates only the selected branch
- returns the selected branch value

This means manual-style conditionals inherit existing branch laziness and result polymorphism.

## 7. AST

No AST changes are required.

The existing conditional payload already stores:

```c
condition
if_true
if_false
```

Manual and project-style conditionals differ only in parser lowering.

## 8. Tests

Functional tests cover:

- tokenization of `then`
- reserved-word boundaries
- true and false branch selection
- boolean, equality, and relational conditions
- lazy branch selection
- nested manual conditionals
- manual examples such as factorial, `nfib`, and reverse
- lambdas, named functions, `fix`, `where`, sequence branches, and higher-order builtins
- coexistence with existing project-style `if`

Robustness tests cover:

- malformed `then` syntax
- non-boolean conditions
- condition evaluation failure
- selected branch failures
- use of the conditional result as the wrong runtime kind
- missing final dot

## 9. Review Checklist

This design is ready when:

- `then` is reserved but longer identifiers are not
- `TOK_THEN` appears in token dumps
- bison reports no conflicts
- existing `if` conditional tests still pass
- manual-style branch laziness is covered
- no evaluator duplication is introduced
