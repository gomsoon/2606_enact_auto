# Slice 011: Currying and Partial Application Core Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/011-currying-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/011-currying-partial-application-requirements.md)

Prerequisite design: [docs/slices/010-lambda-expressions-design.md](/home/tprover/2606_enact_auto/docs/slices/010-lambda-expressions-design.md)

## 1. Design Objective

This document defines partial application as a runtime function-call behavior over the existing `EnactFunction` value.

No new AST node, value kind, or parser syntax is needed.

## 2. Design Decisions Summary

- Calls with fewer arguments than arity return a new function value.
- Calls with exact arity evaluate the function body exactly as before.
- Calls with more arguments than arity remain `ENACT_ERR_ARITY_MISMATCH`.
- Partial application binds only leading parameters.
- Supplied arguments are evaluated eagerly.
- Returned partial functions retain the original body and remaining parameter list.
- Returned partial functions capture the original closure environment plus supplied prefix arguments.

## 3. Runtime Design

Add a helper on `EnactFunction`:

```c
EnactFunction *enact_function_partial(
    const EnactFunction *function,
    const EnactValue *arguments,
    size_t argument_count);
```

The helper:

1. validates `0 < argument_count < arity`
2. clones the source function's captured environment
3. binds each supplied argument to the matching leading parameter name
4. creates a remaining parameter list from `argument_count..arity-1`
5. returns `enact_function_new(remaining_params, original_body, partially_bound_env)`

The returned function is a normal `EnactFunction` and uses the existing reference-counted `ENACT_VALUE_FUNCTION` path.

## 4. Evaluator Design

`enact_eval_call` changes from exact-only arity checking to a three-way branch:

```text
if argument_count > arity:
    fail with ENACT_ERR_ARITY_MISMATCH before evaluating arguments

evaluate supplied arguments eagerly

if argument_count < arity:
    return function_partial(function, arguments)

otherwise:
    evaluate the body with all parameters bound
```

The over-application branch intentionally stays before argument evaluation to preserve the existing robustness behavior where impossible calls do not force extra failing arguments.

## 5. Capture Semantics

Original closure capture remains definition-time:

```text
x:=10; addx:=(a,b)::x+a+b; x:=20; addx(1,2).
```

returns `13`.

Partial creation also captures supplied arguments at partial-creation time:

```text
x:=1; add:=(a,b)::a+b; p:=add(x:=2); x:=9; p(3); x.
```

returns `9`, while `p(3)` evaluates with `a == 2`.

## 6. Error Timing

Supplied prefix arguments are evaluated when the partial is created:

```text
ignore:=(a,b)::a; ignore(1/0).
```

fails with `ENACT_ERR_DIVIDE_BY_ZERO`.

Type errors inside the body are delayed until enough arguments are supplied to evaluate the body:

```text
add:=(a,b)::a+b; p:=add(true); p(1).
```

fails with `ENACT_ERR_TYPE_EXPECTED_INT`.

Over-application still fails before argument evaluation:

```text
one(x):=x; one(1,1/0).
```

fails with `ENACT_ERR_ARITY_MISMATCH`.

## 7. Parser Design

No parser changes are required.

Existing call syntax:

```text
call ::= call "(" argument_list ")"
       | primary
```

already supports chained parenthesized calls:

```text
add(1)(2)
```

## 8. Test Design

Integration tests should cover:

- named function partial application
- lambda partial application
- chained partial application
- completion with grouped remaining arguments
- partial functions assigned to names
- partial functions passed to higher-order functions
- capture of integers, strings, and booleans
- eager prefix argument evaluation
- delayed body type errors
- over-application errors

Unit tests should cover:

- `enact_function_partial` rejects null or invalid inputs
- returned partial function has remaining arity and parameter names
- evaluator returns `ENACT_VALUE_FUNCTION` for an under-applied AST call
- completing a partial call produces the expected value

## 9. Review Checklist

This design is ready for implementation if:

- exact-arity calls preserve existing behavior
- over-application preserves existing error behavior
- partial creation frees evaluated arguments and temporary environments correctly
- returned partial functions use existing function retain/release behavior
- no grammar conflicts are introduced
