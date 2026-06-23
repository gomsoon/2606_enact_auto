# Slice 127: Release Readiness Docs + Compatibility Matrix Design

Related requirements: [docs/slices/127-release-readiness-docs-compatibility-matrix-requirements.md](/home/tprover/2606_enact_auto/docs/slices/127-release-readiness-docs-compatibility-matrix-requirements.md)

## Overview

Slice 127 is a documentation hardening slice. It does not alter the runtime, grammar, evaluator, or CI workflow. Instead it makes the current implementation understandable from the repository root and records the implemented compatibility surface in one matrix.

## README

The new `README.md` is the user-facing entry point. It documents:

- required local tools.
- `make`, `make test`, `make coverage`, and `make coverage-check`.
- basic stdin and TTY REPL usage.
- top-level command behavior for `load` and `bye`.
- implemented runtime/language surfaces.
- project-default compatibility choices such as strings, `==`, `!=`, unary `-`, and newline termination.
- CI behavior and documentation links.

The README intentionally references the compatibility matrix instead of duplicating every slice-level decision.

## Compatibility Matrix

`docs/compatibility-matrix.md` groups the current behavior into:

- milestone coverage.
- project defaults and compatibility choices.
- deferred items.
- quality gates.

The matrix maps broad product areas to slice ranges and test anchors. It is not meant to replace the detailed slice documents; it is the release-readiness index for readers who need to understand current scope quickly.

## Documentation Regression Test

`tests/test_release_docs.py` is a small stdlib-only test that checks for the presence of key README and compatibility-matrix references:

- build and test commands.
- coverage-check and baseline threshold documentation.
- CI workflow link.
- milestone/status table content.
- project-default and deferred compatibility notes.

`make test` runs this documentation test along with the existing functional, tool, CI workflow, and C unit tests.
