# ENACT Auto

ENACT Auto is a test-first C implementation of the ENACT executable specification language, based on the supplied ENACT reference manual (`260614_enact_manual.pdf`) and the project PRD in [docs/enact-prd.md](docs/enact-prd.md).

The current implementation reconstructs a practical ENACT core with a REPL, script execution, file loading, functional programming, object-oriented features, collections, introspection helpers, and CI-backed quality gates.

## Requirements

- C compiler and standard build tools
- `make`
- `flex`
- `bison`
- `python3`
- `gcov` for coverage reporting

On Ubuntu, the CI workflow installs these with:

```sh
sudo apt-get install -y build-essential flex bison
```

## Build And Test

```sh
make
make test
make smoke
make coverage
make coverage-check
make clean
```

`make test` runs:

- functional regression tests in `tests/run_tests.py`
- Python tool/workflow tests
- release smoke fixture tests in `tests/test_release_smoke.py`
- error diagnostic golden tests in `tests/test_error_diagnostics.py`
- coverage ratchet tests in `tests/test_coverage_ratchet.py`
- C unit tests in `tests/unit_tests.c`

`make smoke` runs a small release-readiness fixture suite from `tests/smoke`. It executes the built interpreter through real stdin script files and covers functional, object, collection, `load`, nested `load`, `bye`, and representative failure paths.

`make coverage` reports handwritten C source coverage only. Generated Bison/Flex sources are intentionally excluded.

`make coverage-check` enforces the current baseline gate:

- line coverage: `82.0%`
- branch coverage: `74.5%`

The PRD final hardening target remains higher at line `95%` and branch `90%`; the baseline gate prevents regression while later slices can raise the threshold.

## Run

Build the interpreter:

```sh
make
```

Evaluate a script from standard input:

```sh
printf '1+2.\n' | build/enact
```

Expected output:

```text
3
```

Use the interactive REPL by running:

```sh
build/enact
```

In TTY mode, a top-level newline terminates an expression:

```text
x:=41
x+1
bye
```

Expected printed results before exit:

```text
41
42
```

Load a file from a session or script:

```text
load "examples.en"
```

`load` and `bye` are top-level session commands, not first-class builtins.

## Implemented Surface

The current compatibility target includes:

- integers, booleans, strings, atoms, lists, functions, classes, objects, sets, and bags
- arithmetic, comparison, boolean logic, manual-style conditionals, assignment, sequencing, `where`, and `fix`
- named functions, lambda expressions using `::`, currying, partial application, and whitespace application
- list construction, list printing, list builtins, and higher-order list builtins
- `class`, `new`, `with`, attributes, methods, `self`, `super`, and multiple inheritance linearization
- Set and Bag constructors, collection payloads, collection operations, dot-method syntax, and bound collection methods
- introspection helpers such as `classof`, `attrs`, `supers`, `superiors`, `classes`, `methods`, `OK`, `badAttrs`, `suppliers`, method/callable signature helpers, and type predicates
- utility functions and commands such as `version`, `time`, `ask`, `cells`, `maxcells`, `bye`, and `load`

See [docs/compatibility-matrix.md](docs/compatibility-matrix.md) for the implementation status, related slices, and known deferred items.

## Project-Default Compatibility Choices

Some choices are documented project defaults rather than strict historical ENACT behavior:

- double-quoted literals are immutable strings
- equality uses `==`
- inequality uses `!=`
- unary negation uses `-`
- top-level newlines can terminate REPL/script expressions

A future strict compatibility mode may revisit historical spelling such as `=`, `<>`, `~`, or alternate quoted literal semantics if stronger reference evidence requires it.

## CI

GitHub Actions runs the quality gates on pushes to `main` and on pull requests:

```text
make test
make coverage-check
```

The workflow is defined in [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Documentation

- [Product requirements](docs/enact-prd.md)
- [Compatibility matrix](docs/compatibility-matrix.md)
- [Slice requirements and designs](docs/slices)

The implementation is intentionally slice-driven: each language or hardening increment is documented in `docs/slices` and backed by regression tests.
