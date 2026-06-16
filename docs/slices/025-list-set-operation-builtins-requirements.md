# Slice 025: List Set-Operation Builtins Phase 1 Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/024-fix-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/024-fix-core-requirements.md)

## 1. Slice Goal

This slice adds the first list-backed set-operation builtin group:

```text
member(value, list)
remove(value, list)
union(left, right)
difference(left, right)
intersection(left, right)
```

These operations treat ordinary ENACT lists as set-like lists. They are intended to prepare for the later `Set` and `Bag` collection-class slices without introducing object or class runtime values yet.

## 2. Source Basis

The ENACT manual Appendix 1, p.233-p.234, lists predefined functions:

- `union(x,y)`: assuming `x` and `y` are lists without repetition, form the set union of lists `x` and `y`
- `difference(x,y)`: assuming `x` and `y` are lists without repetition, form the set difference of lists `x` and `y`
- `intersection(x,y)`: assuming `x` and `y` are lists without repetition, form the set intersection of lists `x` and `y`
- `member(x,y)`: assuming `y` is a list without repetition, return true only if `x` is a member of list `y`
- `remove(x,y)`: assuming `y` is a list without repetition, return a list with the same members as `y` except for one occurrence of `x`, if any

The manual says these functions are used to implement object-oriented set operations that are defined later.

## 3. In Scope

This slice includes:

- default environment installation for all five builtins
- builtin metadata and arity support
- partial application through the existing builtin partial infrastructure
- list membership using existing runtime value equality
- list result construction with deterministic ordering
- direct builtin unit tests
- functional regression tests covering ordinary calls, partial calls, and higher-order use

## 4. Out Of Scope

This slice explicitly excludes:

- `Set` and `Bag` object/class runtime values
- dot-method dispatch such as `s.union(t)`
- quoted symbol or atom literals
- object identity membership behavior
- enforcing that input lists are duplicate-free
- special syntax for set literals

## 5. Value Equality Semantics

Membership uses `enact_value_equal`, the same runtime equality helper used by list equality.

For membership and set operations, values of different runtime kinds are simply not equal. This is useful for mixed lists:

```text
member(1,(true,"1")) == false
```

This differs from the user-facing `==` operator, which still reports `ENACT_ERR_TYPE_EQUALITY_MISMATCH` when its two operands have different runtime kinds.

## 6. Builtin Semantics

`member(value, list)` shall:

1. require exactly two arguments
2. require the second argument to be a list
3. scan the list from head to tail
4. return `true` if any element equals `value`
5. return `false` otherwise

`remove(value, list)` shall:

1. require exactly two arguments
2. require the second argument to be a list
3. remove the first equal occurrence of `value`, if present
4. preserve the order of every remaining element
5. return the original members unchanged when `value` is absent

`difference(left, right)` shall:

1. require both arguments to be lists
2. preserve the order of `left`
3. keep only elements from `left` that are not members of `right`

`intersection(left, right)` shall:

1. require both arguments to be lists
2. preserve the order of `left`
3. keep only elements from `left` that are members of `right`

`union(left, right)` shall:

1. require both arguments to be lists
2. compute `append(difference(left, right), right)`
3. therefore preserve the manual-style ordering where left-only elements come first and the whole right list follows

For example:

```text
union((3,2,1),(5,4,3)) == (2,1,5,4,3)
```

This matches the ordering shown by the manual's `s.union(t)` example.

## 7. Duplicate Input Policy

The manual defines these operations under the assumption that the relevant lists are without repetition. This slice does not validate that precondition.

When duplicate inputs are supplied:

- `remove` removes the first equal occurrence only
- `difference` and `intersection` apply their membership rule to each left-side list cell
- `union` follows the documented formula `append(difference(left, right), right)`

These rules make duplicate behavior deterministic without pretending to introduce a complete mathematical set abstraction before the object collection slices.

## 8. User-Facing Behavior

Accepted examples:

- `member(1,nil).` => `false`
- `member(1,(1,2,3)).` => `true`
- `member(4,(1,2,3)).` => `false`
- `member((1,2),((1,2),(3,4))).` => `true`
- `remove(1,nil).` => `nil`
- `remove(1,(1,2,3)).` => `2:3:nil`
- `remove(2,(1,2,3)).` => `1:3:nil`
- `difference((1,2,3),(2,4)).` => `1:3:nil`
- `intersection((1,2,3),(2,3,4)).` => `2:3:nil`
- `union(nil,(2,3)).` => `2:3:nil`
- `union((3,2,1),(5,4,3)).` => `2:1:5:4:3:nil`
- `union((1,2),(2,3)).` => `1:2:3:nil`
- `reduce(union,nil,((1,2),(2,3),(3,4))).` => `1:2:3:4:nil`

Error examples:

- `member(1,1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `remove(1,true).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `union(1,nil).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `difference(nil,1).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `intersection(1,nil).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `member(1,nil,1/0).` => `ENACT_ERR_ARITY_MISMATCH`
- `member(1/0,nil).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `member(1,(1,2))+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 9. Boundary Analysis Requirements

The regression suite shall include:

- `member` over nil
- `member` finding head, tail, and missing values
- string membership
- nested-list membership
- function identity membership
- builtin identity membership
- `remove` over nil
- `remove` at head and middle
- `remove` of a missing value
- deterministic duplicate removal
- `difference` with nil on either side
- `difference` with overlap
- string difference
- `intersection` with nil on either side
- `intersection` with overlap
- nested-list intersection
- `union` with nil on either side
- manual-style `union((3,2,1),(5,4,3))`
- overlapping union
- partial application of `union`
- `reduce` using `union`
- `filter` using a `member` partial
- `map` using a `remove` partial
- `all` using a `member` partial
- `size` over a union result

## 10. Robustness Requirements

The regression suite shall include:

- non-list second argument for `member`
- non-list second argument for `remove`
- non-list left and right arguments for each two-list operation
- over-application does not evaluate impossible extra arguments
- argument evaluation failure before builtin execution
- unbound value argument before builtin execution
- boolean result used as an integer
- list result compared with a non-list
- list result used as a boolean
- bad captured type in partially applied `member`
- bad captured type in partially applied `remove`
- bad captured type in partially applied `union`
- bad captured type in partially applied `difference`
- bad captured type in partially applied `intersection`
- list result called as a function

## 11. Acceptance Criteria

This slice is accepted when:

- all five builtins are installed in the default environment
- all five builtins have the expected arity
- `member`, `remove`, `union`, `difference`, and `intersection` work over empty and non-empty lists
- `union` ordering follows `append(difference(left, right), right)`
- builtins can be partially applied and used higher-order
- previous Slice 001 through Slice 024 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
