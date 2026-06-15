# Slice 014: Builtin Function Infrastructure Core Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/014-builtin-function-infrastructure-requirements.md](/home/tprover/2606_enact_auto/docs/slices/014-builtin-function-infrastructure-requirements.md)

Prerequisite design: [docs/slices/013-list-core-design.md](/home/tprover/2606_enact_auto/docs/slices/013-list-core-design.md)

## 1. Design Summary

Add builtin functions as a new runtime value kind rather than as parser keywords.

This keeps builtin names ordinary identifiers and lets the existing evaluator machinery handle assignment, environment lookup, closure capture, and higher-order passing.

Seed the builtin table with:

- `hd`
- `tl`

Both are unary builtins over non-empty lists.

## 2. Runtime Model

Introduce an opaque builtin descriptor:

```c
typedef struct EnactBuiltin EnactBuiltin;
```

Add `ENACT_VALUE_BUILTIN` to `EnactValueKind`:

```c
typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL,
    ENACT_VALUE_STRING,
    ENACT_VALUE_FUNCTION,
    ENACT_VALUE_LIST,
    ENACT_VALUE_BUILTIN
} EnactValueKind;
```

The value payload stores:

```c
const EnactBuiltin *as_builtin;
```

Builtin descriptors are static and immutable, so:

- copy is pointer copy
- free is no-op
- equality is pointer identity
- `NULL` builtin payload is invalid for copying

## 3. Builtin API

Create `src/builtin.h` and `src/builtin.c`.

The public API is:

```c
const EnactBuiltin *enact_builtin_lookup(const char *name);
const char *enact_builtin_name(const EnactBuiltin *builtin);
size_t enact_builtin_arity(const EnactBuiltin *builtin);
int enact_builtin_apply(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
int enact_install_builtins(EnactEnv *env);
```

`enact_install_builtins` defines each builtin name in the supplied environment using `enact_env_define`.

## 4. Evaluation Integration

Top-level evaluation uses:

```c
enact_env_init(&env);
enact_install_builtins(&env);
status = enact_eval_ast_with_env(ast, &env, value, diag);
```

The supplied-env path remains explicit: callers that directly use `enact_eval_ast_with_env` can install builtins themselves when desired.

This keeps helper tests and future internal callers in control of environment contents.

## 5. Call Dispatch

`AST_CALL` currently assumes that every callee is `ENACT_VALUE_FUNCTION`.

Refactor call evaluation into two paths:

```text
evaluate callee
if callee is user function:
    use existing user-function call path
else if callee is builtin:
    use builtin call path
else:
    ENACT_ERR_TYPE_EXPECTED_FUNCTION
```

The builtin call path:

1. reads `enact_builtin_arity`
2. rejects zero, too few, or too many arguments with `ENACT_ERR_ARITY_MISMATCH`
3. evaluates arguments eagerly after arity validation
4. calls `enact_builtin_apply`
5. frees evaluated arguments and callee value

Partial application for multi-argument builtins is intentionally deferred.

## 6. Builtin Semantics

`hd`:

```text
hd nil        -> ENACT_ERR_LIST_EMPTY
hd (x:xs)     -> x
hd non_list   -> ENACT_ERR_TYPE_EXPECTED_LIST
```

Implementation:

1. require argument kind `ENACT_VALUE_LIST`
2. require list payload non-null
3. copy `enact_list_head(list)` into `out`

`tl`:

```text
tl nil        -> ENACT_ERR_LIST_EMPTY
tl (x:xs)     -> xs
tl non_list   -> ENACT_ERR_TYPE_EXPECTED_LIST
```

Implementation:

1. require argument kind `ENACT_VALUE_LIST`
2. require list payload non-null
3. retain `enact_list_tail(list)` and return an `ENACT_VALUE_LIST`

## 7. Diagnostics

Add:

```c
ENACT_ERR_LIST_EMPTY
```

Message:

```text
non-empty list required
```

The type diagnostic remains:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

for non-list arguments.

## 8. Printing

Builtin values print as:

```text
<function>
```

This matches user-defined function values and avoids exposing implementation categories in ordinary output.

## 9. Parser Impact

No parser changes are required.

`hd` and `tl` remain ordinary identifiers, which means all existing call syntax already applies:

```text
hd(1:nil)
hd (1:nil)
f:=hd; f(1:nil)
apply(f,x):=f x; apply(hd, 1:nil)
```

## 10. Test Strategy

Regression tests:

- first-order calls to `hd` and `tl`
- higher-order passing
- assignment aliasing
- closure capture
- shadowing
- equality/inequality
- arity, type, and empty-list errors

Unit tests:

- builtin lookup metadata
- builtin value copy/equality
- builtin environment installation
- direct builtin apply success/failure
- direct AST call through an environment containing builtins

## 11. Future Extension Notes

Slice 015 can add `append` and `size` on top of this descriptor/call path.

Higher-order builtins such as `map`, `filter`, `all`, and `reduce` can reuse the same descriptor shape, but they will likely need an internal helper for applying an `EnactValue` callee from C.

If future multi-argument builtins should support partial application, add a builtin partial value or a small generic applied-prefix wrapper rather than special-casing each builtin.
