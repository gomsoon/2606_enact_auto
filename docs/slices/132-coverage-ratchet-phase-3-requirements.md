# Slice 132: Coverage Ratchet Phase 3 Requirements

## Goal

Raise the handwritten-source coverage gate one more small step while keeping the changes limited to regression coverage and release documentation.

## Functional Requirements

- Add targeted tests for under-covered execution paths:
  - large stdin script input that grows the main input buffer.
  - token dumping for an operator name that was not previously covered.
  - long TTY line input that grows the line reader.
  - bound collection method null and out-of-range accessors.
- Keep all new runner behavior stdlib-only and deterministic.
- Preserve current ENACT runtime semantics.
- Raise the default coverage-check thresholds only after measured totals leave margin above the new gate.

## Non-Requirements

- Do not rewrite the coverage tool.
- Do not change interpreter behavior for coverage.
- Do not attempt the final PRD `95%` line / `90%` branch target in this slice.
- Do not add broad refactors or new language features.

## Regression Expectations

- `tests/test_coverage_ratchet.py` shall report the updated boundary and robustness counts.
- `make test` shall pass.
- `make coverage-check` shall pass with the ratcheted thresholds.
- README and the compatibility matrix shall document the new thresholds and measured totals.
