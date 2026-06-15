# Slice 007: Local Definitions with where Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/007-local-definitions-where-requirements.md](/home/tprover/2606_enact_auto/docs/slices/007-local-definitions-where-requirements.md)

Prerequisite design: [docs/slices/006-strings-mod-design.md](/home/tprover/2606_enact_auto/docs/slices/006-strings-mod-design.md)

## 1. Design Objective

This document defines the smallest scoped local-definition mechanism needed before function definition and function argument binding.

The slice intentionally supports one local binding per `where` expression.

## 2. Design Decisions Summary

- Surface form is `body where name:=value`.
- The binding left-hand side must be a bare identifier.
- The binding value is evaluated in a clone of the current environment.
- The binding is then defined in that cloned environment.
- The body is evaluated in the cloned environment.
- The outer environment is not mutated.
- The binding is not recursive in this slice.
- Multiple local definition lists are deferred.

## 3. Lexer Design

Add token:

```c
TOK_WHERE
```

The lexer rule for `where` must appear before the identifier rule.

The token sets `expect_operand = true` so a following `-` is classified as unary.

## 4. Parser Design

Insert a `where_expr` layer between `logical_and` and `logical_not`:

```text
logical_and ::= logical_and "and" where_expr
              | where_expr

where_expr  ::= logical_not
              | logical_not "where" identifier ":=" logical_not
```

This preserves the PRD precedence relationship:

- comparison is tighter than `where`
- `where` is tighter than `and`

The right-hand side is intentionally limited to `logical_not` for this slice. Larger expressions can still be used with parentheses:

```text
x where x:=(1 if true else 2)
```

This keeps the grammar conflict-free while semicolon remains outside the `where` clause.

## 5. AST Design

Add node kind:

```c
AST_WHERE
```

Add payload:

```c
struct {
    EnactAst *body;
    char *name;
    EnactAst *value;
} where_expr;
```

Add constructor:

```c
EnactAst *enact_ast_new_where(EnactAst *body, char *name, EnactAst *value);
```

Destruction frees:

- body AST
- binding name
- binding value AST

## 6. Environment Design

Add helper:

```c
int enact_env_clone(EnactEnv *out, const EnactEnv *in);
```

The clone helper:

1. initializes `out`
2. deep-copies every binding from `in`
3. frees partial output and returns false on allocation failure

The current flat environment remains sufficient for Slice 007. Nested scope behavior is represented by cloning rather than by introducing parent pointers.

Parent-linked environments are likely better once functions and closures arrive, but cloning is simpler and safer for this slice.

## 7. Evaluation Design

`AST_WHERE` evaluation:

1. clone the current environment into `local`
2. evaluate `value` using `local`
3. define `name` in `local`
4. free the temporary binding value after `enact_env_define` copies it
5. evaluate `body` using `local`
6. free `local`
7. return the body result

If cloning or definition fails, report `ENACT_ERR_OUT_OF_MEMORY`.

If binding value evaluation fails, return that diagnostic and do not evaluate the body.

## 8. Scoping Examples

Local shadowing:

```text
x:=10; (x where x:=1); x.
```

returns `10`.

Nested local definitions can be expressed by nesting:

```text
x + (y where y:=2) where x:=1.
```

returns `3`.

Semicolon remains an outer sequence separator:

```text
(x where x:=1); x.
```

fails because the second `x` is outside the local scope.

## 9. Test Design

Integration tests should cover:

- token output for `where`
- `wherever` as an identifier
- integer, boolean, and string local bindings
- expression-valued bindings
- shadowing and non-leakage
- nested `where`
- malformed where forms
- unbound names in the body and binding value
- type-invalid body use

Unit tests should cover:

- environment cloning
- direct AST `where` evaluation
- clone isolation after redefining a binding in the clone

## 10. Review Checklist

This design is ready for implementation if:

- no parser conflict is introduced
- semicolon behavior is explicit
- environment clones deep-copy string values
- returned values do not point into freed local environments
- function-related syntax remains deferred
