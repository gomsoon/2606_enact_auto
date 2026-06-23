# Slice 125: Coverage Gate Baseline Core Requirements

## Goal

Add a baseline coverage gate for handwritten source coverage so regressions fail explicitly while preserving the existing report-only `make coverage` workflow.

## Functional Requirements

- Coverage reporting shall continue to include only handwritten C sources.
- Generated parser and lexer sources shall remain excluded from the handwritten source totals.
- `make coverage` shall keep its existing report-only behavior.
- A new `make coverage-check` target shall run the same coverage flow and fail when totals fall below configured baseline thresholds.
- Baseline thresholds shall be configurable from Make variables:
  - `COVERAGE_MIN_LINES`
  - `COVERAGE_MIN_BRANCHES`
- The default baseline shall be set below the current measured totals:
  - line coverage minimum: `81.0%`
  - branch coverage minimum: `73.0%`
- The PRD targets, line `95%` and branch `90%`, shall remain documented as final hardening goals rather than this slice's immediate gate.
- The coverage report tool shall accept threshold options:
  - `--min-lines`
  - `--min-branches`
- Threshold values shall be percentages in the inclusive range `0` through `100`.
- A threshold failure shall return a non-zero process status and print a clear diagnostic.

## Regression Scope

Boundary checks cover:

- parsing gcov line and branch counters.
- aggregating a bounded handwritten-source coverage file list.
- zero-total percentage behavior.
- threshold values at `0` and `100`.
- passing the default baseline gate.

Robustness checks cover:

- missing gcov input.
- rejecting negative threshold percentages.
- rejecting threshold percentages greater than `100`.
- rejecting non-numeric threshold percentages.
- failing a line threshold that exceeds the measured total.
- failing a branch threshold that exceeds the measured total.

## Non-Goals

- Do not raise the project to the PRD final `95%` line / `90%` branch targets in this slice.
- Do not include generated Bison/Flex sources in handwritten coverage totals.
- Do not add external Python test dependencies.
- Do not change runtime language behavior.
