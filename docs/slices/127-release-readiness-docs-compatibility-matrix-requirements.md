# Slice 127: Release Readiness Docs + Compatibility Matrix Requirements

## Goal

Add release-readiness documentation that explains how to build, run, test, and understand the current ENACT compatibility surface.

## Functional Requirements

- Add a top-level `README.md`.
- The README shall document:
  - project purpose.
  - local build and test commands.
  - coverage and coverage-check commands.
  - basic stdin and REPL usage.
  - `load` and `bye` command status.
  - implemented language surface.
  - project-default compatibility choices.
  - CI quality gates.
  - key documentation links.
- Add `docs/compatibility-matrix.md`.
- The compatibility matrix shall document:
  - PRD milestone implementation status.
  - related slice ranges.
  - test anchors.
  - project-default compatibility choices.
  - deferred items.
  - active quality gates and baseline coverage values.
- Add a small stdlib-only documentation regression test so key release-readiness references cannot be removed silently.
- Do not change runtime language behavior.

## Regression Scope

Boundary checks cover:

- README presence.
- compatibility matrix presence.
- documented build/test commands.
- documented coverage gate commands.
- documented CI workflow reference.
- documented compatibility matrix link.
- documented milestone/status table content.

Robustness checks cover:

- README documenting deferred compatibility items.
- compatibility matrix documenting project-default choices.
- compatibility matrix documenting deferred items.
- compatibility matrix documenting baseline coverage thresholds.

## Non-Goals

- Do not rewrite the PRD.
- Do not change the GitHub Actions workflow.
- Do not raise coverage thresholds.
- Do not add runtime features.
- Do not add external documentation tooling.
