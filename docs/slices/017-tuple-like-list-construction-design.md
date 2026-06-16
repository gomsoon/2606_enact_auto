# Slice 017: Tuple-Like List Construction Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/017-tuple-like-list-construction-requirements.md](/home/tprover/2606_enact_auto/docs/slices/017-tuple-like-list-construction-requirements.md)

Prerequisite design: [docs/slices/016-builtin-partial-application-design.md](/home/tprover/2606_enact_auto/docs/slices/016-builtin-partial-application-design.md)

## 1. Design Summary

Implement tuple-like list construction as parser sugar only.

The parser recognizes parenthesized comma expressions with at least two elements and lowers them to the existing cons-list AST:

```text
(a,b,c) -> a:b:c:nil
```

No runtime tuple value is introduced.

## 2. Grammar Shape

Add a separate nonterminal:

```text
tuple_list:
    assignment "," assignment
  | tuple_list "," assignment
```

and add a primary expression alternative:

```text
primary:
    "(" tuple_list ")"
```

The existing grouping rule remains:

```text
primary:
    "(" expr ")"
```

Because `tuple_list` requires a comma, `(x)` remains unambiguous grouping.

## 3. Lowering Helper

Reuse `EnactAstList` as the temporary parser container for tuple elements.

Add a grammar helper:

```c
static EnactAst *enact_make_tuple_list(EnactAstList *elements);
```

The helper right-folds the element list into cons nodes:

```text
tail = nil
for elements from right to left:
    tail = element : tail
return tail
```

The helper consumes the `EnactAstList` and transfers each element into the resulting AST. On failure, it frees the partially-built tree and any untransferred elements.

## 4. Evaluation

No evaluator changes are required.

The lowered AST uses:

- `AST_CONS`
- `AST_NIL`

so tuple-like list evaluation follows the existing Slice 013 cons semantics, including:

- left-to-right element evaluation
- tail list validation
- immutable list construction
- structural list equality
- list printing

## 5. Function Call Interaction

Function call syntax is unchanged:

```text
f(x,y)
```

continues to mean a two-argument call.

A tuple-like list passed as one argument must be grouped as an expression:

```text
f((x,y))
```

This avoids changing the meaning of existing multi-argument calls.

## 6. Test Strategy

Regression tests cover:

- tokenization of tuple-like syntax using existing tokens
- list printing for two and three elements
- mixed element values
- nested tuple-like lists
- expression elements
- assignment side effects in element order
- `hd`, `tl`, `size`, and `append`
- builtin partial completion with tuple-like list arguments
- equality with explicit cons syntax
- malformed comma forms
- preserving multi-argument call behavior

Unit tests cover one API-level tuple-like list evaluation and inspect the resulting runtime list cells directly.

## 7. Future Extension Notes

This syntax is intended to make later higher-order list builtin tests readable:

```text
map(f, (1,2,3))
filter(p, (1,2,3))
reduce(f, 0, (1,2,3))
```

The later builtin slices should keep using this syntax as input sugar while preserving the same underlying cons-list runtime.
