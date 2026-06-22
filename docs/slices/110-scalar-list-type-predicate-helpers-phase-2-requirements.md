# Slice 110: Scalar/List Type Predicate Helpers Phase 2 Requirements

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slices:

- [docs/slices/013-list-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/013-list-core-requirements.md)
- [docs/slices/034-quoted-atoms-symbol-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/034-quoted-atoms-symbol-core-requirements.md)
- [docs/slices/108-type-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/108-type-predicate-helpers-phase-1-requirements.md)
- [docs/slices/109-collection-type-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/109-collection-type-predicate-helpers-phase-1-requirements.md)

## Goal

Add exact value-kind predicates for scalar and list-shaped runtime values:

```text
isInt(value)
isBool(value)
isString(value)
isList(value)
isSymbol(value)
```

These complete the first practical predicate family after `isObject`, `isClass`, `isCallable`, `isCollection`, `isSet`, and `isBag`.

## Functional Requirements

- Add a builtin named `isInt`.
- Add a builtin named `isBool`.
- Add a builtin named `isString`.
- Add a builtin named `isList`.
- Add a builtin named `isSymbol`.
- All five builtins shall have arity one.
- All five builtins shall return boolean values.
- `isInt(value)` shall return `true` only for integer values.
- `isBool(value)` shall return `true` only for boolean values.
- `isString(value)` shall return `true` only for string values.
- `isList(value)` shall return `true` for every runtime list value, including `nil`, `()`, cons-built lists, tuple-like lists, and `list(value)` results.
- `isSymbol(value)` shall return `true` only for quoted symbol/atom values.
- Type mismatches shall return `false`; they shall not report type errors.
- The predicates shall be normal first-class builtins and support existing builtin partial-application and shadowing behavior.

## Boundary Examples

```text
isInt(1)       -> true
isInt(true)    -> false

isBool(true)   -> true
isBool(false)  -> true
isBool(1)      -> false

isString("x")  -> true
isString('x)   -> false

isList(nil)    -> true
isList(())     -> true
isList((1,2))  -> true
isList(set())  -> false

isSymbol('x)   -> true
isSymbol("x")  -> false
```

## Atom Compatibility

The existing `atom(value)` builtin is broader than `isSymbol(value)`:

```text
atom(1)        -> true
isSymbol(1)    -> false

atom(nil)      -> true
isList(nil)    -> true
```

`isSymbol` is intentionally named to avoid redefining or narrowing `atom`.

## Error Requirements

- Arity errors shall use the existing builtin arity diagnostics.
- Argument evaluation errors shall propagate normally.
- Type mismatches are not errors for these predicates; non-matching values return `false`.

## Non-Goals

- Do not add `isNil` in this slice.
- Do not add `isNumber`; the runtime currently has only integer numbers.
- Do not add `typeOf`, `typeName`, or structured runtime type records.
- Do not change the existing `atom` semantics.
- Do not classify Set and Bag objects as lists.

## Regression Requirements

- Add boundary tests for exact scalar matches and cross-type false results.
- Add list boundary tests for `nil`, `()`, cons lists, tuple-like lists, and collection objects.
- Add symbol boundary tests showing the difference between quoted symbols and strings.
- Add higher-order tests with `map`, `filter`, and `all`.
- Add robustness tests for arity mismatch, argument evaluation failure, boolean-result misuse, higher-order misuse, and user shadowing.
- Keep handwritten source coverage reporting unchanged.
