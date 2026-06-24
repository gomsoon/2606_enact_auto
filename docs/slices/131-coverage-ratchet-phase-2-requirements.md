# Slice 131: Coverage Ratchet Phase 2 Requirements

## Goal

Raise the handwritten-source coverage gate again through small regression additions that exercise existing behavior without changing ENACT runtime semantics.

## Functional Requirements

- Add targeted tests for under-covered public execution paths:
  - load-command grammar diagnostics beyond the Phase 1 malformed string cases.
  - TTY `--tokens` line execution for success and recoverable lexical failure.
  - bound collection method value copy and equality helpers.
- Keep the coverage-ratchet runner stdlib-only and compatible with local `make test` and CI.
- Keep coverage reporting scoped to handwritten C sources.
- Raise the default coverage-check thresholds only after measured totals leave margin above the new gate.

## Non-Requirements

- Do not change interpreter language behavior for coverage.
- Do not rewrite the coverage report tool.
- Do not attempt the final PRD `95%` line / `90%` branch target in this slice.
- Do not add timing-sensitive or non-deterministic assertions.

## Regression Expectations

- `tests/test_coverage_ratchet.py` shall report the updated boundary and robustness check counts.
- `make test` shall pass.
- `make coverage-check` shall pass with the ratcheted thresholds.
- README and the compatibility matrix shall document the new threshold values.
