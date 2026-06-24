# Slice 131: Coverage Ratchet Phase 2 Design

Related requirements: [docs/slices/131-coverage-ratchet-phase-2-requirements.md](/home/tprover/2606_enact_auto/docs/slices/131-coverage-ratchet-phase-2-requirements.md)

## Overview

Slice 131 continues the coverage ratchet by adding small tests around existing public behavior and value helpers. No runtime semantics are changed.

The selected targets come from recent `gcov` output:

- `api.c` load-command grammar branches for missing command whitespace, non-string path tokens, and missing terminators.
- `main.c` TTY `--tokens` line execution for both token dumps and lexical diagnostics.
- `value.c` bound collection method value copy and equality branches.

## Runner Updates

`tests/test_coverage_ratchet.py` remains stdlib-only. It still creates fixture files under `build/coverage_ratchet`, and now also uses a small pty helper for interactive token-mode coverage. The TTY checks assert ordered output fragments to avoid depending on terminal echo formatting.

The Phase 2 additions are:

```text
1 boundary check
4 robustness checks
```

The full ratchet runner now reports:

```text
coverage ratchet tests passed (4 boundary checks, 7 robustness checks)
```

## Unit Coverage

`tests/unit_tests.c` adds a value-helper regression for `ENACT_VALUE_BOUND_COLLECTION_METHOD`. It verifies that copying retains the same bound method pointer, equality succeeds for the copied value, and equality is false for an independently allocated bound collection method.

## Coverage Ratchet

After the runner and unit coverage are added, `make coverage-check` reports:

```text
TOTAL lines 4837/5898 (82.0%)  branches 2512/3373 (74.5%)
```

The default thresholds in `Makefile` are raised conservatively to:

```text
COVERAGE_MIN_LINES=81.8
COVERAGE_MIN_BRANCHES=74.2
```

This keeps margin below the measured totals while preventing regressions below the new Phase 2 floor.
