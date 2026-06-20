# Slice 071: Bag Algebraic Operations Phase 1 Design

Related requirements: [docs/slices/071-bag-algebraic-operations-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/071-bag-algebraic-operations-phase-1-requirements.md)

## Same Builtin Surface

`union`, `difference`, and `intersection` keep their original names and arity:

```text
union(left, right)
difference(left, right)
intersection(left, right)
```

Ordinary lists still take the existing list path. Object-backed collections use the same-kind collection validation introduced for `subset` and `equal`:

```text
Set + Set -> Set-style operation
Bag + Bag -> Bag-style operation
Set + Bag -> ENACT_ERR_TYPE_EXPECTED_LIST
Bag + Set -> ENACT_ERR_TYPE_EXPECTED_LIST
```

This keeps duplicate-suppressed and multiplicity-aware semantics explicit instead of silently converting between collection kinds.

## Bag Multiplicity Helpers

Bag algebra is implemented over each collection object's hidden payload list. A shared count helper compares values through `enact_value_equal`, so strings, atoms, classes, functions, and object identity use the same equality model as the rest of the runtime.

The resulting multiplicity rules are:

```text
union:        max(left_count, right_count)
difference:  max(left_count - right_count, 0)
intersection:min(left_count, right_count)
```

`union` is built as Bag difference plus append:

```text
append(bag_difference(left, right), right)
```

This mirrors the existing list/Set union structure while swapping in multiplicity-aware difference.

## Result Construction

Collection results are wrapped with:

```c
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
```

The left operand is the prototype object, so Bag operations preserve the left operand's runtime class and user-visible attributes just like the existing Set operation path.

## Order-Agnostic Tests

The runtime still does not expose a stable user-facing collection iteration order. Regression tests verify Bag-operation results through `equal`, `size`, `member`, `subset`, `reduce`, and `map(size, ...)` rather than relying on printing the hidden payload list.

## Deliberately Narrow Scope

This slice adds binary Bag algebra for `union`, `difference`, and `intersection` only. Bag-aware aggregate `UNION` is deferred in this slice and later added by Slice 072. Dot-method collection syntax and custom collection printing remain deferred.
