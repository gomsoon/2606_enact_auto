# Slice 109: Collection Type Predicate Helpers Phase 1 Requirements

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slices:

- [docs/slices/055-set-bag-constructor-scaffolding-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/055-set-bag-constructor-scaffolding-core-requirements.md)
- [docs/slices/056-collection-payload-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/056-collection-payload-core-requirements.md)
- [docs/slices/108-type-predicate-helpers-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/108-type-predicate-helpers-phase-1-requirements.md)

## Goal

Add runtime collection predicates:

```text
isCollection(value)
isSet(value)
isBag(value)
```

These extend Slice 108's predicate family with Set/Bag-aware object checks.

## Functional Requirements

- Add a builtin named `isCollection`.
- Add a builtin named `isSet`.
- Add a builtin named `isBag`.
- All three builtins shall have arity one.
- All three builtins shall return boolean values.
- `isCollection(value)` shall return `true` only for object values whose runtime collection kind is Set or Bag.
- `isSet(value)` shall return `true` only for object values whose runtime collection kind is Set.
- `isBag(value)` shall return `true` only for object values whose runtime collection kind is Bag.
- Plain objects, class values, functions, builtins, lists, atoms, strings, booleans, integers, and nil shall return `false`.
- User-defined subclasses of `Set` and `Bag` shall be classified through their object runtime collection kind.
- The `Set` and `Bag` class values themselves shall return `false`; the predicates classify runtime object values, not class metadata.
- The predicates shall be normal first-class builtins and support existing builtin partial-application and shadowing behavior.

## Boundary Examples

```text
isCollection(set()) -> true
isCollection(bag()) -> true
isCollection(new Object) -> false

isSet(set()) -> true
isSet(bag()) -> false
isSet(Set) -> false

isBag(bag()) -> true
isBag(set()) -> false
isBag(Bag) -> false
```

Subclasses keep the collection kind inherited at object construction time:

```text
class MySet < Set
isSet(new MySet) -> true

class MyBag < Bag
isBag(new MyBag) -> true
```

## Error Requirements

- Arity errors shall use the existing builtin arity diagnostics.
- Argument evaluation errors shall propagate normally.
- Type mismatches are not errors for these predicates; non-matching values return `false`.

## Non-Goals

- Do not add class-level collection predicates.
- Do not add `typeOf` or structured runtime type records.
- Do not change collection constructors, collection method dispatch, or collection equality semantics.

## Regression Requirements

- Add boundary tests for Set, Bag, plain objects, Set/Bag subclasses, predefined class values, scalar values, lists, functions, builtins, builtin partials, and user-visible collection attributes.
- Add robustness tests for arity mismatch, argument evaluation failure, boolean-result misuse, higher-order misuse, and user shadowing.
- Keep handwritten source coverage reporting unchanged.
