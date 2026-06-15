# Slice 013: List Core Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/013-list-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/013-list-core-requirements.md)

Prerequisite design: [docs/slices/012-whitespace-function-application-design.md](/home/tprover/2606_enact_auto/docs/slices/012-whitespace-function-application-design.md)

## 1. Design Objective

This document defines the first runtime list representation for ENACT.

The implementation should be small, immutable, and compatible with existing environment/value copy behavior.

## 2. Design Decisions Summary

- `nil` is a reserved literal token.
- `:` is the cons operator.
- Cons is right-associative.
- Lists print in source-like cons notation.
- A list is represented as an opaque reference-counted `EnactList`.
- `nil` is represented as a list value with a null list payload.
- Cons cells retain their tail list and own a copied head value.
- Structural equality is supported for lists.
- List builtins are deferred.

## 3. Lexer Design

Add:

```text
TOK_NIL
TOK_CONS
```

Rule order:

```text
"::"
":="
":"
```

`nil` must appear before the identifier rule. Identifier-like words such as `nilx` remain identifiers.

## 4. AST Design

Add:

```c
AST_NIL
AST_CONS
```

`AST_CONS` uses the existing binary payload:

```c
as.binary.left  // head expression
as.binary.right // tail expression
```

No extra AST constructor is needed for cons because `enact_ast_new_binary` already handles binary nodes.

## 5. Parser Design

Insert a cons layer between comparison and additive:

```text
comparison ::= cons
             | cons comparison_operator cons

cons       ::= additive ":" cons
             | additive
```

This makes `:` right-associative and lower precedence than `+` and `-`:

```text
1+2:nil
```

parses as:

```text
(1+2):nil
```

## 6. Runtime Value Design

Extend `EnactValueKind`:

```c
ENACT_VALUE_LIST
```

Use an opaque list payload:

```c
typedef struct EnactList EnactList;
```

`NULL` means `nil`.

A cons cell stores:

```c
size_t ref_count;
EnactValue head;
EnactList *tail;
```

The constructor:

```c
EnactList *enact_list_cons(const EnactValue *head, EnactList *tail);
```

copies `head` and retains `tail`.

## 7. Evaluation Design

`AST_NIL` evaluates to:

```c
enact_value_make_list(NULL)
```

`AST_CONS`:

1. evaluates the head expression
2. evaluates the tail expression
3. requires the tail value to be `ENACT_VALUE_LIST`
4. creates a cons cell using the head and tail payload
5. returns `ENACT_VALUE_LIST`

If the tail is not a list, evaluation fails with:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

## 8. Printing Design

`main.c` should split value printing into:

- an inner printer without a trailing newline
- the existing top-level `enact_print_value` with one trailing newline

Lists print recursively:

```text
nil
1:nil
1:2:nil
```

When a head value is itself a list, print parentheses:

```text
(1:nil):nil
```

## 9. Equality Design

Move value equality into a value-layer helper:

```c
int enact_value_equal(const EnactValue *left, const EnactValue *right, bool *out);
```

The helper compares:

- integers by value
- booleans by value
- strings by text
- functions by pointer identity
- lists structurally

The evaluator still rejects equality across different value kinds before calling the helper.

## 10. Test Design

Integration tests should cover:

- token output for `nil` and `:`
- nil printing
- cons printing
- nested list printing
- list assignment and environment copy
- cons precedence with arithmetic
- equality and inequality
- type errors for non-list tails
- type errors for list arithmetic and ordering
- `nilx` as an ordinary identifier

Unit tests should cover:

- list value creation
- list retain/copy/free behavior
- list equality through evaluator equality
- direct AST cons evaluation

## 11. Review Checklist

This design is ready for implementation if:

- `::` and `:=` are not disturbed by `:`
- Bison introduces no parser conflicts
- list copy/free behavior follows existing environment ownership rules
- list printing does not add extra newlines inside nested values
- previous function call precedence tests remain green
