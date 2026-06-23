# Slice 112: Empty Predicate Core Design

## Overview

`isEmpty(value)` is implemented as a small value predicate beside `isNil` in `src/builtin.c`. It recognizes empty native lists and empty collection objects, and returns `false` for all other value kinds.

## Runtime Behavior

- For `ENACT_VALUE_LIST`, the predicate returns whether `as_list == NULL`.
- For `ENACT_VALUE_OBJECT`, the predicate first checks `enact_object_collection_kind(...)`.
- Object values are empty only when their collection kind is not `ENACT_COLLECTION_NONE` and `enact_object_collection_items(...) == NULL`.
- All non-list and non-collection-object values return `false`.

## Error Handling

The implementation deliberately does not call `enact_builtin_require_list_or_collection`. That helper is correct for operations that require a list or collection payload, but `isEmpty` is a predicate and should answer `false` for mismatched runtime types.

Normal call validation still applies before the builtin body runs:

- wrong arity fails with `ENACT_ERR_ARITY_MISMATCH`
- unbound argument expressions fail with `ENACT_ERR_NAME_UNBOUND`
- failing argument expressions preserve their original diagnostics

## Tests

Slice 112 adds functional regression cases for:

- empty list spellings and list-producing empty results
- empty Set/Bag values, including subclass-derived collection objects
- non-empty list, Set, and Bag values
- scalar, symbol, class, callable, and plain-object false cases
- higher-order use through `map`, `filter`, and `all`
- callable parameter metadata and shadowing
- arity, evaluation, and misuse robustness cases

Unit tests cover builtin lookup, arity, default environment installation, scalar/list/object direct calls, and empty Set/Bag direct calls.
