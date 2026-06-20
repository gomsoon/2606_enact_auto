# Slice 070: Bag Multiplicity Predicates Design

Related requirements: [docs/slices/070-bag-multiplicity-predicates-requirements.md](/home/tprover/2606_enact_auto/docs/slices/070-bag-multiplicity-predicates-requirements.md)

## Predicate Surface

`subset` and `equal` now accept two same-kind collection operands:

```text
subset(set, set) -> bool
subset(bag, bag) -> bool
equal(set, set)  -> bool
equal(bag, bag)  -> bool
```

Mixed `Set`/`Bag` pairs stay unsupported. This avoids silently choosing either duplicate-suppressed or multiplicity-aware semantics for ambiguous calls.

## Same-Kind Validation

The implementation validates both operands as collection objects and then checks their `EnactCollectionKind` values. A kind mismatch reports the same collection helper diagnostic used elsewhere:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

This preserves existing rejection behavior for ordinary lists, classes, non-collection objects, and mixed collection kinds.

## Bag Multiplicity

Set subset keeps the existing membership-based helper. Bag subset uses occurrence counts:

```text
count(left, value) <= count(right, value)
```

The count helper delegates value comparison to `enact_value_equal`, so strings, atoms, classes, functions, and object identity follow the same equality rules as existing list and collection operations.

## Equality

Both Set and Bag equality remain mutual subset:

```text
equal(left, right) == subset(left, right) and subset(right, left)
```

For Bags this makes equality independent of payload order while still preserving duplicate counts.

## Deliberately Narrow Scope

This slice does not define Bag-aware binary `union`, `difference`, or `intersection`; Slice 071 later adds those operations. Bag-aware aggregate `UNION` is deferred in this slice and later added by Slice 072. This slice also does not change collection printing or introduce dot-method collection syntax. Slice 073 later adds kind-aware collection payload display.
