# Slice 021: Atom Builtin Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/020-higher-order-list-builtins-reduce-requirements.md](/home/tprover/2606_enact_auto/docs/slices/020-higher-order-list-builtins-reduce-requirements.md)

## 1. Slice Goal

This slice adds the `atom` builtin:

```text
atom(value)
```

`atom` tells whether a value is atomic rather than a non-empty list.

## 2. Source Basis

The PRD records:

- atom-like symbolic values are part of the larger ENACT model
- the initial builtin library includes `atom`
- recursive list examples are expected in the functional-core milestone

The current implementation does not yet have quoted atom values. This slice therefore defines `atom` over the runtime value kinds that already exist.

## 3. In Scope

This slice includes:

- `atom` as a one-argument builtin
- default environment installation
- builtin metadata and direct-apply unit tests
- regression tests over integers, booleans, strings, lists, functions, builtins, and builtin partials

## 4. Out Of Scope

This slice explicitly excludes:

- quoted atom syntax such as `'hello`
- a distinct runtime atom value kind
- `isObject`
- object/class/set/bag semantics
- recursive definitions or `fix`

## 5. Semantics

`atom value` shall return `true` unless `value` is a non-empty list.

This means:

- integers are atoms
- booleans are atoms
- strings are atoms
- functions are atoms
- builtin functions are atoms
- builtin partials are atoms
- `nil` is an atom
- non-empty lists are not atoms

The important list distinction is:

```text
atom(nil)   == true
atom(1:nil) == false
```

This makes `atom` useful as a base-condition helper for future recursive list examples while still treating actual cons-list structures as compound values.

## 6. Lambda And Function Values

Lambda expressions evaluate to function values.

Therefore:

```text
atom(x::x) == true
```

Assigned functions, named functions, builtin functions, and builtin partials follow the same rule because they are single first-class values, not list cells.

## 7. User-Facing Behavior

Accepted examples:

- `atom(1).` => `true`
- `atom(-1).` => `true`
- `atom(true).` => `true`
- `atom(false).` => `true`
- `atom("x").` => `true`
- `atom(nil).` => `true`
- `atom(1:nil).` => `false`
- `atom((1,2)).` => `false`
- `atom((1:nil):nil).` => `false`
- `atom(x::x).` => `true`
- `f:=x::x; atom(f).` => `true`
- `atom(hd).` => `true`
- `atom(append(1:nil)).` => `true`
- `atom(atom).` => `true`

Error examples:

- `atom(1,1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `atom(1/0).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `atom(missing).` => `ENACT_ERR_NAME_UNBOUND`
- `atom(1)+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `atom(1)==1.` => `ENACT_ERR_TYPE_EQUALITY_MISMATCH`
- `atom(1)(2).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`

## 8. Boundary Analysis Requirements

The regression suite shall include:

- integer atom
- negative integer atom
- true atom
- false atom
- string atom
- nil atom
- non-empty cons list non-atom
- tuple-like list non-atom
- nested-list head still making the outer list non-atom
- lambda atom
- assigned function atom
- builtin atom
- builtin partial atom
- reduce partial atom
- map with `atom`
- filter with `atom`
- all with `atom`
- all detecting a non-atom list value
- reduce over filtered atoms
- `atom` itself as an atom

## 9. Robustness Requirements

The regression suite shall include:

- atom over-application does not evaluate impossible extra arguments
- atom over-application with nil does not evaluate impossible extra arguments
- argument evaluation failure
- unbound argument
- tuple-like argument evaluation failure
- atom result used as an integer
- atom result used as an integer on the right side
- atom result compared with a non-bool
- atom result used as a cons tail
- atom result called as a function
- atom result used in ordering
- atom-result list used as an integer

## 10. Acceptance Criteria

This slice is accepted when:

- `atom` is installed in the default environment
- `atom` has arity 1
- `atom(nil)` returns `true`
- `atom(non_empty_list)` returns `false`
- function-like values, including lambdas and builtin partials, return `true`
- previous Slice 001 through Slice 020 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
