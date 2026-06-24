# Slice 132: Coverage Ratchet Phase 3 Design

Related requirements: [docs/slices/132-coverage-ratchet-phase-3-requirements.md](/home/tprover/2606_enact_auto/docs/slices/132-coverage-ratchet-phase-3-requirements.md)

## Overview

Slice 132 continues the coverage ratchet with another narrow set of regression additions. It does not change language behavior.

The selected targets come from recent `gcov` output:

- `main.c` stdin read-all buffer growth.
- `main.c` TTY line-reader buffer growth.
- `scan.c` token-name coverage for `TOK_OR`.
- `value.c` bound collection method null and out-of-range accessor branches.

## Runner Updates

`tests/test_coverage_ratchet.py` now adds:

```text
3 boundary checks
0 robustness checks
```

The new boundary checks cover:

- a large stdin script that forces the non-TTY input reader to grow.
- a token dump for `true or false.` so `TOK_OR` is printed.
- a long TTY comment line followed by an expression so the TTY line reader grows and still evaluates the next line.

The full ratchet runner now reports:

```text
coverage ratchet tests passed (7 boundary checks, 7 robustness checks)
```

## Unit Coverage

`tests/unit_tests.c` adds bound collection method helper checks for null retain/release, null accessors, null argument lookup, and zero-argument out-of-range lookup. These are edge-path checks for existing helper semantics.

## Coverage Ratchet

After the runner and unit additions, `make coverage-check` reports:

```text
TOTAL lines 4850/5902 (82.2%)  branches 2523/3373 (74.8%)
```

The default thresholds in `Makefile` are raised conservatively to:

```text
COVERAGE_MIN_LINES=82.0
COVERAGE_MIN_BRANCHES=74.5
```

This keeps a small margin under the measured totals while continuing the release-hardening ratchet.
