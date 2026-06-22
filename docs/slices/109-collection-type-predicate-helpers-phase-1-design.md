# Slice 109: Collection Type Predicate Helpers Phase 1 Design

Related requirements: [docs/slices/109-collection-type-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/109-collection-type-predicate-helpers-phase-1-requirements.md)

## Contract

The new builtins are:

```text
isCollection(value)
isSet(value)
isBag(value)
```

They return booleans and never report type errors for non-matching values.

## Runtime Boundary

The predicates classify object values by `EnactCollectionKind`:

```c
enact_object_collection_kind(object)
```

The shared helper first requires the value kind to be `ENACT_VALUE_OBJECT`; all non-object values classify as `ENACT_COLLECTION_NONE`.

## Predicate Semantics

`isCollection` is true for Set-like and Bag-like object values:

```text
isCollection(set()) -> true
isCollection(bag()) -> true
isCollection(new Object) -> false
```

`isSet` and `isBag` refine that classification:

```text
isSet(set()) -> true
isSet(bag()) -> false

isBag(bag()) -> true
isBag(set()) -> false
```

## Class Values

The predicates classify runtime object values, not class values:

```text
isSet(Set) -> false
isBag(Bag) -> false
```

This keeps them aligned with `isObject` and avoids introducing class-level type predicates. Class-level checks can be added later if they become useful.

## Subclasses

Object construction already stores a collection kind derived from the class inheritance graph. Therefore subclasses work without a special case:

```text
class MySet < Set
isSet(new MySet) -> true

class MyBag < Bag
isBag(new MyBag) -> true
```

## First-Class Behavior

All three predicates use the shared `value` parameter metadata:

```text
callableParams(isCollection) -> 'value:nil
callableParams(isSet) -> 'value:nil
callableParams(isBag) -> 'value:nil
```

Existing builtin shadowing remains unchanged:

```text
isCollection:=x::false
isCollection(set()) -> false
```

## Deferred Work

This slice does not add scalar predicates, class-level collection predicates, or a general `typeOf` helper.
