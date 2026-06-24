# Slice 133: Release Candidate Checklist + Final Audit Docs Requirements

## Goal

Create a concise release-candidate checklist that ties together the current build, test, coverage, compatibility, and deferred-work status.

## Functional Requirements

- Add a top-level release-candidate checklist document under `docs/`.
- Document the required local release gates:
  - `make test`
  - `make smoke`
  - `make coverage-check`
- Document the current coverage thresholds and most recent measured totals.
- Summarize the implemented compatibility surface at release-candidate level.
- Summarize project-default compatibility choices.
- Summarize known deferred items.
- Link the checklist from README and the compatibility matrix.
- Extend release-doc regression tests so the checklist does not drift silently.

## Non-Requirements

- Do not add interpreter runtime behavior.
- Do not raise coverage thresholds in this slice.
- Do not change smoke fixtures or diagnostic golden cases.
- Do not tag or publish a release candidate.

## Regression Expectations

- `tests/test_release_docs.py` shall verify the checklist exists and contains required commands, coverage values, compatibility choices, and deferred items.
- `make test` shall pass.
- `make coverage-check` shall pass with the unchanged Slice 132 coverage gate.
