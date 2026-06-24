#!/usr/bin/env python3

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MATRIX = ROOT / "docs" / "compatibility-matrix.md"
RC_CHECKLIST = ROOT / "docs" / "release-candidate-checklist.md"


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def main() -> int:
    counts = {"boundary": 0, "robustness": 0}

    require(README.exists(), "README exists", counts, "boundary")
    require(MATRIX.exists(), "compatibility matrix exists", counts, "boundary")
    require(RC_CHECKLIST.exists(), "release candidate checklist exists", counts, "boundary")

    readme = README.read_text()
    matrix = MATRIX.read_text()
    rc_checklist = RC_CHECKLIST.read_text()

    for command in ["make", "make test", "make smoke", "make coverage", "make coverage-check", "make rc-check"]:
        require(command in readme, f"README documents {command}", counts, "boundary")

    require(".github/workflows/ci.yml" in readme, "README links CI workflow", counts, "boundary")
    require("docs/compatibility-matrix.md" in readme, "README links compatibility matrix", counts, "boundary")
    require("docs/release-candidate-checklist.md" in readme, "README links release candidate checklist", counts, "boundary")
    require("load" in readme and "bye" in readme, "README documents load and bye", counts, "boundary")
    require("==`" in readme and "!=`" in readme, "README documents comparison defaults", counts, "boundary")
    require("tests/test_error_diagnostics.py" in readme, "README documents diagnostic golden tests", counts, "boundary")
    require("tests/test_coverage_ratchet.py" in readme, "README documents coverage ratchet tests", counts, "boundary")

    require("Milestone Coverage" in matrix, "matrix has milestone section", counts, "boundary")
    require("Project Defaults And Compatibility Choices" in matrix, "matrix has project defaults section", counts, "boundary")
    require("Deferred Items" in matrix, "matrix has deferred section", counts, "boundary")
    require("Quality Gates" in matrix, "matrix has quality gates section", counts, "boundary")

    require("82.0%" in matrix and "74.5%" in matrix, "matrix documents coverage thresholds", counts, "robustness")
    require("95%" in matrix and "90%" in matrix, "matrix documents final PRD coverage target", counts, "robustness")
    require("Full Appendix 2 collection class source compatibility" in matrix, "matrix documents Appendix 2 deferral", counts, "robustness")
    require("Strict historical compatibility mode" in matrix, "matrix documents strict mode deferral", counts, "robustness")
    require("make smoke" in matrix and "Slice 128" in matrix, "matrix documents release smoke target", counts, "robustness")
    require("Error diagnostic golden tests" in matrix and "Slice 129" in matrix, "matrix documents diagnostic golden tests", counts, "robustness")
    require("Coverage ratchet phase 1" in matrix and "Slice 130" in matrix, "matrix documents coverage ratchet", counts, "robustness")
    require("Coverage ratchet phase 2" in matrix and "Slice 131" in matrix, "matrix documents coverage ratchet phase 2", counts, "robustness")
    require("Coverage ratchet phase 3" in matrix and "Slice 132" in matrix, "matrix documents coverage ratchet phase 3", counts, "robustness")
    require("Release candidate checklist" in matrix and "Slice 133" in matrix, "matrix documents release candidate checklist", counts, "robustness")
    require("Release candidate gate target" in matrix and "Slice 134" in matrix, "matrix documents release candidate gate target", counts, "robustness")

    for command in ["make rc-check", "make test", "make smoke", "make coverage-check"]:
        require(command in rc_checklist, f"RC checklist documents {command}", counts, "boundary")
    require("82.0%" in rc_checklist and "74.5%" in rc_checklist, "RC checklist documents coverage thresholds", counts, "robustness")
    require("82.2%" in rc_checklist and "74.8%" in rc_checklist, "RC checklist documents measured coverage", counts, "robustness")
    require("Project-Default Compatibility Choices" in rc_checklist, "RC checklist documents compatibility choices", counts, "robustness")
    require("Deferred Items" in rc_checklist, "RC checklist documents deferred items", counts, "robustness")
    require("Full Appendix 2 collection class source compatibility" in rc_checklist, "RC checklist names Appendix 2 deferral", counts, "robustness")
    require("Strict historical compatibility mode" in rc_checklist, "RC checklist names strict mode deferral", counts, "robustness")

    print(
        "release docs tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
