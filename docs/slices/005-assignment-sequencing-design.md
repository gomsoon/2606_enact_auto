# Slice 005: Assignment and Sequencing Core Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/005-assignment-sequencing-requirements.md](/home/tprover/2606_enact_auto/docs/slices/005-assignment-sequencing-requirements.md)

Prerequisite design: [docs/slices/004-identifiers-environment-design.md](/home/tprover/2606_enact_auto/docs/slices/004-identifiers-environment-design.md)

## 1. Design Objective

This document defines the implementation design for the first mutable binding syntax:

- assignment with `:=`
- sequencing with `;`

The slice intentionally uses the flat environment from Slice 004 and does not introduce lexical scopes or persistent REPL state.

## 2. Design Decisions Summary

The following decisions are fixed for Slice 005:

- assignment left-hand side must be a bare identifier token
- `x:=expr` returns the assigned value
- assignment updates the current evaluation environment
- `;` evaluates left-to-right and returns the rightmost value
- assignment is right-associative
- sequencing is left-associative
- public `enact_eval_text` still creates a fresh environment per input
- no binding persists across separate input expressions

## 3. Lexer Design

Add tokens:

- `TOK_ASSIGN` for `:=`
- `TOK_SEMI` for `;`

Rules:

```text
":=" => TOK_ASSIGN
";"  => TOK_SEMI
```

Both tokens should set `expect_operand = true`.

## 4. Parser Design

Add nonterminals above the existing conditional layer:

```text
expr       ::= sequence
sequence   ::= assignment
             | sequence TOK_SEMI assignment
assignment ::= conditional
             | TOK_IDENTIFIER TOK_ASSIGN assignment
```

This preserves the existing conditional grammar unchanged underneath assignment.

Ownership:

- `TOK_IDENTIFIER` payload moves into the assignment AST on success
- parser action frees the identifier payload if AST allocation fails

## 5. AST Design

Add node kinds:

- `AST_ASSIGN`
- `AST_SEQUENCE`

Assignment shape:

```c
struct {
    char *name;
    EnactAst *value;
} assignment;
```

Sequence can reuse the existing binary shape:

```c
left;
right;
```

Constructors:

```c
EnactAst *enact_ast_new_assignment(char *name, EnactAst *value);
EnactAst *enact_ast_new_binary(AST_SEQUENCE, left, right);
```

Destruction:

- assignment frees `name` and `value`
- sequence frees both children through the binary node path

## 6. Evaluation Design

The evaluator already accepts an `EnactEnv` for Slice 004 identifier lookup.

For Slice 005, recursive evaluator helpers should accept mutable `EnactEnv *` rather than `const EnactEnv *`.

`AST_ASSIGN` evaluation:

1. evaluate the right-hand side expression
2. define or update the name in the environment
3. fail with `ENACT_ERR_OUT_OF_MEMORY` if definition fails
4. return the assigned value

`AST_SEQUENCE` evaluation:

1. evaluate left child
2. discard the left result
3. evaluate right child
4. return the right result

This preserves left-to-right side effects.

## 7. Public API Impact

No `api.h` signature changes are required.

The lower-level evaluator helper should change from `const EnactEnv *` to `EnactEnv *`
so assignment can mutate caller-provided environments when tests or future internals use
`enact_eval_ast_with_env` directly.

`enact_eval_ast` should continue to create one temporary environment for the whole AST evaluation.

`enact_eval_text` therefore supports bindings inside one expression:

```text
x:=1; x+2.
```

but does not persist bindings across calls.

## 8. Diagnostics

No new diagnostic code is required.

Use existing codes:

- `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `ENACT_ERR_NAME_UNBOUND`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `ENACT_ERR_OUT_OF_MEMORY`

## 9. Test Design

Integration tests should cover:

- token output for `:=` and `;`
- assignment returns value
- lookup after assignment
- reassignment
- dependent assignment
- parenthesized sequence
- boolean assignment
- malformed assignment and sequence syntax
- non-persistent public evaluation using separate subprocess calls

Unit tests should cover:

- assignment AST construction and evaluation
- sequence AST construction and left-to-right mutation behavior
- assignment OOM is not practical to force in this slice

## 10. Review Checklist

This design is ready for implementation if:

- assignment grammar only admits identifier left-hand sides
- sequencing remains the loosest expression form
- assignment is right-associative
- evaluator environment is mutable during one evaluation
- public API behavior stays backward compatible
