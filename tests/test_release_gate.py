#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
README = ROOT / "README.md"
MATRIX = ROOT / "docs" / "compatibility-matrix.md"
RC_CHECKLIST = ROOT / "docs" / "release-candidate-checklist.md"


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def main() -> int:
    counts = {"boundary": 0, "robustness": 0}

    require(MAKEFILE.exists(), "Makefile exists", counts, "boundary")
    require(README.exists(), "README exists", counts, "boundary")
    require(MATRIX.exists(), "compatibility matrix exists", counts, "boundary")
    require(RC_CHECKLIST.exists(), "release candidate checklist exists", counts, "boundary")

    makefile = MAKEFILE.read_text()
    readme = README.read_text()
    matrix = MATRIX.read_text()
    rc_checklist = RC_CHECKLIST.read_text()

    require("\nrc-check:" in makefile, "Makefile defines rc-check target", counts, "boundary")
    require("$(MAKE) test" in makefile, "rc-check runs make test", counts, "boundary")
    require("$(MAKE) smoke" in makefile, "rc-check runs make smoke", counts, "boundary")
    require("$(MAKE) coverage-check" in makefile, "rc-check runs make coverage-check", counts, "boundary")
    require("python3 tests/test_release_gate.py" in makefile, "make test runs release gate test", counts, "boundary")
    require("make rc-check" in readme, "README documents make rc-check", counts, "boundary")
    require("Release candidate gate target" in matrix and "Slice 134" in matrix, "matrix documents rc-check target", counts, "boundary")
    require("make rc-check" in rc_checklist, "RC checklist documents make rc-check", counts, "boundary")

    phony_line = next((line for line in makefile.splitlines() if line.startswith(".PHONY:")), "")
    require("rc-check" in phony_line, "rc-check is phony", counts, "robustness")
    require(
        makefile.index("$(MAKE) test") < makefile.index("$(MAKE) smoke")
        < makefile.index("$(MAKE) coverage-check"),
        "rc-check command order is test, smoke, coverage-check",
        counts,
        "robustness",
    )
    require(
        "make test" in rc_checklist and "make smoke" in rc_checklist and "make coverage-check" in rc_checklist,
        "RC checklist expands rc-check into component gates",
        counts,
        "robustness",
    )

    dry_run = subprocess.run(
        ["make", "-n", "rc-check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    dry_output = dry_run.stdout + dry_run.stderr
    require(dry_run.returncode == 0, "make -n rc-check succeeds", counts, "robustness")
    require("make test" in dry_output, "dry-run includes make test", counts, "robustness")
    require("make smoke" in dry_output, "dry-run includes make smoke", counts, "robustness")
    require("make coverage-check" in dry_output, "dry-run includes make coverage-check", counts, "robustness")

    print(
        "release gate tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
