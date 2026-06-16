# Slice 029: Utility Builtins Phase 1 Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/029-utility-builtins-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/029-utility-builtins-phase-1-requirements.md)

Prerequisite design: [docs/slices/028-unitset-builtin-design.md](/home/tprover/2606_enact_auto/docs/slices/028-unitset-builtin-design.md)

## 1. Design Summary

`isObject` and `version` are plain builtins installed in the default environment:

```c
{"isObject", 1, enact_builtin_is_object}
{"version", 0, enact_builtin_version}
```

No lexer, parser, AST, or evaluator grammar changes are required. Both names remain ordinary identifiers and can be shadowed by user code.

## 2. Runtime Semantics

`isObject` currently returns `false` for every input value:

```text
isObject(value) == false
```

The current runtime has no object value kind, so a positive result would require inventing object semantics too early. The builtin is still useful now because it reserves the user-facing name and gives later object work a tested compatibility point.

`version()` returns an owned ENACT string:

```text
"enact-auto 0.1.0"
```

The implementation copies the compile-time version text before wrapping it in `ENACT_VALUE_STRING`, matching the existing string ownership rule that `enact_value_make_string` takes ownership of the pointer.

## 3. Error Behavior

Arity validation remains centralized in the callable/builtin apply path:

- `version(1)` reports `ENACT_ERR_ARITY_MISMATCH`
- `version(1/0)` reports `ENACT_ERR_ARITY_MISMATCH` before evaluating the impossible argument
- `isObject()` reports `ENACT_ERR_ARITY_MISMATCH`
- `isObject(1,1/0)` reports `ENACT_ERR_ARITY_MISMATCH` before evaluating the impossible extra argument

The ordinary type checks still apply when returned values are used in incompatible positions:

- `version()+1` reports `ENACT_ERR_TYPE_EXPECTED_INT`
- `not version()` reports `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `version()==1` reports `ENACT_ERR_TYPE_EQUALITY_MISMATCH`
- `version()()` reports `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `isObject(1)+1` reports `ENACT_ERR_TYPE_EXPECTED_INT`

## 4. Higher-Order Behavior

Both builtins are first-class values.

`isObject` is unary, so it works naturally with the existing list traversal helpers:

```text
map(isObject,(1,true,"x",nil))
filter(isObject,(1,true,"x",nil))
all(x::not isObject(x),(1,true,"x",nil))
```

`version` is nullary, so it can be applied by a helper that explicitly calls a zero-argument function:

```text
apply0(f):=f(); apply0(version)
```

Passing `version` to a unary or binary higher-order list helper remains an arity error.

## 5. Test Strategy

Functional regression tests cover:

- direct `version()` calls
- first-class builtin printing for `version`
- equality between repeated version strings
- composition with `list` and `unitset`
- zero-argument higher-order invocation
- `isObject` over integers, booleans, strings, nil, lists, user functions, builtins, builtin partials, and `version()` strings
- higher-order use with `map`, `filter`, and `all`
- builtin shadowing

Robustness tests cover:

- arity failures for both builtins
- arity failures that must happen before impossible argument evaluation
- type misuse of the returned string and boolean values
- use of `version` in higher-order contexts that require a unary or binary callable
- shadowed non-function builtin calls

Unit tests cover:

- lookup
- arity metadata
- direct builtin application
- default environment installation
