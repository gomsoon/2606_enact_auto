# Slice 126: CI Quality Gate Integration Requirements

## Goal

Connect the local quality gates to GitHub Actions so pushes and pull requests automatically run the normal test suite and the handwritten-source coverage baseline gate.

## Functional Requirements

- Add a GitHub Actions workflow under `.github/workflows`.
- The workflow shall run on:
  - pushes to `main`
  - pull requests
- The workflow shall run on an Ubuntu-hosted runner.
- The workflow shall install the build dependencies required by the project:
  - C build toolchain
  - `flex`
  - `bison`
- The workflow shall run the normal test target:
  - `make test`
- The workflow shall run the coverage baseline gate added by Slice 125:
  - `make coverage-check`
- The workflow shall keep repository permissions minimal and read-only unless future CI tasks need more access.
- The workflow shall rely on the existing Makefile targets instead of duplicating build or coverage logic in YAML.

## Regression Scope

Boundary checks cover:

- workflow file presence under `.github/workflows`.
- push and pull-request trigger declarations.
- normal build/test gate invocation.
- coverage baseline gate invocation.

Robustness checks cover:

- CI dependency installation for a fresh Ubuntu runner.
- minimal repository permission declaration.
- bounded workflow runtime through a job timeout.
- normal test gate running before the coverage gate.

## Non-Goals

- Do not add release packaging or artifact upload.
- Do not publish coverage reports to an external service.
- Do not raise the Slice 125 baseline thresholds in this slice.
- Do not add a matrix across operating systems or compiler versions yet.
- Do not add secrets or write permissions.
