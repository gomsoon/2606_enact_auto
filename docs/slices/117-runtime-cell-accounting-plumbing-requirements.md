# Slice 117: Runtime Cell Accounting Plumbing Requirements

## Goal

Add internal runtime-cell accounting that records how many ENACT runtime cells are currently alive and the maximum number observed since the last counter reset.

This slice is plumbing for later `cells()` and `maxcells()` utility builtins. It intentionally does not expose a user-visible builtin yet.

## Functional Requirements

- The runtime shall maintain a process-wide current live-cell count.
- The runtime shall maintain a process-wide peak live-cell count.
- The current count shall increase when a tracked runtime cell becomes live.
- The current count shall decrease only when a tracked runtime cell reaches its final release.
- Retain operations shall not change the count.
- Releasing a retained value before its final release shall not change the count.
- The peak count shall update when the current count exceeds the previous peak.
- The peak count shall not decrease when cells are released.

## Tracked Runtime Cells

This slice shall track ref-counted runtime value containers:

- list cons cells
- user function values
- class values
- object values
- builtin partial values
- bound object method values
- bound native collection method values

## Non-Tracked Allocations

This slice shall not track implementation-support allocations such as:

- copied strings or atom payloads
- AST nodes and parser lists
- environment entries
- class superclass link nodes
- class method entries
- object attribute entries
- temporary vectors and traversal buffers

Those allocations are ordinary host implementation details, not ENACT runtime cells for this first accounting layer.

## API Requirements

- A small C API shall expose:
  - reset counters
  - record one cell allocation
  - record one cell final release
  - read current cells
  - read peak cells
- The accounting API shall be usable from unit tests.
- The API shall not require an `EnactEnv` or `EnactSession`.

## Error And Edge Requirements

- Releasing at zero shall keep the current count at zero.
- Reset shall set both current and peak counters to zero.
- Existing runtime behavior, printing, parsing, evaluation, and diagnostics shall not change.

## Non-Goals

- Do not add `cells()` or `maxcells()` builtins in this slice.
- Do not add per-session accounting.
- Do not add memory limits or allocation failure injection.
- Do not change allocation ownership rules.
- Do not make the counters thread-safe.
