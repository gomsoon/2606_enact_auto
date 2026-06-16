# Slice 023: List Compatibility Design

Status: Draft 0.1

Last updated: 2026-06-16

Update note: Slice 027 supersedes the empty-call boundary described here. `f()` is now valid call syntax, while current non-nullary builtins such as `list()` and `size()` report `ENACT_ERR_ARITY_MISMATCH`.

Related requirements: [docs/slices/023-list-compatibility-requirements.md](/home/tprover/2606_enact_auto/docs/slices/023-list-compatibility-requirements.md)

Prerequisite design: [docs/slices/022-recursive-named-functions-design.md](/home/tprover/2606_enact_auto/docs/slices/022-recursive-named-functions-design.md)

## 1. Design Summary

This slice is intentionally shallow:

- `()` is parsed as the existing nil AST
- `list` is installed as a unary builtin
- no runtime value kind changes are needed

The existing list representation already models nil as `ENACT_VALUE_LIST` with a `NULL` list pointer, and non-empty lists as immutable cons cells.

## 2. Parser Design

Add one `primary` production:

```bison
TOK_LPAREN TOK_RPAREN
{
    $$ = enact_make_nil();
}
```

This makes:

```text
()
```

equivalent to:

```text
nil
```

The production is placed beside the existing grouping and tuple-like list productions.

## 3. Empty Call Boundary

At Slice 023 time, parenthesized function calls still required `argument_list`:

```bison
call TOK_LPAREN argument_list TOK_RPAREN
```

Therefore, before Slice 027:

```text
list()
size()
f()
```

remained parse errors.

Slice 027 later added empty-call syntax. The scanner still discards whitespace, so the implementation cannot distinguish `f()` from `f ()`. A parenthesized nil argument must still be written as:

```text
f(())
```

This keeps the existing empty-call rejection stable.

## 4. Builtin Design

Add:

```c
static int enact_builtin_list(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

The callback constructs one cons cell:

```text
arguments[0] : nil
```

using `enact_list_cons(&arguments[0], NULL)`.

Register the builtin in `builtin_table`:

```c
{"list", 1, enact_builtin_list}
```

No lexer keyword is added. `list` remains a normal identifier that resolves through the environment, just like `hd`, `tl`, `append`, and the other builtins.

## 5. Evaluation And Ownership

`enact_builtin_list` copies the head value through `enact_list_cons`, so singleton lists follow the same ownership behavior as ordinary cons lists.

The result is returned as:

```c
*out = enact_value_make_list(result);
```

The caller owns the resulting value and releases it through the normal value cleanup path.

## 6. Shadowing

Because `list` is installed as an environment binding, user code may shadow it:

```text
list:=x::x; list 4.
```

returns `4`.

If the user shadows `list` with a non-callable value:

```text
list:=1; list 2.
```

the existing call evaluator reports `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## 7. Test Strategy

Regression tests cover:

- `()` as nil
- `99:()` and `1:2:()`
- `list` with whitespace and parenthesized application
- singleton lists containing booleans, nil, and nested lists
- `size`, `atom`, `hd`, `tl`, `append`, `map`, and `reduce` interactions
- assignment/equality with `()`
- shadowing behavior
- empty-call rejection
- arity, evaluation, type, ordering, cons-tail, and empty-list failures

Unit tests cover:

- `list` builtin lookup
- `list` arity
- direct builtin application
- installation into the default environment
