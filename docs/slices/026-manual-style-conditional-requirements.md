# Slice 026: Manual-Style Conditional Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/025-list-set-operation-builtins-requirements.md](/home/tprover/2606_enact_auto/docs/slices/025-list-set-operation-builtins-requirements.md)

## 1. Slice Goal

This slice adds the manual-style conditional expression:

```text
condition then true_expr else false_expr
```

The existing project-default conditional form remains supported:

```text
true_expr if condition else false_expr
```

Both forms evaluate to the same AST shape and use the same lazy branch-selection behavior.

## 2. Source Basis

The ENACT manual Appendix 1 describes conditionals using `then` and `else`, and uses examples such as factorial, `nfib`, and recursive list processing in that style. The precedence table later lists `if` and `then` together below `or`, with `else` one level looser.

Earlier project slices deliberately started with `true_expr if condition else false_expr` as a small modernized core. This slice closes the compatibility gap by accepting the manual surface form as well.

## 3. In Scope

This slice includes:

- `then` as a reserved lexer keyword
- token dumping for `TOK_THEN`
- parser support for `condition then true_expr else false_expr`
- reuse of the existing conditional AST node
- no evaluator behavior change
- regression tests for manual examples, nested conditionals, branch laziness, functions, lambdas, `fix`, and higher-order list builtins

## 4. Out Of Scope

This slice explicitly excludes:

- changing the project-default `if` form
- historical equality `=`
- historical inequality `<>`
- `loop`
- lazy evaluation beyond ordinary conditional branch selection
- object/class semantics
- a general precedence-table rewrite

## 5. User-Facing Behavior

Accepted examples:

- `true then 1 else 2.` => `1`
- `false then 1 else 2.` => `2`
- `1==1 then 10 else 20.` => `10`
- `1==2 then 10 else 20.` => `20`
- `fact(n):=n==0 then 1 else n*fact(n-1); fact(5).` => `120`
- `nfib(n):=n<2 then 1 else nfib(n-1)+nfib(n-2)+1; nfib(5).` => `15`
- `false then 1 else true then 2 else 3.` => `2`
- `true then false then 1 else 2 else 3.` => `2`

The selected branch may have any runtime value kind:

- `true then "yes" else "no".` => `"yes"`
- `true then union((1,2),(2,3)) else nil.` => `1:2:3:nil`

Malformed or type-invalid examples:

- `then.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `true then 1.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `true then else 2.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `1 then 2 else 3.` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `"x" then 1 else 2.` => `ENACT_ERR_TYPE_EXPECTED_BOOL`

## 6. Lexical Requirements

The lexer shall recognize exact `then` as `TOK_THEN`.

Identifier-like words that merely contain `then`, such as `thenish` and `thenValue`, remain ordinary identifiers because the lexer uses longest-match behavior before exact reserved-word matches.

`then` shall set scanner state to expect an operand afterward, like other binary operators and conditional keywords.

## 7. Parser Requirements

Add the conceptual grammar arm:

```text
conditional ::= logical_or
              | logical_or "then" conditional "else" conditional
              | logical_or "if" logical_or "else" conditional
```

The `then` form constructs:

```text
AST_CONDITIONAL(condition=left, if_true=true_expr, if_false=false_expr)
```

The existing `if` form continues to construct:

```text
AST_CONDITIONAL(condition=condition_expr, if_true=true_expr, if_false=false_expr)
```

The true and false branches of the `then` form use `conditional` so nested conditionals can appear naturally in either branch.

## 8. Associativity And Precedence

The parser shall preserve these user-facing rules:

- `and` and `or` bind tighter than `then`
- the false branch is right-associative
- parenthesized conditionals can be used as a condition to another conditional

Therefore:

```text
false then 1 else true then 2 else 3
```

is parsed as:

```text
false then 1 else (true then 2 else 3)
```

and returns `2`.

## 9. Evaluation Semantics

No evaluator changes are needed. The existing `AST_CONDITIONAL` evaluator already:

1. evaluates the condition first
2. requires a boolean condition
3. evaluates only the selected branch
4. returns the selected branch value unchanged

This preserves lazy branch selection:

- `false then 1/0 else 2.` => `2`
- `true then 1 else 1/0.` => `1`

## 10. Boundary Analysis Requirements

The regression suite shall include:

- `then` tokenization
- identifier-like words containing `then`
- true and false branch selection
- equality and relational conditions
- boolean `and` and `or` in conditions
- lazy true branch
- lazy false branch
- nested false branch conditional
- nested true branch conditional
- parenthesized manual conditional as a condition
- manual-style factorial
- manual-style `nfib`
- manual-style recursive reverse
- variable-bound conditions
- lambda body using manual conditional
- `map`, `filter`, `all`, and `reduce` using manual conditional
- `where` in a condition
- sequence expressions inside selected branches
- fixed recursive functions using manual conditional
- mixed manual/project conditional branch
- list/set builtin branch result
- reserved-word boundary with `thenValue`

## 11. Robustness Requirements

The regression suite shall include:

- bare `then`
- missing `else`
- missing true branch
- missing condition
- missing false branch
- duplicate `else`
- malformed nested `then`
- incomplete mixed conditional
- non-boolean integer condition
- non-boolean string condition
- condition evaluation failure
- selected true branch failure
- selected false branch failure
- selected branch type failures
- manual conditional result used as a non-matching runtime kind
- missing final dot

## 12. Acceptance Criteria

This slice is accepted when:

- `then` tokenizes as `TOK_THEN`
- `thenish` and `thenValue` remain identifiers
- `condition then true_expr else false_expr` parses without bison conflicts
- existing `true_expr if condition else false_expr` behavior remains unchanged
- manual-style factorial, `nfib`, and reverse examples pass
- previous Slice 001 through Slice 025 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
