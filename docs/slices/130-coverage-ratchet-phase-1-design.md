# Slice 130: Coverage Ratchet Phase 1 Design

Related requirements: [docs/slices/130-coverage-ratchet-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/130-coverage-ratchet-phase-1-requirements.md)

## Overview

Slice 130 is a hardening slice focused on small coverage gains. It adds targeted tests around existing public behavior rather than changing the runtime.

The initial targets are paths visible in recent `gcov` output:

- `api.c` load-file buffer growth.
- `api.c` load-command string escape decoding.
- `api.c` malformed load-command string diagnostics.
- `main.c` string value printing for carriage returns.

## Runner

`tests/test_coverage_ratchet.py` is stdlib-only. It creates temporary fixture files under `build/coverage_ratchet` and then runs `build/enact` with stdin source strings.

The runner uses real `load "filename"` commands instead of direct API calls so the coverage improvement still follows the user-facing script path.

## Coverage Ratchet

After the runner is added, `make coverage-check` is used to measure the new totals. The first measured totals for this slice are:

```text
TOTAL lines 4830/5897 (81.9%)  branches 2505/3373 (74.3%)
```

The default thresholds in `Makefile` are raised conservatively to:

```text
COVERAGE_MIN_LINES=81.5
COVERAGE_MIN_BRANCHES=74.0
```

This keeps the gate conservative while still preventing future regressions below the new floor.
