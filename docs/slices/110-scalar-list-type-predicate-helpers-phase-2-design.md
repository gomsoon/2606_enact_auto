# Slice 110: Scalar/List Type Predicate Helpers Phase 2 Design

Related requirements: [docs/slices/110-scalar-list-type-predicate-helpers-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/110-scalar-list-type-predicate-helpers-phase-2-requirements.md)

## Contract

The new builtins are exact value-kind predicates:

```text
isInt(value)
isBool(value)
isString(value)
isList(value)
isSymbol(value)
```

They return booleans and never report type errors for non-matching values.

## Runtime Mapping

Each predicate maps directly to `EnactValueKind`:

```text
isInt     -> ENACT_VALUE_INT
isBool    -> ENACT_VALUE_BOOL
isString  -> ENACT_VALUE_STRING
isList    -> ENACT_VALUE_LIST
isSymbol  -> ENACT_VALUE_ATOM
```

This keeps the implementation intentionally small and avoids adding a new runtime type description layer.

## List Boundary

`nil` is represented as an `ENACT_VALUE_LIST` with a null payload. Therefore it is still a list for exact type predicates:

```text
isList(nil) -> true
isList(())  -> true
```

Set and Bag values are object-backed collections, not list values:

```text
isList(set()) -> false
isList(bag()) -> false
```

## Symbol Boundary

The runtime stores quoted symbols as `ENACT_VALUE_ATOM`. The public predicate name is `isSymbol`, not `isAtom`, because the existing manual-style `atom` builtin already means "not a non-empty list":

```text
atom(1)      -> true
isSymbol(1)  -> false

atom('x)     -> true
isSymbol('x) -> true
```

## First-Class Behavior

All five predicates use the shared `value` parameter metadata:

```text
callableParams(isInt)    -> 'value:nil
callableParams(isBool)   -> 'value:nil
callableParams(isString) -> 'value:nil
callableParams(isList)   -> 'value:nil
callableParams(isSymbol) -> 'value:nil
```

Existing builtin shadowing remains unchanged:

```text
isInt:=x::false
isInt(1) -> false
```

## Deferred Work

This slice does not add `isNil`, `isNumber`, class-level type predicates, or a general `typeOf` helper.
