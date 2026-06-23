#!/usr/bin/env python3

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def require(condition: bool, label: str, counts: dict[str, int], kind: str) -> None:
    counts[kind] += 1
    if not condition:
        raise AssertionError(label)


def main() -> int:
    counts = {"boundary": 0, "robustness": 0}

    require(WORKFLOW.exists(), "CI workflow exists", counts, "boundary")
    workflow = WORKFLOW.read_text()
    require("push:" in workflow and "- main" in workflow, "CI runs on pushes to main", counts, "boundary")
    require("pull_request:" in workflow, "CI runs on pull requests", counts, "boundary")
    require("run: make test" in workflow, "CI runs make test", counts, "boundary")
    require("run: make coverage-check" in workflow, "CI runs make coverage-check", counts, "boundary")

    require("contents: read" in workflow, "CI uses read-only contents permission", counts, "robustness")
    require("timeout-minutes:" in workflow, "CI job has a timeout", counts, "robustness")
    require(
        "build-essential" in workflow and "flex" in workflow and "bison" in workflow,
        "CI installs required build dependencies",
        counts,
        "robustness",
    )
    require(
        workflow.find("run: make test") < workflow.find("run: make coverage-check"),
        "normal test gate runs before coverage gate",
        counts,
        "robustness",
    )

    print(
        "CI workflow tests passed "
        f"({counts['boundary']} boundary checks, {counts['robustness']} robustness checks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
