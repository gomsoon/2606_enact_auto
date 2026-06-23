#!/usr/bin/env python3

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MATRIX = ROOT / "docs" / "compatibility-matrix.md"


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def main() -> int:
    counts = {"boundary": 0, "robustness": 0}

    require(README.exists(), "README exists", counts, "boundary")
    require(MATRIX.exists(), "compatibility matrix exists", counts, "boundary")

    readme = README.read_text()
    matrix = MATRIX.read_text()

    for command in ["make", "make test", "make coverage", "make coverage-check"]:
        require(command in readme, f"README documents {command}", counts, "boundary")

    require(".github/workflows/ci.yml" in readme, "README links CI workflow", counts, "boundary")
    require("docs/compatibility-matrix.md" in readme, "README links compatibility matrix", counts, "boundary")
    require("load" in readme and "bye" in readme, "README documents load and bye", counts, "boundary")
    require("==`" in readme and "!=`" in readme, "README documents comparison defaults", counts, "boundary")

    require("Milestone Coverage" in matrix, "matrix has milestone section", counts, "boundary")
    require("Project Defaults And Compatibility Choices" in matrix, "matrix has project defaults section", counts, "boundary")
    require("Deferred Items" in matrix, "matrix has deferred section", counts, "boundary")
    require("Quality Gates" in matrix, "matrix has quality gates section", counts, "boundary")

    require("81.0%" in matrix and "73.0%" in matrix, "matrix documents coverage thresholds", counts, "robustness")
    require("95%" in matrix and "90%" in matrix, "matrix documents final PRD coverage target", counts, "robustness")
    require("Full Appendix 2 collection class source compatibility" in matrix, "matrix documents Appendix 2 deferral", counts, "robustness")
    require("Strict historical compatibility mode" in matrix, "matrix documents strict mode deferral", counts, "robustness")

    print(
        "release docs tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
