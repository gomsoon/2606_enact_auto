# Slice 112: Empty Predicate Core Requirements

## Goal

Add an `isEmpty(value)` builtin predicate that reports whether a value is an empty list-like container without treating ordinary scalar or object values as type errors.

## Functional Requirements

- `isEmpty(value)` must be available as a first-class builtin in the default environment.
- `isEmpty` must accept exactly one argument and return a boolean.
- `isEmpty(nil)`, `isEmpty(())`, and list-producing empty results such as `tl(1:nil)` must return `true`.
- `isEmpty(set())`, `isEmpty(bag())`, and empty Set/Bag-derived collection objects must return `true`.
- `isEmpty` must return `false` for non-empty lists, non-empty Sets, and non-empty Bags.
- `isEmpty` must return `false` for scalars, strings, symbols, class values, callables, and plain non-collection objects.
- `isEmpty` must preserve the current predicate style: invalid argument expressions still fail before the builtin runs, while non-empty-compatible values simply return `false`.

## Compatibility Requirements

- `isEmpty(nil)` must be consistent with `isNil(nil)`, but `isEmpty(set())` and `isEmpty(bag())` must be `true` while `isNil(...)` remains `false`.
- `isEmpty` must not change `isNil`, `isList`, `isCollection`, `size`, or collection traversal semantics.
- `isEmpty` must expose the same single parameter metadata style as other value predicates: `callableParams(isEmpty)` returns `'value:nil`.
- User bindings must be able to shadow the builtin using existing assignment rules.

## Non-Goals

- Do not add `isNonEmpty`, `empty?`, or a generalized `typeOf` feature.
- Do not make `isEmpty` enforce list or collection types with diagnostics.
- Do not change collection display order or collection construction behavior.
