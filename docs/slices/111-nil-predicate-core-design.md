# Slice 111: Nil Predicate Core Design

Related requirements: [docs/slices/111-nil-predicate-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/111-nil-predicate-core-requirements.md)

## Contract

The new builtin is:

```text
isNil(value)
```

It returns a boolean and never reports type errors for non-matching values.

## Runtime Mapping

`nil` is represented as a list value with a null payload:

```c
value.kind == ENACT_VALUE_LIST && value.as.as_list == NULL
```

`isNil` maps exactly to that runtime shape.

## Predicate Boundary

The predicate is narrower than `isList`:

```text
isList(nil)  -> true
isNil(nil)   -> true

isList(1:nil) -> true
isNil(1:nil)  -> false
```

It is also narrower than `atom`, which remains a manual-style "not a non-empty list" helper:

```text
atom(1)  -> true
isNil(1) -> false
```

## Collection Boundary

Set and Bag values are object-backed collections. Even when their payload is empty, they are not the empty list:

```text
isNil(set()) -> false
isNil(bag()) -> false
```

General collection emptiness can be introduced later as a separate `isEmpty` style helper if needed.

## First-Class Behavior

`isNil` uses the shared `value` parameter metadata:

```text
callableParams(isNil) -> 'value:nil
```

Existing builtin shadowing remains unchanged:

```text
isNil:=x::false
isNil(nil) -> false
```

## Deferred Work

This slice does not add `isEmpty`, `isNumber`, class-level type predicates, or a general `typeOf` helper.
