# Slice 035: OO Keyword / Parser Scaffolding Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/034-quoted-atoms-symbol-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/034-quoted-atoms-symbol-core-requirements.md)

## 1. Slice Goal

This slice reserves the first object-oriented surface keywords without introducing object runtime values yet:

```text
class
new
with
```

The goal is to make later object-core slices safer by establishing token boundaries before grammar and evaluator behavior expand.

## 2. Source Basis

The PRD requires object-oriented features including:

- class definition syntax such as `class Node < Object.`
- object construction using `new`
- attribute initialization using `with`
- method bodies with `self`

The PRD's reserved-word list explicitly includes `class`, `new`, and `with`.

## 3. In Scope

This slice includes:

- lexer tokens for `class`, `new`, and `with`
- token-dump names for the new tokens
- regression tests proving the words are reserved
- regression tests proving prefix/similar identifiers still work
- parser rejection tests for not-yet-implemented OO forms
- documentation of the `self` decision
- documentation of newline terminator modernization as a separate follow-up

## 4. Out Of Scope

This slice explicitly excludes:

- class AST nodes
- class or object runtime value kinds
- `Object` installation in the default environment
- `new Object` evaluation
- `class C < Object` registration
- `with` attribute initialization semantics
- dot attribute access or method dispatch
- `self` as a global reserved word
- newline-based expression termination

## 5. `self` Boundary

`self` remains an ordinary identifier in this slice.

Reasons:

- the PRD describes `self` as a method-body binding, not as part of the reserved-word list
- existing recursive function and `fix` tests use `self` as a normal identifier
- method slices can later bind the ordinary name `self` in a method environment without breaking the functional core

This means:

```text
self:=4; self.
```

continues to evaluate to `4`.

## 6. Newline Terminator Follow-Up

The project should consider a separate terminator modernization slice that accepts top-level newline as an expression terminator, especially for REPL ergonomics.

That change is not included here because it affects:

- lexer treatment of newline trivia
- parser expectations around `TOK_DOT`
- script chunk splitting
- `load` execution
- TTY recovery behavior
- the future meaning of dot for object attribute access and method dispatch

Keeping it separate avoids mixing object keyword reservation with a broad top-level execution change.

## 7. User-Facing Behavior

Tokenization examples:

- `class Node < Object.` => `TOK_CLASS TOK_IDENTIFIER TOK_LT TOK_IDENTIFIER TOK_DOT TOK_EOF`
- `new Object.` => `TOK_NEW TOK_IDENTIFIER TOK_DOT TOK_EOF`
- `obj with x:=1.` => `TOK_IDENTIFIER TOK_WITH TOK_IDENTIFIER TOK_ASSIGN TOK_INT_LITERAL TOK_DOT TOK_EOF`
- `classy newer within self.` remains ordinary identifiers
- `'class 'new 'with.` remains atom literals

Current evaluation behavior:

- `class Node < Object.` fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `new Object.` fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `obj with x:=1.` fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `class:=1.` fails with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`

Accepted boundary examples:

- `classy:=1; classy.` => `1`
- `newer:=2; newer.` => `2`
- `within:=3; within.` => `3`
- `self:=4; self.` => `4`
- `('class,'new,'with).` => `'class:'new:'with:nil`

## 8. Boundary Analysis Requirements

The regression suite shall include:

- direct tokenization for `class`
- direct tokenization for `new`
- direct tokenization for `with`
- similar identifiers that should not become reserved words
- quoted atom payloads that match OO keywords
- successful assignment/lookup for similar identifiers
- successful assignment/lookup for ordinary `self`

## 9. Robustness Requirements

The regression suite shall include:

- class definition syntax rejected before implementation
- incomplete `class`
- malformed class-super syntax
- `new` expression rejected before implementation
- call-like `new(...)` rejected before implementation
- incomplete `new`
- `with` expression rejected before implementation
- leading `with` rejected before implementation
- assignment attempts to `class`, `new`, and `with`

## 10. Acceptance Criteria

This slice is accepted when:

- `class`, `new`, and `with` are emitted as dedicated tokens
- similarly named identifiers are unaffected
- `self` remains an ordinary identifier
- not-yet-implemented OO forms fail with stable parser diagnostics
- all regression and unit tests pass
