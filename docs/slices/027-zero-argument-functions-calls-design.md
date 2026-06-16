# Slice 027: Zero-Argument Functions and Calls Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/027-zero-argument-functions-calls-requirements.md](/home/tprover/2606_enact_auto/docs/slices/027-zero-argument-functions-calls-requirements.md)

Prerequisite design: [docs/slices/026-manual-style-conditional-design.md](/home/tprover/2606_enact_auto/docs/slices/026-manual-style-conditional-design.md)

## 1. Design Summary

The existing function representation already stores parameters in an `EnactNameList`, so the runtime only needs to stop rejecting empty lists.

The parser adds explicit empty-call and empty-lambda productions. The evaluator then treats zero arguments as a valid exact-arity call only when the callable has no remaining parameters.

## 2. Parser Design

Add an empty argument-list call production:

```bison
call TOK_LPAREN TOK_RPAREN
```

The production creates an empty `EnactAstList` and lowers to the existing `AST_CALL` node. Non-empty calls continue to use the existing `argument_list` production.

Add an empty lambda head production:

```bison
TOK_LPAREN TOK_RPAREN
```

The production creates an empty `EnactNameList` and lowers to the existing `AST_FUNCTION_LITERAL` node.

## 3. Assignment Lowering

`f():=body` already parses as a call-shaped left-hand side. Assignment lowering now accepts one direct empty argument list and creates a recursive named function assignment:

```text
f := ()::body
```

Nested empty stages remain invalid:

```text
f(x)():=x
f()(x):=x
```

This avoids silently ignoring an empty stage while the language has no explicit model for multi-stage definition arity.

## 4. Function Construction

`enact_function_new` and `enact_function_new_recursive` now accept empty parameter lists.

Partial application behavior is unchanged:

- zero captured arguments do not create a partial
- exact arity application does not create a partial
- zero-arity functions cannot be partially applied

## 5. Evaluation Design

`enact_eval_check_callable_arity` computes remaining arity:

```text
remaining = arity - captured_count
```

Calls are valid when:

- `argument_count <= remaining`
- and `argument_count == 0` only when `remaining == 0`

This preserves the existing under-application rule for non-nullary functions while allowing exact nullary calls.

`enact_eval_call` allocates the evaluated argument array only when `argument_count > 0`, avoiding implementation-defined `calloc(0, ...)` behavior.

## 6. Builtin Behavior

No new zero-argument builtin is added in this slice.

The callable arity helper is ready for future zero-arity builtins, but all current builtins have arity one or more. Therefore current forms such as:

```text
size()
list()
append()
```

now parse and report `ENACT_ERR_ARITY_MISMATCH`.

## 7. Test Strategy

Regression tests cover:

- tokenization for empty calls, empty function definitions, and empty lambda heads
- zero-argument functions returning every existing value category
- lambda calls and function-returning nullary functions
- captured environment behavior and local assignment isolation
- higher-order helper calls using nullary functions
- recursive and fixed nullary definitions
- arity mismatch before impossible argument evaluation
- builtin zero-argument calls
- invalid nested empty-stage definition left-hand sides

Unit tests cover:

- zero-argument function construction
- zero-argument recursive function construction
- rejection of partial application for zero-arity functions
- direct AST evaluation of a zero-argument function call
- public callable helper application with zero arguments
