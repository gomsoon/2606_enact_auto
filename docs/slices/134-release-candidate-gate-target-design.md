# Slice 134: Release Candidate Gate Target Design

Related requirements: [docs/slices/134-release-candidate-gate-target-requirements.md](/home/tprover/2606_enact_auto/docs/slices/134-release-candidate-gate-target-requirements.md)

## Overview

Slice 134 is a release-hardening slice. It adds no ENACT language behavior. The purpose is to provide a single command that runs the release-candidate gates documented in Slice 133.

The new command is:

```text
make rc-check
```

## Makefile Integration

The `rc-check` target is a phony target that delegates to the existing component targets:

```text
$(MAKE) test
$(MAKE) smoke
$(MAKE) coverage-check
```

Using `$(MAKE)` preserves recursive make behavior and any caller-selected make binary. The target intentionally keeps `test`, `smoke`, and `coverage-check` as separate commands so each gate remains independently usable and independently visible in logs.

## Documentation Integration

README lists `make rc-check` beside the other build and quality commands and describes it as the release-candidate gate.

The compatibility matrix records Slice 134 as the milestone that introduced the gate target.

The release-candidate checklist now tells release reviewers to run `make rc-check`, while still listing the component gates that it expands to.

## Regression

`tests/test_release_gate.py` checks the Makefile and release docs without running the full release-candidate gate recursively. It verifies:

- the `rc-check` target exists.
- the target runs `test`, `smoke`, and `coverage-check` in order.
- the target is phony.
- `make test` includes the release-gate regression test.
- `make -n rc-check` exposes the component commands.
- README, the compatibility matrix, and the release-candidate checklist mention the gate.

`tests/test_release_docs.py` keeps the broader release documentation contract aligned with the new gate.
