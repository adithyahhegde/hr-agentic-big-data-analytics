"""Evaluate canonical schema mapping against a normalized-name baseline on deterministic fixtures."""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any

from app.services.profiling import profile_dataset
from app.services.schema_engine import CANONICAL_FIELDS, normalize_name

try:
    from scripts.benchmark import SCHEMA_SCENARIOS, SCENARIO_EXPECTATIONS, make_fixture
except ModuleNotFoundError:  # Supports direct execution: `python scripts/schema_mapping_evaluation.py ...`.
    from benchmark import SCHEMA_SCENARIOS, SCENARIO_EXPECTATIONS, make_fixture


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _baseline_mapping(source_name: str) -> str | None:
    """Map only an exact normalized canonical field name; deliberately ignore aliases."""
    normalized = normalize_name(source_name)
    if normalized in CANONICAL_FIELDS:
        return normalized
    return None


def evaluate(*, sizes: tuple[int, ...] = (20, 100), seed: int = 42) -> dict[str, Any]:
    if not sizes:
        raise ValueError("sizes must contain at least one value")
    if any(size < 1 for size in sizes):
        raise ValueError("sizes must contain only positive values")

    records: list[dict[str, Any]] = []
    for size in sizes:
        for scenario, mapping in SCHEMA_SCENARIOS.items():
            with tempfile.TemporaryDirectory(prefix="hr_mapping_eval_") as tmp:
                path = Path(tmp) / "fixture.csv"
                make_fixture(path, size, seed, scenario)
                headers, rows = _rows(path)
                expected_gate = SCENARIO_EXPECTATIONS[scenario]["schema_gate"]
                expected = dict(mapping)

                if expected_gate != "ACCEPTABLE":
                    records.append({"size": size, "scenario": scenario, "schema_gate": expected_gate,
                                    "evaluated_columns": 0, "semantic_exact": 0, "baseline_exact": 0,
                                    "semantic_accuracy": None, "baseline_accuracy": None, "blocked": True})
                    continue

                profile = profile_dataset(headers, rows)
                semantic_exact = 0
                baseline_exact = 0
                for source, target in expected.items():
                    candidate = profile.mappings.get(source)
                    if candidate is not None and candidate.canonical_field == target and candidate.decision != "UNMAPPED":
                        semantic_exact += 1
                    if _baseline_mapping(source) == target:
                        baseline_exact += 1
                evaluated = len(expected)
                records.append({"size": size, "scenario": scenario, "schema_gate": expected_gate,
                                "evaluated_columns": evaluated, "semantic_exact": semantic_exact,
                                "baseline_exact": baseline_exact,
                                "semantic_accuracy": round(semantic_exact / evaluated, 4) if evaluated else None,
                                "baseline_accuracy": round(baseline_exact / evaluated, 4) if evaluated else None,
                                "blocked": False})

    evaluated = [record for record in records if not record["blocked"]]
    semantic_exact = sum(record["semantic_exact"] for record in evaluated)
    baseline_exact = sum(record["baseline_exact"] for record in evaluated)
    columns = sum(record["evaluated_columns"] for record in evaluated)
    return {"seed": seed, "sizes": list(sizes), "scenarios": list(SCHEMA_SCENARIOS), "records": records,
            "aggregate": {"evaluated_columns": columns, "semantic_exact": semantic_exact,
                           "baseline_exact": baseline_exact,
                           "semantic_accuracy": round(semantic_exact / columns, 4) if columns else None,
                           "baseline_accuracy": round(baseline_exact / columns, 4) if columns else None,
                           "semantic_beats_baseline": semantic_exact > baseline_exact if columns else False}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20, 100])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(sizes=tuple(args.sizes), seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
