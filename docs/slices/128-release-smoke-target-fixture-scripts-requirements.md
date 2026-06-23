# Slice 128: Release Smoke Target + Fixture Scripts Requirements

## Goal

Add a small release-readiness smoke test target that exercises the built `enact` executable through real stdin script files. The target should complement the broader regression suite by giving maintainers a quick user-facing sanity check before a release.

## Functional Requirements

- Provide `make smoke` as an explicit top-level target.
- Keep `make test` running the smoke checks so CI exercises the same path.
- Store readable fixture scripts under `tests/smoke`.
- Execute fixture scripts through `build/enact` stdin, matching the documented batch/script usage.
- Cover representative success paths for:
  - functional core.
  - object and method behavior.
  - Set/Bag collection behavior.
  - `load "filename"` from real fixture files.
  - nested `load` plus `bye` command handling.
- Cover representative failure paths for:
  - missing load targets.
  - malformed scripts.
  - runtime name failures.
  - errors raised inside loaded scripts.

## Non-Requirements

- Do not replace the full functional regression suite.
- Do not add new runtime, grammar, or evaluator behavior.
- Do not introduce non-stdlib Python dependencies.
- Do not require shell redirection syntax inside the test runner; direct stdin file handles are sufficient.

## Regression Expectations

- The smoke runner prints boundary and robustness check counts.
- The smoke runner compares successful stdout exactly.
- Failure checks must assert a non-zero exit status, the expected error code, and any user-visible stdout emitted before the failure.
