# Slice 029: Utility Builtins Phase 1 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/028-unitset-builtin-requirements.md](/home/tprover/2606_enact_auto/docs/slices/028-unitset-builtin-requirements.md)

## 1. Slice Goal

This slice starts the utility and introspection builtin group with two low-risk helpers:

```text
version()
isObject(value)
```

`version` validates the zero-argument builtin call path with a deterministic result. `isObject` establishes the object-introspection name before object runtime values exist.

## 2. Source Basis

The PRD lists the initial builtin library and utility group, including:

- `isObject`
- `version`
- `classof`
- `attrs`
- `time`
- `cells`
- `maxcells`
- `bye`
- `ask`

This slice intentionally chooses the deterministic and runtime-local subset. It avoids I/O, process lifecycle behavior, memory instrumentation, and object/class metadata that require larger semantic commitments.

## 3. In Scope

This slice includes:

- default environment installation for `isObject` and `version`
- builtin metadata and arity support
- `version()` returning a deterministic string
- `isObject(value)` returning `false` for every currently implemented runtime value kind
- use through higher-order list builtins where the callable arity matches
- builtin shadowing behavior consistent with all ordinary builtins
- regression tests for boundary behavior and robustness failures

## 4. Out Of Scope

This slice explicitly excludes:

- object/class runtime values
- changing `isObject` to recognize future object values
- `classof` and `attrs`
- non-deterministic `time()`
- memory/accounting helpers such as `cells()` and `maxcells()`
- interactive or process-control helpers such as `ask()` and `bye()`
- changing lexer or parser behavior

## 5. User-Facing Behavior

Accepted examples:

- `version().` => `"enact-auto 0.1.0"`
- `version.` => `<function>`
- `version()==version().` => `true`
- `list(version()).` => `"enact-auto 0.1.0":nil`
- `apply0(f):=f(); apply0(version).` => `"enact-auto 0.1.0"`
- `isObject(1).` => `false`
- `isObject(true).` => `false`
- `isObject("x").` => `false`
- `isObject(nil).` => `false`
- `isObject((1,2)).` => `false`
- `isObject(x::x).` => `false`
- `isObject(hd).` => `false`
- `isObject(append(nil)).` => `false`
- `map(isObject,(1,true,"x",nil,(1,2))).` => `false:false:false:false:false:nil`
- `isObject:=x::true; isObject(1).` => `true`

Error examples:

- `version(1).` => `ENACT_ERR_ARITY_MISMATCH`
- `version(1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `isObject().` => `ENACT_ERR_ARITY_MISMATCH`
- `isObject(1,1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `version()+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `not version().` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `version()==1.` => `ENACT_ERR_TYPE_EQUALITY_MISMATCH`
- `version()().` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `map(version,(1,2)).` => `ENACT_ERR_ARITY_MISMATCH`
- `isObject:=1; isObject 2.` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`

## 6. Semantic Requirements

`version()` shall return the string:

```text
"enact-auto 0.1.0"
```

The returned string shall be a normal owned ENACT string value. It shall compare equal to another `version()` result by string value and shall work in list/set helper positions that accept arbitrary values.

`isObject(value)` shall return `false` for all currently implemented value kinds:

- integer
- boolean
- string
- nil
- non-empty list
- user function
- builtin function
- builtin partial

This result is a compatibility baseline, not a statement that ENACT will never have object values. When object values are added later, `isObject` shall become the natural extension point.

## 7. Boundary Analysis Requirements

The regression suite shall include:

- direct zero-argument `version()` calls
- treating `version` itself as a first-class builtin value
- repeated `version()` equality
- `version()` values inside `list` and `unitset`
- higher-order zero-argument invocation through a user helper
- `isObject` over all current runtime value categories
- boolean composition with `not isObject(...)`
- higher-order use with `map`, `filter`, and `all`
- builtin shadowing

## 8. Robustness Requirements

The regression suite shall include:

- `version` called with one argument
- `version` over-application that must not evaluate an impossible failing argument
- `isObject` zero-argument call
- `isObject` over-application that must not evaluate an impossible failing argument
- `version()` misused as an integer, boolean, function, and equality peer
- `isObject(...)` misused as an integer and equality peer
- `version` passed where a unary or binary higher-order callable is required
- shadowed non-function `isObject` and `version` calls

## 9. Acceptance Criteria

This slice is accepted when:

- `isObject` is installed in the default environment with arity one
- `version` is installed in the default environment with arity zero
- `version()` returns `"enact-auto 0.1.0"`
- `isObject` returns `false` for every currently implemented value kind
- previous Slice 001 through Slice 028 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
