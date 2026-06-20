# Slice 073: Collection Display / Printing Core Design

Related requirements: [docs/slices/073-collection-display-printing-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/073-collection-display-printing-core-requirements.md)

## Printer-Only Change

This slice changes the command-line value printer in `main.c`. Runtime values, equality, membership, collection construction, and evaluator semantics stay unchanged.

The object branch now checks:

```c
enact_object_collection_kind(object)
```

before falling back to the ordinary object display. Non-collection objects still print as:

```text
<object ClassName>
```

## Display Forms

Collection values print by collection kind:

```text
set()
bag()
set(1:2:nil)
bag(1:1:2:nil)
```

The payload part delegates to the existing list printer. This keeps nested list, string, atom, class, function, object, and nested collection display consistent with established CLI output.

## Subclasses

Objects whose class inherits from `Set` or `Bag` already carry a collection kind. This slice prints them with the same `set(...)` or `bag(...)` form as root collection objects.

The printed form intentionally does not include the concrete subclass or user-visible attributes. Those remain available through:

```text
classof(collection)
attrs(collection)
```

## Ordering

Set and Bag display exposes the current hidden payload order. This makes REPL output useful without adding a sorting or canonicalization layer.

For Sets, this means display is deterministic for a given construction path but not a mathematical ordering guarantee. A later slice may add sorted or canonical display if the project wants a stronger user-visible contract.

## Deliberately Narrow Scope

This slice does not change collection semantics, does not add dot-method collection syntax, and does not introduce tuple-like or comma-style collection display. It only replaces opaque collection object printing with kind-aware payload display. Slice 074 later begins dot-method collection syntax for `size`, `member`, `insert`, and `remove`.
