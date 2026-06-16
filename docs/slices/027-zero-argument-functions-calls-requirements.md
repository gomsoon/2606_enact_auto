# Slice 027: Zero-Argument Functions and Calls Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/026-manual-style-conditional-requirements.md](/home/tprover/2606_enact_auto/docs/slices/026-manual-style-conditional-requirements.md)

## 1. Slice Goal

This slice supports nullary user functions and explicit zero-argument calls:

```text
f():=1
f()
()::1
```

The feature closes the gap between the manual-style call syntax and the current function model, so named functions, lambdas, recursion, fixed definitions, and higher-order helpers can represent delayed computations with no explicit input.

## 2. Source Basis

The manual uses parenthesized empty calls in several places, including examples such as `time()` and object-style calls such as `A.f()`. Object dispatch remains out of scope, but the empty-call core is needed before those later forms can be considered.

## 3. In Scope

This slice includes:

- empty parenthesized calls: `f()`
- named zero-argument definitions: `f():=expr`
- zero-argument lambdas: `()::expr`
- zero-argument calls on returned functions: `make()()`
- recursive named zero-argument functions
- `fix` definitions containing zero-argument functions
- higher-order use of nullary functions through existing call helpers
- regression tests for arity, parsing, delayed evaluation, recursion, and non-function calls

## 4. Out Of Scope

This slice explicitly excludes:

- adding new zero-argument builtins such as `time()` or `version()`
- object/member dispatch such as `A.f()`
- treating `f ()` differently from `f()`
- allowing empty stages inside curried definition left-hand sides such as `f(x)():=x` or `f()(x):=x`
- changing `()` as a list literal; it still evaluates to `nil` when used as a primary expression

## 5. User-Facing Behavior

Accepted examples:

- `f():=1; f().` => `1`
- `f():=true; f().` => `true`
- `f():=(1,2); f().` => `1:2:nil`
- `(()::7)().` => `7`
- `f:=()::7; f().` => `7`
- `apply0(f):=f(); thunk():=5; apply0(thunk).` => `5`
- `fact fix (fact():=1); fact().` => `1`
- `(a,b) fix (a():=1; b():=a()+1); b().` => `2`
- `f():=1; map(x::f(),(1,2,3)).` => `1:1:1:nil`

Error examples:

- `f().` => `ENACT_ERR_NAME_UNBOUND`
- `1().` => `ENACT_ERR_TYPE_EXPECTED_FUNCTION`
- `f(x):=x; f().` => `ENACT_ERR_ARITY_MISMATCH`
- `f():=1; f(1).` => `ENACT_ERR_ARITY_MISMATCH`
- `size().` => `ENACT_ERR_ARITY_MISMATCH`
- `f(x)():=x.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`

## 6. Syntax Requirements

The parser shall accept an empty argument list after any call expression:

```text
call ::= call "(" ")"
```

The parser shall accept an empty lambda parameter list:

```text
lambda_head ::= "(" ")"
```

For assignment lowering, `f():=expr` shall become a recursive named function assignment with an empty parameter list.

Nested empty stages on function-definition left-hand sides shall be rejected so `f(x)():=x` and `f()(x):=x` do not silently collapse into another arity.

## 7. Evaluation Requirements

A callable with remaining arity zero shall accept exactly zero arguments and evaluate its body.

A callable with remaining arity greater than zero shall reject a zero-argument call with `ENACT_ERR_ARITY_MISMATCH`.

A zero-argument call shall not allocate or evaluate an argument array. This avoids treating implementation-defined `calloc(0, ...)` behavior as an out-of-memory failure.

Arity checking shall continue to happen before evaluating arguments, so examples such as:

```text
f():=1; f(1/0)
```

return `ENACT_ERR_ARITY_MISMATCH`, not `ENACT_ERR_DIVIDE_BY_ZERO`.

## 8. Boundary Analysis Requirements

The regression suite shall include:

- tokenization for `f()`
- tokenization for `f():=1`
- tokenization for `()::1`
- zero-argument functions returning int, bool, string, nil, and list values
- zero-argument functions returning functions
- zero-argument lambda calls
- assignment from a zero-argument function result
- captured environment behavior
- local assignment inside a zero-argument function
- higher-order `apply0`
- recursive and fixed zero-argument definitions
- conditionals, arithmetic, equality, `atom`, `list`, `map`, and `reduce` interaction

## 9. Robustness Requirements

The regression suite shall include:

- unbound zero-argument call
- non-function zero-argument call
- nil/list zero-argument call
- under-applied non-nullary functions
- over-applied nullary functions
- over-applied nullary calls that must not evaluate impossible arguments
- builtins called with zero arguments
- zero-argument lambda over-application
- invalid empty-stage definition left-hand sides
- invalid empty-parameter function definition arguments
- missing names inside a nullary body
- nullary function values used as integers
- higher-order list builtins receiving a nullary callable when they require a unary or binary callable

## 10. Acceptance Criteria

This slice is accepted when:

- `f():=expr; f().` evaluates `expr`
- `()::expr` creates a callable with arity zero
- zero-argument recursive named functions and `fix` definitions work
- existing non-nullary functions still reject `f()` with `ENACT_ERR_ARITY_MISMATCH`
- existing builtins still reject zero-argument calls with `ENACT_ERR_ARITY_MISMATCH`
- handwritten source coverage remains reported separately from generated parser/lexer coverage
