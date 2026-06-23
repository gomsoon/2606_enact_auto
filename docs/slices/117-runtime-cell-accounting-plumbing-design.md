# Slice 117: Runtime Cell Accounting Plumbing Design

Related requirements: [docs/slices/117-runtime-cell-accounting-plumbing-requirements.md](/home/tprover/2606_enact_auto/docs/slices/117-runtime-cell-accounting-plumbing-requirements.md)

## Overview

Runtime cell accounting is implemented as a small process-wide counter module:

```c
void enact_runtime_stats_reset(void);
void enact_runtime_cell_allocated(void);
void enact_runtime_cell_released(void);
size_t enact_runtime_cells(void);
size_t enact_runtime_max_cells(void);
```

The counters live outside `EnactEnv` and `EnactSession`. That keeps the plumbing small and matches the current runtime, where default classes and retained values may outlive a single evaluation call through normal reference-counted ownership.

## Counting Rule

The accounting boundary is a ref-counted ENACT runtime value container, not every host allocation.

Tracked cells:

- `EnactList`
- `EnactFunction`
- `EnactClass`
- `EnactObject`
- `EnactBuiltinPartial`
- `EnactBoundObjectMethod`
- `EnactBoundCollectionMethod`

Each constructor records a cell only after the object has been fully initialized and is safe to return to callers. Failure paths that free partially initialized storage do not affect the counters.

Each release function records a cell release only when the reference count reaches zero and the storage is about to be freed. Retain and non-final release operations leave the count unchanged.

## Peak Count

`enact_runtime_cell_allocated()` increments the current count and updates the peak count when the new current count exceeds the previous peak. Final release decrements only the current count.

`enact_runtime_cell_released()` defensively leaves the current count at zero if called when no cells are live. This keeps the plumbing robust for unit-level edge coverage; normal runtime release paths should still be balanced.

## Scope Decisions

Strings, atom payloads, AST nodes, environment entries, superclass links, method entries, attributes, and temporary vectors are deliberately excluded. They are implementation-support allocations and do not have the same user-visible runtime-cell identity as lists, functions, classes, objects, partials, and bound methods.

This means future `cells()` and `maxcells()` will describe ENACT runtime value pressure, not exact `malloc` activity.

## Tests

Unit tests cover:

- reset behavior
- direct allocation/release accounting helpers
- release-at-zero robustness
- list allocation, retain, shared tail release, and cascading final release
- builtin partial allocation, retain, extension, and release
- function, class, object, bound object method, extended bound object method, and bound collection method accounting
- default builtin class installation and environment teardown

No Python golden-output regression tests are added because this slice intentionally has no user-visible language feature.
