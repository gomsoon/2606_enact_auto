# Slice 024: Fix Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Manual source: `260614_enact_manual.pdf`, Appendix 1, p.232

Prerequisite slice: [docs/slices/023-list-compatibility-requirements.md](/home/tprover/2606_enact_auto/docs/slices/023-list-compatibility-requirements.md)

## 1. Slice Goal

This slice implements the manual's fixed-point operator core:

```text
(P,Q) fix (P:=...; Q:=...)
```

The purpose is to support mutually recursive function definitions, which were intentionally out of scope for Slice 022.

## 2. Source Basis

The manual describes `fix` as an operator for mutually recursive definitions. It gives examples in this shape:

```text
(P,Q) fix (P:=...; Q:=...)
(f,g) fix (f(x):=... g(x) ...; g(x):=... f(x) ...)
```

The manual also notes that the actual values are available during evaluation in a restricted way and that this operator is usually used for mutually recursive functions.

## 3. In Scope

This slice includes:

- lexer support for `fix`
- manual-style infix syntax
- fixed-name lists written as `(f,g,...)`
- single-name project extension syntax written as `f fix (...)`
- fixed definitions using named function syntax
- fixed definitions using assignment-bound lambda syntax
- mutually recursive functions
- fixed functions used through currying, partial application, and higher-order calls
- fixed functions preserving static capture of ordinary free variables
- fixed function values preserving their fixed peer bindings after outer rebinding
- regression and unit tests for parser, evaluator, and ownership helpers

## 4. Out Of Scope

This slice explicitly excludes:

- arbitrary fixed-point values that are not syntactic function definitions
- RHS expressions that only evaluate to function values at runtime
- non-function fixed bindings
- general lazy evaluation
- mutual recursion through `where`
- zero-argument functions
- object methods and `self`
- infinite recursion detection
- tail-call optimization

## 5. User-Facing Behavior

Accepted examples:

- `fact fix (fact(n):=1 if n==0 else n*fact(n-1)); fact(5).` => `120`
- `fact fix (fact:=n::1 if n==0 else n*fact(n-1)); fact(5).` => `120`
- `(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); even(4).` => `true`
- `(even,odd) fix (even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1)); odd(4).` => `false`
- `sum fix (sum(a,b):=b if a==0 else sum(a-1,b+a)); sum(3)(0).` => `6`
- `step:=2; count fix (count(n):=0 if n==0 else step+count(n-1)); step:=10; count(3).` => `6`

Error examples:

- `fix.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `(f,f) fix (f(n):=n).` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `(even,odd) fix (even(n):=true).` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `x fix (x:=1).` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `f fix (g(n):=n); f(1).` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `f fix (f(n):=f(n,1)); f(1).` => `ENACT_ERR_ARITY_MISMATCH`

## 6. Syntax Requirements

Add `fix` as a reserved token:

```text
fix => TOK_FIX
```

The parser shall accept:

```text
fix_expr ::= assignment "fix" assignment
```

The left assignment expression shall be validated as either:

```text
f
(f,g,...)
```

where each item is an identifier and duplicates are rejected.

The right assignment expression shall normally be parenthesized when it contains multiple definitions:

```text
(f,g) fix (f(x):=...; g(x):=...)
```

## 7. Semantic Requirements

The RHS shall be interpreted as a sequence of assignments. For this core slice:

- every fixed name must be assigned exactly once
- every RHS assignment name must appear in the fixed-name set
- every fixed assignment RHS must be a syntactic function literal
- both `f(x):=...` and `f:=x::...` are accepted when `f` is fixed

For each fixed function:

1. create a recursive function value using the fixed name as its self name
2. install peer fixed function values into its captured environment
3. assign all fixed function values into the current environment
4. return the last fixed function value as the expression result

## 8. Boundary Analysis Requirements

The regression suite shall include:

- tokenization of `fix`
- longer identifier containing `fix`
- tokenization of a fixed function expression
- single recursive factorial through named function syntax
- single recursive factorial through lambda assignment syntax
- nfib recursion
- recursive list length
- recursive list reverse
- mutually recursive even/odd predicates
- mutual recursion consumed by `map`
- cross-calling mutually recursive integer functions
- currying with a fixed function
- assigned partial fixed function
- higher-order fixed function call
- static outer capture
- saved fixed function after rebinding
- saved mutual fixed function after rebinding peers
- nested fixed function returned from a function
- self identity inside a fixed function body
- fixed function observed by `atom`
- fixed function used through `map`
- mutual fixed function forwarding

## 9. Robustness Requirements

The regression suite shall include:

- bare `fix` rejected
- duplicate fixed names rejected
- missing fixed assignment rejected
- assignment to a non-fixed name rejected
- non-function fixed RHS rejected
- non-assignment fixed body rejected
- fixed assignment name mismatch rejected
- fixed self-call arity mismatch
- mutual peer-call arity mismatch
- fixed call argument type failure
- fixed recursive body type failure
- fixed over-application does not evaluate impossible extra arguments
- ordinary assignment-bound lambda remains non-recursive
- fixed lambda self-call arity mismatch
- fixed over-application with body not evaluated
- fixed arithmetic argument type failure
- fixed list failure

## 10. Acceptance Criteria

This slice is accepted when:

- manual-style infix `fix` parses without grammar conflicts
- fixed definitions install all declared function names
- fixed functions can call themselves and fixed peers
- fixed functions preserve ordinary static capture
- fixed functions preserve fixed peer bindings after outer rebinding
- non-function or malformed fixed definitions fail deterministically
- previous Slice 001 through Slice 023 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
