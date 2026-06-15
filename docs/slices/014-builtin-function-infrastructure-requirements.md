# Slice 014: Builtin Function Infrastructure Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/013-list-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/013-list-core-requirements.md)

## 1. Slice Goal

This slice introduces the smallest builtin-function runtime path.

The goal is not to complete the predefined library yet. The goal is to make builtin functions ordinary callable values that can be:

- resolved from the default top-level environment
- passed as arguments
- assigned to names
- called through the existing parenthesized and whitespace application syntax

The slice seeds the mechanism with `hd` and `tl` because Slice 013 already provides immutable list values.

## 2. Source Basis

The PRD records:

- predefined functions include `hd`, `tl`, `append`, `size`, `map`, `filter`, `all`, and `reduce`
- function application works in parenthesized and whitespace-applied forms
- higher-order functions are part of the functional core
- list values are now available through `nil` and cons `:`

This slice creates the infrastructure needed for later predefined functions without adding a special parser case for each builtin name.

## 3. In Scope

This slice includes:

- a runtime builtin function value kind
- a builtin descriptor table
- default environment installation for builtin names
- call evaluator dispatch for user functions and builtin functions
- exact arity validation for builtins
- builtin value copy/free/equality support
- printing builtin values as function-like values
- `hd` for the head of a non-empty list
- `tl` for the tail of a non-empty list
- regression and unit tests for first-class builtin behavior

## 4. Out Of Scope

This slice explicitly excludes:

- builtin partial application for multi-argument builtins
- `append`, `size`, `map`, `filter`, `all`, and `reduce`
- tuple-like list construction with `(x,y,z)`
- pattern matching
- lazy evaluation
- recursive definitions or `fix`
- object or collection builtins

## 5. User-Facing Behavior

Accepted examples:

- `hd(1:nil).` => `1`
- `tl(1:2:nil).` => `2:nil`
- `tl(1:nil).` => `nil`
- `hd("a":nil).` => `"a"`
- `hd((1:nil):nil).` => `1:nil`
- `f:=hd; f(1:nil).` => `1`
- `apply(f,x):=f x; apply(hd, 1:nil).` => `1`
- `id(x):=x; id(hd)(1:nil).` => `1`
- `hd == hd.` => `true`
- `hd != tl.` => `true`

Error examples:

- `hd nil.` => `ENACT_ERR_LIST_EMPTY`
- `tl nil.` => `ENACT_ERR_LIST_EMPTY`
- `hd 1.` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `tl true.` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `hd(1:nil, 2:nil).` => `ENACT_ERR_ARITY_MISMATCH`

## 6. Syntax Requirements

No new lexer or parser tokens are required.

Builtin names remain ordinary identifiers. They are resolved from the evaluator's default environment.

This keeps builtin names shadowable by ordinary assignment:

```text
hd:=x::x; hd 4.
```

shall evaluate to:

```text
4
```

## 7. Semantic Requirements

At the start of a top-level evaluation, the evaluator shall install builtin bindings into the environment:

```text
hd -> builtin hd
tl -> builtin tl
```

`hd list` shall:

1. require exactly one argument
2. require that argument to be a list
3. fail with `ENACT_ERR_LIST_EMPTY` when the argument is `nil`
4. return a copy of the head value

`tl list` shall:

1. require exactly one argument
2. require that argument to be a list
3. fail with `ENACT_ERR_LIST_EMPTY` when the argument is `nil`
4. return the tail list

Builtin arguments shall use the existing eager argument evaluation behavior.

Arity validation shall happen before argument evaluation, matching user-defined function calls.

## 8. Runtime Value Requirements

Add a builtin value kind that stores a pointer to an immutable builtin descriptor.

Builtin values shall:

- copy by pointer
- free as a no-op
- compare by descriptor identity
- print as `<function>`

Comparing builtin values with non-builtin values remains a cross-kind equality mismatch.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- `hd` of an integer list
- `tl` of a two-element list
- `tl` of a singleton list
- `hd` of a string list
- `hd` of a nested list
- builtin assigned to another name
- builtin passed to a higher-order function
- builtin returned from an identity function and then called
- builtin captured in a closure
- builtin name shadowing
- builtin equality
- builtin inequality

## 10. Robustness Requirements

The regression suite shall include:

- `hd nil`
- `tl nil`
- `hd` with a non-list argument
- `tl` with a non-list argument
- zero-argument builtin call syntax
- too many builtin arguments
- eager argument evaluation failure
- builtin value used as a boolean
- builtin value used as an integer
- builtin value used as a cons tail
- builtin compared with a non-builtin value

## 11. Acceptance Criteria

This slice is accepted when:

- `hd` and `tl` are available in the default environment
- builtin values can be copied, stored, assigned, compared, and passed
- existing call syntax dispatches to builtins without parser special-cases
- `hd` and `tl` reject `nil` with `ENACT_ERR_LIST_EMPTY`
- `hd` and `tl` reject non-list arguments with `ENACT_ERR_TYPE_EXPECTED_LIST`
- previous Slice 001 through Slice 013 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
