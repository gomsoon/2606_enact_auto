# Slice 113: Native Collection isEmpty Dot-Method Integration Design

## Overview

Slice 113 extends the native collection method table with a zero-visible-argument `isEmpty` entry. The underlying builtin remains the Slice 112 top-level `isEmpty(value)` predicate.

## Runtime Integration

The native collection method table entry is:

```c
{"isEmpty", ENACT_COLLECTION_METHOD_ANY, 0}
```

This means:

- the method applies to both Set and Bag collection kinds.
- the receiver is inserted at builtin argument index `0`.
- the visible method arity is `enact_builtin_arity(isEmpty) - 1`, which is `0`.

No evaluator-specific dispatch branch is needed. The existing bound collection method path builds the builtin argument vector and delegates to `enact_builtin_apply_in_env`.

## Lookup And Shadowing

The established dot lookup order remains unchanged:

1. user-visible object attributes
2. user-defined class methods
3. native collection method table

Therefore:

- `set().isEmpty()` uses the native table entry.
- `set() with isEmpty:=f` dispatches to the attribute value.
- `Set.isEmpty():=...` dispatches to the user-defined class method.
- `isEmpty:=...` at top level does not affect native collection dot lookup.

## Introspection

Because Slice 104 and Slice 105 route native method signatures and effective method listings through the native collection method table, the new entry is automatically visible through:

- `methodArity`
- `methodParams`
- `hasMethod`
- `effectiveMethods`
- callable introspection on the bound method value

`methods` stays direct-user-method-only.

## Tests

Slice 113 adds regression coverage for:

- direct zero-argument dot-calls on empty and non-empty Set/Bag values
- bare bound method values and zero-argument application
- Set/Bag subclass receivers
- higher-order use through `map`, `filter`, and `all`
- callable and method introspection metadata
- native effective method listing order and count
- top-level, object-attribute, and user-defined class-method shadowing
- arity, non-receiver, and `nil` parameter-list robustness cases
