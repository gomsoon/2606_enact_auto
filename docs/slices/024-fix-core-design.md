# Slice 024: Fix Core Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/024-fix-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/024-fix-core-requirements.md)

Prerequisite design: [docs/slices/023-list-compatibility-design.md](/home/tprover/2606_enact_auto/docs/slices/023-list-compatibility-design.md)

## 1. Design Summary

`fix` is implemented as a low-precedence infix expression:

```text
(f,g) fix (f(x):=...; g(x):=...)
```

The parser first parses the left side as an ordinary expression, then the parser action validates that it is either an identifier or a tuple-like list of identifiers. This avoids grammar conflicts with tuple-like list syntax and lambda parameter lists.

## 2. Lexer Design

Add:

```flex
"fix" { return enact_emit_simple_token(TOK_FIX, 1); }
```

`fixer` and other longer identifiers remain ordinary identifiers because the lexer chooses the longest match.

`scan.c` maps `TOK_FIX` to its token dump name.

## 3. Parser Design

Add `AST_FIX`:

```c
struct {
    EnactNameList *names;
    EnactAst *body;
} fix_expr;
```

Add constructor:

```c
EnactAst *enact_ast_new_fix(EnactNameList *names, EnactAst *body);
```

Add grammar:

```bison
fix_expr:
    assignment TOK_FIX assignment
  | assignment
```

`sequence` now uses `fix_expr` as its item type:

```bison
sequence:
    sequence TOK_SEMI fix_expr
  | fix_expr
```

The left-hand AST is converted to a fixed-name list by accepting:

- `AST_IDENTIFIER`
- `AST_GROUP` around an accepted shape
- tuple-like list lowering made of `AST_CONS` cells whose heads are identifiers and whose tail is `AST_NIL`

Any other left-hand form fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

## 4. AST Ownership

`AST_FIX` owns:

- an `EnactNameList`
- a body AST

Clone and free support mirror existing `AST_FUNCTION_LITERAL` and `AST_WHERE` ownership patterns.

## 5. Evaluation Design

`enact_eval_fix` evaluates structurally rather than by ordinary assignment evaluation.

First it unwraps grouping around the body and flattens `AST_SEQUENCE` nodes. Every leaf must be:

```text
AST_ASSIGN(name, AST_FUNCTION_LITERAL(...))
```

Then it validates:

- each assignment name appears in the fixed-name list
- no fixed assignment appears more than once
- every fixed name appears exactly once
- every fixed RHS is a syntactic function literal

Non-function RHS values fail with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`. Malformed fixed definition shape fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

## 6. Function Construction

Each fixed assignment creates a recursive function with:

```c
enact_function_new_recursive(params, body, env, fixed_name)
```

This preserves the Slice 022 self-binding rule: the function binds its own name at call time.

After all fixed functions are created, each function's captured environment is extended with the peer fixed function values:

```c
enact_function_define_capture(function, peer_name, peer_value)
```

Self is not installed as a captured peer because recursive self-binding already handles it without an immediate self-cycle.

Finally, all fixed values are assigned to the current environment. The expression result is the last fixed value.

## 7. Static Binding

Ordinary free variables still come from the environment at the time the `fix` expression is evaluated:

```text
step:=2;
count fix (count(n):=0 if n==0 else step+count(n-1));
step:=10;
count(3).
```

returns `6`.

Fixed peer functions are also preserved as captured values, so saving one fixed function before rebinding the original names keeps the old fixed group behavior.

## 8. Limitations

This core slice supports only syntactic function definitions on the RHS. For example:

```text
f fix (f:=make_recursive_candidate)
```

is out of scope even if the RHS would evaluate to a function at runtime.

General fixed-point values, lazy tying of arbitrary values, and recursive local `where` bindings can be considered later.

## 9. Test Strategy

Regression tests cover:

- tokenization
- single fixed functions
- mutually recursive fixed functions
- named function and lambda-assignment RHS forms
- currying and partial application
- higher-order calls through `map` and `apply`
- static capture and rebinding stability
- malformed fixed sets and body shapes
- type, arity, list, and ordinary non-recursive lambda failures

Unit tests cover:

- `AST_FIX` clone/free/evaluation path
- direct captured-environment extension on functions
