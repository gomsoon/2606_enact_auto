# Slice 134: Release Candidate Gate Target Requirements

## Goal

Turn the Slice 133 release-candidate checklist into a single local gate command that can be run before tagging or publishing a release candidate.

## Functional Requirements

- Add a top-level `make rc-check` target.
- `make rc-check` shall run these component gates in order:
  - `make test`
  - `make smoke`
  - `make coverage-check`
- Keep the component gates independently runnable.
- Include the release-candidate gate test in `make test`.
- Document `make rc-check` in README, the compatibility matrix, and the release-candidate checklist.
- Extend release documentation regression checks so the new gate remains visible.

## Non-Requirements

- Do not change interpreter runtime behavior.
- Do not change smoke fixtures.
- Do not change CI workflow behavior in this slice.
- Do not raise coverage thresholds.
- Do not tag or publish a release candidate.

## Regression Expectations

- `tests/test_release_gate.py` shall verify the Makefile target, command order, phony declaration, docs references, and dry-run visibility.
- `tests/test_release_docs.py` shall verify the release documents mention the Slice 134 gate.
- `make test` shall pass.
- `make smoke` shall pass.
- `make coverage-check` shall pass with the unchanged coverage gate.
