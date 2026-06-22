# Slice 111: Nil Predicate Core Requirements

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slices:

- [docs/slices/013-list-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/013-list-core-requirements.md)
- [docs/slices/023-list-compatibility-requirements.md](/home/tprover/2606_enact_auto/docs/slices/023-list-compatibility-requirements.md)
- [docs/slices/110-scalar-list-type-predicate-helpers-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/110-scalar-list-type-predicate-helpers-phase-2-requirements.md)

## Goal

Add an exact empty-list predicate:

```text
isNil(value)
```

This closes the narrow deferred predicate from Slice 110 without broadening into general emptiness for Set or Bag values.

## Functional Requirements

- Add a builtin named `isNil`.
- `isNil` shall have arity one.
- `isNil` shall return a boolean value.
- `isNil(value)` shall return `true` only when `value` is the empty list value.
- `nil` and `()` shall both return `true`.
- Non-empty lists, including `1:nil`, tuple-like lists, and `list(nil)`, shall return `false`.
- Empty Set and Bag collection objects shall return `false`.
- All non-list values shall return `false`.
- Type mismatches shall return `false`; they shall not report type errors.
- `isNil` shall be a normal first-class builtin and support existing builtin partial-application and shadowing behavior.

## Boundary Examples

```text
isNil(nil)       -> true
isNil(())        -> true
isNil(tl(1:nil)) -> true

isNil(1:nil)     -> false
isNil((1,2))     -> false
isNil(list(nil)) -> false
isNil(set())     -> false
isNil(bag())     -> false
```

## Predicate Compatibility

`isNil` is intentionally narrower than both `atom` and `isList`:

```text
atom(nil)   -> true
isList(nil) -> true
isNil(nil)  -> true

atom(1)     -> true
isNil(1)    -> false

isList(1:nil) -> true
isNil(1:nil)  -> false
```

## Error Requirements

- Arity errors shall use the existing builtin arity diagnostics.
- Argument evaluation errors shall propagate normally.
- Type mismatches are not errors for this predicate; non-matching values return `false`.

## Non-Goals

- Do not add a general `isEmpty` predicate in this slice.
- Do not classify empty Set or Bag objects as nil.
- Do not change the existing `atom` or `isList` semantics.
- Do not add `typeOf`, `typeName`, or structured runtime type records.

## Regression Requirements

- Add boundary tests for `nil`, `()`, list operations producing nil, non-empty lists, scalar values, symbols, functions, classes, objects, Set, and Bag.
- Add higher-order tests with `map`, `filter`, and `all`.
- Add robustness tests for arity mismatch, argument evaluation failure, boolean-result misuse, higher-order misuse, and user shadowing.
- Keep handwritten source coverage reporting unchanged.
