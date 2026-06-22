# Slice 108: Type Predicate Helpers Phase 1 Design

Related requirements: [docs/slices/108-type-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/108-type-predicate-helpers-phase-1-requirements.md)

## Contract

The new builtins are:

```text
isClass(value)
isCallable(value)
```

They return booleans and never report type errors for non-matching values.

## Class Predicate

`isClass` is a direct value-kind predicate:

```text
isClass(Object) -> true
isClass(new Object) -> false
```

It does not inspect inheritance or class names. Any class value is true, including predefined classes such as `Object`, `Set`, and `Bag`, and user-defined classes.

## Callable Predicate

`isCallable` uses the same runtime callable boundary as the existing callable metadata helpers. It returns `true` for:

- `ENACT_VALUE_FUNCTION`
- `ENACT_VALUE_BUILTIN`
- `ENACT_VALUE_BUILTIN_PARTIAL`
- `ENACT_VALUE_BOUND_OBJECT_METHOD`
- `ENACT_VALUE_BOUND_COLLECTION_METHOD`

The implementation factors that boundary into a small internal helper and reuses it from the existing callable validator. This keeps `isCallable(value)` aligned with `callableArity(value)`, `callableMinArity(value)`, `callableParams(value)`, and `callableArityRange(value)`.

## Naming

The public name is `isCallable`, not `isFunction`, because ENACT has several callable value shapes that are not stored as plain user-defined functions:

```text
isCallable(hd) -> true
isCallable(append(nil)) -> true
isCallable(set().size) -> true
```

## First-Class Behavior

Both predicates are normal builtins with the shared parameter metadata:

```text
callableParams(isClass) -> 'value:nil
callableParams(isCallable) -> 'value:nil
```

Existing builtin shadowing remains unchanged:

```text
isCallable:=x::false
isCallable(hd) -> false
```

## Deferred Work

This slice does not add collection-specific predicates such as `isSet`, `isBag`, or `isCollection`, and does not add a general `typeOf` helper.
