# Slice 016: Builtin Partial Application Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/015-list-builtins-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/015-list-builtins-phase-2-requirements.md)

## 1. Slice Goal

This slice lets builtin functions participate in currying and partial application.

After this slice, under-applying a multi-argument builtin returns a first-class function-like value that captures the supplied prefix arguments:

```text
append(1:nil)
```

evaluates to:

```text
<function>
```

and can later be completed:

```text
append(1:nil)(2:nil)
```

evaluates to:

```text
1:2:nil
```

## 2. Source Basis

The PRD records:

- functions are first-class values
- currying and partial application are part of the function feature set
- builtin list functions include `append` and `size`

Slices 011 and 012 already implement partial application for user-defined functions. Slices 014 and 015 add first-class builtin values, but builtin under-application still fails with arity mismatch.

## 3. In Scope

This slice includes:

- a runtime builtin partial value
- reference-counted ownership for captured prefix arguments
- builtin partial copy/free/equality support
- call evaluator support for:
  - builtin under-application
  - completing a builtin partial
  - extending a builtin partial one or more arguments at a time
- `<function>` printing for builtin partial values
- regression and unit tests for builtin partial creation, completion, capture timing, and errors

## 4. Out Of Scope

This slice explicitly excludes:

- non-prefix partial application
- placeholder arguments
- zero-argument calls
- over-application
- partially applying unary builtins with zero arguments
- `map`, `filter`, `all`, and `reduce`
- recursive definitions or `fix`

## 5. User-Facing Behavior

Accepted examples:

- `append(1:nil).` => `<function>`
- `append(1:nil)(2:nil).` => `1:2:nil`
- `p:=append(1:nil); p(2:nil).` => `1:2:nil`
- `append(nil)(1:nil).` => `1:nil`
- `append(1:nil) nil.` => `1:nil`
- `(append(1:nil)) (2:nil).` => `1:2:nil`
- `apply(f,x):=f x; apply(append(1:nil), 2:nil).` => `1:2:nil`
- `make(f):=x::f x; append1:=make(append(1:nil)); append1(2:nil).` => `1:2:nil`
- `xs:=1:nil; p:=append(xs); xs:=2:nil; p(3:nil).` => `1:3:nil`
- `append(1:nil) == append(1:nil).` => `false`

Error examples:

- `append(1).` => `<function>` succeeds, but `append(1)(nil).` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `append(1:nil)(2:nil, 3:nil).` => `ENACT_ERR_ARITY_MISMATCH`
- `size(1:nil, 2:nil).` => `ENACT_ERR_ARITY_MISMATCH`
- `append(1:nil)(1/0).` => `ENACT_ERR_DIVIDE_BY_ZERO`
- `append(1:nil)+1.` => `ENACT_ERR_TYPE_EXPECTED_INT`

## 6. Semantic Requirements

Calling a builtin shall use the same arity split as user-defined functions:

```text
supplied < arity   -> return partial builtin value
supplied == arity  -> apply builtin
supplied > arity   -> ENACT_ERR_ARITY_MISMATCH
```

Calling a builtin partial shall combine the already captured prefix with the newly supplied arguments:

```text
captured + supplied < arity   -> return extended partial builtin value
captured + supplied == arity  -> apply builtin
captured + supplied > arity   -> ENACT_ERR_ARITY_MISMATCH
```

Prefix arguments are evaluated eagerly when the partial value is created.

Builtin body/type validation happens only when the builtin has enough arguments to apply. This matches the delayed body evaluation behavior of user-defined partial functions.

## 7. Runtime Value Requirements

Add an opaque builtin partial runtime object:

```c
typedef struct EnactBuiltinPartial EnactBuiltinPartial;
```

It shall contain:

- reference count
- pointer to the immutable builtin descriptor
- owned array of captured `EnactValue` prefix arguments
- captured argument count

Builtin partial values shall:

- copy by retaining the partial object
- free by releasing the partial object
- compare by partial-object identity
- print as `<function>`

## 8. Boundary Analysis Requirements

The regression suite shall include:

- direct partial creation
- direct partial completion
- assigned partial completion
- partial with nil prefix
- whitespace completion
- parenthesized whitespace completion
- higher-order partial application
- returned closure using a builtin partial
- eager capture of prefix arguments
- completing a partial with a string list
- partial equality false for independently-created partials
- partial copy through assignment

## 9. Robustness Requirements

The regression suite shall include:

- invalid prefix type is delayed until completion
- invalid suffix type at completion
- over-applying a partial
- unary builtin over-application remains an arity mismatch
- completion argument evaluation failure
- partial value used as an integer
- partial value used as a boolean
- partial value used as a cons tail
- partial compared with non-function value
- missing completion still prints as function

## 10. Acceptance Criteria

This slice is accepted when:

- multi-argument builtins can be partially applied
- partial builtins are first-class assignable/passable values
- captured prefix arguments are copied at partial creation time
- completing a partial preserves existing builtin type/error behavior
- over-application still reports `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments
- previous Slice 001 through Slice 015 behavior remains green, except Slice 015 under-application robustness cases superseded by this feature
- handwritten source coverage remains reported separately from generated parser/lexer coverage
