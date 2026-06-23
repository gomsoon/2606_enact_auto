# Slice 130: Coverage Ratchet Phase 1 Requirements

## Goal

Start moving the coverage baseline upward in small, reviewable increments. This slice should improve handwritten C source coverage without changing ENACT language semantics.

## Functional Requirements

- Add targeted regression tests for currently under-covered runtime paths.
- Keep tests stdlib-only and compatible with local `make test` and CI.
- Run the new coverage-ratchet tests from `make test`.
- Cover representative paths that are not already well exercised:
  - large `load` file reads that grow the file buffer.
  - escaped filenames in `load` command parsing.
  - escaped string printing for carriage returns.
  - malformed `load` command diagnostics.
- Raise `COVERAGE_MIN_LINES` and `COVERAGE_MIN_BRANCHES` only after measured `make coverage-check` results leave safe margin.

## Non-Requirements

- Do not attempt to reach the final PRD `95%` line / `90%` branch target in this slice.
- Do not rewrite the coverage tool.
- Do not change interpreter runtime behavior solely for coverage.
- Do not add non-deterministic performance or timing checks.

## Regression Expectations

- The new runner shall print boundary and robustness check counts.
- `make test` shall include the runner.
- `make coverage-check` shall pass with the ratcheted thresholds.
- README and the compatibility matrix shall document the new threshold values.
