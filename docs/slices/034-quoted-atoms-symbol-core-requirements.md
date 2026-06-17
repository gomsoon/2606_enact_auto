# Slice 034: Quoted Atoms / Symbol Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/021-atom-builtin-requirements.md](/home/tprover/2606_enact_auto/docs/slices/021-atom-builtin-requirements.md)

## 1. Slice Goal

This slice adds quoted atom literals as the first symbol-like runtime value:

```text
'hello.
```

The value is distinct from strings and prints back with the leading quote.

## 2. Source Basis

The PRD includes atom-oriented behavior through the `atom` builtin and the manual-style language has a symbol vocabulary that should not be modeled as strings.

Slices 021 through 033 already provide the supporting runtime:

- `atom` can classify non-list values
- equality is kind-sensitive
- lists and set-like builtins can carry arbitrary values
- scripts and `load` can preserve top-level values across a session

## 3. In Scope

This slice includes:

- a lexer token for quoted atoms
- parser support for atom literals in ordinary expression positions
- an AST literal kind for atoms
- a runtime value kind separate from strings
- deep copy, free, and equality support for atoms
- printing atoms as `'name`
- `atom('name)` returning `true`
- atoms flowing through lists, higher-order builtins, set builtins, assignments, functions, and `load`
- regression and unit tests for the above

## 4. Syntax Boundary

Quoted atoms use an identifier-shaped payload:

```text
'name
'_name123
'true
'load
```

The quote is part of the literal syntax, not a standalone quote operator.

Reserved words are allowed after the quote because the quoted payload is not parsed as an identifier token.

## 5. Out Of Scope

This slice explicitly excludes:

- single-quoted strings
- atom names with whitespace, punctuation, or escape sequences
- quoted list/data syntax beyond one atom literal
- an atom interning table
- object/class dispatch or slot lookup
- changing the `atom` builtin's existing list-vs-non-list rule

## 6. User-Facing Behavior

Accepted examples:

- `'hello.` => `'hello`
- `'true.` => `'true`
- `'load.` => `'load`
- `atom('hello).` => `true`
- `'hello=='hello.` => `true`
- `'hello!="world".` fails because strings and atoms are different kinds
- `('a,'b).` => `'a:'b:nil`
- `member('a,('b,'a)).` => `true`
- `filter(x::x!='skip,('keep,'skip,'also)).` => `'keep:'also:nil`

Malformed examples:

- `'.` => `ENACT_ERR_LEX_INVALID_CHAR`
- `'1.` => `ENACT_ERR_LEX_INVALID_CHAR`
- `'hello+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `not 'hello.` => `ENACT_ERR_TYPE_EXPECTED_BOOL`
- `'hello=="hello".` => `ENACT_ERR_TYPE_EQUALITY_MISMATCH`

## 7. Runtime Semantics

Atoms are immutable scalar values.

They compare equal only to atoms with identical payload text. They do not compare equal to strings, even when the visible payload is the same.

Atoms are non-list values, so the existing `atom` builtin returns `true` for them.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- tokenization of ordinary atoms
- tokenization of atom payloads matching reserved words
- direct printing
- equality and inequality
- assignment and lookup
- list construction and printing
- set/list builtins such as `member` and `remove`
- higher-order builtins such as `map`, `filter`, and `exists`
- function return values
- loaded script values

## 9. Robustness Requirements

The regression suite shall include:

- bare quote
- quote followed by a non-identifier starter
- arithmetic misuse
- boolean misuse
- atom/string equality mismatch
- relational misuse
- call misuse
- cons tail misuse
- list builtin misuse
- `where` binding with quoted atom on the left side

## 10. Acceptance Criteria

This slice is accepted when:

- quoted atom literals parse and evaluate successfully
- atoms are represented by a dedicated runtime value kind
- string values and atom values remain distinct
- atom values print with the leading quote
- existing builtins can carry atom values without special cases
- all regression and unit tests pass
