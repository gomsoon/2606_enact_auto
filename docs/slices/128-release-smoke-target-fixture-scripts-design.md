# Slice 128: Release Smoke Target + Fixture Scripts Design

Related requirements: [docs/slices/128-release-smoke-target-fixture-scripts-requirements.md](/home/tprover/2606_enact_auto/docs/slices/128-release-smoke-target-fixture-scripts-requirements.md)

## Overview

Slice 128 adds an executable release smoke layer on top of the existing regression suite. It does not change language semantics. Instead, it verifies that the built command-line interpreter can run realistic script files and report representative failures through the same stdin path documented in the README.

## Fixtures

Fixtures live under `tests/smoke`:

- `functional.en` covers recursive functions, lambdas, closures, tuple-like lists, and `reduce`.
- `object.en` covers classes, methods, object attributes, attribute assignment, and `classes`.
- `collections.en` covers Set/Bag construction, size, dot-method algebra, collection transform, and bound method calls.
- `load_main.en` and `load_defs.en` cover real file loading and caller-session bindings.
- `load_nested_outer.en` and `load_nested_inner.en` cover nested `load` and `bye`.
- malformed/failing fixtures cover missing load files, parse errors, runtime name errors, and loaded-script error propagation.

## Runner

`tests/test_release_smoke.py` is stdlib-only. It runs each fixture by opening the `.en` file and passing it as stdin to `build/enact` with the repository root as the process working directory. That keeps fixture-local `load "tests/smoke/..."` paths stable without adding shell-specific behavior.

Successful cases require:

- return code `0`.
- exact stdout match.
- empty stderr.

Failure cases require:

- non-zero return code.
- expected `ENACT_ERR_*` code in stderr.
- exact stdout for any results printed before the failure.

## Make Targets

`make smoke` builds `build/enact` if needed and runs `tests/test_release_smoke.py`.

`make test` also runs the smoke runner so the CI `make test` quality gate includes the release smoke path.
