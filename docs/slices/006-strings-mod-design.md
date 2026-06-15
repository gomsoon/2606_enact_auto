# Slice 006: String Literals and Mod Operator Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/006-strings-mod-requirements.md](/home/tprover/2606_enact_auto/docs/slices/006-strings-mod-requirements.md)

Prerequisite design: [docs/slices/005-assignment-sequencing-design.md](/home/tprover/2606_enact_auto/docs/slices/005-assignment-sequencing-design.md)

## 1. Design Objective

This document defines the smallest implementation shape for:

- string literal values
- the integer `mod` operator

The design keeps the current expression architecture intact and adds value ownership helpers before strings can flow through environments.

## 2. Design Decisions Summary

- String literals are double-quoted primary expressions.
- Supported escapes are `\\`, `\"`, `\n`, `\r`, and `\t`.
- Unsupported escapes fail lexically with `ENACT_ERR_LEX_BAD_STRING`.
- Runtime strings are heap-owned by `EnactValue`.
- Environments store deep copies of values.
- Environment lookup returns deep copies.
- `enact_result_free` releases successful string results.
- CLI output prints strings in double-quoted escaped form.
- `mod` is a reserved word, not an identifier.
- `mod` shares precedence and associativity with `*` and `/`.

## 3. Lexer Design

Add token:

```c
%token <text> TOK_STRING_LITERAL
%token TOK_MOD
```

String matching can use a permissive double-quoted token candidate that excludes physical newlines, followed by C-side decoding:

```text
\"([^\"\\\r\n]|\\.)*\"
```

The decoder:

1. skips the surrounding quotes
2. copies ordinary bytes directly
3. decodes supported escapes
4. rejects unknown escapes
5. returns a newly allocated NUL-terminated string payload

Malformed string candidates should set `ENACT_ERR_LEX_BAD_STRING` at the string start offset and return `TOK_ERROR`.

The keyword rule for `mod` must appear before the identifier rule.

## 4. Parser Design

Add string literals to `primary`:

```text
primary:
    TOK_STRING_LITERAL
```

The token text moves into an `AST_STRING_LITERAL` node on success. Parser destructors free `<text>` payloads on parse failure.

Add `TOK_MOD` to `multiplicative`:

```text
multiplicative TOK_MOD unary
```

This emits `AST_MOD` through the existing binary AST constructor.

## 5. AST Design

Add node kinds:

- `AST_STRING_LITERAL`
- `AST_MOD`

Add string payload:

```c
char *string_value;
```

Add constructor:

```c
EnactAst *enact_ast_new_string(char *value);
```

Destruction:

- string literal frees `string_value`
- mod reuses the binary child-free path

## 6. Runtime Value Design

Extend `EnactValueKind`:

```c
ENACT_VALUE_STRING
```

Extend payload:

```c
char *as_string;
```

Add helpers:

```c
EnactValue enact_value_make_string(char *value);
int enact_value_copy(EnactValue *out, const EnactValue *in);
void enact_value_free(EnactValue *value);
```

Ownership rules:

- `enact_value_make_string` takes ownership of the provided pointer.
- `enact_value_copy` deep-copies strings and shallow-copies primitive scalar payloads.
- `enact_value_free` releases string payloads and resets the value to integer zero.

## 7. Environment Design

Because environments can now store heap-owned payloads:

- `enact_env_define` should deep-copy the incoming value before storing it
- replacing an existing binding should free the old stored value
- `enact_env_lookup` should deep-copy the stored value into the caller's output
- `enact_env_free` should free stored values before freeing entries

This lets assignment both return the assigned string and keep an independent environment copy.

## 8. Evaluation Design

String literal evaluation:

1. copy the AST literal string into a new runtime value
2. report `ENACT_ERR_OUT_OF_MEMORY` on copy failure
3. return `ENACT_VALUE_STRING`

Temporary values in evaluator helpers must be freed on every success and failure path after they are no longer needed.

Equality:

- int equality compares integers
- bool equality compares booleans
- string equality uses `strcmp`
- different value kinds still fail with `ENACT_ERR_TYPE_EQUALITY_MISMATCH`

`mod`:

- lives in the same checked arithmetic helper as `+`, `-`, `*`, and `/`
- requires integer operands through the existing integer checks
- rejects right operand zero with `ENACT_ERR_DIVIDE_BY_ZERO`
- rejects `INT32_MIN mod -1` with `ENACT_ERR_INT_OVERFLOW`
- computes `left % right`

## 9. CLI Printing Design

Add string output support to `main.c`.

Strings should print as a quoted escaped representation:

```text
"hello\n"
```

The printer should escape:

- `\\`
- `\"`
- newline
- carriage return
- tab

Other bytes can print directly in this slice.

## 10. Test Design

Integration tests should cover:

- token output for strings and `mod`
- successful string literals, escapes, assignment, conditionals, and equality
- malformed strings
- strings rejected by arithmetic, ordering, and boolean contexts
- successful `mod` examples with precedence and sign behavior
- malformed and type-invalid `mod`

Unit tests should cover:

- string value construction, copy, and free
- environment storage and lookup for strings
- direct AST string evaluation
- direct AST mod evaluation

## 11. Review Checklist

This design is ready for implementation if:

- all string-owning paths have a matching cleanup path
- assignment and environment lookup do not share mutable string pointers
- `mod` does not disturb existing unary minus precedence
- reserved `mod` does not consume identifiers such as `modern`
- public `api.h` signatures stay unchanged
