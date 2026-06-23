# Slice 125: Coverage Gate Baseline Core Design

Related requirements: [docs/slices/125-coverage-gate-baseline-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/125-coverage-gate-baseline-core-requirements.md)

## Overview

This slice adds a coverage gate around the existing handwritten-source coverage flow. The project currently reports:

```text
TOTAL lines 4800/5897 (81.4%)  branches 2494/3373 (73.9%)
```

The PRD final hardening targets are higher, at line `95%` and branch `90%`. Because the current implementation is below those targets, this slice starts with a baseline gate that catches regressions without blocking all development. Later hardening slices can raise the defaults as coverage improves.

## Make Targets

`make coverage` stays report-only:

```text
make coverage
```

It still cleans, rebuilds with `--coverage`, runs the full test suite, runs `gcov`, and prints the handwritten-source report.

`make coverage-check` wraps the same flow and passes threshold arguments to the report tool:

```text
make coverage-check
```

The default gate is:

```text
COVERAGE_MIN_LINES=81.0
COVERAGE_MIN_BRANCHES=73.0
```

The values are Make variables, so a stricter local or CI check can override them:

```text
make coverage-check COVERAGE_MIN_LINES=82.0 COVERAGE_MIN_BRANCHES=74.0
```

## Coverage Report Tool

`tools/coverage_report.py` now has three separable responsibilities:

- collect coverage rows from the handwritten `.gcov` file list.
- print the existing human-readable summary.
- optionally check total line and branch percentages against thresholds.

The CLI accepts:

```text
--min-lines PERCENT
--min-branches PERCENT
```

Each percentage must be between `0` and `100`, inclusive. Invalid threshold syntax is rejected by argument parsing. Missing `.gcov` files keep returning status `2`, matching the existing “coverage input missing” failure mode.

## Tests

A small stdlib-only Python test, `tests/test_coverage_report.py`, exercises the coverage tool without requiring real build artifacts. It creates a temporary `.gcov` fixture and verifies:

- line and branch parsing.
- aggregation.
- missing input handling.
- percentage boundary validation.
- pass/fail threshold behavior.

The normal `make test` target runs this tool test between the functional runner and the C unit tests.
