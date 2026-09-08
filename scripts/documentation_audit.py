"""Executable documentation consistency checks for the frozen product status."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_FILES = (
    "README.md",
    "docs/IMPLEMENTATION.md",
    "docs/EVALUATION_PLAN.md",
    "docs/EVALUATION_RESULTS.md",
)

REQUIRED_MARKERS = {
    "README.md": (
        "A successful CI evaluation run on 2026-09-08",
        "External Spark target-cluster scalability has not yet been measured.",
        "application-level API-key identities scope",
    ),
    "docs/IMPLEMENTATION.md": (
        "[x] Reproducible local scalability measurements at 100, 1,000, and 10,000 rows",
        "[x] Comparative schema-mapping evaluation against baseline methods, with CI evidence recorded.",
        "[x] Executable objective-feasibility evaluation against explicit fixture-contract labels and a weak baseline, with CI evidence recorded.",
        "[x] Executable bounded planner-to-synthesis reliability/abstention evaluation, with CI evidence recorded.",
        "[x] SHAP smoke evaluation contract and CI smoke execution for optional local explainability.",
        "[ ] External Spark target-cluster scalability validation.",
        "[x] Documentation consistency audit after final feature freeze.",
    ),
    "docs/EVALUATION_RESULTS.md": (
        "GitHub Actions run `34212312393`",
        "External Spark scalability remains unverified",
        "do not establish generalization to real-world heterogeneous HR schemas",
    ),
}

FORBIDDEN_STALE_MARKERS = (
    "empirical execution still outstanding",
    "execute the robustness/scalability protocol",
    "comparative schema/feasibility accuracy remain evaluation items",
    "no empirical accuracy or scalability claim is made until workflow artifacts are inspected",
)


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    texts: dict[str, str] = {}
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required documentation: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[relative] = text
        for marker in REQUIRED_MARKERS.get(relative, ()):
            if marker not in text:
                errors.append(f"{relative}: missing current-status marker: {marker}")
        for marker in FORBIDDEN_STALE_MARKERS:
            if marker in text:
                errors.append(f"{relative}: stale status marker: {marker}")

    implementation = root / "docs/IMPLEMENTATION.md"
    if implementation.is_file():
        text = texts.get("docs/IMPLEMENTATION.md", implementation.read_text(encoding="utf-8"))
        if "## Definition of done" not in text:
            errors.append("docs/IMPLEMENTATION.md: missing Definition of done section")
        if "## Current status" not in text:
            errors.append("docs/IMPLEMENTATION.md: missing Current status section")
        if "[ ] Documentation consistency audit after final feature freeze." in text:
            errors.append("docs/IMPLEMENTATION.md: stale status marker: documentation consistency audit remains unchecked")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = audit(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Documentation consistency audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
