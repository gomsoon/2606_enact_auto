# Slice 028: unitset Builtin Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/027-zero-argument-functions-calls-requirements.md](/home/tprover/2606_enact_auto/docs/slices/027-zero-argument-functions-calls-requirements.md)

## 1. Slice Goal

This slice adds the remaining list-backed set helper:

```text
unitset(x)
```

`unitset` returns the singleton list `x:nil`. It completes the set-helper group started in Slice 025 before the project moves toward object-backed `Set` and `Bag` values.

## 2. Source Basis

The PRD lists set helper functions including:

- `union`
- `difference`
- `intersection`
- `member`
- `remove`
- `unitset`

Slice 025 implemented the first five helpers over ordinary ENACT lists. This slice adds `unitset` using the same list-backed compatibility strategy.

## 3. In Scope

This slice includes:

- default environment installation for `unitset`
- builtin metadata and arity support
- direct singleton-list construction for any existing runtime value kind
- use through higher-order list builtins
- shadowing behavior consistent with all ordinary builtins
- regression tests for boundary behavior and robustness failures

## 4. Out Of Scope

This slice explicitly excludes:

- object-backed `Set` or `Bag` runtime values
- enforcing duplicate-free set invariants
- set literal syntax
- dot-method dispatch such as `s.unitset()`
- changing the existing `list` builtin

## 5. User-Facing Behavior

Accepted examples:

- `unitset(1).` => `1:nil`
- `unitset true.` => `true:nil`
- `unitset("a").` => `"a":nil`
- `unitset nil.` => `(nil):nil`
- `unitset((1,2)).` => `(1:2:nil):nil`
- `member(1,unitset(1)).` => `true`
- `unitset(1)==list(1).` => `true`
- `union(unitset(1),unitset(2)).` => `1:2:nil`
- `reduce(union,nil,map(unitset,(1,2))).` => `1:2:nil`

Error examples:

- `unitset().` => `ENACT_ERR_ARITY_MISMATCH`
- `unitset(1,1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `unitset(1/0).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `unitset(missing).` => `ENACT_ERR_NAME_UNBOUND`
- `filter(unitset,(1,2)).` => `ENACT_ERR_TYPE_EXPECTED_BOOL`

## 6. Semantic Requirements

`unitset(value)` shall return a newly constructed singleton list:

```text
value:nil
```

The head value shall be copied through the existing list-cell construction path. The returned list shall behave like any other ENACT list for equality, printing, membership, `hd`, `tl`, `size`, `map`, `filter`, `all`, and `reduce`.

## 7. Boundary Analysis Requirements

The regression suite shall include:

- singleton integer, boolean, string, nil, and nested-list values
- equality with `list(x)`
- membership checks over a unit set
- `hd`, `tl`, and `size` over a unit set
- composition with `union`, `difference`, and `intersection`
- higher-order use with `map`, `filter`, `all`, and `reduce`
- function and builtin values inside a unit set
- builtin shadowing

## 8. Robustness Requirements

The regression suite shall include:

- zero-argument call
- over-application that must not evaluate impossible extra arguments
- argument evaluation failure
- unbound argument failure
- unit-set result used as an integer
- unit-set result used as a boolean
- unit-set result compared with a non-list
- unit-set result used as a cons tail with a non-list right operand
- unit-set result called as a function
- shadowed non-function `unitset` call
- `unitset` passed where a predicate or reducer of another arity is required

## 9. Acceptance Criteria

This slice is accepted when:

- `unitset` is installed in the default environment
- `unitset` has arity one
- `unitset(x)` returns the same list shape as `list(x)`
- `unitset` composes with existing list-backed set helpers
- previous Slice 001 through Slice 027 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
