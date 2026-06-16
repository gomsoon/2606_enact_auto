# Slice 017: Tuple-Like List Construction Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/016-builtin-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/016-builtin-partial-application-requirements.md)

## 1. Slice Goal

This slice adds a compact list literal form:

```text
(1,2,3)
```

which evaluates exactly like:

```text
1:2:3:nil
```

The goal is readability. Higher-order list builtin tests should be able to use concise lists without changing the runtime list model.

## 2. Source Basis

The PRD records tuple-like list construction as part of the list feature set.

Slice 013 already defines the underlying immutable cons-list runtime. Slice 014 through Slice 016 add list builtins and builtin partial application. This slice only improves surface syntax.

## 3. In Scope

This slice includes:

- parenthesized comma list syntax with two or more elements
- parser lowering from tuple-like syntax to existing cons-list AST nodes
- support for arbitrary expressions as tuple elements
- nested tuple-like lists
- tuple-like lists passed to existing list builtins
- regression tests for parsing, evaluation, precedence, and error cases

## 4. Out Of Scope

This slice explicitly excludes:

- a new tuple runtime type
- singleton tuple syntax such as `(x,)`
- empty tuple syntax `()`
- changing ordinary grouping `(x)`
- changing function call syntax such as `f(x,y)`
- the historical singleton convention `99:()`
- a `list` builtin
- `map`, `filter`, `all`, and `reduce`
- recursive definitions or `fix`

## 5. User-Facing Behavior

Accepted examples:

- `(1,2).` => `1:2:nil`
- `(1,2,3).` => `1:2:3:nil`
- `("a",true,3).` => `"a":true:3:nil`
- `((1,2),3).` => `(1:2:nil):3:nil`
- `(1+2,3*4).` => `3:12:nil`
- `xs:=(1,2); xs.` => `1:2:nil`
- `size((1,2,3)).` => `3`
- `hd((1,2,3)).` => `1`
- `tl((1,2,3)).` => `2:3:nil`
- `append((1,2),(3,4)).` => `1:2:3:4:nil`
- `append((1,2))((3,4)).` => `1:2:3:4:nil`
- `(1,2)==1:2:nil.` => `true`

Because `f(x,y)` remains a two-argument function call, a tuple-like list used as a single call argument needs its own grouping:

```text
size((1,2,3))
```

not:

```text
size(1,2,3)
```

Error examples:

- `().` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `(1,).` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `(,1).` => `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `(1,,2).` => `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `(1,2.` => `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `(1,2,).` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `size(1,2).` => `ENACT_ERR_ARITY_MISMATCH`
- `hd((1/0,2)).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `(1,2)+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 6. Syntax Requirements

No new lexer tokens are required. This syntax uses the existing `(`, `)`, and `,` tokens.

The parser shall accept tuple-like list syntax only when at least one comma appears:

```text
tuple_list ::= assignment "," assignment
             | tuple_list "," assignment
```

The existing grouping form remains unchanged:

```text
(expr)
```

## 7. Semantic Requirements

Tuple-like list syntax shall be lowered to existing list construction:

```text
(a,b,c)
```

is equivalent to:

```text
a:b:c:nil
```

Tuple elements shall evaluate left-to-right through the existing cons evaluation path.

The runtime value shall be `ENACT_VALUE_LIST`; no tuple-specific value kind shall be added.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- two-element integer list
- three-element integer list
- mixed string, boolean, and integer values
- nested tuple-like list head
- arithmetic expressions as elements
- left-to-right element evaluation
- assignment and retrieval
- `size` over tuple-like list
- `hd` over tuple-like list
- `tl` over tuple-like list
- `append` with tuple-like list arguments
- builtin partial completion with tuple-like list arguments
- equality against explicit cons syntax
- tuple-like list passed as a single function argument
- tuple-like list returned from a closure

## 9. Robustness Requirements

The regression suite shall include:

- empty tuple-like syntax rejected
- trailing comma rejected
- leading comma rejected
- double comma rejected
- missing closing parenthesis rejected
- trailing comma after multiple elements rejected
- function call comma syntax remains multi-argument call syntax
- element evaluation failure propagates
- tuple-like list used as an integer
- tuple-like list used as a boolean
- tuple-like list compared with a non-list

## 10. Acceptance Criteria

This slice is accepted when:

- `(x,y,...)` with at least two elements evaluates as a cons list
- `(x)` remains ordinary grouping
- `f(x,y)` remains ordinary two-argument function application
- tuple-like list syntax works with existing list builtins
- malformed tuple-like syntax reports parser errors
- previous Slice 001 through Slice 016 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
