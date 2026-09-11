"""Validate provenance fields in an external Spark evidence artifact.

This intentionally validates metadata only; it never inspects or prints employee rows.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    source_revision = data.get("source_revision")
    if not isinstance(source_revision, str) or not SOURCE_REVISION_RE.fullmatch(source_revision):
        raise ValueError("evidence source_revision must be a 40-character lowercase Git commit SHA")
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("evidence runtime provenance is required")
    for key in ("python_version", "platform"):
        if not isinstance(runtime.get(key), str) or not runtime[key].strip():
            raise ValueError(f"evidence runtime.{key} is required")
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("evidence must contain at least one run")
    return {
        "source_revision": source_revision,
        "python_version": runtime["python_version"],
        "platform": runtime["platform"],
        "run_count": len(runs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    summary = validate_evidence(args.path)
    print(
        "External Spark evidence provenance verified: "
        f"revision={summary['source_revision']}, runs={summary['run_count']}"
    )


if __name__ == "__main__":
    main()
