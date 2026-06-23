# Slice 126: CI Quality Gate Integration Design

Related requirements: [docs/slices/126-ci-quality-gate-integration-requirements.md](/home/tprover/2606_enact_auto/docs/slices/126-ci-quality-gate-integration-requirements.md)

## Overview

Slice 126 wires the existing local quality workflow into GitHub Actions. Slice 125 introduced `make coverage-check`; this slice makes that gate run automatically for pushes and pull requests.

The CI workflow intentionally delegates project behavior to Makefile targets:

```text
make test
make coverage-check
```

That keeps CI thin and avoids maintaining a second build/test recipe in YAML.

## Workflow

The workflow lives at:

```text
.github/workflows/ci.yml
```

It runs on:

- `push` to `main`
- `pull_request`

The single job uses `ubuntu-latest` and installs:

- `build-essential`
- `flex`
- `bison`

`build-essential` provides the C compiler and `gcov` used by the coverage target. The Makefile still owns all compiler flags, generated parser/lexer steps, functional tests, Python tool tests, C unit tests, and coverage gate thresholds.

## Permissions

The workflow declares:

```yaml
permissions:
  contents: read
```

This is enough for checkout and keeps the CI job from receiving broader repository write access.

## Test Strategy

Local verification still runs the same targets that CI will run:

```text
make test
make coverage-check
```

Since GitHub Actions cannot be fully executed locally in this repository, a small stdlib-only test, `tests/test_ci_workflow.py`, pins the workflow's expected triggers, dependency installation, permission shape, timeout, and Make target order. The referenced local targets must also pass before commit.
