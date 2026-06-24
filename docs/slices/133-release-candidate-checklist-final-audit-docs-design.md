# Slice 133: Release Candidate Checklist + Final Audit Docs Design

Related requirements: [docs/slices/133-release-candidate-checklist-final-audit-docs-requirements.md](/home/tprover/2606_enact_auto/docs/slices/133-release-candidate-checklist-final-audit-docs-requirements.md)

## Overview

Slice 133 is a release-hardening documentation slice. It adds no runtime behavior. The purpose is to make the current release-candidate state easy to audit before tagging or publishing.

The new top-level document is:

```text
docs/release-candidate-checklist.md
```

## Checklist Structure

The checklist records:

- required gate commands: `make test`, `make smoke`, and `make coverage-check`.
- current coverage thresholds: `82.0%` line and `74.5%` branch.
- recent measured totals: `82.2%` line and `74.8%` branch.
- the implemented release-candidate surface.
- project-default compatibility choices such as `==`, `!=`, unary `-`, immutable double-quoted strings, and newline terminators.
- deferred items such as strict historical compatibility mode, Appendix 2 source compatibility, rich strings, tooling, performance tuning, and the PRD final coverage target.

## Documentation Integration

README links the checklist from both the implemented-surface paragraph and the documentation list.

The compatibility matrix gains a Slice 133 milestone row so the checklist is visible beside the other release hardening artifacts.

## Regression

`tests/test_release_docs.py` is extended to verify that:

- the checklist exists.
- README links it.
- the compatibility matrix records Slice 133.
- the checklist includes the required gate commands.
- the checklist includes current coverage thresholds and measured totals.
- the checklist includes compatibility choices and deferred items.

This keeps the final audit document from drifting when future slices update release gates, coverage values, or compatibility status.
