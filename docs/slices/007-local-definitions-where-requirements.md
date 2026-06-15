# Slice 007: Local Definitions with where Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/006-strings-mod-requirements.md](/home/tprover/2606_enact_auto/docs/slices/006-strings-mod-requirements.md)

## 1. Slice Goal

This slice introduces local definition syntax using `where`.

The immediate purpose is to establish scoped environment evaluation before function definition and function argument binding are added.

## 2. Source Basis

The PRD records:

- local definitions using `where`
- `where` has lower precedence than comparison and higher precedence than `and`
- functions use static binding, so future function work needs a way to evaluate expressions against scoped environments

## 3. In Scope

This slice includes:

- lexer support for reserved word `where`
- parser support for one local binding:

```text
expr where name:=value
```

- AST support for a local `where` expression
- evaluator support for local environment cloning and shadowing
- tests for local integer, boolean, and string bindings
- tests proving local bindings do not mutate the surrounding environment
- malformed syntax and type-misuse regression tests

## 4. Out Of Scope

This slice explicitly excludes:

- multiple local definitions in one `where` clause
- function definitions such as `f(x):=x+1`
- recursive local definitions
- `fix`
- lambda expressions using `::`
- function application
- local binding lists separated by `;` or `,`

Multiple local definitions are intentionally deferred to avoid mixing `where` with sequence parsing before function syntax is designed.

## 5. User-Facing Behavior

Accepted examples:

- `x where x:=1.` => `1`
- `x+2 where x:=1.` => `3`
- `x==1 where x:=1.` => `true`
- `x where x:=(1 if true else 2).` => `1`
- `x where x:="hi".` => `"hi"`
- `x:=10; (x where x:=1); x.` => `10`
- `x + (y where y:=2) where x:=1.` => `3`
- `true and x where x:=true.` => `true`

The binding only exists while evaluating the `where` expression body.

## 6. Lexical Requirements

The lexer shall recognize:

- `where` as `TOK_WHERE`

Identifier-like words containing `where`, such as `wherever`, remain identifiers.

`TOK_WHERE` shall set operand expectation to true after emission.

## 7. Syntax Requirements

For this slice, `where` is a postfix local-binding operator:

```text
where_expr ::= logical_not
             | logical_not "where" identifier ":=" logical_not
```

`where_expr` shall be used below `and` and above comparison-bearing `logical_not` in the current parser structure. This preserves:

- comparison binds tighter than `where`
- `where` binds tighter than `and`
- assignment and sequencing remain looser than `where`

The binding value is intentionally limited to the same `logical_not` layer in this slice. Larger expressions such as conditionals, sequences, or assignments may be used by parenthesizing them:

```text
x where x:=(1 if true else 2)
```

Because only one binding is in scope, semicolon after a `where` expression is an outer sequence separator:

```text
x where x:=1; x
```

is interpreted as:

```text
(x where x:=1); x
```

and the second `x` is outside the local binding.

## 8. Semantic Requirements

The evaluator shall:

1. clone the current environment
2. evaluate the binding value in the cloned environment
3. define or update the binding name in the cloned environment
4. evaluate the body in the cloned environment
5. free the cloned environment
6. return the body's value

The evaluator shall not mutate the surrounding environment.

The binding value may refer to existing outer bindings through the cloned environment, but it is not recursive in this slice.

## 9. Error Requirements

Existing diagnostic codes are sufficient:

- `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `ENACT_ERR_PARSE_MISSING_DOT`
- `ENACT_ERR_NAME_UNBOUND`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `ENACT_ERR_OUT_OF_MEMORY`

Malformed `where` syntax shall fail with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

## 10. Boundary Analysis Requirements

The regression suite shall include:

- integer local binding
- boolean local binding
- string local binding
- local binding from an expression
- local shadowing of an outer binding
- local assignment inside a `where` body does not leak
- nested `where`
- `where` in a conditional condition
- `where` in a logical expression

## 11. Robustness Requirements

The regression suite shall include malformed or risky cases such as:

- leading `where`
- missing local binding name
- non-identifier binding left-hand side
- missing binding right-hand side
- missing final `.`
- local binding not visible after outer `;`
- type-invalid use of a locally bound value
- unbound name in the binding value

## 12. Acceptance Criteria

This slice is accepted when:

- `where` tokenizes as a reserved word
- `wherever` remains an identifier
- local bindings shadow outer bindings only inside the `where` expression
- local binding values can be integers, booleans, or strings
- all previous slice tests remain green
